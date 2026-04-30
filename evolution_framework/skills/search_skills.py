# -*- coding: utf-8 -*-
"""
jiaolong Skills - SkillBuilder v2: 自动发现/创建/改进Skill
> 版本: v2.0 | 2026-04-02
> 对应: Claude Code skills/auto_skill_builder
"""
from __future__ import annotations
import json, re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import os
WORKSPACE = Path(os.environ.get("JIAOLONG_WORKSPACE", str(Path.home() / ".claude" / "jiaolong")))
SKILLS_DIR = WORKSPACE / "evolution_framework" / "skills"


class SkillTemplate:
    """Skill模板"""

    @staticmethod
    def basic(name: str, description: str, commands: List[str]) -> str:
        return f"""# SKILL: {name}
> 版本: v1.0 | {datetime.now().strftime('%Y-%m-%d')}
> 描述: {description}

## 触发条件
自动触发（可配置）

## 功能
{chr(10).join(f'- {cmd}' for cmd in commands)}

## 使用方式
```
/{name.lower().replace(' ', '_')}
```

## 示例
```
/{name.lower().replace(' ', '_')} param1=value1
```

## 实现
> 由 SkillBuilder 自动生成
"""

    @staticmethod
    def with_params(name: str, description: str, params: List[dict],
                    steps: List[str], examples: List[dict]) -> str:
        params_md = "\n".join(
            f'- `{p["name"]}`: {p["description"]} (类型: {p["type"]})'
            for p in params
        )
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        examples_md = "\n".join(
            f'- `{ex["cmd"]}` → {ex["result"]}'
            for ex in examples
        )
        return f"""# SKILL: {name}
> 版本: v1.0 | {datetime.now().strftime('%Y-%m-%d')}
> 描述: {description}

## 触发关键词
- `/{name.lower().replace(' ', '_')}`
- `{name}`

## 参数说明
{params_md}

## 执行步骤
{steps_md}

## 示例
{examples_md}

## 实现
> 由 SkillBuilder v2 自动生成
"""


class SkillDiscovery:
    """自动发现已有Skills"""

    def __init__(self):
        self.skills_dir = SKILLS_DIR

    def list_all_skills(self) -> List[dict]:
        """列出所有Skill"""
        skills = []
        if not self.skills_dir.exists():
            return skills

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text(encoding="utf-8")
                skills.append({
                    "name": skill_dir.name,
                    "path": str(skill_dir),
                    "has_skill_md": True,
                    "has_script": (skill_dir / "script.py").exists(),
                })
        return skills

    def get_skill_info(self, skill_name: str) -> Optional[dict]:
        """获取单个Skill详情"""
        skill_path = self.skills_dir / skill_name / "SKILL.md"
        if not skill_path.exists():
            return None
        content = skill_path.read_text(encoding="utf-8")
        return {
            "name": skill_name,
            "path": str(skill_path),
            "content": content,
            "lines": len(content.split("\n")),
        }

    def search_skills(self, keyword: str) -> List[dict]:
        """搜索包含关键词的Skill"""
        results = []
        for skill in self.list_all_skills():
            info = self.get_skill_info(skill["name"])
            if info and keyword.lower() in info["content"].lower():
                results.append(info)
        return results


class SkillImprover:
    """
    Skill自动改进
    分析现有Skill，提出改进建议
    """

    def __init__(self):
        self.discovery = SkillDiscovery()

    def analyze(self, skill_name: str) -> dict:
        """分析Skill并给出改进建议"""
        info = self.discovery.get_skill_info(skill_name)
        if not info:
            return {"error": f"Skill不存在: {skill_name}"}

        content = info["content"]
        lines = content.split("\n")

        suggestions = []

        # 检查结构完整性
        required_sections = ["## 触发条件", "## 功能", "## 使用方式"]
        for section in required_sections:
            if section not in content:
                suggestions.append(f"缺少必要章节: {section}")

        # 检查示例数量
        if "## 示例" not in content:
            suggestions.append("建议添加示例章节")

        # 检查版本
        if "版本: v1.0" in content:
            suggestions.append("已是v1.0，可考虑增加参数验证")

        # 检查描述长度
        if len(content) < 200:
            suggestions.append("内容偏少，建议补充详细说明")

        return {
            "skill": skill_name,
            "lines": info["lines"],
            "chars": len(content),
            "suggestions": suggestions,
        }


class SkillBuilder:
    """
    自动创建新Skill
    根据描述自动生成完整Skill
    """

    def __init__(self):
        self.skills_dir = SKILLS_DIR
        self.discovery = SkillDiscovery()

    def create(self, name: str, description: str,
                params: List[dict] = None,
                steps: List[str] = None,
                examples: List[dict] = None,
                auto_register: bool = True) -> dict:
        """
        创建新Skill

        Args:
            name: Skill名称
            description: 功能描述
            params: 参数列表 [{name, description, type}]
            steps: 执行步骤
            examples: 示例 [{cmd, result}]
            auto_register: 是否自动注册
        """
        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 生成SKILL.md
        skill_md = SkillTemplate.with_params(
            name=name,
            description=description,
            params=params or [],
            steps=steps or ["1. 读取输入", "2. 执行处理", "3. 返回结果"],
            examples=examples or [],
        )
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill_md, encoding="utf-8")

        # 生成script.py（骨架）
        script_py = self._generate_script(name, params or [])
        script_file = skill_dir / "script.py"
        script_file.write_text(script_py, encoding="utf-8")

        # 生成__init__.py
        init_py = f'# -*- coding: utf-8 -*-\n"""{name} Skill"""\n'
        (skill_dir / "__init__.py").write_text(init_py, encoding="utf-8")

        # 注册到skills_index.json
        if auto_register:
            self._register_skill(name, str(skill_dir))

        return {
            "skill": name,
            "created": True,
            "files": [str(skill_file), str(script_file)],
            "path": str(skill_dir),
        }

    def _generate_script(self, name: str, params: List[dict]) -> str:
        """生成Python脚本骨架"""
        param_lines = []
        for p in params:
            pname = p["name"]
            ptype = p.get("type", "str")
            pdesc = p.get("description", "")
            param_lines.append(f'    {pname}: {ptype} = None  # {pdesc}')

        param_sig = ",\n".join(param_lines) if param_lines else "    **kwargs"

        return f'''# -*- coding: utf-8 -*-
"""
{name} Skill Script
> 自动生成
"""
from __future__ import annotations
from typing import Any, Dict

def run({param_sig}
) -> Dict[str, Any]:
    """
    执行 {name}

    Returns:
        {{"success": bool, "data": Any, "error": str}}
    """
    # TODO: 实现逻辑
    return {{
        "success": True,
        "data": {{"message": "{name} 执行中"}},
        "error": ""
    }}


if __name__ == "__main__":
    result = run()
    print(result)
'''

    def _register_skill(self, name: str, path: str):
        """注册到skills_index.json"""
        index_file = self.skills_dir / "skills_index.json"
        if index_file.exists():
            index = json.loads(index_file.read_text(encoding="utf-8"))
        else:
            index = {"skills": [], "last_updated": ""}

        # 检查是否已注册
        existing = [s for s in index["skills"] if s["name"] == name]
        if not existing:
            index["skills"].append({
                "name": name,
                "path": path,
                "created_at": datetime.now().isoformat(),
                "version": "v1.0",
            })
            index["last_updated"] = datetime.now().isoformat()
            index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    def improve(self, skill_name: str) -> dict:
        """改进现有Skill"""
        improver = SkillImprover()
        analysis = improver.analyze(skill_name)
        if "error" in analysis:
            return analysis

        # 生成改进版
        info = self.discovery.get_skill_info(skill_name)
        improved_md = info["content"] + f"\n\n---\n> 改进版 | {datetime.now().isoformat()}\n"

        improved_path = self.skills_dir / skill_name / "SKILL.md"
        improved_path.write_text(improved_md, encoding="utf-8")

        return {
            "skill": skill_name,
            "improved": True,
            "suggestions": analysis["suggestions"],
            "path": str(improved_path),
        }


if __name__ == "__main__":
    builder = SkillBuilder()
    discovery = SkillDiscovery()

    print("=== SkillBuilder 验证 ===")
    skills = discovery.list_all_skills()
    print(f"发现 Skills: {len(skills)}")
    for s in skills:
        print(f"  - {s['name']}")

    print("\n=== 分析已有Skills ===")
    for s in skills[:3]:
        analysis = SkillImprover().analyze(s["name"])
        print(f"  {s['name']}: {analysis.get('lines', 0)}行, 建议:{len(analysis.get('suggestions',[]))}条")
