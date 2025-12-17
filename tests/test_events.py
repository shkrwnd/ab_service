"""Tests for event recording.

Just basic tests for event create + batch create.
"""
import pytest
from datetime import datetime
from app.models import Event
from app.services.event_service import create_event, create_events_batch
from app.schemas import EventCreate


def test_create_single_event(db):
    """Test creating a single event"""
    event_data = EventCreate(
        user_id="user_123",
        type="click",
        timestamp=datetime.now(),
        properties={"button": "signup", "page": "home"}
    )
    
    event = create_event(db, event_data)
    
    assert event.id is not None
    assert event.user_id == "user_123"
    assert event.event_type == "click"
    assert event.properties is not None  # Should be JSON string
    
    # Verify it's in the database
    db_event = db.query(Event).filter(Event.id == event.id).first()
    assert db_event is not None
    assert db_event.user_id == "user_123"


def test_create_event_without_properties(db):
    """Test creating event without optional properties"""
    event_data = EventCreate(
        user_id="user_456",
        type="page_view",
        timestamp=datetime.now()
    )
    
    event = create_event(db, event_data)
    
    assert event.id is not None
    assert event.properties is None


def test_create_events_batch(db):
    """Test batch event creation"""
    events_data = [
        EventCreate(
            user_id=f"user_{i}",
            type="click",
            timestamp=datetime.now(),
            properties={"index": i}
        )
        for i in range(5)
    ]
    
    events = create_events_batch(db, events_data)
    
    assert len(events) == 5
    assert all(e.id is not None for e in events)
    
    # Verify all are in database
    db_events = db.query(Event).filter(Event.user_id.like("user_%")).all()
    assert len(db_events) >= 5

