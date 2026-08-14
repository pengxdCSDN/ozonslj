from dataclasses import dataclass
from typing import Literal, Protocol

AlertSeverity = Literal["warning", "error"]


@dataclass(frozen=True, slots=True)
class ParserChange:
    field_name: str
    old_value: str | None
    new_value: str | None
    severity: AlertSeverity
    message: str


class ParserAlertGateway(Protocol):
    async def create_alerts(
        self, *, workspace_id: str, url: str, changes: list[ParserChange]
    ) -> list[ParserChange]: ...

    async def list_alerts(
        self, *, workspace_id: str, limit: int = 50
    ) -> list[ParserChange]: ...


def detect_parser_changes(
    previous: dict[str, str | None],
    current: dict[str, str | None],
) -> list[ParserChange]:
    """比较规范化字段，缺失关键字段时生成错误告警而不是静默覆盖。"""
    changes: list[ParserChange] = []
    for field_name in sorted(set(previous) | set(current)):
        old_value = previous.get(field_name)
        new_value = current.get(field_name)
        if old_value == new_value:
            continue
        severity: AlertSeverity = "error" if new_value is None else "warning"
        changes.append(
            ParserChange(
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                severity=severity,
                message=(
                    f"字段 {field_name} 从页面中消失"
                    if new_value is None
                    else f"字段 {field_name} 解析结果发生变化"
                ),
            )
        )
    return changes
