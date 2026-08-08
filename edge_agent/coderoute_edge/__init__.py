"""CodeRoute Center Edge Agent — daemon local de continuité d'examen."""

from .app import create_app
from .config import EdgeAgentConfig

__all__ = ["create_app", "EdgeAgentConfig"]
