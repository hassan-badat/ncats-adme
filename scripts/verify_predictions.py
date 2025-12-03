#!/usr/bin/env python
"""
Compare baseline predictions to verify model outputs haven't changed.

Use this script after making code changes to ensure predictions remain identical.

Usage:
    python scripts/verify_predictions.py baseline_predictions.json updated_predictions.json

Requirements:
    pip install requests
"""

import json
import argparse
import sys
from typing import Any, Dict, List, Tuple


def load_baseline(filepath: str) -> dict:
    """Load a baseline predictions file."""
    with open(filepath, "r") as f:
        return json.load(f)


def compare_predictions(
    baseline: dict, 
    updated: dict, 
    tolerance: float = 1e-6
) -> Tuple[bool, List[str]]:
    """
    Compare two prediction result sets.
    
    Args:
        baseline: Original baseline predictions
        updated: New predictions to compare
        tolerance: Tolerance for floating point comparisons
    
    Returns:
        Tuple of (all_match, list_of_differences)
    """
    differences = []
    
    # Compare models tested
    baseline_models = set(baseline.get("predictions", {}).keys())
    updated_models = set(updated.get("predictions", {}).keys())
    
    if baseline_models != updated_models:
        missing = baseline_models - updated_models
        extra = updated_models - baseline_models
        if missing:
            differences.append(f"Missing models in updated: {missing}")
        if extra:
            differences.append(f"Extra models in updated: {extra}")
    
    # Compare each model's predictions
    for model in baseline_models & updated_models:
        baseline_pred = baseline["predictions"].get(model, {})
        updated_pred = updated["predictions"].get(model, {})
        
        # Check status codes
        baseline_status = baseline_pred.get("status_code")
        updated_status = updated_pred.get("status_code")
        
        if baseline_status != updated_status:
            differences.append(
                f"[{model}] Status code changed: {baseline_status} -> {updated_status}"
            )
            continue
        
        # If both failed, skip detailed comparison
        if baseline_status != 200:
            continue
        
        # Compare response data
        baseline_response = baseline_pred.get("response", {})
        updated_response = updated_pred.get("response", {})
        
        if model not in baseline_response or model not in updated_response:
            if model in baseline_response and model not in updated_response:
                differences.append(f"[{model}] Model key missing in updated response")
            continue
        
        baseline_data = baseline_response[model].get("data", [])
        updated_data = updated_response[model].get("data", [])
        
        if len(baseline_data) != len(updated_data):
            differences.append(
                f"[{model}] Different number of results: {len(baseline_data)} -> {len(updated_data)}"
            )
            continue
        
        # Compare each prediction row
        for i, (b_row, u_row) in enumerate(zip(baseline_data, updated_data)):
            row_diffs = compare_rows(b_row, u_row, tolerance)
            for diff in row_diffs:
                differences.append(f"[{model}] Row {i}: {diff}")
    
    return len(differences) == 0, differences


def compare_rows(baseline_row: dict, updated_row: dict, tolerance: float) -> List[str]:
    """Compare two prediction rows and return differences."""
    diffs = []
    
    all_keys = set(baseline_row.keys()) | set(updated_row.keys())
    
    for key in all_keys:
        if key not in baseline_row:
            diffs.append(f"New column '{key}' in updated")
            continue
        if key not in updated_row:
            diffs.append(f"Missing column '{key}' in updated")
            continue
        
        b_val = baseline_row[key]
        u_val = updated_row[key]
        
        # Handle numeric comparisons with tolerance
        if isinstance(b_val, (int, float)) and isinstance(u_val, (int, float)):
            if abs(b_val - u_val) > tolerance:
                diffs.append(f"'{key}' changed: {b_val} -> {u_val}")
        # Handle string comparisons of numeric values
        elif is_numeric_string(b_val) and is_numeric_string(u_val):
            try:
                b_num = float(b_val)
                u_num = float(u_val)
                if abs(b_num - u_num) > tolerance:
                    diffs.append(f"'{key}' changed: {b_val} -> {u_val}")
            except ValueError:
                if b_val != u_val:
                    diffs.append(f"'{key}' changed: {b_val} -> {u_val}")
        # Direct comparison for other types
        elif b_val != u_val:
            diffs.append(f"'{key}' changed: {b_val} -> {u_val}")
    
    return diffs


def is_numeric_string(val: Any) -> bool:
    """Check if a value is a string that represents a number."""
    if not isinstance(val, str):
        return False
    try:
        float(val)
        return True
    except ValueError:
        return False


def print_summary(baseline: dict, updated: dict):
    """Print summary information about both baselines."""
    print("=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    
    b_meta = baseline.get("metadata", {})
    u_meta = updated.get("metadata", {})
    
    print(f"\nBaseline:")
    print(f"  Captured: {b_meta.get('capture_date', 'Unknown')}")
    print(f"  URL: {b_meta.get('base_url', 'Unknown')}")
    print(f"  Models: {b_meta.get('models_tested', [])}")
    
    print(f"\nUpdated:")
    print(f"  Captured: {u_meta.get('capture_date', 'Unknown')}")
    print(f"  URL: {u_meta.get('base_url', 'Unknown')}")
    print(f"  Models: {u_meta.get('models_tested', [])}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare two baseline prediction files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Compare baseline to updated predictions
    python scripts/verify_predictions.py baseline_predictions.json updated_predictions.json
    
    # With custom tolerance for numeric comparisons
    python scripts/verify_predictions.py baseline.json updated.json --tolerance 0.001
        """
    )
    parser.add_argument(
        "baseline",
        help="Path to the original baseline predictions JSON"
    )
    parser.add_argument(
        "updated",
        help="Path to the updated predictions JSON to compare"
    )
    parser.add_argument(
        "--tolerance", "-t",
        type=float,
        default=1e-6,
        help="Tolerance for floating point comparisons (default: 1e-6)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output including matching fields"
    )
    parser.add_argument(
        "--max-diffs",
        type=int,
        default=50,
        help="Maximum number of differences to show (default: 50)"
    )
    args = parser.parse_args()
    
    # Load files
    try:
        baseline = load_baseline(args.baseline)
    except FileNotFoundError:
        print(f"ERROR: Baseline file not found: {args.baseline}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in baseline file: {e}")
        return 1
    
    try:
        updated = load_baseline(args.updated)
    except FileNotFoundError:
        print(f"ERROR: Updated file not found: {args.updated}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in updated file: {e}")
        return 1
    
    # Print summary
    print_summary(baseline, updated)
    
    # Compare predictions
    print("\n" + "=" * 70)
    print("COMPARING PREDICTIONS")
    print("=" * 70)
    
    all_match, differences = compare_predictions(baseline, updated, args.tolerance)
    
    if all_match:
        print("\n✓ All predictions match!")
        print("\nThe code changes did not affect model outputs.")
        return 0
    else:
        print(f"\n✗ Found {len(differences)} difference(s):\n")
        
        for i, diff in enumerate(differences[:args.max_diffs]):
            print(f"  {i+1}. {diff}")
        
        if len(differences) > args.max_diffs:
            print(f"\n  ... and {len(differences) - args.max_diffs} more differences")
        
        print("\n" + "=" * 70)
        print("VERIFICATION FAILED")
        print("=" * 70)
        print("\nThe predictions have changed. Review the differences above.")
        print("If changes are expected (e.g., after model retraining), update the baseline.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

