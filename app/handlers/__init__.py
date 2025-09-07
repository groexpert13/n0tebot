from .start import router as start_router
from .misc import router as misc_router
from .notes import router as notes_router
from .commands import router as commands_router
from .ai import router as ai_router

__all__ = ["start_router", "misc_router", "notes_router", "commands_router", "ai_router"]
