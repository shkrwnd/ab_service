
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import DetachedInstanceError
from fastapi import HTTPException
from app.models import Experiment, Variant, UserAssignment
from app.utils.assignment import hash_user_experiment, assign_variant
from app.utils.cache import get_assignment, set_assignment, get_experiment, set_experiment

# # from sqlalchemy.exc import IntegrityError
# # from sqlalchemy import select
# # from sqlalchemy.exc import NoResultFound


def get_or_create_assignment(
    db: Session, 
    experiment_id: int, 
    user_id: str
) -> UserAssignment:
    """
    Get existing assignment or create new one.
    This is the core idempotent assignment logic.
    """
    cached = get_assignment(experiment_id, user_id)
    if cached:
        # return cached
        # Cache stores the assignment object, but we need to refresh from DB
        # to ensure we have the latest data
        assignment = db.query(UserAssignment).filter(
            UserAssignment.experiment_id == experiment_id,
            UserAssignment.user_id == user_id
        ).first()
        if assignment:
            return assignment
    
    assignment = db.query(UserAssignment).filter(
        UserAssignment.experiment_id == experiment_id,
        UserAssignment.user_id == user_id
    ).first()
    
    if assignment:
        set_assignment(experiment_id, user_id, assignment)
        return assignment

    

    experiment = get_experiment(experiment_id)
    if not experiment:
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        set_experiment(experiment_id, experiment)
    # else:
    #     db.refresh(experiment)

    try:
        status = experiment.status
    except DetachedInstanceError:
        status = db.query(Experiment.status).filter(Experiment.id == experiment_id).scalar()

    if status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Experiment is not active (status: {status})"
        )
    # if status == "paused":
    #     raise HTTPException(status_code=400, detail="Experiment paused")
    

    variants = db.query(Variant).filter(
        Variant.experiment_id == experiment_id
    ).order_by(Variant.id).all()
    
    if not variants:
        raise HTTPException(
            status_code=400, 
            detail="Experiment has no variants configured"
        )
    
    variant_percentages = [(v.id, v.traffic_percentage) for v in variants]
    
    hash_value = hash_user_experiment(user_id, experiment_id)
    
    variant_id = assign_variant(hash_value, variant_percentages)
    

    new_assignment = UserAssignment(
        experiment_id=experiment_id,
        user_id=user_id,
        variant_id=variant_id
    )
    
    db.add(new_assignment)
    # db.flush()
    db.commit()
    db.refresh(new_assignment)
    
    set_assignment(experiment_id, user_id, new_assignment)
    
    return new_assignment

    # return assignment

