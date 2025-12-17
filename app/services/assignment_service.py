"""Service for handling user assignments - ensures idempotency"""
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import DetachedInstanceError
from fastapi import HTTPException
from app.models import Experiment, Variant, UserAssignment
from app.utils.assignment import hash_user_experiment, assign_variant
from app.utils.cache import get_assignment, set_assignment, get_experiment, set_experiment


def get_or_create_assignment(
    db: Session, 
    experiment_id: int, 
    user_id: str
) -> UserAssignment:
    """
    Get existing assignment or create new one.
    This is the core idempotent assignment logic.
    """
    # First check cache
    cached = get_assignment(experiment_id, user_id)
    if cached:
        # Cache stores the assignment object, but we need to refresh from DB
        # to ensure we have the latest data
        assignment = db.query(UserAssignment).filter(
            UserAssignment.experiment_id == experiment_id,
            UserAssignment.user_id == user_id
        ).first()
        if assignment:
            return assignment
    
    # Check database for existing assignment
    assignment = db.query(UserAssignment).filter(
        UserAssignment.experiment_id == experiment_id,
        UserAssignment.user_id == user_id
    ).first()
    
    if assignment:
        # Cache it for next time
        set_assignment(experiment_id, user_id, assignment)
        return assignment

    
    # No assignment exists - create one
    # First, get experiment and variants
    experiment = get_experiment(experiment_id)
    if not experiment:
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        set_experiment(experiment_id, experiment)

    # Always enforce experiment status (even if experiment came from cache).
    # NOTE: cached ORM instances can be detached from the current Session, so
    # accessing attributes can raise DetachedInstanceError. Fetch status safely.
    try:
        status = experiment.status
    except DetachedInstanceError:
        status = db.query(Experiment.status).filter(Experiment.id == experiment_id).scalar()

    if status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Experiment is not active (status: {status})"
        )
    
    # Get variants for this experiment
    variants = db.query(Variant).filter(
        Variant.experiment_id == experiment_id
    ).order_by(Variant.id).all()
    
    if not variants:
        raise HTTPException(
            status_code=400, 
            detail="Experiment has no variants configured"
        )
    
    # Build list of (variant_id, traffic_percentage) for assignment logic
    variant_percentages = [(v.id, v.traffic_percentage) for v in variants]
    
    # Generate deterministic hash for this user+experiment
    hash_value = hash_user_experiment(user_id, experiment_id)
    
    # Assign to variant based on hash and traffic allocation
    variant_id = assign_variant(hash_value, variant_percentages)
    
    # Create and save assignment
    new_assignment = UserAssignment(
        experiment_id=experiment_id,
        user_id=user_id,
        variant_id=variant_id
    )
    
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    
    # Cache the new assignment
    set_assignment(experiment_id, user_id, new_assignment)
    
    return new_assignment

