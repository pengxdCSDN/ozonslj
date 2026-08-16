"""轻量级可观测性组件。

首期不引入 Prometheus 客户端或外部日志平台，避免增加云服务器内存和部署依赖。
指标只保存进程内的聚合计数，不保存 URL 查询参数、请求正文、凭据、客户标识或模型响应。
生产环境通过内部 `/metrics` 读取文本格式指标，发布验收脚本读取健康端点和该指标出口。
"""

from __future__ import annotations

import shutil
import threading
import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Final

_BUCKETS: Final[tuple[float, ...]] = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    """宿主机资源快照；读取失败时返回 None，不影响业务请求。"""

    memory_bytes: int | None
    swap_bytes: int | None
    disk_used_ratio: float | None


class MetricsRegistry:
    """进程内聚合指标注册表，标签值必须来自受控枚举，禁止接收用户输入。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = defaultdict(int)
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], list[int]] = defaultdict(
            lambda: [0] * (len(_BUCKETS) + 1)
        )

    def inc(self, name: str, *, labels: dict[str, str] | None = None, value: int = 1) -> None:
        key = (name, _labels(labels))
        with self._lock:
            self._counters[key] += value

    def set_gauge(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        key = (name, _labels(labels))
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        key = (name, _labels(labels))
        with self._lock:
            buckets = self._histograms[key]
            for index, boundary in enumerate(_BUCKETS):
                if value <= boundary:
                    buckets[index] += 1
            buckets[-1] += 1

    def render(self) -> str:
        """渲染 Prometheus 文本格式；输出只包含聚合数据。"""
        with self._lock:
            counters = list(self._counters.items())
            gauges = list(self._gauges.items())
            histograms = list(self._histograms.items())
        lines: list[str] = []
        for (name, labels), counter_value in sorted(counters):
            lines.append(f"{name}{_format_labels(labels)} {counter_value}")
        for (name, labels), gauge_value in sorted(gauges):
            lines.append(f"{name}{_format_labels(labels)} {gauge_value:g}")
        for (name, labels), buckets in sorted(histograms):
            running = 0
            for index, boundary in enumerate(_BUCKETS):
                running += buckets[index]
                bucket_labels = dict(labels)
                bucket_labels["le"] = str(boundary)
                lines.append(f"{name}_bucket{_format_labels(_labels(bucket_labels))} {running}")
            bucket_labels = dict(labels)
            bucket_labels["le"] = "+Inf"
            lines.append(f"{name}_bucket{_format_labels(_labels(bucket_labels))} {buckets[-1]}")
            lines.append(f"{name}_count{_format_labels(labels)} {buckets[-1]}")
        return "\n".join(lines) + ("\n" if lines else "")


METRICS = MetricsRegistry()


def _labels(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, value) for key, value in (labels or {}).items()))


def _format_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    escaped = (
        f'{key}="{value.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        for key, value in labels
    )
    return "{" + ",".join(escaped) + "}"


def record_model_call(*, model_kind: str, provider: str, duration_seconds: float, success: bool,
                      status: str = "ok") -> None:
    """记录模型调用耗时和结果；provider/model_kind 由服务端配置传入，不接受请求原文。"""
    labels = {"model_kind": model_kind, "provider": provider, "status": status}
    METRICS.inc("ozonslj_model_calls_total", labels=labels)
    if not success:
        METRICS.inc("ozonslj_model_errors_total", labels=labels)
    METRICS.observe(
        "ozonslj_model_call_duration_seconds",
        max(0.0, duration_seconds),
        labels={"model_kind": model_kind, "provider": provider},
    )


@contextmanager
def model_call_timer(*, model_kind: str, provider: str) -> Iterator[None]:
    """为模型适配器提供统一计时；异常分类由调用方作为 status 补充。"""
    started = time.perf_counter()
    try:
        yield
    except Exception:
        record_model_call(
            model_kind=model_kind, provider=provider,
            duration_seconds=time.perf_counter() - started, success=False, status="error",
        )
        raise
    else:
        record_model_call(
            model_kind=model_kind, provider=provider,
            duration_seconds=time.perf_counter() - started, success=True,
        )


def collect_resource_snapshot(*, path: str = "/") -> ResourceSnapshot:
    """读取 Linux 容器可见资源；Windows/测试环境安全返回可用子集。"""
    memory_bytes = _read_meminfo("MemAvailable")
    swap_bytes = _read_meminfo("SwapFree")
    try:
        usage = shutil.disk_usage(path)
        disk_ratio = (usage.used / usage.total) if usage.total else None
    except OSError:
        disk_ratio = None
    return ResourceSnapshot(memory_bytes, swap_bytes, disk_ratio)


def update_resource_metrics() -> ResourceSnapshot:
    snapshot = collect_resource_snapshot()
    if snapshot.memory_bytes is not None:
        METRICS.set_gauge("ozonslj_memory_available_bytes", snapshot.memory_bytes)
    if snapshot.swap_bytes is not None:
        METRICS.set_gauge("ozonslj_swap_free_bytes", snapshot.swap_bytes)
    if snapshot.disk_used_ratio is not None:
        METRICS.set_gauge("ozonslj_disk_used_ratio", snapshot.disk_used_ratio)
    return snapshot


def _read_meminfo(field: str) -> int | None:
    try:
        with open("/proc/meminfo", encoding="ascii") as meminfo:
            for line in meminfo:
                if line.startswith(field + ":"):
                    value = line.split()[1]
                    return int(value) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None
