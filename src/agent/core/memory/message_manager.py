from typing import List, Dict, Optional
from datetime import datetime


class MessageManager:
    """Manages recent message history and conversations"""

    def __init__(self) -> None:
        self._messages: List[Dict] = []

    def add_message(
        self,
        content: str,
        role: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Add a new message to the history

        Args:
            content: Message content
            role: Role of the message sender
            timestamp: Optional message timestamp
        """
        self._messages.append(
            {
                "content": content,
                "role": role,
                "tool_calls": tool_calls,
                "tool_call_id": tool_id,
                "timestamp": (timestamp or datetime.now()).isoformat(),
            }
        )

    def get_messages(self) -> List[Dict]:
        """Get all messages"""
        return self._messages
