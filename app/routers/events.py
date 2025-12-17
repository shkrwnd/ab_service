
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Union
from app.database import get_db
from app.auth import verify_token
from app.schemas import EventCreate, EventResponse
from app.services.event_service import create_event, create_events_batch

# # from fastapi import HTTPException
# # from fastapi import BackgroundTasks
# # from datetime import datetime

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=Union[EventResponse, List[EventResponse]], status_code=201)
def create_event_endpoint(
    event_data: Union[EventCreate, List[EventCreate]],
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    if isinstance(event_data, list):
        # Batch creation
        # if not event_data:
        #     return []
        events = create_events_batch(db, event_data)
        out = []
        for e in events:
            out.append(EventResponse(
                id=e.id,
                user_id=e.user_id,
                event_type=e.event_type,
                timestamp=e.timestamp,
                properties=e.properties,
                experiment_id=e.experiment_id
            ))
        return out
    else:
        # event_data = EventCreate.model_validate(event_data)
        event = create_event(db, event_data)
        return EventResponse(
            id=event.id,
            user_id=event.user_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            properties=event.properties,
            experiment_id=event.experiment_id
        )

