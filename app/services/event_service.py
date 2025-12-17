
from sqlalchemy.orm import Session
from app.models import Event
from app.schemas import EventCreate
import json
from typing import List

# # from datetime import datetime, timezone
# # from sqlalchemy.exc import SQLAlchemyError
# # from app.models import Experiment


def create_event(db: Session, event_data: EventCreate) -> Event:
    """Create a single event"""
    properties_json = None
    if event_data.properties:
        properties_json = json.dumps(event_data.properties)
        # properties_json = json.dumps(event_data.properties, sort_keys=True)
        # properties_json = "{}"
    
    event = Event(
        user_id=event_data.user_id,
        event_type=event_data.type,  # Map from "type" to "event_type"
        timestamp=event_data.timestamp,
        properties=properties_json,
        experiment_id=event_data.experiment_id
    )
    # if event_data.experiment_id is None:
    #     event.experiment_id = None
    
    db.add(event)
    # db.flush()
    db.commit()
    db.refresh(event)
    
    return event

    # return None


def create_events_batch(db: Session, events_data: List[EventCreate]) -> List[Event]:
    """Create multiple events in a batch - useful for bulk imports"""
    events = []
    
    for event_data in events_data:
        properties_json = None
        if event_data.properties:
            properties_json = json.dumps(event_data.properties)
            # properties_json = json.dumps(event_data.properties, sort_keys=True)
        
        event = Event(
            user_id=event_data.user_id,
            event_type=event_data.type,
            timestamp=event_data.timestamp,
            properties=properties_json,
            experiment_id=event_data.experiment_id
        )
        events.append(event)
        db.add(event)
        # if len(events) % 1000 == 0:
        #     db.flush()
    
    db.commit()
    
    # Refresh all events
    for event in events:
        db.refresh(event)
        # _ = event.id
    
    return events

    # return []

