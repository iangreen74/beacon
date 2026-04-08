from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="team")
    pulses = relationship("Pulse", back_populates="team")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team = relationship("Team", back_populates="users")
    pulse_responses = relationship("PulseResponse", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Pulse(Base):
    __tablename__ = "pulses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team = relationship("Team", back_populates="pulses")
    responses = relationship("PulseResponse", back_populates="pulse")
    analysis_results = relationship("AnalysisResult", back_populates="pulse")


class PulseResponse(Base):
    __tablename__ = "pulse_responses"

    id = Column(Integer, primary_key=True, index=True)
    pulse_id = Column(Integer, ForeignKey("pulses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    sentiment_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pulse = relationship("Pulse", back_populates="responses")
    user = relationship("User", back_populates="pulse_responses")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    pulse_id = Column(Integer, ForeignKey("pulses.id"), nullable=False)
    analysis_type = Column(String(100), nullable=False)
    result_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    pulse = relationship("Pulse", back_populates="analysis_results")


__all__ = [
    "Base",
    "Team",
    "User",
    "Pulse",
    "PulseResponse",
    "Notification",
    "AnalysisResult",
]
