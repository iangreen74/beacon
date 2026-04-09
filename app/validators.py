"""Input validation and sanitization utilities.

Provides Pydantic validators, input sanitization functions, and SQL injection
prevention helpers for API request validation and data processing.
"""

import re
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


class ErrorResponse(BaseModel):
    """Consistent error response format across all endpoints."""

    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[Any] = Field(None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")


class PulseSubmissionValidator(BaseModel):
    """Validator for pulse submission requests."""

    sentiment_score: int = Field(..., ge=1, le=5, description="Sentiment score 1-5")
    feedback_text: Optional[str] = Field(None, max_length=2000)
    team_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)

    @validator("feedback_text")
    def sanitize_feedback_text(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize feedback text for AI API calls and storage."""
        if v is None:
            return v
        # Remove control characters except newlines and tabs
        sanitized = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", v)
        # Limit consecutive whitespace
        sanitized = re.sub(r"\s{10,}", " ", sanitized)
        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()
        return sanitized if sanitized else None


class TeamCreationValidator(BaseModel):
    """Validator for team creation requests."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    manager_id: int = Field(..., gt=0)

    @validator("name")
    def sanitize_team_name(cls, v: str) -> str:
        """Sanitize team name and validate format."""
        # Remove control characters
        sanitized = re.sub(r"[\x00-\x1f\x7f]", "", v)
        sanitized = sanitized.strip()
        if not sanitized:
            raise ValueError("Team name cannot be empty after sanitization")
        # Prevent SQL injection patterns
        if re.search(r"[;'\"\\]", sanitized):
            raise ValueError("Team name contains invalid characters")
        return sanitized

    @validator("description")
    def sanitize_description(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize description text."""
        if v is None:
            return v
        sanitized = re.sub(r"[\x00-\x1f\x7f]", "", v)
        sanitized = sanitized.strip()
        return sanitized if sanitized else None


class NotificationPreferencesValidator(BaseModel):
    """Validator for notification preferences."""

    email_enabled: bool = Field(default=True)
    reminder_frequency: str = Field(default="weekly", regex="^(daily|weekly|monthly)$")
    email_address: Optional[str] = Field(None, max_length=255)

    @validator("email_address")
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v is None:
            return v
        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email address format")
        return v.lower()


def sanitize_sql_parameter(value: str) -> str:
    """Sanitize SQL parameters to prevent injection.
    
    Args:
        value: Raw parameter value
        
    Returns:
        Sanitized parameter value safe for SQL usage
    """
    if not isinstance(value, str):
        return value
    # Remove dangerous SQL characters and keywords
    sanitized = re.sub(r"[;'\"\\]", "", value)
    # Block common SQL injection patterns
    blocked_patterns = [
        r"\bDROP\b", r"\bDELETE\b", r"\bINSERT\b", r"\bUPDATE\b",
        r"\bEXEC\b", r"\bUNION\b", r"--", r"/\*", r"\*/", r"xp_"
    ]
    for pattern in blocked_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise ValueError(f"Potentially malicious SQL pattern detected: {pattern}")
    return sanitized


def sanitize_ai_input(text: str, max_length: int = 2000) -> str:
    """Sanitize text input before sending to AI APIs.
    
    Args:
        text: Raw text input
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text safe for AI API calls
    """
    if not text:
        return ""
    # Remove control characters except newlines and tabs
    sanitized = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize whitespace
    sanitized = re.sub(r"\s+", " ", sanitized)
    # Truncate to max length
    sanitized = sanitized[:max_length]
    # Strip and validate
    sanitized = sanitized.strip()
    return sanitized
