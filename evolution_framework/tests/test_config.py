# -*- coding: utf-8 -*-
"""Tests for jiaolong_config module."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from jiaolong_config import (
    get_evolution_dir,
    get_experiments_dir,
    get_home,
    get_memory_dir,
    get_native_memory_dir,
    get_skills_dir,
    get_workspace,
    memory_hot_path,
)


# ─────────────────────────────────────────────────────────────────────────────
# Path functions
# ─────────────────────────────────────────────────────────────────────────────


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

    def test_get_memory_dir(self):
        mem = get_memory_dir()
        assert isinstance(mem, Path)

    def test_get_native_memory_dir(self):
        native = get_native_memory_dir()
        assert isinstance(native, Path)
        assert "memory" in str(native)

    def test_memory_hot_path(self):
        hot = memory_hot_path()
        assert isinstance(hot, Path)
        assert "memory_hot.json" in str(hot)

    def test_workspace_is_jiaolong_cowork(self):
        workspace = get_workspace()
        assert "jiaolong-cowork" in str(workspace)
