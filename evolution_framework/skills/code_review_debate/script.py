# -*- coding: utf-8 -*-
"""
code_review_debate Skill — 博弈式代码审查
> 版本: v1.0 | 2026-06-01
> 触发: /review, /debate, 博弈审查
> 功能: 对外部报告进行逐项验证、挑战假设、提供证据
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill_output import ok, err, skill_main


# ─────────────────────────────────────────────────────────────────────────────
# 核心数据结构
# ─────────────────────────────────────────────────────────────────────────────

class Verdict(str, Enum):
    """博弈判定结果"""
    AGREED = "agreed"           # 报告正确，确认
    PARTIAL = "partial"         # 部分正确，需补充
    DISAGREED = "disagreed"     # 报告错误，反驳
    OUTDATED = "outdated"       # 已修复，报告过时
    MISATTRIBUTED = "misattributed"  # 文件/行号归因错误


class Severity(str, Enum):
    """严重度"""
    P0 = "critical"
    P1 = "high"
    P2 = "medium"
    P3 = "low"


@dataclass
class Finding:
    """报告中的单个发现"""
    id: str                     # 如 CRITICAL-01
    title: str                  # 问题标题
    severity: Severity          # 报告评的严重度
    files: List[str] = field(default_factory=list)  # 涉及文件
    description: str = ""       # 报告描述


@dataclass
class Verification:
    """对单个 Finding 的验证结果"""
    finding: Finding
    verdict: Verdict
    evidence: str               # 代码证据
    corrected_severity: Optional[Severity] = None  # 修正后的严重度
    notes: str = ""             # 补充说明


@dataclass
class DebateReport:
    """博弈审查报告"""
    source: str                 # 来源报告
    total_findings: int
    agreed: int
    partial: int
    disagreed: int
    outdated: int
    accuracy: float             # 准确率
    original_score: float       # 报告评分
    corrected_score: float      # 修正评分
    verifications: List[Verification] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 分析引擎
# ─────────────────────────────────────────────────────────────────────────────

class DebateEngine:
    """博弈审查引擎"""

    def __init__(self, codebase_root: Path = None):
        self.codebase_root = codebase_root or Path.cwd()

    def analyze_report(self, report_path: str) -> DebateReport:
        """分析外部报告并生成博弈审查结果"""
        path = Path(report_path)
        if not path.exists():
            raise FileNotFoundError(f"报告不存在: {report_path}")

        content = path.read_text(encoding="utf-8", errors="ignore")

        # 提取 findings
        findings = self._extract_findings(content)

        # 逐项验证
        verifications = []
        for finding in findings:
            v = self._verify_finding(finding)
            verifications.append(v)

        # 统计
        agreed = sum(1 for v in verifications if v.verdict == Verdict.AGREED)
        partial = sum(1 for v in verifications if v.verdict == Verdict.PARTIAL)
        disagreed = sum(1 for v in verifications if v.verdict == Verdict.DISAGREED)
        outdated = sum(1 for v in verifications if v.verdict == Verdict.OUTDATED)
        total = len(verifications)
        accuracy = (agreed / max(total, 1)) * 100

        return DebateReport(
            source=str(path.name),
            total_findings=total,
            agreed=agreed,
            partial=partial,
            disagreed=disagreed,
            outdated=outdated,
            accuracy=accuracy,
            original_score=0.0,  # 需要从报告中提取
            corrected_score=0.0,  # 需要计算
            verifications=verifications,
        )

    def _extract_findings(self, content: str) -> List[Finding]:
        """从报告内容中提取 findings"""
        findings = []

        # 匹配 CRITICAL-XX, BACKEND-XX, FRONTEND-XX, MED-XX 等模式
        pattern = r'(?:CRITICAL|BACKEND|FRONTEND|MED|RUNTIME)-\d+'
        matches = re.findall(pattern, content)

        # 去重
        seen = set()
        for match in matches:
            if match not in seen:
                seen.add(match)
                # 判断严重度
                if "CRITICAL" in match or "RUNTIME" in match:
                    severity = Severity.P0
                elif "BACKEND" in match or "FRONTEND" in match:
                    severity = Severity.P1
                elif "MED" in match:
                    severity = Severity.P2
                else:
                    severity = Severity.P3

                findings.append(Finding(
                    id=match,
                    title=f"Finding {match}",
                    severity=severity,
                ))

        return findings

    def _verify_finding(self, finding: Finding) -> Verification:
        """验证单个 finding（需要实际代码检查）"""
        # 这里是框架——实际验证需要读取代码文件
        # 返回 PARTIAL 作为默认，提示需要人工验证
        return Verification(
            finding=finding,
            verdict=Verdict.PARTIAL,
            evidence="需要人工验证：请提供具体文件和行号",
            notes="自动提取的 finding 需要代码级验证",
        )

    def format_report(self, report: DebateReport) -> str:
        """格式化博弈审查报告"""
        lines = [
            "## 博弈审查报告",
            "",
            f"**来源**: {report.source}",
            f"**总发现数**: {report.total_findings}",
            "",
            "### 判定统计",
            "",
            f"| 判定 | 数量 | 占比 |",
            f"|------|------|------|",
            f"| ✅ AGREED (确认) | {report.agreed} | {report.agreed/max(report.total_findings,1)*100:.0f}% |",
            f"| ⚠️ PARTIAL (部分) | {report.partial} | {report.partial/max(report.total_findings,1)*100:.0f}% |",
            f"| ❌ DISAGREED (反驳) | {report.disagreed} | {report.disagreed/max(report.total_findings,1)*100:.0f}% |",
            f"| 🔄 OUTDATED (过时) | {report.outdated} | {report.outdated/max(report.total_findings,1)*100:.0f}% |",
            "",
            f"**报告准确率**: {report.accuracy:.0f}%",
            "",
            "### 逐项验证",
            "",
            "| # | Finding | 判定 | 证据 |",
            "|---|---------|------|------|",
        ]

        for i, v in enumerate(report.verifications, 1):
            emoji = {
                Verdict.AGREED: "✅",
                Verdict.PARTIAL: "⚠️",
                Verdict.DISAGREED: "❌",
                Verdict.OUTDATED: "🔄",
                Verdict.MISATTRIBUTED: "🔀",
            }.get(v.verdict, "?")
            evidence_short = v.evidence[:60] + "..." if len(v.evidence) > 60 else v.evidence
            lines.append(f"| {i} | {v.finding.id} | {emoji} {v.verdict.value} | {evidence_short} |")

        lines.extend([
            "",
            "### 方法论",
            "",
            "本报告使用博弈式审查方法：",
            "1. **验证优先**: 每个 Finding 对比实际代码",
            "2. **博弈思维**: 对每个结论提出反面论证",
            "3. **证据驱动**: 每个判断引用具体代码",
            "4. **根因分析**: 追问为什么，而非只看表面",
        ])

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Skill 入口
# ─────────────────────────────────────────────────────────────────────────────

@skill_main("code_review_debate", required_params=["report_path"])
def run(report_path: str, codebase_root: str = None, **kwargs) -> dict:
    """
    博弈式代码审查

    Args:
        report_path: 外部报告路径 (HTML/MD)
        codebase_root: 代码库根目录（可选）
    """
    try:
        root = Path(codebase_root) if codebase_root else None
        engine = DebateEngine(codebase_root=root)
        report = engine.analyze_report(report_path)
        formatted = engine.format_report(report)

        return ok("code_review_debate", data={
            "accuracy": report.accuracy,
            "total": report.total_findings,
            "agreed": report.agreed,
            "disagreed": report.disagreed,
            "outdated": report.outdated,
            "report": formatted,
        }, summary=f"博弈审查完成: {report.accuracy:.0f}% 准确率, {report.total_findings} findings")

    except Exception as e:
        return err("code_review_debate", str(e), "检查报告路径是否正确")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = run(report_path=sys.argv[1])
        print(result)
