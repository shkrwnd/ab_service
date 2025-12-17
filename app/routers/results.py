"""Results/analytics endpoints.

Returns aggregated stats for an experiment.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from app.database import get_db
from app.auth import verify_token
from app.schemas import ExperimentResults
from app.services.results_service import get_experiment_results

router = APIRouter(prefix="/experiments", tags=["results"])


@router.get("/{experiment_id}/results", response_model=ExperimentResults)
def get_results_endpoint(
    experiment_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering events (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering events (ISO format)"),
    event_type: Optional[str] = Query(None, description="Filter by specific event type"),
    variant_id: Optional[int] = Query(None, description="Filter by specific variant ID")
):
    """
    Get experiment performance results.
    
    Only counts events that occur AFTER a user's assignment timestamp.
    Supports filtering by date range, event type, and variant.
    
    Returns metrics including:
    - Total assigned users per variant
    - Event counts and breakdowns by type
    - Conversion rates
    - Comparison/lift metrics between variants
    """
    # actual calculations are inside the service
    results = get_experiment_results(
        db=db,
        experiment_id=experiment_id,
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        variant_id=variant_id
    )
    
    return results

