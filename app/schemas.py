
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# from pydantic import validator
# from pydantic import ConfigDict
# from enum import Enum


class VariantCreate(BaseModel):
    name: str
    traffic_percentage: float = Field(..., ge=0, le=100)


class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    variants: List[VariantCreate]


class VariantResponse(BaseModel):
    id: int
    name: str
    traffic_percentage: float
    
    class Config:
        from_attributes = True


class ExperimentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    variants: List[VariantResponse]
    
    class Config:
        from_attributes = True


# Assignment schemas
class AssignmentResponse(BaseModel):
    experiment_id: int
    user_id: str
    variant_id: int
    variant_name: str
    assigned_at: datetime


class EventCreate(BaseModel):
    user_id: str
    # NOTE: we accept "type" in JSON but map to event_type internally
    type: str = Field(..., alias="event_type")
    timestamp: datetime
    properties: Optional[Dict[str, Any]] = None
    experiment_id: Optional[int] = None
    
    class Config:
        # Allow both "type" and "event_type"
        populate_by_name = True

    # @validator("timestamp")
    # def _validate_timestamp(cls, v: datetime) -> datetime:
    #     return v


class EventResponse(BaseModel):
    id: int
    user_id: str
    event_type: str
    timestamp: datetime
    properties: Optional[str] = None
    experiment_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class VariantMetrics(BaseModel):
    variant_id: int
    variant_name: str
    assigned_count: int
    event_count: int
    events_by_type: Dict[str, int]
    conversion_rate: float
    unique_users_with_events: int

    primary_event_type: Optional[str] = None
    primary_event_count: Optional[int] = None
    primary_unique_users: Optional[int] = None
    primary_conversion_rate: Optional[float] = None
    primary_events_per_assigned_user: Optional[float] = None


class ExperimentResults(BaseModel):
    experiment: ExperimentResponse
    summary: Dict[str, Any]
    variants: List[VariantMetrics]
    comparison: Optional[Dict[str, Any]] = None
    comparisons: Optional[List[Dict[str, Any]]] = None
    timeseries: Optional[List[Dict[str, Any]]] = None

# class EventType(str, Enum):
#     click = "click"
#     purchase = "purchase"

