"""Experiment service.

This file has the experiment logic (creating + fetching).
Probably could be cleaned up later but works for now.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import Experiment, Variant
from app.schemas import ExperimentCreate
from app.utils.cache import clear_experiment_cache, get_experiment, set_experiment


def create_experiment(db: Session, experiment_data: ExperimentCreate) -> Experiment:
    """
    Create a new experiment with variants.

    Stuff we validate:
    - traffic percentages total should be 100 (give or take float rounding)
    - should have at least 1 variant
    - experiment name should not already exist
    """
    # Validate traffic percentages
    total_percentage = sum(v.traffic_percentage for v in experiment_data.variants)
    
    # Float check, since sometimes it can be 99.999 etc
    if abs(total_percentage - 100.0) > 0.1:
        raise HTTPException(
            status_code=400,
            detail=f"Variant traffic percentages must sum to 100% (got {total_percentage}%)"
        )
    
    if not experiment_data.variants:
        raise HTTPException(
            status_code=400,
            detail="Experiment must have at least one variant"
        )
    
    # Check if experiment name already exists
    existing_exp = db.query(Experiment).filter(Experiment.name == experiment_data.name).first()
    if existing_exp:
        raise HTTPException(
            status_code=400,
            detail=f"Experiment with name '{experiment_data.name}' already exists"
        )
    
    # Create experiment and variants in one go
    experiment = Experiment(
        name=experiment_data.name,
        description=experiment_data.description,
        status="draft"  # start as draft for now
    )
    
    db.add(experiment)
    db.flush()  # Get the experiment ID (needed for variants)
    
    # Create variants
    for variant_data in experiment_data.variants:
        # make variant row
        variant = Variant(
            experiment_id=experiment.id,
            name=variant_data.name,
            traffic_percentage=variant_data.traffic_percentage
        )
        db.add(variant)
    
    db.commit()
    db.refresh(experiment)
    
    return experiment


def get_experiment_by_id(db: Session, experiment_id: int) -> Experiment:
    """Get experiment by id (tries cache first)."""
    # Check cache first
    cached_exp = get_experiment(experiment_id)
    if cached_exp is not None:
        return cached_exp
    
    experiment_obj = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment_obj is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Cache it
    set_experiment(experiment_id, experiment_obj)
    
    return experiment_obj

