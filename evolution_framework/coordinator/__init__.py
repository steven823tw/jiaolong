# -*- coding: utf-8 -*-
"""
jiaolong协调器 - coordinator package
> 版本: v1.0 | 2026-04-02
> 包含: 5个模块（Task-CO-1 ~ CO-5）
"""
from .decomposer import TaskDecomposer, TaskTree, TaskNode, TaskStatus
from .role_matcher import RoleMatcher, TaskToRoleAssigner, AgentRole, ROLE_META
from .messaging import MessageBus, MessageType, Message, SendMessageTool, ReceiveMessageTool
from .state_sync import TaskStateManager, TaskState as StateState
from .team_mode import TeamOrchestrator, TeamStatus, TeamStatusTool

# 兼容性别名
TaskState = TaskStatus  # 避免与state_sync.TaskState重名

__all__ = [
    # Decomposer
    "TaskDecomposer",
    "TaskTree",
    "TaskNode",
    "TaskStatus",
    # Role Matcher
    "RoleMatcher",
    "TaskToRoleAssigner",
    "AgentRole",
    "ROLE_META",
    # Messaging
    "MessageBus",
    "MessageType",
    "Message",
    "SendMessageTool",
    "ReceiveMessageTool",
    # State Sync
    "TaskStateManager",
    # Team Mode
    "TeamOrchestrator",
    "TeamStatus",
    "TeamStatusTool",
]


if __name__ == "__main__":
    print("=== jiaolong协调器 - 模块加载 ===")
    print("TaskDecomposer:", TaskDecomposer)
    print("RoleMatcher:", RoleMatcher)
    print("MessageBus:", MessageBus)
    print("TaskStateManager:", TaskStateManager)
    print("TeamOrchestrator:", TeamOrchestrator)
