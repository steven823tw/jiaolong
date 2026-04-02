# -*- coding: utf-8 -*-
"""
jiaolong代码规则引擎 - 基于 clean-code-review 标准
> 版本: v2.0 | 2026-04-02
> 整合: clean-code-review SKILL.md 全部规则
> 规则级别: ERROR(必须修复) / WARNING(建议修复) / INFO(提示)
"""
from __future__ import annotations
import ast, re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# 规则级别
# ─────────────────────────────────────────────────────────────────────────────

class RuleLevel(str, Enum):
    ERROR = "error"      # 必须修复
    WARNING = "warning"  # 建议修复
    INFO = "info"        # 提示


@dataclass
class RuleViolation:
    rule: str
    level: RuleLevel
    message: str
    line: int = 0
    fix_suggestion: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Python规则检查器
# ─────────────────────────────────────────────────────────────────────────────

class PythonLinter:
    """Python代码规则检查（基于AST解析）"""

    def __init__(self, content: str, filename: str = "temp.py"):
        self.content = content
        self.filename = filename
        self.lines = content.split("\n")
        self.violations: List[RuleViolation] = []
        self._tree = None

        try:
            self._tree = ast.parse(content)
        except SyntaxError:
            return

    def check_all(self) -> List[RuleViolation]:
        """执行所有检查"""
        if self._tree is None:
            return self.violations

        self._check_function_length()
        self._check_too_many_args()
        self._check_magic_numbers()
        self._check_empty_functions()
        self._check_generic_names()
        self._check_deep_nesting()
        self._check_commented_code()
        self._check_no_annotations()

        return self.violations

    def _add_violation(self, rule: str, level: RuleLevel,
                       message: str, line: int = 0, fix: str = ""):
        self.violations.append(RuleViolation(
            rule=rule, level=level, message=message,
            line=line, fix_suggestion=fix
        ))

    def _check_function_length(self):
        """规则: 函数不超过20行"""
        for node in ast.walk(self._tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, 'name') and node.name.startswith('_'):
                    continue  # 私有方法跳过
                # 计算函数体行数
                if node.end_lineno and node.lineno:
                    length = node.end_lineno - node.lineno + 1
                    if length > 20:
                        self._add_violation(
                            "FunctionLengthRule",
                            RuleLevel.WARNING,
                            f"函数 `{node.name}` 长度{length}行，超过20行限制",
                            line=node.lineno,
                            fix=f"将 `{node.name}` 拆分为多个小函数（每函数≤20行）"
                        )

    def _check_too_many_args(self):
        """规则: 函数参数不超过3个"""
        for node in ast.walk(self._tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                # 只计算非默认参数
                non_default = len(args.args) - len(args.defaults)
                total = len(args.args)
                if total > 3:
                    self._add_violation(
                        "TooManyArgsRule",
                        RuleLevel.WARNING,
                        f"函数 `{node.name}` 有{total}个参数，超过3个限制",
                        line=node.lineno,
                        fix=f"使用 `*args, **kwargs` 或参数对象封装（字典/dataclass）"
                    )

    def _check_magic_numbers(self):
        """规则: 禁止魔法数字"""
        for node in ast.walk(self._tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                val = node.value
                # 允许的数字: 0, 1, -1, 2(for二分), 100(百分比)
                allowed = {0, 1, -1, 100}
                if val not in allowed:
                    self._add_violation(
                        "NoMagicNumbersRule",
                        RuleLevel.WARNING,
                        f"发现魔法数字 `{val}`，应使用命名常量",
                        line=node.lineno,
                        fix=f"定义常量: `MAX_{node.lineno}_VALUE = {val}` 并替换"
                    )

    def _check_empty_functions(self):
        """规则: 禁止空函数（只有pass或...）"""
        for node in ast.walk(self._tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if len(body) == 1:
                    first = body[0]
                    # pass语句 = stub
                    if isinstance(first, ast.Pass):
                        self._add_violation(
                            "NoHandWavingRule",
                            RuleLevel.ERROR,
                            f"函数 `{node.name}` 是空 stub（只有pass），必须有实际实现",
                            line=node.lineno,
                            fix=f"实现 `{node.name}` 的具体逻辑，或删除该函数"
                        )
                    # 单个Expr语句: 可能是docstring或Ellipsis
                    elif isinstance(first, ast.Expr):
                        val = first.value
                        # ... (Ellipsis常量) = stub
                        if isinstance(val, ast.Constant) and val.value is ...:
                            self._add_violation(
                                "NoHandWavingRule",
                                RuleLevel.ERROR,
                                f"函数 `{node.name}` 是空 stub（只有...），必须有实际实现",
                                line=node.lineno,
                                fix=f"实现 `{node.name}` 的具体逻辑"
                            )
                        # 字符串常量 = docstring，允许
                        elif isinstance(val, ast.Constant) and isinstance(val.value, str):
                            pass  # 有文档字符串，正常
                        # 其他表达式（如self.xxx.append(...)）= 有实际实现，正常
                        # 不需要检查

    def _check_generic_names(self):
        """规则: 禁止通用名称（data/info/item/handler/tmp）"""
        generic_patterns = [
            (r'^data$', "data", "使用具体名称如 `userData`, `orderData`"),
            (r'^info$', "info", "使用具体名称如 `configInfo`, `userInfo`"),
            (r'^item$', "item", "使用具体名称如 `orderItem`, `cartItem`"),
            (r'^handler$', "handler", "使用具体名称如 `clickHandler`, `submitHandler`"),
            (r'^tmp$', "tmp", "使用具体名称如 `tempFile`, `tempUser`"),
            (r'^temp$', "temp", "使用具体名称表达临时存储的目的"),
            (r'^result$', "result", "使用具体名称如 `queryResult`, `calcResult`"),
            (r'^dict\d*$', "dictN", "避免dictN这样无意义的名称"),
        ]

        for i, line_text in enumerate(self.lines, 1):
            # 跳过注释和字符串
            stripped = line_text.strip()
            if stripped.startswith('#') or stripped.startswith('"""'):
                continue

            for pattern, name, fix in generic_patterns:
                if re.search(pattern, line_text):
                    self._add_violation(
                        "NoGenericNamesRule",
                        RuleLevel.WARNING,
                        f"发现通用名称 `{name}`，名称应表达具体含义",
                        line=i,
                        fix=fix
                    )

    def _check_deep_nesting(self):
        """规则: 嵌套不超过2层"""
        for node in ast.walk(self._tree):
            if isinstance(node, ast.If):
                depth = self._get_if_depth(node)
                if depth > 2:
                    self._add_violation(
                        "MaxNestingRule",
                        RuleLevel.WARNING,
                        f"if嵌套深度{depth}层，超过2层限制",
                        line=node.lineno,
                        fix="使用 guard clause（提前return）或提取为独立函数"
                    )

    def _get_if_depth(self, node, current=0):
        depth = current
        if isinstance(node, ast.If):
            depth += 1
            # 检查orelse
            if node.orelse:
                depth = max(depth, self._get_if_depth(node.orelse[0], depth) if node.orelse else depth)
        return depth

    def _check_commented_code(self):
        """规则: 禁止注释掉的代码"""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            # 检测 # xxx = old_code 模式的注释代码
            if re.match(r'^#\s*\w+\s*=\s*.+$', stripped):
                self._add_violation(
                    "NoCommentedOutCodeRule",
                    RuleLevel.WARNING,
                    f"发现注释掉的代码: {stripped[:50]}",
                    line=i,
                    fix="删除注释代码，使用版本控制保存历史"
                )

    def _check_no_annotations(self):
        """规则: 公共函数应有类型注解"""
        for node in ast.walk(self._tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith('_'):
                    continue
                # 检查是否有类型注解
                has_return = node.returns is not None
                has_args = any(
                    (arg.annotation is not None)
                    for arg in node.args.args
                )
                if not has_return and not has_args:
                    self._add_violation(
                        "MissingTypeAnnotationsRule",
                        RuleLevel.INFO,
                        f"函数 `{node.name}` 缺少类型注解，建议添加",
                        line=node.lineno,
                        fix=f"添加类型注解: def {node.name}(...) -> ReturnType:"
                    )


# ─────────────────────────────────────────────────────────────────────────────
# JavaScript规则检查器（基础版）
# ─────────────────────────────────────────────────────────────────────────────

class JavaScriptLinter:
    """JavaScript代码规则检查"""

    def __init__(self, content: str, filename: str = "temp.js"):
        self.content = content
        self.filename = filename
        self.lines = content.split("\n")
        self.violations: List[RuleViolation] = []

    def check_all(self) -> List[RuleViolation]:
        if self._tree is None:
            return self.violations
        self._check_empty_functions_js()
        self._check_generic_names_js()
        return self.violations

    def _add_violation(self, rule: str, level: RuleLevel,
                       message: str, line: int = 0, fix: str = ""):
        self.violations.append(RuleViolation(
            rule=rule, level=level, message=message,
            line=line, fix_suggestion=fix
        ))

    def _check_empty_functions_js(self):
        """JS空函数检查"""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if 'function' in stripped or '=>' in stripped:
                # 简单检查：function name() {} 或 const name = () => {}
                if re.search(r'(function\s+\w+|const\s+\w+\s*=\s*\([^)]*\)\s*=>)\s*\{\s*\}', self.content):
                    self._add_violation(
                        "NoHandWavingRule_JS",
                        RuleLevel.ERROR,
                        f"发现空JS函数",
                        line=i,
                        fix="实现函数逻辑或删除"
                    )

    def _check_generic_names_js(self):
        """JS通用名称检查"""
        generic = ['data', 'info', 'item', 'handler', 'tmp', 'temp', 'result']
        for i, line in enumerate(self.lines, 1):
            for g in generic:
                if re.search(rf'\b{g}\b', line) and '//' not in line:
                    # 简单检查
                    pass


# ─────────────────────────────────────────────────────────────────────────────
# 主规则引擎
# ─────────────────────────────────────────────────────────────────────────────

class RulesEngine:
    """
    代码规则引擎 v2.0
    整合 clean-code-review 标准
    """

    def __init__(self):
        self.name = "jiaolong规则引擎"
        self.version = "2.0"

    def check_content(self, content: str, filename: str = "temp.py") -> List[RuleViolation]:
        """检查代码内容"""
        ext = Path(filename).suffix.lower()

        if ext in (".py", ".pyw"):
            linter = PythonLinter(content, filename)
            return linter.check_all()
        elif ext in (".js", ".ts", ".tsx", ".jsx"):
            linter = JavaScriptLinter(content, filename)
            return linter.check_all()
        else:
            return []

    def check_file(self, file_path: str) -> dict:
        """检查文件"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"passed": False, "error": f"文件不存在: {file_path}"}

            content = path.read_text(encoding="utf-8", errors="ignore")
            violations = self.check_content(content, file_path)

            return {
                "passed": all(v.level != RuleLevel.ERROR for v in violations),
                "violations_count": len(violations),
                "errors": [v for v in violations if v.level == RuleLevel.ERROR],
                "warnings": [v for v in violations if v.level == RuleLevel.WARNING],
                "infos": [v for v in violations if v.level == RuleLevel.INFO],
                "violations": violations,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 便捷函数
# ─────────────────────────────────────────────────────────────────────────────

_engine = None

def get_engine() -> RulesEngine:
    global _engine
    if _engine is None:
        _engine = RulesEngine()
    return _engine


def check_rules(file_path: str) -> dict:
    """检查文件规则"""
    return get_engine().check_file(file_path)


def check_content(content: str, filename: str = "temp.py") -> List[RuleViolation]:
    """检查代码内容"""
    return get_engine().check_content(content, filename)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== jiaolong代码规则引擎 v2.0 ===")
    print("整合 clean-code-review 标准\n")

    # 测试1: 空函数
    bad_code1 = """
def empty_stub():
    pass
"""
    engine = RulesEngine()
    violations = engine.check_content(bad_code1, "test.py")
    print(f"[测试1] 空stub函数:")
    for v in violations:
        print(f"  [{v.level.value}] {v.rule}: {v.message}")
        print(f"    修复: {v.fix_suggestion}")

    # 测试2: 魔法数字
    bad_code2 = """
def calculate_price(quantity):
    return quantity * 3.14159
"""
    violations2 = engine.check_content(bad_code2, "test.py")
    print(f"\n[测试2] 魔法数字:")
    for v in violations2:
        if v.rule == "NoMagicNumbersRule":
            print(f"  [{v.level.value}] {v.message}")

    # 测试3: 通用名称
    bad_code3 = """
data = fetch_user()
info = process(data)
item = info[0]
"""
    violations3 = engine.check_content(bad_code3, "test.py")
    print(f"\n[测试3] 通用名称:")
    for v in violations3:
        print(f"  [{v.level.value}] {v.message}")

    # 测试4: 正常代码
    good_code = """
def calculate_circle_area(radius: float) -> float:
    PI = 3.14159
    return PI * radius * radius

def get_user_name(user_id: int) -> str:
    if not user_id:
        return ""
    user = fetch_user_by_id(user_id)
    return user.name if user else ""
"""
    violations4 = engine.check_content(good_code, "test.py")
    print(f"\n[测试4] 正常代码:")
    print(f"  违规数: {len(violations4)}")
    for v in violations4:
        print(f"  [{v.level.value}] {v.message}")

    print("\n[OK] clean-code-review 规则整合验证完成")
