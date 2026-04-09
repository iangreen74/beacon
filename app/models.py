"""Database models for pulse tracking and team management."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Index
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Team(Base):
    """Team entity for organizing users and pulses."""
    
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    users = relationship("User", back_populates="team")
    pulses = relationship("Pulse", back_populates="team")


class User(Base):
    """User entity with team membership."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    team = relationship("Team", back_populates="users")
    pulses = relationship("Pulse", back_populates="user")


class Pulse(Base):
    """Pulse submission tracking mood and feedback."""
    
    __tablename__ = "pulses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    mood_score = Column(Float, nullable=False)
    feedback_text = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    user = relationship("User", back_populates="pulses")
    team = relationship("Team", back_populates="pulses")
    
    __table_args__ = (
        Index("idx_pulses_team_created", "team_id", "created_at"),
        Index("idx_pulses_user_created", "user_id", "created_at"),
    )
