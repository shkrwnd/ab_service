
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
    variant_id: Optional[int] = None,
    primary_event_type: Optional[str] = None,
    group_by: Optional[str] = None
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

    # Validate grouping param early
    if group_by not in (None, "day", "hour"):
        raise HTTPException(status_code=400, detail="group_by must be one of: day, hour")
    
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
        primary_unique_users = set()
        primary_event_count = 0
        
        for event, assigned_at, v_id in variant_events:
            event_type = event.event_type
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
            unique_users.add(event.user_id)

            if primary_event_type and event.event_type == primary_event_type:
                primary_event_count += 1
                primary_unique_users.add(event.user_id)
        
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
            unique_users_with_events=len(unique_users),

            primary_event_type=primary_event_type,
            primary_event_count=primary_event_count if primary_event_type else None,
            primary_unique_users=len(primary_unique_users) if primary_event_type else None,
            primary_conversion_rate=(
                round((len(primary_unique_users) / assigned_count), 4)
                if (primary_event_type and assigned_count > 0) else (0.0 if primary_event_type else None)
            ),
            primary_events_per_assigned_user=(
                round((primary_event_count / assigned_count), 4)
                if (primary_event_type and assigned_count > 0) else (0.0 if primary_event_type else None)
            ),
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

    # SRM (Sample Ratio Mismatch): expected split (traffic %) vs observed assignments.
    # Uses chi-square goodness-of-fit; p-value uses Wilson–Hilferty normal approximation (no scipy).
    srm = None
    if total_assigned > 0 and len(variants) >= 2:
        expected_split = {v.id: float(v.traffic_percentage) for v in variants}
        observed_split = {}
        chi_square = 0.0

        # observed split based on assignments
        for vm in variant_metrics_list:
            observed_split[vm.variant_id] = (vm.assigned_count / total_assigned) * 100.0

        # chi-square stat
        for vm in variant_metrics_list:
            exp_cnt = total_assigned * (expected_split.get(vm.variant_id, 0.0) / 100.0)
            obs_cnt = vm.assigned_count
            if exp_cnt > 0:
                chi_square += ((obs_cnt - exp_cnt) ** 2) / exp_cnt

        df = max(len(variant_metrics_list) - 1, 1)

        def _norm_cdf(z: float) -> float:
            return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

        # Wilson–Hilferty transform to approximate chi-square survival function
        p_value = None
        if chi_square >= 0 and df > 0:
            w = ((chi_square / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(2.0 / (9.0 * df))
            # sf = 1 - cdf
            p_value = 1.0 - _norm_cdf(w)

        # Common SRM threshold in A/B testing is 0.01
        flagged = (p_value is not None) and (p_value < 0.01)

        srm = {
            "total_assigned": total_assigned,
            "expected_split_percent": {str(k): round(v, 4) for k, v in expected_split.items()},
            "observed_split_percent": {str(k): round(v, 4) for k, v in observed_split.items()},
            "chi_square": round(chi_square, 6),
            "df": df,
            "p_value": None if p_value is None else round(p_value, 8),
            "flagged": flagged,
        }

    # Stats helper: baseline vs variant (two-proportion z-test)
    def _norm_cdf(z: float) -> float:
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

    def _compare_variants(baseline: VariantMetrics, treatment: VariantMetrics) -> Dict[str, Any]:
        # Choose which conversion to use: primary (if requested) otherwise default.
        if primary_event_type:
            x1 = baseline.primary_unique_users or 0
            n1 = baseline.assigned_count
            x2 = treatment.primary_unique_users or 0
            n2 = treatment.assigned_count
            p1 = baseline.primary_conversion_rate or 0.0
            p2 = treatment.primary_conversion_rate or 0.0
        else:
            x1 = baseline.unique_users_with_events
            n1 = baseline.assigned_count
            x2 = treatment.unique_users_with_events
            n2 = treatment.assigned_count
            p1 = baseline.conversion_rate
            p2 = treatment.conversion_rate

        # Lift based on chosen conversion rate
        if p1 > 0:
            lift = ((p2 - p1) / p1) * 100
        else:
            lift = 0.0 if p2 == 0 else float('inf')

        alpha = 0.05
        z_score = None
        p_value = None
        significant = None
        conf_int_95 = None

        if n1 > 0 and n2 > 0:
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

        return {
            "baseline": baseline.variant_name,
            "baseline_variant_id": baseline.variant_id,
            "treatment": treatment.variant_name,
            "treatment_variant_id": treatment.variant_id,
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
            "metric": primary_event_type or "any_event",
        }

    # Multi-variant comparisons (each vs baseline)
    comparisons = None
    comparison = None  # keep old field for backwards compatibility (baseline vs first treatment)
    if len(variant_metrics_list) >= 2:
        baseline = variant_metrics_list[0]
        comparisons = []
        for vm in variant_metrics_list[1:]:
            comparisons.append(_compare_variants(baseline, vm))

        comparison = comparisons[0] if comparisons else None

    # Time-series aggregation (optional)
    timeseries = None
    if group_by in ("day", "hour"):
        # Pull assignments for bucketing assigned users
        assignments_q = db.query(UserAssignment).filter(UserAssignment.experiment_id == experiment_id)
        if variant_id:
            assignments_q = assignments_q.filter(UserAssignment.variant_id == variant_id)
        assignments = assignments_q.all()

        def _bucket_key(dt: datetime) -> str:
            if group_by == "hour":
                return dt.replace(minute=0, second=0, microsecond=0).isoformat()
            return dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        # assigned per bucket + variant
        assigned_by_bucket: Dict[str, Dict[int, int]] = {}
        for a in assignments:
            b = _bucket_key(a.assigned_at)
            assigned_by_bucket.setdefault(b, {})
            assigned_by_bucket[b][a.variant_id] = assigned_by_bucket[b].get(a.variant_id, 0) + 1

        # conversions/events per bucket + variant (from event_results)
        events_by_bucket: Dict[str, Dict[int, int]] = {}
        conv_users_by_bucket: Dict[str, Dict[int, set]] = {}
        for e, assigned_at, v_id in event_results:
            b = _bucket_key(e.timestamp)
            events_by_bucket.setdefault(b, {})
            events_by_bucket[b][v_id] = events_by_bucket[b].get(v_id, 0) + 1

            # conversion user tracking (primary if requested, otherwise any event)
            if (primary_event_type is None) or (e.event_type == primary_event_type):
                conv_users_by_bucket.setdefault(b, {})
                conv_users_by_bucket[b].setdefault(v_id, set())
                conv_users_by_bucket[b][v_id].add(e.user_id)

        # Build rows sorted by time
        all_buckets = sorted(set(assigned_by_bucket.keys()) | set(events_by_bucket.keys()) | set(conv_users_by_bucket.keys()))
        timeseries = []
        for b in all_buckets:
            row = {"bucket": b, "group_by": group_by, "metric": primary_event_type or "any_event", "variants": []}
            for v in variants:
                a_cnt = assigned_by_bucket.get(b, {}).get(v.id, 0)
                e_cnt = events_by_bucket.get(b, {}).get(v.id, 0)
                conv_users = conv_users_by_bucket.get(b, {}).get(v.id, set())
                conv_cnt = len(conv_users)
                rate = (conv_cnt / a_cnt) if a_cnt > 0 else 0.0
                row["variants"].append({
                    "variant_id": v.id,
                    "variant_name": v.name,
                    "assigned": a_cnt,
                    "events": e_cnt,
                    "conversions": conv_cnt,
                    "conversion_rate": round(rate, 4),
                })
            timeseries.append(row)
    
    # Reporting: Executive summary, insights, recommendations
    insights = None
    recommendation = None
    confidence_level = None
    winning_variant = None
    comparison_matrix = None
    
    if len(variant_metrics_list) >= 2 and comparisons:
        # Determine winning variant (highest conversion rate, if significant)
        best_comp = None
        best_lift = float('-inf')
        for comp in comparisons:
            if comp.get("significant") and comp.get("lift_percentage", 0) > best_lift:
                best_lift = comp["lift_percentage"]
                best_comp = comp
        
        if best_comp:
            winning_variant_id = best_comp["treatment_variant_id"]
            winning_vm = next((vm for vm in variant_metrics_list if vm.variant_id == winning_variant_id), None)
            if winning_vm:
                winning_variant = {
                    "variant_id": winning_vm.variant_id,
                    "variant_name": winning_vm.variant_name,
                    "conversion_rate": winning_vm.primary_conversion_rate if primary_event_type else winning_vm.conversion_rate,
                    "lift_percentage": best_comp["lift_percentage"],
                    "p_value": best_comp["p_value"],
                    "metric": primary_event_type or "any_event"
                }
        
        baseline = variant_metrics_list[0]
        metric_name = primary_event_type or "any_event"
        baseline_rate = baseline.primary_conversion_rate if primary_event_type else baseline.conversion_rate
        
        if best_comp:
            lift = best_comp["lift_percentage"]
            p_val = best_comp["p_value"]
            treatment_name = best_comp["treatment"]
            insights = f"{treatment_name} shows {abs(lift):.1f}% {'increase' if lift > 0 else 'decrease'} in {metric_name} conversion rate vs {baseline.variant_name} ({baseline_rate:.1%} → {baseline_rate * (1 + lift/100):.1%}). "
            insights += f"Statistically significant (p={p_val:.4f})."
        elif comparisons:
            # No significant winner
            max_lift = max((c.get("lift_percentage", 0) for c in comparisons), default=0)
            if abs(max_lift) < 5:
                insights = f"No significant difference between variants. All variants show similar {metric_name} conversion rates (within 5%)."
            else:
                best_non_sig = max(comparisons, key=lambda c: c.get("lift_percentage", 0))
                p_val_str = f"{best_non_sig.get('p_value', 1.0):.4f}" if best_non_sig.get('p_value') is not None else "N/A"
                insights = f"{best_non_sig['treatment']} shows {best_non_sig['lift_percentage']:.1f}% lift vs {baseline.variant_name}, but not statistically significant (p={p_val_str}). More data needed."
        

        if best_comp and best_comp.get("significant"):
            if best_comp["lift_percentage"] > 0:
                recommendation = f"Launch {best_comp['treatment']} variant. Shows significant positive lift."
            else:
                recommendation = f"Keep {baseline.variant_name} (baseline). Treatment shows significant negative impact."
        elif comparisons:
            p_values = [c.get("p_value") for c in comparisons if c.get("p_value") is not None]
            min_p = min(p_values) if p_values else 1.0
            if min_p < 0.10:  # trending but not significant
                recommendation = "Continue experiment. Results trending toward significance. Collect more data."
            else:
                recommendation = "No clear winner. Continue experiment or consider stopping if sufficient sample size reached."
        else:
            recommendation = "Insufficient data for recommendation. Continue experiment."
        
        # Determine confidence level
        if comparisons:
            has_significant = any(c.get("significant") for c in comparisons)
            min_sample = min((vm.assigned_count for vm in variant_metrics_list), default=0)
            p_vals = [c.get("p_value") for c in comparisons if c.get("p_value") is not None]
            avg_p = sum(p_vals) / len(p_vals) if p_vals else 1.0
            
            if has_significant and min_sample >= 100:
                confidence_level = "High"
            elif has_significant or (min_sample >= 50 and avg_p < 0.15):
                confidence_level = "Medium"
            else:
                confidence_level = "Low"
        else:
            confidence_level = "Low"
        
        # Build comparison matrix (table-friendly format)
        comparison_matrix = []
        baseline = variant_metrics_list[0]
        baseline_rate = baseline.primary_conversion_rate if primary_event_type else baseline.conversion_rate
        
        for vm in variant_metrics_list:
            comp = next((c for c in comparisons if c.get("treatment_variant_id") == vm.variant_id), None)
            row = {
                "variant_id": vm.variant_id,
                "variant_name": vm.variant_name,
                "assigned_count": vm.assigned_count,
                "conversion_rate": vm.primary_conversion_rate if primary_event_type else vm.conversion_rate,
                "vs_baseline_lift": comp["lift_percentage"] if comp else 0.0,
                "vs_baseline_p_value": comp["p_value"] if comp else None,
                "vs_baseline_significant": comp.get("significant") if comp else False,
                "metric": primary_event_type or "any_event"
            }
            comparison_matrix.append(row)
    
    # Report metadata
    report_metadata = {
        "report_generated_at": datetime.now().isoformat(),
        "experiment_status": experiment.status,
        "data_coverage": round((total_assigned / max(experiment.created_at.timestamp(), 1)) * 100, 2) if total_assigned > 0 else 0.0,
        "experiment_health": "healthy" if (srm and not srm.get("flagged")) and (total_assigned > 0) else ("warning" if total_assigned == 0 else "critical")
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
        comparison=comparison,
        comparisons=comparisons,
        timeseries=timeseries,
        srm=srm,
        insights=insights,
        recommendation=recommendation,
        confidence_level=confidence_level,
        winning_variant=winning_variant,
        comparison_matrix=comparison_matrix,
        report_metadata=report_metadata
    )

    # return ExperimentResults(experiment=experiment_response, summary=summary, variants=[], comparison=None)

