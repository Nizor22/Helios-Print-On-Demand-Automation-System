from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict

import orjson
from loguru import logger


@dataclass
class ActionRecord:
    """Record of a single action execution"""
    timestamp: str
    command: str
    parameters: dict[str, Any]
    result_summary: dict[str, Any]
    dry_run: bool
    success: bool
    error: Optional[str] = None


class ActionHistory:
    """Manages history of action executions"""
    
    def __init__(self, history_file: Optional[Path] = None):
        self.history_file = history_file or Path.home() / ".helios" / "history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()
    
    def _ensure_file(self) -> None:
        """Ensure history file exists"""
        if not self.history_file.exists():
            self.history_file.write_text("[]")
    
    def _load_history(self) -> list[dict[str, Any]]:
        """Load history from file"""
        try:
            content = self.history_file.read_bytes()
            return orjson.loads(content) if content else []
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []
    
    def _save_history(self, history: list[dict[str, Any]]) -> None:
        """Save history to file"""
        try:
            self.history_file.write_bytes(
                orjson.dumps(history, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
            )
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def add_record(self, record: ActionRecord) -> None:
        """Add a new action record to history"""
        history = self._load_history()
        history.append(asdict(record))
        
        # Keep only last 100 records
        if len(history) > 100:
            history = history[-100:]
        
        self._save_history(history)
        logger.info(f"Added action record: {record.command} at {record.timestamp}")
    
    def get_last_record(self) -> Optional[ActionRecord]:
        """Get the most recent action record"""
        history = self._load_history()
        if not history:
            return None
        
        last = history[-1]
        return ActionRecord(**last)
    
    def get_recent_records(self, limit: int = 10) -> list[ActionRecord]:
        """Get recent action records"""
        history = self._load_history()
        recent = history[-limit:] if history else []
        return [ActionRecord(**record) for record in reversed(recent)]
    
    def clear_history(self) -> None:
        """Clear all history"""
        self._save_history([])
        logger.info("Cleared action history")


# Global history instance
_history = ActionHistory()


def record_action(
    command: str,
    parameters: dict[str, Any],
    result_summary: dict[str, Any],
    dry_run: bool,
    success: bool,
    error: Optional[str] = None
) -> None:
    """Record an action execution"""
    record = ActionRecord(
        timestamp=datetime.now().isoformat(),
        command=command,
        parameters=parameters,
        result_summary=result_summary,
        dry_run=dry_run,
        success=success,
        error=error
    )
    _history.add_record(record)


def get_last_action() -> Optional[ActionRecord]:
    """Get the last recorded action"""
    return _history.get_last_record()


def get_recent_actions(limit: int = 10) -> list[ActionRecord]:
    """Get recent actions"""
    return _history.get_recent_records(limit)


def clear_history() -> None:
    """Clear action history"""
    _history.clear_history()