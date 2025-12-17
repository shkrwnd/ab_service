"""Tests for assignment functionality.

Main stuff: idempotency and roughly even distribution.
"""
import pytest
from app.models import UserAssignment, Experiment, Variant
from app.services.assignment_service import get_or_create_assignment


def test_assignment_idempotency(db, sample_experiment):
    """Test that assignment is idempotent - same user gets same variant"""
    user_id = "test_user_123"
    experiment_id = sample_experiment.id
    
    # First assignment
    assignment1 = get_or_create_assignment(db, experiment_id, user_id)
    variant_id_1 = assignment1.variant_id
    
    # Second assignment - should return same variant
    assignment2 = get_or_create_assignment(db, experiment_id, user_id)
    variant_id_2 = assignment2.variant_id
    
    assert variant_id_1 == variant_id_2, "Assignment should be idempotent"
    assert assignment1.id == assignment2.id, "Should return same assignment object"
    
    # Verify only one assignment exists in DB
    count = db.query(UserAssignment).filter(
        UserAssignment.experiment_id == experiment_id,
        UserAssignment.user_id == user_id
    ).count()
    assert count == 1, "Should only have one assignment per user per experiment"


def test_traffic_allocation(db, sample_experiment):
    """Test that traffic allocation works correctly"""
    experiment_id = sample_experiment.id
    
    # Assign 100 users and check distribution
    assignments = {}
    for i in range(100):
        user_id = f"user_{i}"
        assignment = get_or_create_assignment(db, experiment_id, user_id)
        variant_id = assignment.variant_id
        assignments[variant_id] = assignments.get(variant_id, 0) + 1
    
    # Should have roughly 50/50 split (allowing some variance)
    variant_ids = list(assignments.keys())
    assert len(variant_ids) == 2, "Should have both variants"
    
    # Check that distribution is roughly even (within 20% tolerance)
    counts = list(assignments.values())
    ratio = min(counts) / max(counts) if max(counts) > 0 else 0
    assert ratio > 0.6, f"Traffic should be roughly even, got {assignments}"


def test_assignment_deterministic(db, sample_experiment):
    """Test that assignment is deterministic - same user+experiment always gets same variant"""
    user_id = "deterministic_user"
    experiment_id = sample_experiment.id
    
    # Get assignment
    assignment1 = get_or_create_assignment(db, experiment_id, user_id)
    variant_id_1 = assignment1.variant_id
    
    # Clear cache and get again - should still be same
    from app.utils.cache import assignment_cache
    assignment_cache.clear()
    
    assignment2 = get_or_create_assignment(db, experiment_id, user_id)
    variant_id_2 = assignment2.variant_id
    
    assert variant_id_1 == variant_id_2, "Assignment should be deterministic"


def test_assignment_inactive_experiment(db):
    """Test that assignment fails for inactive experiments"""
    experiment = Experiment(
        name="Inactive Experiment",
        status="paused"
    )
    db.add(experiment)
    db.flush()
    
    variant = Variant(
        experiment_id=experiment.id,
        name="control",
        traffic_percentage=100.0
    )
    db.add(variant)
    db.commit()
    
    with pytest.raises(Exception):  # Should raise HTTPException
        get_or_create_assignment(db, experiment.id, "test_user")

