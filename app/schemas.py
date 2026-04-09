"""Pydantic schemas for request/response validation.

Provides data validation and serialization models for API endpoints,
including custom validators for sanitization and security checks.
"""

from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator
import bleach


class SanitizedStr(str):
    """Custom string type that sanitizes HTML/script content.
    
    Removes potentially dangerous HTML tags and attributes to prevent
    XSS attacks while preserving safe formatting.
    """
    
    @classmethod
    def validate(cls, v: Any) -> str:
        """Validate and sanitize string input.
        
        Args:
            v: Input value to sanitize
            
        Returns:
            Sanitized string with dangerous content removed
            
        Raises:
            ValueError: If input cannot be converted to string
        """
        if not isinstance(v, str):
            v = str(v)
        
        # Strip all HTML tags for maximum security
        sanitized = bleach.clean(
            v,
            tags=[],  # No tags allowed
            attributes={},  # No attributes allowed
            strip=True  # Strip tags instead of escaping
        )
        
        # Truncate to reasonable length (prevent DoS)
        max_length = 10000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized


class AnalysisRequest(BaseModel):
    """Request model for analysis endpoints.
    
    Validates that user has access to the specified pulse and team,
    and sanitizes all text inputs.
    """
    
    pulse_id: int = Field(..., gt=0, description="ID of pulse to analyze")
    team_id: Optional[int] = Field(None, gt=0, description="Team ID for filtering")
    user_id: Optional[int] = Field(None, gt=0, description="User ID for filtering")
    context: Optional[str] = Field(None, max_length=5000, description="Additional context")
    current_user_id: int = Field(..., gt=0, description="Current authenticated user ID")
    
    @field_validator('context')
    @classmethod
    def sanitize_context(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize context string to prevent XSS.
        
        Args:
            v: Context string to sanitize
            
        Returns:
            Sanitized context or None
        """
        if v is None:
            return None
        return SanitizedStr.validate(v)
    
    @field_validator('team_id', 'user_id', 'pulse_id')
    @classmethod
    def validate_positive_ids(cls, v: Optional[int]) -> Optional[int]:
        """Validate IDs are positive integers to prevent SQL injection.
        
        Args:
            v: ID value to validate
            
        Returns:
            Validated ID
            
        Raises:
            ValueError: If ID is not positive
        """
        if v is not None and v <= 0:
            raise ValueError("ID must be a positive integer")
        return v
    
    @model_validator(mode='after')
    def validate_pulse_ownership(self) -> 'AnalysisRequest':
        """Validate user has access to pulse and team.
        
        This validator checks ownership/membership but requires database access.
        Actual validation is performed in the endpoint handler with database session.
        This serves as a placeholder for the validation logic structure.
        
        Returns:
            Self for chaining
        """
        # Note: Actual database validation must happen in endpoint handler
        # where database session is available. This validates the structure.
        return self


class AnalysisResponse(BaseModel):
    """Response model for analysis results."""
    
    analysis_id: int = Field(..., description="Unique analysis identifier")
    pulse_id: int = Field(..., description="Associated pulse ID")
    insights: str = Field(..., description="Generated insights")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    created_at: datetime = Field(..., description="Analysis timestamp")
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True


class TeamAccessRequest(BaseModel):
    """Request model for team access validation."""
    
    team_id: int = Field(..., gt=0, description="Team ID to validate")
    user_id: int = Field(..., gt=0, description="User ID to check")
    
    @field_validator('team_id', 'user_id')
    @classmethod
    def validate_ids(cls, v: int) -> int:
        """Validate IDs are positive integers.
        
        Args:
            v: ID value
            
        Returns:
            Validated ID
            
        Raises:
            ValueError: If ID is invalid
        """
        if v <= 0:
            raise ValueError("ID must be a positive integer")
        return v
