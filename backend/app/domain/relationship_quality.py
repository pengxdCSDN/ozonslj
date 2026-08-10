from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RelationshipFinding:
    row_index: int
    rule_code: str
    message: str
    severity: str = "error"


def check_relationship_and_time(
    rows: list[dict[str, object]], *, parent_ids: set[str], id_field: str = "id",
    parent_field: str = "parent_id", time_field: str = "observed_at"
) -> list[RelationshipFinding]:
    findings: list[RelationshipFinding] = []
    seen: set[str] = set()
    previous: datetime | None = None
    for index, row in enumerate(rows, start=1):
        row_id = str(row.get(id_field, ""))
        parent_id = str(row.get(parent_field, ""))
        if parent_id and parent_id not in parent_ids:
            findings.append(RelationshipFinding(index, "DQ-004-ORPHAN", "关联父记录不存在"))
        if row_id and row_id in seen:
            findings.append(RelationshipFinding(index, "DQ-004-DUPLICATE", "事实标识重复"))
        if row_id:
            seen.add(row_id)
        raw_time = row.get(time_field)
        if isinstance(raw_time, datetime):
            if previous and raw_time < previous:
                findings.append(RelationshipFinding(index, "DQ-004-TIME-BACKWARD", "时间顺序倒退"))
            previous = raw_time
    return findings
