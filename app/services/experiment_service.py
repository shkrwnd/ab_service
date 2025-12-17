"""Service for experiment management"""
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import Experiment, Variant
from app.schemas import ExperimentCreate
from app.utils.cache import clear_experiment_cache, get_experiment, set_experiment


def create_experiment(db: Session, experiment_data: ExperimentCreate) -> Experiment:
    """
    Create a new experiment with variants.
    Validates that traffic percentages sum to 100% (with small tolerance for floating point).
    """
    # Validate traffic percentages
    total_percentage = sum(v.traffic_percentage for v in experiment_data.variants)
    
    # Allow small floating point differences (e.g., 99.99 or 100.01)
    # This prevents issues with floating point precision
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
    existing = db.query(Experiment).filter(Experiment.name == experiment_data.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Experiment with name '{experiment_data.name}' already exists"
        )
    
    # Create experiment and variants in a transaction
    experiment = Experiment(
        name=experiment_data.name,
        description=experiment_data.description,
        status="draft"  # Start as draft, can be activated later
    )
    
    db.add(experiment)
    db.flush()  # Get the experiment ID
    
    # Create variants
    for variant_data in experiment_data.variants:
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
    """Get experiment by ID, with caching"""
    # Check cache first
    cached = get_experiment(experiment_id)
    if cached:
        return cached
    
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Cache it
    from app.utils.cache import set_experiment
    set_experiment(experiment_id, experiment)
    
    return experiment

