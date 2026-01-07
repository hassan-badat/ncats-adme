#!/usr/bin/env python
"""
Test retrained ADME models against baseline predictions.

Runs predictions with updated models, stores results, and performs
comprehensive comparison against the original baseline.

Usage:
    python testing/test_retrained_models.py [--baseline testing/baseline_predictions.json] [--url http://localhost:5000] [--output retrained_predictions.json]

Requirements:
    pip install requests
"""

import json
import requests
import argparse
from datetime import datetime
import sys
from typing import Dict, List, Tuple, Any
import re

# Configuration
DEFAULT_BASE_URL = "http://localhost:5000"
API_ENDPOINT = "/api/v1/predict"

# Working models that have been retrained and are available
WORKING_MODELS = [
    "rlm",        # Rat Liver Microsome - GCNN (Chemprop 2.x)
    "hlm",        # Human Liver Microsome - XGBoost
    "pampa",      # PAMPA pH 7.4 - GCNN (Chemprop 2.x)
    "pampa50",    # PAMPA pH 5.0 - GCNN (Chemprop 2.x)
    "pampabbb",   # PAMPA Blood-Brain Barrier - GCNN + RDKit
    "solubility", # Aqueous Solubility - GCNN (Chemprop 2.x)
    "hlc",        # Human Liver Cytosol - Ensemble RF (3 models)
]

# Models with missing components - uncomment when available
# PENDING_MODELS = [
#     "cyp450",    # CYP450 substrate models missing (cyp2c9_subs, cyp2d6_subs, cyp3a4_subs)
# ]

# Same test molecules as baseline
TEST_MOLECULES = [
    ("Ethanol", "CCO"),
    ("Methanol", "CO"),
    ("Acetone", "CC(=O)C"),
    ("Benzaldehyde", "C1=CC=C(C=C1)C=O"),
    ("Phenol", "C1=CC=C(C=C1)O"),
    ("Toluene", "CC1=CC=CC=C1"),
    ("Aspirin", "CC(=O)OC1=CC=CC=C1C(=O)O"),
    ("Caffeine", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"),
    ("Ibuprofen", "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"),
    ("Paracetamol", "CC(=O)NC1=CC=C(C=C1)O"),
    ("Metformin", "CN(C)C(=N)NC(=N)N"),
    ("Warfarin", "CC(=O)CC(C1=CC=CC=C1)C2=C(C3=CC=CC=C3OC2=O)O"),
    ("Pyridine", "C1=CC=NC=C1"),
    ("Imidazole", "C1=CN=CN1"),
    ("Thiophene", "C1=CSC=C1"),
    ("Glycine", "NCC(=O)O"),
    ("Acetic_acid", "CC(=O)O"),
    ("Ethylamine", "CCN"),
    ("Diethyl_ether", "CCOCC"),
    ("Omeprazole", "CC1=CN=C(C(=C1OC)C)CS(=O)C2=NC3=C(N2)C=CC(=C3)OC"),
    ("Atorvastatin", "CC(C)C1=C(C(=C(N1CCC(CC(CC(=O)O)O)O)C2=CC=C(C=C2)F)C3=CC=CC=C3)C(=O)NC4=CC=CC=C4"),
]


def make_single_prediction(base_url: str, smiles: str, model: str, timeout: int = 300) -> dict:
    """Make a prediction API call for a single molecule and model."""
    params = [("smiles", smiles), ("model", model)]
    url = f"{base_url}{API_ENDPOINT}"
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        return {
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text,
            "success": True
        }
    except requests.exceptions.Timeout:
        return {
            "status_code": None,
            "response": f"Request timed out after {timeout} seconds",
            "success": False
        }
    except requests.exceptions.RequestException as e:
        return {
            "status_code": None,
            "response": str(e),
            "success": False
        }
    except json.JSONDecodeError as e:
        return {
            "status_code": response.status_code,
            "response": f"JSON decode error: {e}",
            "success": False
        }


def capture_predictions(base_url: str, models: List[str]) -> dict:
    """Capture predictions from specified models."""
    results = {
        "metadata": {
            "capture_date": datetime.now().isoformat(),
            "base_url": base_url,
            "api_endpoint": API_ENDPOINT,
            "models_tested": models,
            "num_valid_molecules": len(TEST_MOLECULES),
            "script_version": "1.0.0",
        },
        "test_molecules": {name: smiles for name, smiles in TEST_MOLECULES},
        "predictions": {},
        "summary": {
            "models_successful": [],
            "models_failed": [],
        }
    }
    
    print("=" * 70)
    print("TESTING RETRAINED MODELS")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print(f"Test molecules: {len(TEST_MOLECULES)}")
    print(f"Models to test: {len(models)}")
    print("=" * 70)
    
    for i, model in enumerate(models, 1):
        print(f"\n[{i}/{len(models)}] {model.upper()}")
        print(f"    Testing {len(TEST_MOLECULES)} molecules...")
        
        model_results = {
            "molecules": {},
            "successful_count": 0,
            "failed_count": 0,
            "columns": None,
        }
        
        for mol_name, smiles in TEST_MOLECULES:
            result = make_single_prediction(base_url, smiles, model)
            
            if result["success"] and result["status_code"] == 200:
                response_data = result["response"]
                if model in response_data:
                    model_response = response_data[model]
                    data = model_response.get("data", [])
                    
                    if model_results["columns"] is None:
                        model_results["columns"] = model_response.get("columns", [])
                    
                    model_results["molecules"][mol_name] = {
                        "smiles": smiles,
                        "status_code": result["status_code"],
                        "data": data[0] if data else None,
                        "hasErrors": model_response.get("hasErrors", False),
                        "errorMessages": model_response.get("errorMessages", []),
                    }
                    model_results["successful_count"] += 1
                else:
                    model_results["molecules"][mol_name] = {
                        "smiles": smiles,
                        "status_code": result["status_code"],
                        "error": f"Model key '{model}' not in response",
                    }
                    model_results["failed_count"] += 1
            else:
                model_results["molecules"][mol_name] = {
                    "smiles": smiles,
                    "status_code": result["status_code"],
                    "error": result["response"][:200] if isinstance(result["response"], str) else str(result["response"]),
                }
                model_results["failed_count"] += 1
        
        results["predictions"][model] = model_results
        
        if model_results["failed_count"] == 0:
            print(f"    ✓ Success: {model_results['successful_count']}/{len(TEST_MOLECULES)} predictions")
            results["summary"]["models_successful"].append(model)
        else:
            print(f"    ⚠ Partial: {model_results['successful_count']}/{len(TEST_MOLECULES)} succeeded, {model_results['failed_count']} failed")
            if model_results["successful_count"] > 0:
                results["summary"]["models_successful"].append(model)
            else:
                results["summary"]["models_failed"].append(model)
    
    return results


def parse_prediction_value(value: str) -> Tuple[int, float]:
    """Parse prediction string like '0 (0.98)' into (class, probability)."""
    if not isinstance(value, str):
        return None, None
    
    match = re.match(r'(\d+)\s*\(([\d.]+)\)', value)
    if match:
        return int(match.group(1)), float(match.group(2))
    return None, None


def extract_prediction_class(data: dict) -> str:
    """Extract prediction class from data dict."""
    if not data:
        return None
    
    pred_key = "Prediction"
    if pred_key in data:
        return data[pred_key]
    
    prob_key = "Predicted Class (Probability)"
    if prob_key in data:
        class_val, _ = parse_prediction_value(data[prob_key])
        if class_val is not None:
            return "stable" if class_val == 0 else "unstable"
    
    return None


def compare_with_baseline(baseline: dict, updated: dict) -> dict:
    """Compare new predictions against baseline."""
    comparison = {
        "models_compared": [],
        "per_model_stats": {},
        "overall_summary": {
            "total_molecules": len(TEST_MOLECULES),
            "models_tested": 0,
            "models_passing": 0,
            "models_failing": 0,
        }
    }
    
    baseline_models = set(baseline.get("predictions", {}).keys())
    updated_models = set(updated.get("predictions", {}).keys())
    common_models = baseline_models & updated_models & set(WORKING_MODELS)
    
    comparison["models_compared"] = sorted(list(common_models))
    comparison["overall_summary"]["models_tested"] = len(common_models)
    
    for model in common_models:
        baseline_pred = baseline["predictions"].get(model, {})
        updated_pred = updated["predictions"].get(model, {})
        
        baseline_molecules = baseline_pred.get("molecules", {})
        updated_molecules = updated_pred.get("molecules", {})
        
        stats = {
            "total_molecules": 0,
            "class_agreements": 0,
            "class_disagreements": 0,
            "baseline_errors": 0,
            "updated_errors": 0,
            "both_errors": 0,
            "probability_diffs": [],
            "mismatches": [],
        }
        
        for mol_name in TEST_MOLECULES:
            mol_name = mol_name[0]
            if mol_name not in baseline_molecules or mol_name not in updated_molecules:
                continue
            
            b_mol = baseline_molecules[mol_name]
            u_mol = updated_molecules[mol_name]
            
            b_status = b_mol.get("status_code")
            u_status = u_mol.get("status_code")
            
            if b_status != 200 or u_status != 200:
                if b_status != 200 and u_status != 200:
                    stats["both_errors"] += 1
                elif b_status != 200:
                    stats["baseline_errors"] += 1
                else:
                    stats["updated_errors"] += 1
                continue
            
            b_data = b_mol.get("data", {})
            u_data = u_mol.get("data", {})
            
            if not b_data or not u_data:
                continue
            
            stats["total_molecules"] += 1
            
            b_class = extract_prediction_class(b_data)
            u_class = extract_prediction_class(u_data)
            
            if b_class and u_class:
                if b_class == u_class:
                    stats["class_agreements"] += 1
                else:
                    stats["class_disagreements"] += 1
                    stats["mismatches"].append({
                        "molecule": mol_name,
                        "baseline": b_class,
                        "updated": u_class,
                    })
            
            b_prob_key = "Predicted Class (Probability)"
            if b_prob_key in b_data and b_prob_key in u_data:
                _, b_prob = parse_prediction_value(b_data[b_prob_key])
                _, u_prob = parse_prediction_value(u_data[b_prob_key])
                if b_prob is not None and u_prob is not None:
                    stats["probability_diffs"].append({
                        "molecule": mol_name,
                        "baseline_prob": b_prob,
                        "updated_prob": u_prob,
                        "diff": abs(b_prob - u_prob),
                    })
        
        agreement_rate = stats["class_agreements"] / stats["total_molecules"] if stats["total_molecules"] > 0 else 0
        avg_prob_diff = sum(d["diff"] for d in stats["probability_diffs"]) / len(stats["probability_diffs"]) if stats["probability_diffs"] else 0
        
        stats["class_agreement_rate"] = agreement_rate
        stats["average_probability_difference"] = avg_prob_diff
        stats["passing"] = agreement_rate >= 0.5
        
        comparison["per_model_stats"][model] = stats
        
        if stats["passing"]:
            comparison["overall_summary"]["models_passing"] += 1
        else:
            comparison["overall_summary"]["models_failing"] += 1
    
    return comparison


def generate_performance_report(baseline: dict, updated: dict, comparison: dict) -> str:
    """Generate detailed performance comparison report."""
    report = []
    report.append("=" * 70)
    report.append("RETRAINED MODEL PERFORMANCE REPORT")
    report.append("=" * 70)
    report.append("")
    
    report.append(f"Baseline captured: {baseline.get('metadata', {}).get('capture_date', 'Unknown')}")
    report.append(f"Updated captured: {updated.get('metadata', {}).get('capture_date', 'Unknown')}")
    report.append("")
    
    report.append("OVERALL SUMMARY")
    report.append("-" * 70)
    overall = comparison["overall_summary"]
    report.append(f"Models tested: {overall['models_tested']}")
    report.append(f"Models passing (≥50% agreement): {overall['models_passing']}")
    report.append(f"Models failing: {overall['models_failing']}")
    report.append("")
    
    report.append("PER-MODEL STATISTICS")
    report.append("-" * 70)
    
    for model in comparison["models_compared"]:
        stats = comparison["per_model_stats"][model]
        report.append(f"\n{model.upper()}")
        report.append(f"  Total molecules: {stats['total_molecules']}")
        report.append(f"  Class agreements: {stats['class_agreements']}")
        report.append(f"  Class disagreements: {stats['class_disagreements']}")
        report.append(f"  Agreement rate: {stats['class_agreement_rate']:.2%}")
        report.append(f"  Avg probability difference: {stats['average_probability_difference']:.4f}")
        report.append(f"  Status: {'✓ PASSING' if stats['passing'] else '✗ FAILING'}")
        
        if stats["mismatches"]:
            report.append(f"  Class mismatches ({len(stats['mismatches'])}):")
            for mismatch in stats["mismatches"][:5]:
                report.append(f"    - {mismatch['molecule']}: {mismatch['baseline']} → {mismatch['updated']}")
            if len(stats["mismatches"]) > 5:
                report.append(f"    ... and {len(stats['mismatches']) - 5} more")
    
    report.append("")
    report.append("=" * 70)
    
    return "\n".join(report)


def check_server(base_url: str) -> bool:
    """Check if the server is running and accessible."""
    try:
        response = requests.get(f"{base_url}/healthcheck", timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test retrained ADME models against baseline predictions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Default: localhost:5000, baseline from testing/baseline_predictions.json
    python testing/test_retrained_models.py
    
    # Custom paths
    python testing/test_retrained_models.py --baseline my_baseline.json --output my_results.json
    
    # Custom URL
    python testing/test_retrained_models.py --url http://adme-server:5000
        """
    )
    parser.add_argument(
        "--baseline", "-b",
        default="testing/baseline_predictions.json",
        help="Path to baseline predictions JSON (default: testing/baseline_predictions.json)"
    )
    parser.add_argument(
        "--output", "-o",
        default="testing/retrained_predictions.json",
        help="Output file path (default: testing/retrained_predictions.json)"
    )
    parser.add_argument(
        "--url", "-u",
        default=DEFAULT_BASE_URL,
        help=f"Base URL for API (default: {DEFAULT_BASE_URL})"
    )
    parser.add_argument(
        "--skip-healthcheck",
        action="store_true",
        help="Skip the initial server healthcheck"
    )
    parser.add_argument(
        "--skip-comparison",
        action="store_true",
        help="Skip comparison with baseline (just capture predictions)"
    )
    args = parser.parse_args()
    
    base_url = args.url.rstrip("/")
    
    if not args.skip_healthcheck:
        print(f"Checking server at {base_url}...")
        if not check_server(base_url):
            print(f"\nERROR: Cannot connect to {base_url}/healthcheck")
            print("\nMake sure the server is running.")
            return 1
        print("Server is running!\n")
    
    updated_results = capture_predictions(base_url, WORKING_MODELS)
    
    with open(args.output, "w") as f:
        json.dump(updated_results, f, indent=2, default=str)
    
    print(f"\nPredictions saved to: {args.output}")
    
    if not args.skip_comparison:
        try:
            with open(args.baseline, "r") as f:
                baseline_results = json.load(f)
            
            print("\n" + "=" * 70)
            print("COMPARING WITH BASELINE")
            print("=" * 70)
            
            comparison = compare_with_baseline(baseline_results, updated_results)
            
            report = generate_performance_report(baseline_results, updated_results, comparison)
            print(report)
            
            comparison_file = args.output.replace(".json", "_comparison.json")
            with open(comparison_file, "w") as f:
                json.dump(comparison, f, indent=2, default=str)
            print(f"\nComparison saved to: {comparison_file}")
            
            if comparison["overall_summary"]["models_failing"] > 0:
                return 1
        except FileNotFoundError:
            print(f"\nWARNING: Baseline file not found: {args.baseline}")
            print("Skipping comparison. Run with --skip-comparison to suppress this warning.")
            return 0
        except Exception as e:
            print(f"\nERROR: Failed to compare with baseline: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

