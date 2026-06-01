# -*- coding: utf-8 -*-
"""Tests for code_review_debate skill."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.code_review_debate.script import (
    DebateEngine,
    DebateReport,
    Finding,
    Severity,
    Verification,
    Verdict,
)


class TestVerdict:
    def test_all_verdicts_exist(self):
        assert Verdict.AGREED.value == "agreed"
        assert Verdict.PARTIAL.value == "partial"
        assert Verdict.DISAGREED.value == "disagreed"
        assert Verdict.OUTDATED.value == "outdated"
        assert Verdict.MISATTRIBUTED.value == "misattributed"


class TestSeverity:
    def test_all_severities_exist(self):
        assert Severity.P0.value == "critical"
        assert Severity.P1.value == "high"
        assert Severity.P2.value == "medium"
        assert Severity.P3.value == "low"


class TestFinding:
    def test_create_finding(self):
        f = Finding(id="CRITICAL-01", title="Test", severity=Severity.P0)
        assert f.id == "CRITICAL-01"
        assert f.severity == Severity.P0
        assert f.files == []

    def test_finding_with_files(self):
        f = Finding(
            id="BACKEND-01",
            title="Test",
            severity=Severity.P1,
            files=["app/test.py"],
        )
        assert len(f.files) == 1


class TestVerification:
    def test_create_verification(self):
        f = Finding(id="TEST-01", title="Test", severity=Severity.P1)
        v = Verification(
            finding=f,
            verdict=Verdict.AGREED,
            evidence="file.py:42 confirms the issue",
        )
        assert v.verdict == Verdict.AGREED
        assert "file.py:42" in v.evidence


class TestDebateEngine:
    def test_create_engine(self):
        engine = DebateEngine()
        assert engine.codebase_root is not None

    def test_extract_findings_from_content(self):
        engine = DebateEngine()
        content = """
        CRITICAL-01: Shell injection
        CRITICAL-02: SSL disabled
        BACKEND-01: Dual enums
        MED-01: Missing auth
        """
        findings = engine._extract_findings(content)
        assert len(findings) == 4
        assert findings[0].id == "CRITICAL-01"
        assert findings[0].severity == Severity.P0
        assert findings[2].id == "BACKEND-01"
        assert findings[2].severity == Severity.P1

    def test_extract_deduplicates(self):
        engine = DebateEngine()
        content = "CRITICAL-01 first\nCRITICAL-01 second"
        findings = engine._extract_findings(content)
        assert len(findings) == 1

    def test_analyze_report_file_not_found(self):
        engine = DebateEngine()
        with pytest.raises(FileNotFoundError):
            engine.analyze_report("/nonexistent/report.html")

    def test_analyze_report(self, tmp_path):
        report = tmp_path / "report.html"
        report.write_text("CRITICAL-01: test issue\nBACKEND-01: another issue", encoding="utf-8")

        engine = DebateEngine()
        result = engine.analyze_report(str(report))
        assert isinstance(result, DebateReport)
        assert result.total_findings == 2
        assert result.source == "report.html"

    def test_format_report(self, tmp_path):
        report = tmp_path / "report.html"
        report.write_text("CRITICAL-01: test", encoding="utf-8")

        engine = DebateEngine()
        result = engine.analyze_report(str(report))
        formatted = engine.format_report(result)
        assert "博弈审查报告" in formatted
        assert "CRITICAL-01" in formatted
        assert "准确率" in formatted


class TestDebateReport:
    def test_report_structure(self):
        report = DebateReport(
            source="test.html",
            total_findings=10,
            agreed=7,
            partial=2,
            disagreed=1,
            outdated=0,
            accuracy=70.0,
            original_score=6.8,
            corrected_score=7.5,
        )
        assert report.accuracy == 70.0
        assert report.agreed + report.partial + report.disagreed + report.outdated == 10
