import hashlib
import json


def assumption_version(assumptions: dict[str, object]) -> str:
    """按稳定 JSON 计算假设版本；版本只用于回溯，不替代业务数据校验。"""
    if not assumptions:
        raise ValueError("测算假设不能为空")
    canonical = json.dumps(assumptions, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
