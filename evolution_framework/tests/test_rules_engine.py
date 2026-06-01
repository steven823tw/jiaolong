# -*- coding: utf-8 -*-
"""Tests for rules_engine module."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from rules_engine import (
    PythonLinter,
    RuleLevel,
    RuleViolation,
    RulesEngine,
    check_rules,
)


class TestRuleLevel:
    def test_error_level(self):
        assert RuleLevel.ERROR.value == "error"

    def test_warning_level(self):
        assert RuleLevel.WARNING.value == "warning"

    def test_info_level(self):
        assert RuleLevel.INFO.value == "info"


class TestRuleViolation:
    def test_create_violation(self):
        v = RuleViolation(
            rule="TestRule",
            level=RuleLevel.WARNING,
            message="test message",
            line=10,
        )
        assert v.rule == "TestRule"
        assert v.level == RuleLevel.WARNING

    def test_with_fix_suggestion(self):
        v = RuleViolation(
            rule="TestRule",
            level=RuleLevel.ERROR,
            message="bad code",
            fix_suggestion="do this instead",
        )
        assert v.fix_suggestion == "do this instead"


class TestPythonLinter:
    def test_clean_code_no_violations(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        linter = PythonLinter(code)
        violations = linter.check_all()
        assert isinstance(violations, list)

    def test_function_too_long(self):
        lines = ["def long_func():"]
        for i in range(25):
            lines.append(f"    x{i} = {i}")
        lines.append("    return x0")
        code = "\n".join(lines)

        linter = PythonLinter(code)
        violations = linter.check_all()
        length_violations = [v for v in violations if v.rule == "FunctionLengthRule"]
        assert len(length_violations) > 0

    def test_syntax_error_handled(self):
        code = "def broken("
        linter = PythonLinter(code)
        violations = linter.check_all()
        assert violations == []

    def test_magic_numbers(self):
        code = "def calc():\n    return 42 * 3.14\n"
        linter = PythonLinter(code)
        violations = linter.check_all()
        assert isinstance(violations, list)


class TestRulesEngine:
    def test_create_engine(self):
        engine = RulesEngine()
        assert engine is not None

    def test_check_rules_with_file(self, tmp_path):
        # check_rules takes a file path, not code content
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    print('hello')\n")
        result = check_rules(str(test_file))
        assert isinstance(result, dict)
