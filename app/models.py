"""SQLAlchemy models for experiments, variants, assignments, and events.

These map to the tables in SQLite.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Experiment(Base):
    """Experiment model - represents an A/B test"""
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    # status values are like: draft, active, paused, completed
    status = Column(String, default="draft", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    variants = relationship("Variant", back_populates="experiment", cascade="all, delete-orphan")
    assignments = relationship("UserAssignment", back_populates="experiment", cascade="all, delete-orphan")
    
    # Index on status for filtering active experiments
    __table_args__ = (
        Index('idx_experiments_status', 'status'),
    )


class Variant(Base):
    """Variant model - represents a variant in an experiment"""
    __tablename__ = "variants"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    name = Column(String, nullable=False)
    traffic_percentage = Column(Float, nullable=False)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    experiment = relationship("Experiment", back_populates="variants")
    assignments = relationship("UserAssignment", back_populates="variant")
    
    # Index on experiment_id for faster lookups
    __table_args__ = (
        Index('idx_variants_experiment_id', 'experiment_id'),
    )


class UserAssignment(Base):
    """User assignment model - tracks which variant a user is assigned to"""
    __tablename__ = "user_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    experiment = relationship("Experiment", back_populates="assignments")
    variant = relationship("Variant", back_populates="assignments")
    
    # Unique constraint ensures idempotency - one assignment per user per experiment
    __table_args__ = (
        Index('idx_assignments_experiment_user', 'experiment_id', 'user_id', unique=True),
        Index('idx_assignments_user_id', 'user_id'),
    )


class Event(Base):
    """Event model - tracks user events/conversions"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)  # click, purchase, signup, etc.
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    properties = Column(Text, nullable=True)  # JSON string for flexible properties
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=True, index=True)
    
    # Relationship (optional - events might not always be linked to experiments)
    experiment = relationship("Experiment")
    
    # Indexes for common query patterns
    __table_args__ = (
        Index('idx_events_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_events_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_events_experiment_timestamp', 'experiment_id', 'timestamp'),
    )

