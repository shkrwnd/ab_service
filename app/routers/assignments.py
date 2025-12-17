from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_token
from app.schemas import AssignmentResponse
from app.services.assignment_service import get_or_create_assignment

# # from fastapi import HTTPException
# # from typing import Optional
# # from app.schemas import AssignmentResponse

router = APIRouter(prefix="/experiments", tags=["assignments"])


@router.get("/{experiment_id}/assignment/{user_id}", response_model=AssignmentResponse)
def get_assignment_endpoint(
    experiment_id: int,
    user_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    # no idea if we want this endpoint name later but ok for now
    # Do the main logic in the service
    # user_id = user_id.strip()
    assignment = get_or_create_assignment(db, experiment_id, user_id)
    
    return AssignmentResponse(
        experiment_id=assignment.experiment_id,
        user_id=assignment.user_id,
        variant_id=assignment.variant_id,
        variant_name=assignment.variant.name,
        assigned_at=assignment.assigned_at
    )

