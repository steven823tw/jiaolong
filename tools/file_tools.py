# -*- coding: utf-8 -*-
"""
jiaolong工具 - FileTools (补充更多文件操作工具)
> 版本: v1.0 | 2026-04-02
> 批量创建文件操作工具: write/append/delete/copy/move
"""
from __future__ import annotations
import shutil, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from .tool_spec import ToolSpec, ToolResult, PermissionModel


class WriteFileTool(ToolSpec):
    """写文件工具"""
    name = "write_file"
    description = "写入文件内容（覆盖）"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["file", "write"]

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "文件内容"},
            "encoding": {"type": "string", "description": "编码", "default": "utf-8"}
        },
        "required": ["path", "content"]
    }

    def execute(self, path: str, content: str, encoding: str = "utf-8", **kwargs) -> ToolResult:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            size = len(content)
            return ToolResult(success=True, data={"path": path, "size": size})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class AppendFileTool(ToolSpec):
    """追加写文件工具"""
    name = "append_file"
    description = "追加内容到文件末尾"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["file", "write", "append"]

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "追加内容"},
            "encoding": {"type": "string", "description": "编码", "default": "utf-8"}
        },
        "required": ["path", "content"]
    }

    def execute(self, path: str, content: str, encoding: str = "utf-8", **kwargs) -> ToolResult:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding=encoding) as f:
                f.write(content)
            return ToolResult(success=True, data={"path": path, "appended": len(content)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CopyFileTool(ToolSpec):
    """复制文件工具"""
    name = "file_copy"
    description = "复制文件或目录"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["file", "copy"]

    input_schema = {
        "type": "object",
        "properties": {
            "src": {"type": "string", "description": "源路径"},
            "dst": {"type": "string", "description": "目标路径"}
        },
        "required": ["src", "dst"]
    }

    def execute(self, src: str, dst: str, **kwargs) -> ToolResult:
        try:
            shutil.copy2(src, dst)
            return ToolResult(success=True, data={"copied": src, "to": dst})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MoveFileTool(ToolSpec):
    """移动文件工具"""
    name = "file_move"
    description = "移动文件或目录"
    permission_model = PermissionModel.CONFIRM
    risk_level = 2
    tags = ["file", "move"]

    input_schema = {
        "type": "object",
        "properties": {
            "src": {"type": "string", "description": "源路径"},
            "dst": {"type": "string", "description": "目标路径"}
        },
        "required": ["src", "dst"]
    }

    def execute(self, src: str, dst: str, **kwargs) -> ToolResult:
        try:
            shutil.move(src, dst)
            return ToolResult(success=True, data={"moved": src, "to": dst})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DeleteFileTool(ToolSpec):
    """删除文件工具（trash）"""
    name = "file_delete"
    description = "删除文件（移到回收站）"
    permission_model = PermissionModel.DENY
    risk_level = 3
    tags = ["file", "delete", "dangerous"]

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"}
        },
        "required": ["path"]
    }

    def execute(self, path: str, **kwargs) -> ToolResult:
        can, reason = self.can_execute()
        if not can:
            return ToolResult(success=False, error=reason)
        try:
            p = Path(path)
            if p.is_file():
                import send2trash
                send2trash.send2trash(path)
            else:
                shutil.rmtree(path)
            return ToolResult(success=True, data={"deleted": path})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ListDirTool(ToolSpec):
    """列出目录内容"""
    name = "list_dir"
    description = "列出目录下的文件/子目录"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["file", "read", "dir"]

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目录路径"},
            "pattern": {"type": "string", "description": "glob过滤"},
            "recursive": {"type": "boolean", "description": "递归", "default": False}
        }
    }

    def execute(self, path: str = ".", pattern: str = "*", recursive: bool = False, **kwargs) -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, error=f"目录不存在: {path}")
            if recursive:
                files = list(p.rglob(pattern))
            else:
                files = list(p.glob(pattern))
            items = [{"name": str(f.relative_to(p)), "is_dir": f.is_dir()} for f in files]
            return ToolResult(success=True, data={"path": path, "count": len(items), "items": items[:100]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileInfoTool(ToolSpec):
    """获取文件信息"""
    name = "file_info"
    description = "获取文件/目录的元信息"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["file", "read", "info"]

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"}
        },
        "required": ["path"]
    }

    def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, error=f"不存在: {path}")
            stat = p.stat()
            return ToolResult(success=True, data={
                "path": str(p.absolute()),
                "size": stat.st_size,
                "is_file": p.is_file(),
                "is_dir": p.is_dir(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SearchInFileTool(ToolSpec):
    """文件内容搜索"""
    name = "file_search"
    description = "在文件中搜索关键词"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["file", "search", "grep"]

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件/目录路径"},
            "keyword": {"type": "string", "description": "搜索关键词"},
            "case_sensitive": {"type": "boolean", "default": False},
            "recursive": {"type": "boolean", "default": True}
        },
        "required": ["path", "keyword"]
    }

    def execute(self, path: str, keyword: str, case_sensitive: bool = False,
                 recursive: bool = True, **kwargs) -> ToolResult:
        try:
            p = Path(path)
            matches = []
            kw = keyword if case_sensitive else keyword.lower()
            pattern = kw if case_sensitive else kw.lower()

            def search_in_file(fp: Path):
                try:
                    content = fp.read_text(encoding="utf-8", errors="ignore")
                    search_in = content if case_sensitive else content.lower()
                    for i, line in enumerate(search_in.split("\n"), 1):
                        if pattern in line:
                            matches.append({
                                "file": str(fp.relative_to(p.parent)),
                                "line": i,
                                "text": content.split("\n")[i-1][:100]
                            })
                except Exception:
                    pass

            if p.is_file():
                search_in_file(p)
            elif p.is_dir():
                for fp in p.rglob("*") if recursive else p.glob("*"):
                    if fp.is_file() and fp.suffix in (".py", ".md", ".txt", ".json", ".js"):
                        search_in_file(fp)

            return ToolResult(success=True, data={
                "keyword": keyword,
                "matches": matches[:50],
                "total": len(matches)
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class HashFileTool(ToolSpec):
    """计算文件哈希"""
    name = "file_hash"
    description = "计算文件的MD5/SHA256哈希"
    permission_model = PermissionModel.AUTO
    risk_level = 1
    tags = ["file", "hash", "checksum"]

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "algorithm": {"type": "string", "enum": ["md5", "sha256"], "default": "sha256"}
        },
        "required": ["path"]
    }

    def execute(self, path: str, algorithm: str = "sha256", **kwargs) -> ToolResult:
        try:
            h = hashlib.new(algorithm)
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return ToolResult(success=True, data={
                "path": path,
                "algorithm": algorithm,
                "hash": h.hexdigest()
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
