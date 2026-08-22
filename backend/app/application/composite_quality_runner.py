"""组合多个只读质量规则运行器，不改变任务触发方向。"""

from backend.app.application.quality_check_worker import QualityRuleRunner
from backend.app.domain.data_quality import QualityCheckJob, QualityFinding


class CompositeQualityRunner:
    """顺序运行规则集合；任一规则失败由 Worker 统一有限重试。"""

    def __init__(self, runners: tuple[QualityRuleRunner, ...]) -> None:
        self._runners = runners

    async def run(self, job: QualityCheckJob) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        for runner in self._runners:
            findings.extend(await runner.run(job))
        return findings
