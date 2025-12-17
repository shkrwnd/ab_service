"""Experiment endpoints (basic CRUD-ish stuff)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_token
from app.schemas import ExperimentCreate, ExperimentResponse
from app.services.experiment_service import create_experiment, get_experiment_by_id

# Router for experiments APIs.
# NOTE: prefix means all routes in here start with /experiments
router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentResponse, status_code=201)
def create_experiment_endpoint(
    experiment_data: ExperimentCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    Create a new experiment.

    It also creates variants. The service layer does validation like making sure
    traffic % totals 100.
    """
    # TODO: maybe add logging here later?
    created_experiment = create_experiment(db, experiment_data)

    # Return the created thing back to the caller
    return created_experiment


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment_endpoint(
    experiment_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """Get experiment by id."""
    # Just fetch it from DB (service handles not found)
    experiment_obj = get_experiment_by_id(db, experiment_id)

    # Return it
    return experiment_obj

