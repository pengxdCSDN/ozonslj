"""受控自动化编排规则。

本模块只保存跨页面自动化的领域约束，不依赖 FastAPI、数据库或消息中间件。
它负责把事件分类、下游白名单、触发链深度和有限重试集中到一个可测试的边界，
避免各页面自行互相触发而形成死循环。外部事实同步、领域计算和高风险写入的
具体执行仍由应用层和基础设施层负责。
"""

from dataclasses import dataclass
from typing import Final, Literal, Protocol

AutomationEventType = Literal[
    "external_fact_changed",
    "domain_fact_changed",
    "calculation_changed",
    "recommendation_created",
    "display_refreshed",
]

# 只有事实变化和受控的人工审核结果可以进入下游自动化；展示刷新和建议生成
# 默认不产生业务联动，防止“刷新 → 同步”或“建议 → 执行”的反向循环。
_ALLOWED_EVENT_TARGETS: Final[dict[AutomationEventType, frozenset[str]]] = {
    "external_fact_changed": frozenset({"data_quality", "domain_calculation"}),
    "domain_fact_changed": frozenset({"data_quality", "domain_calculation", "reporting"}),
    "calculation_changed": frozenset({"exception_review", "reporting"}),
    "recommendation_created": frozenset({"human_review"}),
    "display_refreshed": frozenset(),
}


@dataclass(frozen=True, slots=True)
class AutomationRun:
    """一次自动化运行的最小可追踪上下文。"""

    run_id: str
    workspace_id: str
    automation_type: str
    data_version: str
    depth: int = 0
    root_run_id: str | None = None
    parent_run_id: str | None = None

    def __post_init__(self) -> None:
        """校验链路身份和深度，禁止空标识或负深度进入编排层。"""
        if not self.run_id.strip() or not self.workspace_id.strip():
            raise ValueError("自动化运行必须包含 run_id 和 workspace_id")
        if not self.automation_type.strip() or not self.data_version.strip():
            raise ValueError("自动化运行必须包含自动化类型和数据版本")
        if self.depth < 0:
            raise ValueError("自动化触发链深度不能为负数")
        if self.root_run_id is not None and not self.root_run_id.strip():
            raise ValueError("root_run_id 不能为空字符串")
        if self.parent_run_id is not None and not self.parent_run_id.strip():
            raise ValueError("parent_run_id 不能为空字符串")

    @property
    def effective_root_run_id(self) -> str:
        """返回整条触发链的根运行标识。"""
        return self.root_run_id or self.run_id

    def child(self, *, run_id: str, automation_type: str, data_version: str) -> "AutomationRun":
        """创建一个深度加一的子运行，不修改父运行事实。"""
        return AutomationRun(
            run_id=run_id,
            workspace_id=self.workspace_id,
            automation_type=automation_type,
            data_version=data_version,
            depth=self.depth + 1,
            root_run_id=self.effective_root_run_id,
            parent_run_id=self.run_id,
        )


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """有限重试策略；认证、权限、合规和冲突错误必须由调用方标记为不可重试。"""

    max_attempts: int = 3
    base_delay_seconds: int = 60
    max_delay_seconds: int = 3_600

    def __post_init__(self) -> None:
        """校验重试上限，避免配置错误造成无界重试。"""
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("自动化最大尝试次数必须在 1 到 10 之间")
        if self.base_delay_seconds < 1 or self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("自动化重试延迟范围无效")

    def delay_seconds(self, *, attempt: int, retryable: bool) -> int | None:
        """按指数退避计算下一次重试；不可重试或达到上限时返回 None。"""
        if not retryable or attempt < 1 or attempt >= self.max_attempts:
            return None
        delay: int = self.base_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


@dataclass(frozen=True, slots=True)
class AutomationEvent:
    """Worker 发布给编排层的脱敏事实变化事件。"""

    event_id: str
    event_type: AutomationEventType
    workspace_id: str
    run_id: str
    root_run_id: str
    source: str
    data_version: str


@dataclass(frozen=True, slots=True)
class AutomationEventMessage:
    """Consumer Group 消息；message_id 仅用于确认，不作为业务事实。"""

    message_id: str
    event: AutomationEvent


class AutomationEventPublisher(Protocol):
    """事件发布端口；实现必须按 event_id 幂等，不能把 Redis 当事实库。"""

    async def publish_once(self, event: AutomationEvent) -> bool:
        """发布一次事件；重复 event_id 必须返回 False 且不得重复产生下游任务。"""


def is_allowed_target(event_type: AutomationEventType, target: str) -> bool:
    """判断事件是否允许触发目标，展示刷新和建议生成默认不执行联动。"""
    return target.strip() in _ALLOWED_EVENT_TARGETS[event_type]


def ensure_trigger_allowed(
    *,
    event_type: AutomationEventType,
    target: str,
    run: AutomationRun,
    max_depth: int = 5,
) -> None:
    """执行统一触发闸门，违反白名单或深度上限时立即熔断。"""
    if max_depth < 0:
        raise ValueError("自动化最大链路深度不能为负数")
    if run.depth > max_depth:
        raise ValueError("自动化触发链超过最大深度，已熔断并转人工处理")
    if not is_allowed_target(event_type, target):
        raise ValueError(f"事件 {event_type} 不允许触发目标 {target}")


def build_idempotency_key(run: AutomationRun) -> str:
    """构造工作区范围内稳定的幂等键，防止重复消息产生重复事实。"""
    return ":".join(
        (run.workspace_id, run.effective_root_run_id, run.automation_type, run.data_version)
    )
