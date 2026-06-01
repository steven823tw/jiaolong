# -*- coding: utf-8 -*-
"""Tests for rules_engine module."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from rules_engine import PythonLinter, RuleLevel, RulesEngine, check_rules


class TestFunctionLengthRule:
    def test_short_function_no_violation(self):
        code = "def add(a, b):\n    return a + b\n"
        violations = PythonLinter(code).check_all()
        assert not any(v.rule == "FunctionLengthRule" for v in violations)

    def test_long_function_detected(self):
        lines = ["def long_func():"]
        for i in range(25):
            lines.append(f"    x{i} = {i}")
        lines.append("    return x0")
        code = "\n".join(lines)
        violations = PythonLinter(code).check_all()
        assert any(v.rule == "FunctionLengthRule" for v in violations)

    def test_private_function_skipped(self):
        lines = ["def _private():"]
        for i in range(25):
            lines.append(f"    x{i} = {i}")
        lines.append("    return x0")
        code = "\n".join(lines)
        violations = PythonLinter(code).check_all()
        assert not any(v.rule == "FunctionLengthRule" for v in violations)


class TestTooManyArgsRule:
    def test_three_args_is_ok(self):
        code = "def f(a, b, c):\n    return a\n"
        violations = PythonLinter(code).check_all()
        assert not any(v.rule == "TooManyArgsRule" for v in violations)

    def test_four_args_detected(self):
        code = "def f(a, b, c, d):\n    return a\n"
        violations = PythonLinter(code).check_all()
        arg_violations = [v for v in violations if v.rule == "TooManyArgsRule"]
        assert len(arg_violations) == 1
        assert arg_violations[0].level == RuleLevel.WARNING


class TestMagicNumbersRule:
    def test_magic_number_detected(self):
        code = "def calc():\n    return 42 * 3.14\n"
        violations = PythonLinter(code).check_all()
        magic = [v for v in violations if v.rule == "NoMagicNumbersRule"]
        assert len(magic) >= 1


class TestEmptyFunctionsRule:
    def test_pass_stub_detected(self):
        code = "def stub():\n    pass\n"
        violations = PythonLinter(code).check_all()
        stub = [v for v in violations if v.rule == "NoHandWavingRule"]
        assert len(stub) == 1
        assert stub[0].level == RuleLevel.ERROR

    def test_ellipsis_stub_detected(self):
        code = "def stub():\n    ...\n"
        violations = PythonLinter(code).check_all()
        assert any(v.rule == "NoHandWavingRule" for v in violations)

    def test_docstring_only_not_stub(self):
        code = 'def documented():\n    """This does something."""\n'
        violations = PythonLinter(code).check_all()
        assert not any(v.rule == "NoHandWavingRule" for v in violations)

    def test_real_function_not_stub(self):
        code = "def real():\n    return 42\n"
        violations = PythonLinter(code).check_all()
        assert not any(v.rule == "NoHandWavingRule" for v in violations)


class TestMissingAnnotationsRule:
    def test_missing_annotations_detected(self):
        code = "def public_func(x):\n    return x\n"
        violations = PythonLinter(code).check_all()
        assert any(v.rule == "MissingTypeAnnotationsRule" for v in violations)

    def test_annotated_function_no_violation(self):
        code = "def public_func(x: int) -> int:\n    return x\n"
        violations = PythonLinter(code).check_all()
        assert not any(v.rule == "MissingTypeAnnotationsRule" for v in violations)


class TestCommentedCodeRule:
    def test_commented_code_detected(self):
        code = "x = 1\n# old_var = do_something()\n# result = process(old_var)\n"
        violations = PythonLinter(code).check_all()
        assert any(v.rule == "NoCommentedOutCodeRule" for v in violations)


class TestSyntaxErrorHandling:
    def test_syntax_error_returns_empty(self):
        code = "def broken("
        violations = PythonLinter(code).check_all()
        assert violations == []


class TestRulesEngine:
    def test_check_content_python(self):
        engine = RulesEngine()
        violations = engine.check_content("def f():\n    pass\n", "test.py")
        assert len(violations) > 0

    def test_check_content_unknown_ext(self):
        engine = RulesEngine()
        assert engine.check_content("anything", "test.txt") == []

    def test_check_file_returns_structure(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def f():\n    pass\n")
        result = check_rules(str(f))
        assert "passed" in result
        assert "violations_count" in result

    def test_check_file_missing(self):
        result = check_rules("/nonexistent/file.py")
        assert result["passed"] is False

    def test_check_file_clean_code(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
        result = check_rules(str(f))
        assert result["passed"] is True
        assert result["violations_count"] == 0
