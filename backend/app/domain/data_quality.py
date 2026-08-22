"""说明本模块的职责、边界和主要协作对象。"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

QualitySeverity = Literal["warning", "error"]
QualityFindingStatus = Literal["open", "accepted", "resolved", "ignored"]
QualityFindingSource = Literal["derived_quality"]
QualityCheckJobStatus = Literal["queued", "running", "succeeded", "failed"]


class QualityCheckJob(BaseModel):
    """由事实变化事件创建的可恢复质量检查任务。"""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    status: QualityCheckJobStatus
    data_version: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    parent_run_id: str = Field(min_length=1)
    attempt_count: int = Field(ge=0)
    created_at: datetime


class QualityCheckJobGateway(Protocol):
    """质量检查任务事实端口；重复幂等键必须复用已有任务。"""

    async def schedule_quality_check(
        self, *, workspace_id: str, data_version: str, idempotency_key: str, parent_run_id: str
    ) -> bool:
        """创建或复用质量检查任务，返回是否新建。"""

    async def claim_quality_check(
        self, *, job_id: str, worker_id: str, lease_seconds: int
    ) -> QualityCheckJob | None:
        """领取质量任务；租约有效时同一任务只能被一个 Worker 执行。"""

    async def complete_quality_check(self, *, job_id: str, worker_id: str) -> bool:
        """质量检查成功后关闭任务并释放租约。"""

    async def fail_quality_check(
        self, *, job_id: str, worker_id: str, retry_delay_seconds: int
    ) -> bool:
        """失败任务按有限重试策略重新排队或标记失败。"""

    async def list_dispatchable_quality_checks(self, *, limit: int) -> list[QualityCheckJob]:
        """读取到期排队任务，供 Scheduler 重建 Redis 投递。"""


class QualityFindingRecord(BaseModel):
    """可持久化的质量隔离记录；业务事实表不引用该记录作为替代值。"""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    rule_code: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    severity: QualitySeverity
    message: str = Field(min_length=1)
    status: QualityFindingStatus = "open"
    source: QualityFindingSource = "derived_quality"
    created_at: datetime


class QualityFinding(BaseModel):
    """单条数据质量问题；只保存字段和规则标识，不保存原始敏感值。"""

    model_config = ConfigDict(frozen=True)

    rule_code: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    severity: QualitySeverity
    message: str = Field(min_length=1)
    status: QualityFindingStatus = "open"
    source: QualityFindingSource = "derived_quality"


class QualityFindingGateway(Protocol):
    """数据质量隔离区端口；基础设施层负责组织/工作区边界和事务。"""

    async def list_findings(
        self, *, workspace_id: str, status: QualityFindingStatus | None, limit: int
    ) -> list[QualityFindingRecord]:
        """执行 list_findings 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def create_findings(
        self, *, workspace_id: str, findings: list[QualityFinding]
    ) -> list[QualityFindingRecord]:
        """执行 create_findings 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    findings: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def update_status(
        self, *, finding_id: str, status: QualityFindingStatus
    ) -> QualityFindingRecord | None:
        """执行 update_status 的业务流程并返回该流程的结果。

Args:
    finding_id: 参数语义、输入边界和安全约束。
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def check_required_and_enum(
    record: dict[str, object],
    *,
    required_fields: tuple[str, ...],
    enum_fields: dict[str, frozenset[str]],
) -> list[QualityFinding]:
    """检查必填字段和枚举值，空值不参与业务分析，交由质量中心处理。

Args:
    record: 参数语义、输入边界和安全约束。
    required_fields: 参数语义、输入边界和安全约束。
    enum_fields: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    findings: list[QualityFinding] = []
    for field_name in required_fields:
        value = record.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            findings.append(
                QualityFinding(
                    rule_code="DQ-003-MISSING",
                    field_name=field_name,
                    severity="error",
                    message="必填字段缺失",
                )
            )
    for field_name, allowed in enum_fields.items():
        value = record.get(field_name)
        if value is not None and str(value) not in allowed:
            findings.append(
                QualityFinding(
                    rule_code="DQ-003-ENUM",
                    field_name=field_name,
                    severity="error",
                    message="枚举值不在允许范围内",
                )
            )
    return findings


def check_relationship_and_time(
    record: dict[str, object],
    *,
    required_relationships: tuple[tuple[str, str], ...] = (),
    time_order: tuple[str, str] | None = None,
) -> list[QualityFinding]:
    """检查关联键是否成对存在，以及结束时间是否早于开始时间。

Args:
    record: 参数语义、输入边界和安全约束。
    required_relationships: 参数语义、输入边界和安全约束。
    time_order: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    findings: list[QualityFinding] = []
    for parent_field, child_field in required_relationships:
        parent = record.get(parent_field)
        child = record.get(child_field)
        if (parent is None) != (child is None):
            findings.append(
                QualityFinding(
                    rule_code="DQ-004-ORPHAN",
                    field_name=child_field,
                    severity="error",
                    message="关联字段不完整，记录进入质量隔离",
                )
            )
    if time_order is not None:
        start_field, end_field = time_order
        start = record.get(start_field)
        end = record.get(end_field)
        if isinstance(start, datetime) and isinstance(end, datetime) and end < start:
            findings.append(
                QualityFinding(
                    rule_code="DQ-004-TIME",
                    field_name=end_field,
                    severity="error",
                    message="时间顺序倒退，记录进入质量隔离",
                )
            )
    return findings


def check_amount_and_inventory(record: dict[str, object]) -> list[QualityFinding]:
    """拒绝负库存、非正价格和无法解析的金额，避免异常事实进入运营指标。

Args:
    record: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    findings: list[QualityFinding] = []
    stock = record.get("available_stock")
    if isinstance(stock, (int, float)) and stock < 0:
        findings.append(
            QualityFinding(
                rule_code="DQ-005-STOCK",
                field_name="available_stock",
                severity="error",
                message="可售库存不能为负数",
            )
        )
    price = record.get("price")
    if price is not None:
        try:
            amount = Decimal(str(price))
        except (InvalidOperation, ValueError):
            amount = Decimal("-1")
        if amount <= 0:
            findings.append(
                QualityFinding(
                    rule_code="DQ-005-AMOUNT",
                    field_name="price",
                    severity="error",
                    message="价格必须是可解析的正数",
                )
            )
    return findings


def check_cross_source_consistency(
    record: dict[str, object],
    *,
    source_pairs: tuple[tuple[str, str], ...],
) -> list[QualityFinding]:
    """比较不同来源的同一事实；官方事实和导入值不一致时只报告冲突。

Args:
    record: 参数语义、输入边界和安全约束。
    source_pairs: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    findings: list[QualityFinding] = []
    for official_field, imported_field in source_pairs:
        official = record.get(official_field)
        imported = record.get(imported_field)
        if official is not None and imported is not None and official != imported:
            findings.append(
                QualityFinding(
                    rule_code="DQ-006-CONFLICT",
                    field_name=imported_field,
                    severity="warning",
                    message="官方事实与运营导入值不一致，需要人工确认",
                )
            )
    return findings
