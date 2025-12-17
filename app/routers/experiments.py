"""Experiment endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_token
from app.schemas import ExperimentCreate, ExperimentResponse
from app.services.experiment_service import create_experiment, get_experiment_by_id

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentResponse, status_code=201)
def create_experiment_endpoint(
    experiment_data: ExperimentCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    Create a new experiment with variants.
    Traffic percentages must sum to 100%.
    """
    experiment = create_experiment(db, experiment_data)
    return experiment


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment_endpoint(
    experiment_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """Get experiment details by ID"""
    experiment = get_experiment_by_id(db, experiment_id)
    return experiment

