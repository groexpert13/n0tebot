"""
Database connection and utilities for Tribute integration
"""

import os
from typing import Optional
from .supabase_client import get_supabase


def get_db():
    """Get database connection"""
    supabase = get_supabase()
    if not supabase:
        raise ValueError("Database connection not available")
    return supabase
