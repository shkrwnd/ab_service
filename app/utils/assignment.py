"""Helper functions for deterministic user assignment.

This does a basic hash and then picks a variant based on traffic %.
"""
import hashlib


def hash_user_experiment(user_id: str, experiment_id: int) -> int:
    """
    Generate a deterministic hash value for user+experiment combination.
    Returns a value between 0-99 for traffic allocation.
    """
    # Combine user_id and experiment_id for hashing
    combined = f"{user_id}_{experiment_id}"
    
    # Use MD5 hash and take modulo 100 to get 0-99 range
    # MD5 is fine for this use case - we just need deterministic distribution
    # Not using it for security, just for consistent hashing
    hash_obj = hashlib.md5(combined.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    
    return hash_int % 100


def assign_variant(hash_value: int, variants_with_percentages: list) -> int:
    """
    Assign variant based on hash value and traffic percentages.
    
    Args:
        hash_value: Integer 0-99 from hash function
        variants_with_percentages: List of tuples (variant_id, traffic_percentage)
    
    Returns:
        variant_id that user should be assigned to
    """
    # Build cumulative buckets
    # Example: [30, 70] -> [0-29: variant1, 30-99: variant2]
    cumulative = 0
    for variant_id, percentage in variants_with_percentages:
        cumulative += percentage
        if hash_value < cumulative:
            return variant_id
    
    # Fallback to last variant (shouldn't happen if percentages sum to 100)
    return variants_with_percentages[-1][0]

