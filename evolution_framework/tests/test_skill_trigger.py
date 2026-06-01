# -*- coding: utf-8 -*-
"""Tests for skill_trigger module."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from skill_trigger import DEFAULT_TRIGGERS, AutoTrigger


class TestDefaultTriggers:
    def test_recall_trigger(self):
        assert "/recall" in DEFAULT_TRIGGERS
        assert DEFAULT_TRIGGERS["/recall"] == "recall"

    def test_remember_trigger(self):
        assert "/remember" in DEFAULT_TRIGGERS
        assert DEFAULT_TRIGGERS["/remember"] == "remember"

    def test_evolve_trigger(self):
        assert "/evolve" in DEFAULT_TRIGGERS
        assert DEFAULT_TRIGGERS["/evolve"] == "evolve"

    def test_dream_trigger(self):
        assert "/dream" in DEFAULT_TRIGGERS
        assert DEFAULT_TRIGGERS["/dream"] == "dream"

    def test_monitor_trigger(self):
        assert "/monitor" in DEFAULT_TRIGGERS
        assert DEFAULT_TRIGGERS["/monitor"] == "monitor"

    def test_research_trigger(self):
        assert "/research" in DEFAULT_TRIGGERS
        assert DEFAULT_TRIGGERS["/research"] == "research"

    def test_chinese_triggers(self):
        assert "开始进化" in DEFAULT_TRIGGERS
        assert "整合记忆" in DEFAULT_TRIGGERS

    def test_trigger_count(self):
        assert len(DEFAULT_TRIGGERS) >= 20


class TestAutoTrigger:
    def test_create_trigger(self):
        trigger = AutoTrigger()
        assert trigger is not None

    def test_process_recall_command(self):
        trigger = AutoTrigger()
        result = trigger.process("/recall jiaolong")
        assert isinstance(result, dict)
        assert result.get("triggered") is True
        assert result.get("skill") == "recall"

    def test_process_evolve_command(self):
        trigger = AutoTrigger()
        result = trigger.process("/evolve")
        assert isinstance(result, dict)
        assert result.get("triggered") is True

    def test_process_no_match(self):
        trigger = AutoTrigger()
        result = trigger.process("hello world this is a normal message")
        assert isinstance(result, dict)
        assert result.get("triggered") is False

    def test_process_monitor_command(self):
        trigger = AutoTrigger()
        result = trigger.process("/monitor")
        assert isinstance(result, dict)
        assert result.get("triggered") is True
        assert result.get("skill") == "monitor"
