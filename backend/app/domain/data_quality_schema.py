from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QualitySchemaFinding:
    row_index: int
    field: str
    rule_code: str
    value: str | None
    message: str
    severity: str


@dataclass(frozen=True, slots=True)
class QualitySchemaResult:
    valid: bool
    checked_rows: int
    findings: list[QualitySchemaFinding]
    isolated_required: bool


def check_required_and_enums(
    rows: list[dict[str, object]],
    *,
    required_fields: list[str],
    enum_fields: dict[str, list[str]],
) -> QualitySchemaResult:
    if any(not field.strip() for field in required_fields) or any(
        not field.strip() or not values for field, values in enum_fields.items()
    ):
        raise ValueError("质量规则配置无效")
    findings: list[QualitySchemaFinding] = []
    for index, row in enumerate(rows, start=1):
        for field in required_fields:
            value = row.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                findings.append(QualitySchemaFinding(
                    index, field, "DQ-003", None, "必填字段缺失", "error"
                ))
        for field, allowed in enum_fields.items():
            value = row.get(field)
            if value is not None and str(value) not in allowed:
                findings.append(QualitySchemaFinding(
                    index, field, "DQ-003", str(value), "未知枚举值", "error"
                ))
    return QualitySchemaResult(not findings, len(rows), findings, bool(findings))
