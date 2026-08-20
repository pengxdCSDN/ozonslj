"""说明本模块的职责、边界和主要协作对象。"""

import hashlib
import json


def assumption_version(assumptions: dict[str, object]) -> str:
    """按稳定 JSON 计算假设版本；版本只用于回溯，不替代业务数据校验。

Args:
    assumptions: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if not assumptions:
        raise ValueError("测算假设不能为空")
    canonical = json.dumps(assumptions, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
