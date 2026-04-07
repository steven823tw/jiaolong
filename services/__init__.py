# -*- coding: utf-8 -*-
"""
jiaolong Services 包
> 版本: v1.0 | 2026-04-02
> 包含: compact(上下文压缩) + daemon(后台服务)
"""
from .compact import (
    ConversationCompressor,
    ConversationChunk,
    ContextWindowManager,
    MessageImportance,
    compress_conversation,
)

from .daemon import (
    Daemon,
    DaemonEvent,
    DaemonEventQueue,
    DaemonJob,
    DaemonStatus,
    get_daemon,
)

__all__ = [
    # Compact
    "ConversationCompressor",
    "ConversationChunk",
    "ContextWindowManager",
    "MessageImportance",
    "compress_conversation",
    # Daemon
    "Daemon",
    "DaemonEvent",
    "DaemonEventQueue",
    "DaemonJob",
    "DaemonStatus",
    "get_daemon",
]

if __name__ == "__main__":
    print("=== jiaolong Services ===")
    print("compact: ContextWindowManager + ConversationCompressor")
    print("daemon: Daemon单例 + 定时任务调度")
