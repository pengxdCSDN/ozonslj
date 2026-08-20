"""模型供应商凭据文件存储。

供应商 API Key 可以由管理员在受保护的配置页面提交，但不能进入 PostgreSQL、
浏览器存储、任务载荷或日志。本适配器只负责在部署目录的受限可写卷中原子写入
和读取凭据；数据库保存的只是 provider_id 引用与末尾掩码。
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from contextlib import suppress
from pathlib import Path


class ModelCredentialStore:
    """按供应商 ID 保存 API Key，拒绝目录穿越并尽量收紧文件权限。"""

    _provider_id_pattern = re.compile(r"^[0-9a-fA-F-]{16,80}$")

    def __init__(self, root: Path) -> None:
        """初始化对象依赖和运行时状态。"""
        self._root = root

    async def put(self, provider_id: str, api_key: str) -> str:
        """执行 put 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._put, provider_id, api_key)

    async def get(self, provider_id: str) -> str | None:
        """执行 get 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._get, provider_id)

    async def exists(self, provider_id: str) -> bool:
        """执行 exists 的业务流程并返回该流程的结果。"""
        return await asyncio.to_thread(self._get, provider_id) is not None

    def _path(self, provider_id: str) -> Path:
        """执行内部步骤 _path，供同一模块的公开流程复用。"""
        if not self._provider_id_pattern.fullmatch(provider_id):
            raise ValueError("供应商 ID 格式无效")
        return self._root / f"{provider_id}.key"

    def _put(self, provider_id: str, api_key: str) -> str:
        """执行内部步骤 _put，供同一模块的公开流程复用。"""
        value = api_key.strip()
        if not value:
            raise ValueError("API Key 不能为空")
        path = self._path(provider_id)
        self._root.mkdir(parents=True, exist_ok=True)
        with suppress(OSError):
            os.chmod(self._root, 0o700)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{provider_id}.", dir=self._root)
        temporary_path = Path(temporary_name)
        try:
            with suppress(OSError):
                os.chmod(temporary_path, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            with suppress(OSError):
                os.chmod(path, 0o600)
        finally:
            temporary_path.unlink(missing_ok=True)
        return f"file:{path.name}"

    def _get(self, provider_id: str) -> str | None:
        """执行内部步骤 _get，供同一模块的公开流程复用。"""
        path = self._path(provider_id)
        try:
            value = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        except OSError as error:
            raise RuntimeError("模型供应商凭据文件不可读") from error
        return value or None
