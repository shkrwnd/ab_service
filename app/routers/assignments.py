"""Assignment endpoints.

This is the endpoint that returns which variant a user gets.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_token
from app.schemas import AssignmentResponse
from app.services.assignment_service import get_or_create_assignment

router = APIRouter(prefix="/experiments", tags=["assignments"])


@router.get("/{experiment_id}/assignment/{user_id}", response_model=AssignmentResponse)
def get_assignment_endpoint(
    experiment_id: int,
    user_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    Get or create user assignment for an experiment.
    This endpoint is idempotent - calling it multiple times with the same
    user_id and experiment_id will always return the same assignment.
    """
    # Do the main logic in the service
    assignment = get_or_create_assignment(db, experiment_id, user_id)
    
    return AssignmentResponse(
        experiment_id=assignment.experiment_id,
        user_id=assignment.user_id,
        variant_id=assignment.variant_id,
        variant_name=assignment.variant.name,
        assigned_at=assignment.assigned_at
    )

