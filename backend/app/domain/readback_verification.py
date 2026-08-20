"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReadbackField:
    """说明 ReadbackField 的职责、状态边界和对外协作关系。"""
    field: str
    expected: str | None
    actual: str | None
    matched: bool


@dataclass(frozen=True, slots=True)
class ReadbackVerification:
    """说明 ReadbackVerification 的职责、状态边界和对外协作关系。"""
    matched: bool
    fields: list[ReadbackField]
    message: str


def verify_readback(
    *, expected: dict[str, object], actual: dict[str, object]
) -> ReadbackVerification:
    """执行 verify_readback 的业务流程并返回该流程的结果。"""
    names = list(dict.fromkeys([*expected, *actual]))
    fields = [
        ReadbackField(
            name,
            None if expected.get(name) is None else str(expected.get(name)),
            None if actual.get(name) is None else str(actual.get(name)),
            expected.get(name) == actual.get(name),
        )
        for name in names
    ]
    matched = bool(fields) and all(field.matched for field in fields)
    return ReadbackVerification(matched, fields, "回读核对通过" if matched else "回读核对发现差异")
