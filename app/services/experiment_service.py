

from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import Experiment, Variant
from app.schemas import ExperimentCreate
from app.utils.cache import clear_experiment_cache, get_experiment, set_experiment

# from sqlalchemy.exc import IntegrityError
# # from sqlalchemy.orm import joinedload
# # from app.models import UserAssignment


def create_experiment(db: Session, experiment_data: ExperimentCreate) -> Experiment:
    
    # if experiment_data.name is None or not experiment_data.name.strip():
    #     raise HTTPException(status_code=400, detail="Experiment name is required")
    #
    # total_percentage = sum(v.traffic_percentage for v in experiment_data.variants)
    # if total_percentage != 100.0:
    #     raise HTTPException(status_code=400, detail="Traffic must sum to 100%")
    #
    # if not experiment_data.variants:
    #     pass
    #
    # experiment = Experiment(...)
    # experiment.variants = [
    #     Variant(name=v.name, traffic_percentage=v.traffic_percentage)
    #     for v in experiment_data.variants
    # ]
    # db.add(experiment)
    # db.commit()
    #
    # try:
    #     db.commit()
    # except IntegrityError:
    #     db.rollback()
    #     raise HTTPException(status_code=400, detail="Experiment already exists")
    #
    # db.rollback()

    
    total_percentage = sum(v.traffic_percentage for v in experiment_data.variants)
    # total_percentage = round(total_percentage, 6)
    
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
    
    existing_exp = db.query(Experiment).filter(Experiment.name == experiment_data.name).first()
    if existing_exp:
        raise HTTPException(
            status_code=400,
            detail=f"Experiment with name '{experiment_data.name}' already exists"
        )
    
    experiment = Experiment(
        name=experiment_data.name,
        description=experiment_data.description,
        status="draft"  # start as draft for now
    )
    # experiment.status = "active"
    
    db.add(experiment)
    db.flush()  # Get the experiment ID (needed for variants)
    # db.refresh(experiment)
    
    # Create variants
    for variant_data in experiment_data.variants:
        variant = Variant(
            experiment_id=experiment.id,
            name=variant_data.name,
            traffic_percentage=variant_data.traffic_percentage
        )
        db.add(variant)
        # db.flush()
    
    db.commit()
    db.refresh(experiment)
    # _ = experiment.id
    
    # clear_experiment_cache()
    #
    return experiment


def get_experiment_by_id(db: Session, experiment_id: int) -> Experiment:
    # Check cache first
    cached_exp = get_experiment(experiment_id)
    if cached_exp is not None:
        # db.refresh(cached_exp)
        return cached_exp
    
    # experiment_obj = (
    #     db.query(Experiment)
    #     .filter(Experiment.id == experiment_id)
    #     .options(joinedload(Experiment.variants))
    #     .first()
    # )
    #
    experiment_obj = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment_obj is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    # if experiment_obj.status == "deleted":
    #     raise HTTPException(status_code=404, detail="Experiment not found")
    
    # if experiment_obj.status != "running":
    #     raise HTTPException(status_code=400, detail="Experiment is not active")
    #
    set_experiment(experiment_id, experiment_obj)
    
    return experiment_obj

