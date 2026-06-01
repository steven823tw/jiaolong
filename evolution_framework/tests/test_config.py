# -*- coding: utf-8 -*-
"""Tests for jiaolong_config module."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from jiaolong_config import (
    ensure_dirs,
    get_evolution_dir,
    get_experiments_dir,
    get_home,
    get_native_memory_dir,
    get_skills_dir,
    get_workspace,
)


class TestConfigPaths:
    def test_get_home(self):
        home = get_home()
        assert home.exists()
        assert home.is_dir()

    def test_get_workspace(self):
        workspace = get_workspace()
        assert workspace.exists()
        assert workspace.is_dir()

    def test_get_evolution_dir(self):
        evo = get_evolution_dir()
        assert evo.exists()
        assert evo.is_dir()

    def test_get_skills_dir(self):
        skills = get_skills_dir()
        assert isinstance(skills, Path)

    def test_get_experiments_dir(self):
        exp = get_experiments_dir()
        assert exp.exists()
        assert exp.is_dir()

    def test_get_native_memory_dir(self):
        native = get_native_memory_dir()
        assert isinstance(native, Path)
        assert "memory" in str(native)
        assert "C--cc" in str(native)

    def test_workspace_is_jiaolong_cowork(self):
        workspace = get_workspace()
        assert "jiaolong-cowork" in str(workspace)

    def test_ensure_dirs_creates_dirs(self):
        # Should not raise
        ensure_dirs()
        assert get_evolution_dir().exists()
        assert get_experiments_dir().exists()

    def test_path_relationships(self):
        workspace = get_workspace()
        assert str(get_evolution_dir()) == str(workspace / "evolution_framework")
        assert str(get_skills_dir()) == str(workspace / "skills")
