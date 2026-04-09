"""Database models for team pulse application."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team_memberships = relationship("TeamMember", back_populates="user")
    pulses = relationship("Pulse", back_populates="user")


class Team(Base):
    """Team model for organizing users."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("TeamMember", back_populates="team")
    pulses = relationship("Pulse", back_populates="team")
    analyses = relationship("Analysis", back_populates="team")


class TeamMember(Base):
    """Team membership association."""

    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), default="member")
    created_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


class Pulse(Base):
    """Pulse submission model for tracking team sentiment."""

    __tablename__ = "pulses"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mood = Column(String(50), nullable=False)
    energy_level = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="pulses")
    user = relationship("User", back_populates="pulses")


class Analysis(Base):
    """AI analysis results for team sentiment."""

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    summary = Column(Text, nullable=False)
    recommendations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="analyses")
