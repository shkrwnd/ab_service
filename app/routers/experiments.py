"""Experiment endpoints (basic CRUD-ish stuff).

Not super fancy, just wiring the request -> service calls.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_token
from app.schemas import ExperimentCreate, ExperimentResponse
from app.services.experiment_service import create_experiment, get_experiment_by_id

# Router for experiments APIs.
# NOTE: prefix means all routes in here start with /experiments (sorry if obvious)
router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentResponse, status_code=201)
def create_experiment_endpoint(
    experiment_data: ExperimentCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    # Create a new experiment.
    # Variants are included in payload. Service does the validations (sum=100 etc)
    # TODO: add some logging here maybe? (not urgent)
    exp = create_experiment(db, experiment_data)

    # returning it
    return exp


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment_endpoint(
    experiment_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    # Just fetch it from DB (service handles not found)
    exp = get_experiment_by_id(db, experiment_id)
    return exp

