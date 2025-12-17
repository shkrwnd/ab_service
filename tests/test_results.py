"""Tests for results calculation.

These tests check the rules like "only events after assignment count".
"""
import pytest
from datetime import datetime, timedelta
from app.models import UserAssignment, Event
from app.services.results_service import get_experiment_results
from app.services.assignment_service import get_or_create_assignment
from app.services.event_service import create_event
from app.schemas import EventCreate


def test_results_only_counts_events_after_assignment(db, sample_experiment):
    user_id = "results_user"
    experiment_id = sample_experiment.id
    
    # Create assignment
    assignment = get_or_create_assignment(db, experiment_id, user_id)
    assignment_time = assignment.assigned_at
    
    # Create event BEFORE assignment (should not be counted)
    event_before = EventCreate(
        user_id=user_id,
        type="click",
        timestamp=assignment_time - timedelta(hours=1),
        experiment_id=experiment_id
    )
    create_event(db, event_before)
    
    # Create event AFTER assignment (should be counted)
    event_after = EventCreate(
        user_id=user_id,
        type="purchase",
        timestamp=assignment_time + timedelta(hours=1),
        experiment_id=experiment_id
    )
    create_event(db, event_after)
    
    results = get_experiment_results(db, experiment_id)
    
    variant_metrics = next(
        (v for v in results.variants if v.variant_id == assignment.variant_id),
        None
    )
    
    assert variant_metrics is not None
    # Should only count the event after assignment
    assert variant_metrics.event_count == 1
    assert variant_metrics.events_by_type.get("purchase", 0) == 1
    assert variant_metrics.events_by_type.get("click", 0) == 0


def test_results_conversion_rate(db, sample_experiment):
    """Test conversion rate calculation"""
    experiment_id = sample_experiment.id
    
    # Assign 10 users to first variant (keep generating users until we have 10 that land there)
    variant = sample_experiment.variants[0]
    users_with_events = []
    assigned_to_variant = 0
    i = 0
    
    while assigned_to_variant < 10:
        user_id = f"user_{i}"
        assignment = get_or_create_assignment(db, experiment_id, user_id)
        
        if assignment.variant_id != variant.id:
            i += 1
            continue

        assigned_to_variant += 1

        if assigned_to_variant <= 5:
            event = EventCreate(
                user_id=user_id,
                type="purchase",
                timestamp=assignment.assigned_at + timedelta(minutes=1),
                experiment_id=experiment_id
            )
            create_event(db, event)
            users_with_events.append(user_id)
        i += 1
    
    # Get results
    results = get_experiment_results(db, experiment_id)
    
    variant_metrics = next(
        (v for v in results.variants if v.variant_id == variant.id),
        None
    )
    
    assert variant_metrics is not None
    assert variant_metrics.assigned_count == 10
    assert variant_metrics.unique_users_with_events == 5
    # Conversion rate should be 5/10 = 0.5
    assert variant_metrics.conversion_rate == 0.5


def test_results_with_date_filter(db, sample_experiment):
    """Test results filtering by date range"""
    user_id = "date_filter_user"
    experiment_id = sample_experiment.id
    
    assignment = get_or_create_assignment(db, experiment_id, user_id)
    assignment_time = assignment.assigned_at
    
    # Create events at different times
    event1 = EventCreate(
        user_id=user_id,
        type="click",
        timestamp=assignment_time + timedelta(days=1),
        experiment_id=experiment_id
    )
    create_event(db, event1)
    
    event2 = EventCreate(
        user_id=user_id,
        type="click",
        timestamp=assignment_time + timedelta(days=5),
        experiment_id=experiment_id
    )
    create_event(db, event2)
    
    # Filter to only first 3 days
    start_date = assignment_time
    end_date = assignment_time + timedelta(days=3)
    
    results = get_experiment_results(
        db, 
        experiment_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Should only count event1 (within date range)
    total_events = sum(v.event_count for v in results.variants)
    assert total_events == 1


def test_results_primary_metric(db, sample_experiment):
    experiment_id = sample_experiment.id

    variant = sample_experiment.variants[0]
    assigned_to_variant = 0
    i = 0

    while assigned_to_variant < 10:
        user_id = f"pm_user_{i}"
        assignment = get_or_create_assignment(db, experiment_id, user_id)
        if assignment.variant_id != variant.id:
            i += 1
            continue

        assigned_to_variant += 1
        if assigned_to_variant <= 5:
            create_event(db, EventCreate(
                user_id=user_id,
                type="purchase",
                timestamp=assignment.assigned_at + timedelta(minutes=1),
                experiment_id=experiment_id
            ))
        else:
            # Non-primary event should not count toward primary conversion
            create_event(db, EventCreate(
                user_id=user_id,
                type="click",
                timestamp=assignment.assigned_at + timedelta(minutes=1),
                experiment_id=experiment_id
            ))
        i += 1

    results = get_experiment_results(db, experiment_id, primary_event_type="purchase")
    variant_metrics = next((v for v in results.variants if v.variant_id == variant.id), None)
    assert variant_metrics is not None

    assert variant_metrics.primary_event_type == "purchase"
    assert variant_metrics.primary_event_count == 5
    assert variant_metrics.primary_unique_users == 5
    assert variant_metrics.primary_conversion_rate == 0.5


def test_results_comparison(db, sample_experiment):
    """Test that comparison/lift is calculated correctly"""
    experiment_id = sample_experiment.id
    
    # Assign users and create events for both variants
    variant_a = sample_experiment.variants[0]
    variant_b = sample_experiment.variants[1]
    
    # Variant A: 10 users, 5 conversions (50%)
    for i in range(10):
        user_id = f"variant_a_user_{i}"
        assignment = get_or_create_assignment(db, experiment_id, user_id)
        if assignment.variant_id == variant_a.id and i < 5:
            event = EventCreate(
                user_id=user_id,
                type="purchase",
                timestamp=assignment.assigned_at + timedelta(minutes=1),
                experiment_id=experiment_id
            )
            create_event(db, event)
    
    # Variant B: 10 users, 7 conversions (70%)
    for i in range(10):
        user_id = f"variant_b_user_{i}"
        assignment = get_or_create_assignment(db, experiment_id, user_id)
        if assignment.variant_id == variant_b.id and i < 7:
            event = EventCreate(
                user_id=user_id,
                type="purchase",
                timestamp=assignment.assigned_at + timedelta(minutes=1),
                experiment_id=experiment_id
            )
            create_event(db, event)
    
    results = get_experiment_results(db, experiment_id)
    
    # Should have comparison data
    assert results.comparison is not None
    # Lift should be positive (70% vs 50% = 40% lift)
    assert results.comparison["lift_percentage"] > 0

    # Basic sanity checks for significance fields
    assert "p_value" in results.comparison
    assert "z_score" in results.comparison
    assert "significant" in results.comparison

    # Multi-variant comparisons should be present too
    assert results.comparisons is not None
    assert len(results.comparisons) >= 1
    assert all("p_value" in c for c in results.comparisons)
    assert all("treatment_variant_id" in c for c in results.comparisons)


def test_results_timeseries_group_by_day(db, sample_experiment):
    """Basic timeseries output with group_by=day"""
    experiment_id = sample_experiment.id

    # Create a couple assignments and move them across days
    a1 = get_or_create_assignment(db, experiment_id, "ts_user_1")
    a2 = get_or_create_assignment(db, experiment_id, "ts_user_2")

    # Put one assignment "yesterday"
    yesterday = a1.assigned_at - timedelta(days=1)
    a1.assigned_at = yesterday
    db.add(a1)
    db.commit()
    db.refresh(a1)

    # Events after assignment so they count
    create_event(db, EventCreate(
        user_id=a1.user_id,
        type="purchase",
        timestamp=a1.assigned_at + timedelta(minutes=10),
        experiment_id=experiment_id
    ))
    create_event(db, EventCreate(
        user_id=a2.user_id,
        type="purchase",
        timestamp=a2.assigned_at + timedelta(minutes=10),
        experiment_id=experiment_id
    ))

    results = get_experiment_results(db, experiment_id, group_by="day", primary_event_type="purchase")
    assert results.timeseries is not None
    assert len(results.timeseries) >= 1
    assert results.timeseries[0]["group_by"] == "day"

