"""
Memory management for multi-turn conversations.

This module provides conversation state management for L4 queries.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""
    turn_id: int
    timestamp: datetime
    query: str
    response: str
    context_used: List[str]  # Sources/tools used


class MemoryManager:
    """Base class for memory management strategies."""
    
    def save_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Save a conversation turn to persistent storage."""
        raise NotImplementedError
    
    def get_history(self, session_id: str, last_n: Optional[int] = None) -> List[ConversationTurn]:
        """Retrieve conversation history for a session."""
        raise NotImplementedError
    
    def format_for_llm(self, history: List[ConversationTurn]) -> str:
        """Format conversation history for LLM context."""
        raise NotImplementedError
    
    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        raise NotImplementedError


class BufferMemory(MemoryManager):
    """Store all turns, send all to LLM."""
    
    def __init__(self):
        """Initialize buffer memory with in-memory storage."""
        self.sessions: Dict[str, List[ConversationTurn]] = {}
    
    def save_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Save a conversation turn."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(turn)
    
    def get_history(self, session_id: str, last_n: Optional[int] = None) -> List[ConversationTurn]:
        """Retrieve conversation history."""
        history = self.sessions.get(session_id, [])
        if last_n:
            return history[-last_n:]
        return history
    
    def format_for_llm(self, history: List[ConversationTurn]) -> str:
        """Format conversation history for LLM context."""
        if not history:
            return ""
        
        formatted = "Previous conversation:\n\n"
        for turn in history:
            formatted += f"User: {turn.query}\n"
            formatted += f"Assistant: {turn.response}\n\n"
        return formatted
    
    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]


class WindowMemory(MemoryManager):
    """Store all turns, send only last N to LLM."""
    
    def __init__(self, window_size: int = 5):
        """
        Initialize window memory.
        
        Args:
            window_size: Number of recent turns to include in context
        """
        self.window_size = window_size
        self.sessions: Dict[str, List[ConversationTurn]] = {}
    
    def save_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Save a conversation turn."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(turn)
    
    def get_history(self, session_id: str, last_n: Optional[int] = None) -> List[ConversationTurn]:
        """Retrieve conversation history."""
        history = self.sessions.get(session_id, [])
        n = last_n or self.window_size
        return history[-n:]
    
    def format_for_llm(self, history: List[ConversationTurn]) -> str:
        """Format conversation history for LLM context."""
        if not history:
            return ""
        
        formatted = f"Recent conversation (last {len(history)} turns):\n\n"
        for turn in history:
            formatted += f"User: {turn.query}\n"
            formatted += f"Assistant: {turn.response}\n\n"
        return formatted
    
    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
