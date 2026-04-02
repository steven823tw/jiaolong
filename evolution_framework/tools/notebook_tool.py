# -*- coding: utf-8 -*-
"""
jiaolong工具 - NotebookEditTool
> 版本: v1.0 | 2026-04-02
> 对应: Claude Code NotebookEditTool
> 用途: Jupyter .ipynb 文件读写编辑
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from .tool_spec import ToolSpec, ToolResult, PermissionModel, ProgressState


class NotebookCell:
    """Notebook单元格"""
    def __init__(self, cell_type: str = "code", source: str = "",
                 outputs: List = None, metadata: Dict = None):
        self.cell_type = cell_type  # "code" | "markdown" | "raw"
        self.source = source
        self.outputs = outputs or []
        self.metadata = metadata or {}
        self.execution_count = None

    def to_dict(self) -> dict:
        return {
            "cell_type": self.cell_type,
            "source": self.source,
            "outputs": self.outputs,
            "metadata": self.metadata,
            "execution_count": self.execution_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NotebookCell":
        cell = cls(
            cell_type=d.get("cell_type", "code"),
            source=d.get("source", ""),
            outputs=d.get("outputs", []),
            metadata=d.get("metadata", {}),
        )
        cell.execution_count = d.get("execution_count")
        return cell


class Notebook:
    """Jupyter Notebook对象"""
    def __init__(self, path: str = None):
        self.path = path
        self.nbformat_version = "4.5"
        self.kernel_name = "python3"
        self.cells: List[NotebookCell] = []
        self.metadata = {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.12.0"
            }
        }

        if path and Path(path).exists():
            self.load(path)

    def load(self, path: str):
        """从文件加载"""
        with open(path, "r", encoding="utf-8") as f:
            nb_dict = json.load(f)
        self.path = path
        self.nbformat_version = nb_dict.get("nbformat", "4.5")
        self.metadata = nb_dict.get("metadata", self.metadata)
        self.cells = [NotebookCell.from_dict(c) for c in nb_dict.get("cells", [])]

    def save(self, path: str = None):
        """保存到文件"""
        path = path or self.path
        if not path:
            raise ValueError("没有指定保存路径")

        nb_dict = {
            "nbformat": int(self.nbformat_version),
            "nbformat_minor": 0,
            "metadata": self.metadata,
            "cells": [c.to_dict() for c in self.cells]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb_dict, f, ensure_ascii=False, indent=1)

    def add_cell(self, source: str, cell_type: str = "code",
                  index: int = None) -> NotebookCell:
        """添加单元格"""
        cell = NotebookCell(cell_type=cell_type, source=source)
        if index is None or index >= len(self.cells):
            self.cells.append(cell)
        else:
            self.cells.insert(index, cell)
        return cell

    def delete_cell(self, index: int) -> bool:
        """删除单元格"""
        if 0 <= index < len(self.cells):
            self.cells.pop(index)
            return True
        return False

    def get_cell(self, index: int) -> Optional[NotebookCell]:
        if 0 <= index < len(self.cells):
            return self.cells[index]
        return None

    def cell_count(self) -> int:
        return len(self.cells)


class NotebookEditTool(ToolSpec):
    """Jupyter Notebook 编辑工具"""
    name = "notebook_edit"
    description = "打开/编辑/保存 Jupyter .ipynb 文件"
    permission_model = PermissionModel.CONFIRM  # 写文件需确认
    risk_level = 2
    tags = ["file", "notebook", "jupyter"]

    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["open", "add_cell", "delete_cell", "edit_cell",
                         "get_cell", "list_cells", "save", "run"],
                "description": "操作类型"
            },
            "path": {
                "type": "string",
                "description": ".ipynb 文件路径"
            },
            "cell_index": {
                "type": "integer",
                "description": "单元格索引（从0开始）"
            },
            "cell_type": {
                "type": "string",
                "enum": ["code", "markdown", "raw"],
                "description": "单元格类型",
                "default": "code"
            },
            "source": {
                "type": "string",
                "description": "单元格内容"
            },
            "outputs": {
                "type": "array",
                "description": "单元格输出（仅在run时模拟）"
            }
        },
        "required": ["action", "path"]
    }

    # Notebook实例缓存
    _open_notebooks: Dict[str, Notebook] = {}

    def _get_notebook(self, path: str) -> Notebook:
        """获取或打开notebook"""
        if path not in self._open_notebooks:
            self._open_notebooks[path] = Notebook(path)
        return self._open_notebooks[path]

    def execute(self, action: str, path: str,
                 cell_index: int = None, cell_type: str = "code",
                 source: str = "", outputs: List = None,
                 **kwargs) -> ToolResult:
        """执行notebook操作"""
        nb = self._get_notebook(path)

        if action == "open":
            return ToolResult(
                success=True,
                data={
                    "path": path,
                    "cell_count": nb.cell_count(),
                    "cells": [c.to_dict() for c in nb.cells],
                    "metadata": nb.metadata,
                }
            )

        elif action == "add_cell":
            idx = cell_index if cell_index is not None else None
            cell = nb.add_cell(source=source, cell_type=cell_type, index=idx)
            return ToolResult(
                success=True,
                data={
                    "message": f"添加单元格 @ index {idx or '末尾'}",
                    "cell_index": nb.cells.index(cell),
                    "cell": cell.to_dict(),
                }
            )

        elif action == "delete_cell":
            success = nb.delete_cell(cell_index)
            return ToolResult(
                success=success,
                data={"message": f"删除单元格 @ {cell_index}" if success else ""},
                error="" if success else f"索引无效: {cell_index}"
            )

        elif action == "edit_cell":
            cell = nb.get_cell(cell_index)
            if not cell:
                return ToolResult(success=False, error=f"单元格不存在: {cell_index}")
            if source:
                cell.source = source
            if cell_type:
                cell.cell_type = cell_type
            return ToolResult(
                success=True,
                data={"cell": cell.to_dict()}
            )

        elif action == "get_cell":
            cell = nb.get_cell(cell_index)
            if not cell:
                return ToolResult(success=False, error=f"单元格不存在: {cell_index}")
            return ToolResult(success=True, data={"cell": cell.to_dict()})

        elif action == "list_cells":
            return ToolResult(
                success=True,
                data={
                    "count": nb.cell_count(),
                    "cells": [{"index": i, **c.to_dict()} for i, c in enumerate(nb.cells)]
                }
            )

        elif action == "save":
            nb.save(path)
            return ToolResult(
                success=True,
                data={"message": f"已保存: {path}"}
            )

        elif action == "run":
            # 模拟执行（不真正运行Python）
            cell = nb.get_cell(cell_index)
            if not cell:
                return ToolResult(success=False, error=f"单元格不存在: {cell_index}")
            cell.outputs = outputs or [{"type": "stream", "text": "[模拟输出]\n"}]
            cell.execution_count = cell_index + 1
            return ToolResult(
                success=True,
                data={"cell": cell.to_dict(), "executed": True}
            )

        else:
            return ToolResult(success=False, error=f"未知操作: {action}")


if __name__ == "__main__":
    print("=== NotebookEditTool 验证 ===")
    tool = NotebookEditTool()
    
    test_path = r"C:\Users\steve\.openclaw\workspace\test_notebook.ipynb"
    
    # 创建新notebook
    r1 = tool.execute(action="add_cell", path=test_path,
                      source="print('hello world')", cell_type="code")
    print(f"add_cell: {r1.data}")
    
    # 列出cells
    r2 = tool.execute(action="list_cells", path=test_path)
    print(f"list_cells: {r2.data['count']} cells")
    
    # 保存
    r3 = tool.execute(action="save", path=test_path)
    print(f"save: {r3.data}")
