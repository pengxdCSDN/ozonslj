from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReadbackField:
    field: str
    expected: str | None
    actual: str | None
    matched: bool


@dataclass(frozen=True, slots=True)
class ReadbackVerification:
    matched: bool
    fields: list[ReadbackField]
    message: str


def verify_readback(
    *, expected: dict[str, object], actual: dict[str, object]
) -> ReadbackVerification:
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
