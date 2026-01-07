#!/usr/bin/env python
"""
Compare baseline predictions to verify model outputs haven't changed.

Use this script after making code changes to ensure predictions remain identical.

Usage:
    python testing/verify_predictions.py baseline_predictions.json updated_predictions.json

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
        
        # Get molecules dict for each
        baseline_molecules = baseline_pred.get("molecules", {})
        updated_molecules = updated_pred.get("molecules", {})
        
        # Check if molecules match
        baseline_mol_names = set(baseline_molecules.keys())
        updated_mol_names = set(updated_molecules.keys())
        
        if baseline_mol_names != updated_mol_names:
            missing = baseline_mol_names - updated_mol_names
            extra = updated_mol_names - baseline_mol_names
            if missing:
                differences.append(f"[{model}] Missing molecules in updated: {missing}")
            if extra:
                differences.append(f"[{model}] Extra molecules in updated: {extra}")
        
        # Compare each molecule's predictions
        for mol_name in baseline_mol_names & updated_mol_names:
            b_mol = baseline_molecules[mol_name]
            u_mol = updated_molecules[mol_name]
            
            # Check status codes
            b_status = b_mol.get("status_code")
            u_status = u_mol.get("status_code")
            
            if b_status != u_status:
                differences.append(
                    f"[{model}][{mol_name}] Status code changed: {b_status} -> {u_status}"
                )
                continue
            
            # If both failed, skip detailed comparison
            if b_status != 200:
                continue
            
            # Check for errors
            b_error = b_mol.get("error")
            u_error = u_mol.get("error")
            
            if b_error and not u_error:
                differences.append(f"[{model}][{mol_name}] Error resolved: was '{b_error}'")
                continue
            if not b_error and u_error:
                differences.append(f"[{model}][{mol_name}] New error: '{u_error}'")
                continue
            if b_error and u_error:
                continue
            
            # Compare prediction data
            b_data = b_mol.get("data", {})
            u_data = u_mol.get("data", {})
            
            if b_data is None and u_data is None:
                continue
            if b_data is None or u_data is None:
                differences.append(f"[{model}][{mol_name}] Data presence changed")
                continue
            
            row_diffs = compare_rows(b_data, u_data, tolerance)
            for diff in row_diffs:
                differences.append(f"[{model}][{mol_name}] {diff}")
    
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
    python testing/verify_predictions.py testing/baseline_predictions.json testing/retrained_predictions.json
    
    # With custom tolerance for numeric comparisons
    python testing/verify_predictions.py baseline.json updated.json --tolerance 0.001
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

