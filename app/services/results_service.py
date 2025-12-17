
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.models import Experiment, Variant, UserAssignment, Event
from app.schemas import ExperimentResults, VariantMetrics, ExperimentResponse, VariantResponse
from fastapi import HTTPException
import math

# # from sqlalchemy import select
# # from math import isfinite
# # from collections import defaultdict


def get_experiment_results(
    db: Session,
    experiment_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    event_type: Optional[str] = None,
    variant_id: Optional[int] = None
) -> ExperimentResults:
    """
    Calculate experiment results with various filters.
    Only counts events that occur AFTER user's assignment timestamp.
    """
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    # if experiment.status != "active":
    #     raise HTTPException(status_code=400, detail="Experiment is not active")
    
    # Get all variants for this experiment
    variants_query = db.query(Variant).filter(Variant.experiment_id == experiment_id)
    if variant_id:
        variants_query = variants_query.filter(Variant.id == variant_id)
    variants = variants_query.all()
    # variants = variants_query.order_by(Variant.id).all()
    
    if not variants:
        raise HTTPException(status_code=400, detail="Experiment has no variants")
    

    # This is the key requirement: events must be after assigned_at
    # TODO: Could optimize this query for very large datasets with better indexing
    events_query = db.query(
        Event,
        UserAssignment.assigned_at,
        UserAssignment.variant_id
    ).join(
        UserAssignment,
        and_(
            Event.user_id == UserAssignment.user_id,
            Event.experiment_id == UserAssignment.experiment_id,
            Event.timestamp >= UserAssignment.assigned_at  # Only after assignment
        )
    ).filter(
        UserAssignment.experiment_id == experiment_id
    )
    
    # Apply filters
    if start_date:
        events_query = events_query.filter(Event.timestamp >= start_date)
    if end_date:
        events_query = events_query.filter(Event.timestamp <= end_date)
    if event_type:
        events_query = events_query.filter(Event.event_type == event_type)
    if variant_id:
        events_query = events_query.filter(UserAssignment.variant_id == variant_id)
    # events_query = events_query.limit(1000)
    
    event_results = events_query.all()
    
    variant_metrics_list = []
    total_assigned = 0
    total_events = 0
    
    for variant in variants:
        assigned_count = db.query(func.count(UserAssignment.id)).filter(
            UserAssignment.experiment_id == experiment_id,
            UserAssignment.variant_id == variant.id
        ).scalar() or 0
        
        total_assigned += assigned_count
        
        variant_events = [
            (e, assigned_at, v_id) for e, assigned_at, v_id in event_results
            if v_id == variant.id
        ]
        
        event_count = len(variant_events)
        total_events += event_count
        
        events_by_type = {}
        unique_users = set()
        
        for event, assigned_at, v_id in variant_events:
            event_type = event.event_type
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
            unique_users.add(event.user_id)
        
        conversion_rate = 0.0
        if assigned_count > 0:
            conversion_rate = len(unique_users) / assigned_count
        # conversion_rate = 0.0 if assigned_count == 0 else (event_count / assigned_count)
        
        variant_metrics = VariantMetrics(
            variant_id=variant.id,
            variant_name=variant.name,
            assigned_count=assigned_count,
            event_count=event_count,
            events_by_type=events_by_type,
            conversion_rate=round(conversion_rate, 4),
            unique_users_with_events=len(unique_users)
        )
        
        variant_metrics_list.append(variant_metrics)
    
    summary = {
        "total_assigned": total_assigned,
        "total_events": total_events,
        "date_range": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None
        }
    }
    
    comparison = None
    if len(variant_metrics_list) >= 2:
        baseline = variant_metrics_list[0]
        treatment = variant_metrics_list[1]
        
        if baseline.conversion_rate > 0:
            lift = ((treatment.conversion_rate - baseline.conversion_rate) / baseline.conversion_rate) * 100
        else:
            lift = 0.0 if treatment.conversion_rate == 0 else float('inf')

        # --- Statistical significance (two-proportion z-test) ---
        x1 = baseline.unique_users_with_events
        n1 = baseline.assigned_count
        x2 = treatment.unique_users_with_events
        n2 = treatment.assigned_count

        alpha = 0.05  # 95% confidence

        def _norm_cdf(z: float) -> float:
            return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

        z_score = None
        p_value = None
        significant = None
        conf_int_95 = None  # CI for (p2 - p1)

        if n1 > 0 and n2 > 0:
            p1 = x1 / n1
            p2 = x2 / n2

            # pooled proportion for z-test
            p_pool = (x1 + x2) / (n1 + n2)
            se = math.sqrt(max(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2), 0.0))
            if se > 0:
                z_score = (p2 - p1) / se
                p_value = 2.0 * (1.0 - _norm_cdf(abs(z_score)))
                significant = p_value < alpha

            # 95% CI for difference in proportions (unpooled SE)
            se_diff = math.sqrt(max((p1 * (1.0 - p1) / n1) + (p2 * (1.0 - p2) / n2), 0.0))
            if se_diff > 0:
                z_crit = 1.96
                lo = (p2 - p1) - z_crit * se_diff
                hi = (p2 - p1) + z_crit * se_diff
                conf_int_95 = {"diff_low": round(lo, 6), "diff_high": round(hi, 6)}

        comparison = {
            "baseline": baseline.variant_name,
            "treatment": treatment.variant_name,
            "lift_percentage": round(lift, 2),
            "alpha": alpha,
            "baseline_assigned": n1,
            "treatment_assigned": n2,
            "baseline_converted": x1,
            "treatment_converted": x2,
            "z_score": None if z_score is None else round(z_score, 6),
            "p_value": None if p_value is None else round(p_value, 8),
            "significant": significant,
            "conversion_rate_diff_ci_95": conf_int_95,
        }
    
    experiment_response = ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        status=experiment.status,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        variants=[VariantResponse(
            id=v.id,
            name=v.name,
            traffic_percentage=v.traffic_percentage
        ) for v in variants]
    )
    
    return ExperimentResults(
        experiment=experiment_response,
        summary=summary,
        variants=variant_metrics_list,
        comparison=comparison
    )

    # return ExperimentResults(experiment=experiment_response, summary=summary, variants=[], comparison=None)

