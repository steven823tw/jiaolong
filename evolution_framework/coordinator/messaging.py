# -*- coding: utf-8 -*-
"""
jiaolong协调器 - Task-CO-3: Agent间消息传递协议
> 版本: v1.0 | 2026-04-02
> 用途: Agent间直接消息传递
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import threading


class MessageType(str, Enum):
    """消息类型"""
    TASK = "task"       # 任务分配
    RESULT = "result"   # 结果返回
    STATUS = "status"   # 状态更新
    ERROR = "error"     # 错误通知
    PROGRESS = "progress"  # 进度报告
    ACK = "ack"         # 确认消息


class Message:
    """Agent间消息"""
    _id_counter = 0

    def __init__(self, msg_id: str = None):
        if msg_id:
            self.msg_id = msg_id
        else:
            Message._id_counter += 1
            self.msg_id = f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{Message._id_counter:03d}"

        self.to: str = ""           # 目标Agent角色
        self.from_: str = ""        # 来源Agent角色
        self.type: MessageType = MessageType.TASK
        self.content: Any = None    # 消息内容
        self.context: Dict = {}      # 上下文
        self.reply_to: str = None   # 回复的消息ID
        self.timestamp: str = datetime.now().isoformat()
        self.delivered: bool = False
        self.delivered_at: str = None

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "to": self.to,
            "from": self.from_,
            "type": self.type.value if isinstance(self.type, Enum) else self.type,
            "content": self.content,
            "context": self.context,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
            "delivered": self.delivered,
            "delivered_at": self.delivered_at,
        }

    def deliver(self):
        """标记为已送达"""
        self.delivered = True
        self.delivered_at = datetime.now().isoformat()

    def reply(self, content: Any, msg_type: MessageType = MessageType.RESULT) -> "Message":
        """发送回复消息"""
        reply_msg = Message()
        reply_msg.to = self.from_
        reply_msg.from_ = self.to
        reply_msg.type = msg_type
        reply_msg.content = content
        reply_msg.reply_to = self.msg_id
        return reply_msg

    def __repr__(self):
        return f"Message({self.msg_id} {self.type.value} {self.from_}->{self.to})"


class MessageBus:
    """
    消息总线（单例）
    所有Agent间消息通过此总线中转
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._messages: List[Message] = []
        self._inbox: Dict[str, List[Message]] = {}  # agent -> messages
        self._history: List[Message] = []

    def send(self, message: Message) -> bool:
        """
        发送消息（放入收件箱）
        真实环境：通过 sessions_spawn 做Agent通信
        """
        if not message.to:
            return False

        self._messages.append(message)
        self._history.append(message)

        # 放入目标inbox
        if message.to not in self._inbox:
            self._inbox[message.to] = []
        self._inbox[message.to].append(message)

        return True

    def receive(self, agent: str, mark_read: bool = False) -> List[Message]:
        """获取收件箱消息"""
        messages = self._inbox.get(agent, [])
        if mark_read:
            for msg in messages:
                msg.deliver()
        return messages

    def unread_count(self, agent: str) -> int:
        """未读消息数"""
        inbox = self._inbox.get(agent, [])
        return sum(1 for m in inbox if not m.delivered)

    def history(self, agent: str = None, limit: int = 100) -> List[Message]:
        """消息历史"""
        if agent:
            return [m for m in self._history if m.from_ == agent or m.to == agent][-limit:]
        return self._history[-limit:]

    def clear_inbox(self, agent: str):
        """清空收件箱"""
        self._inbox[agent] = []

    def stats(self) -> dict:
        return {
            "total_messages": len(self._messages),
            "agents_with_mail": len(self._inbox),
            "total_history": len(self._history),
        }


class SendMessageTool:
    """
    Agent间发送消息工具
    封装 MessageBus.send()
    """

    def send_task(self, to_agent: str, task: str,
                  from_agent: str = "boss",
                  context: Dict = None) -> Message:
        """发送任务消息"""
        msg = Message()
        msg.to = to_agent
        msg.from_ = from_agent
        msg.type = MessageType.TASK
        msg.content = {"task": task}
        msg.context = context or {}

        bus = MessageBus()
        success = bus.send(msg)

        return msg if success else None

    def send_result(self, to_agent: str, result: Any,
                    from_agent: str = "boss",
                    reply_to: str = None) -> Message:
        """发送结果消息"""
        msg = Message()
        msg.to = to_agent
        msg.from_ = from_agent
        msg.type = MessageType.RESULT
        msg.content = {"result": result}
        msg.reply_to = reply_to

        bus = MessageBus()
        success = bus.send(msg)

        return msg if success else None

    def send_status(self, to_agent: str, status: str,
                    from_agent: str = "boss",
                    progress: float = None) -> Message:
        """发送状态消息"""
        msg = Message()
        msg.to = to_agent
        msg.from_ = from_agent
        msg.type = MessageType.STATUS
        msg.content = {"status": status, "progress": progress}

        bus = MessageBus()
        success = bus.send(msg)

        return msg if success else None

    def send_error(self, to_agent: str, error: str,
                   from_agent: str = "boss") -> Message:
        """发送错误消息"""
        msg = Message()
        msg.to = to_agent
        msg.from_ = from_agent
        msg.type = MessageType.ERROR
        msg.content = {"error": error}

        bus = MessageBus()
        success = bus.send(msg)

        return msg if success else None


class ReceiveMessageTool:
    """接收消息工具"""

    def receive(self, agent: str, mark_read: bool = True) -> List[Message]:
        """接收所有消息"""
        bus = MessageBus()
        return bus.receive(agent, mark_read=mark_read)

    def unread(self, agent: str) -> int:
        """未读数量"""
        bus = MessageBus()
        return bus.unread_count(agent)

    def peek(self, agent: str, limit: int = 10) -> List[Message]:
        """查看消息（不标记已读）"""
        bus = MessageBus()
        return bus.receive(agent, mark_read=False)[:limit]


if __name__ == "__main__":
    print("=== MessageBus 验证 ===")

    bus = MessageBus()

    sender = SendMessageTool()

    # 小笨 -> 小呆：搜集情报
    msg1 = sender.send_task(
        to_agent="intel",
        task="搜集今日A股成交额Top100",
        from_agent="boss",
        context={"priority": "high", "team_id": "team-001"}
    )
    print(f"发送: {msg1}")

    # 小笨 -> 小傻：执行任务
    msg2 = sender.send_task(
        to_agent="ux",
        task="生成量化选股Dashboard",
        from_agent="boss",
    )
    print(f"发送: {msg2}")

    # 查看小呆收件箱
    inbox = ReceiveMessageTool().peek("intel")
    print(f"\n小呆收件箱: {len(inbox)} 条")
    for m in inbox:
        print(f"  {m.msg_id} [{m.type.value}] {m.from_}: {m.content}")

    # 查看统计
    print(f"\n总线统计: {bus.stats()}")
