#!/usr/bin/env python
"""
Run full test suite and save results.

Tests all ADME models with a diverse set of molecules and saves
detailed results to JSON format.

For RETRAINED models (have baseline): Compares predictions against baseline
For NEW models (no baseline): Shows input/output without comparison

Usage:
    python run_tests.py --url http://localhost:5000 --output /results
"""
import json
import requests
import argparse
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional


# Diverse test molecules covering different chemical classes
# Must match testing/baseline_predictions.json
TEST_MOLECULES: List[Tuple[str, str]] = [
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

# Models that have baseline data (from original system - compare these)
RETRAINED_MODELS: List[str] = [
    'rlm',        # Rat Liver Microsome - GCNN
    'hlm',        # Human Liver Microsome - XGBoost
    'pampa',      # PAMPA pH 7.4 - GCNN
    'pampa50',    # PAMPA pH 5.0 - GCNN
    'pampabbb',   # PAMPA Blood-Brain Barrier - GCNN
    'solubility', # Aqueous Solubility - GCNN
    'hlc',        # Human Liver Cytosol - DNN (BalancedBaggingClassifier)
    'cyp450',     # CYP450 - Random Forest ensemble
]

# New models added in upgrade (no baseline - just show results)
NEW_MODELS: List[str] = [
    'mlc',        # Mouse Liver Cytosol - DNN (BalancedBaggingClassifier)
    'rlc',        # Rat Liver Cytosol - Random Forest (BalancedBaggingClassifier)
]

# All models to test
ALL_MODELS: List[str] = RETRAINED_MODELS + NEW_MODELS


def parse_prediction_value(value: str) -> Tuple[Optional[int], Optional[float]]:
    """Parse prediction string like '0 (0.98)' into (class, probability)."""
    if not isinstance(value, str):
        return None, None
    
    match = re.match(r'(\d+)\s*\(([\d.]+)\)', value)
    if match:
        return int(match.group(1)), float(match.group(2))
    return None, None


def extract_prediction_class(data: dict) -> Optional[str]:
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
    
    # CYP450 format: columns like 'CYP2C9 Inhibition' with values like '0 (0.99)'
    # Combine all CYP450 predictions into a single string for comparison
    cyp_keys = sorted(k for k in data.keys() if k.startswith('CYP'))
    if cyp_keys:
        classes = []
        for k in cyp_keys:
            class_val, _ = parse_prediction_value(data[k])
            if class_val is not None:
                classes.append(str(class_val))
        if classes:
            return ','.join(classes)
    
    return None


def load_baseline(baseline_path: Path) -> Optional[Dict]:
    """Load baseline predictions if available."""
    if not baseline_path.exists():
        print(f"  Baseline file not found: {baseline_path}")
        return None
    
    try:
        with open(baseline_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"  Error loading baseline: {e}")
        return None


def compare_model_to_baseline(model: str, model_results: List[Dict], baseline: Dict) -> Dict:
    """
    Compare model predictions to baseline with enhanced validation.
    
    Checks:
    1. Class agreement rate (text labels like 'stable'/'unstable')
    2. Probability value similarity
    3. Prediction variance (flags if all predictions are identical)
    """
    comparison = {
        "total_molecules": 0,
        "class_agreements": 0,
        "class_disagreements": 0,
        "probability_diffs": [],
        "mismatches": [],
        "baseline_classes": [],
        "updated_classes": [],
        "baseline_probs": [],
        "updated_probs": [],
    }
    
    baseline_pred = baseline.get("predictions", {}).get(model, {})
    baseline_molecules = baseline_pred.get("molecules", {})
    
    if not baseline_molecules:
        return comparison
    
    for result in model_results:
        mol_name = result.get("molecule")
        if mol_name not in baseline_molecules:
            continue
        
        b_mol = baseline_molecules[mol_name]
        
        # Skip if either had errors
        if b_mol.get("status_code") != 200 or result.get("status_code") != 200:
            continue
        
        b_data = b_mol.get("data", {})
        u_data = result.get("data", [{}])
        if isinstance(u_data, list) and u_data:
            u_data = u_data[0] if u_data else {}
        
        if not b_data or not u_data:
            continue
        
        comparison["total_molecules"] += 1
        
        b_class = extract_prediction_class(b_data)
        u_class = extract_prediction_class(u_data)
        
        if b_class:
            comparison["baseline_classes"].append(b_class)
        if u_class:
            comparison["updated_classes"].append(u_class)
        
        if b_class and u_class:
            if b_class == u_class:
                comparison["class_agreements"] += 1
            else:
                comparison["class_disagreements"] += 1
                comparison["mismatches"].append({
                    "molecule": mol_name,
                    "baseline": b_class,
                    "updated": u_class,
                })
        
        # Compare probabilities - extract raw values
        prob_key = "Predicted Class (Probability)"
        if prob_key in b_data and prob_key in u_data:
            b_class_val, b_prob = parse_prediction_value(b_data[prob_key])
            u_class_val, u_prob = parse_prediction_value(u_data[prob_key])
            if b_prob is not None and u_prob is not None:
                comparison["baseline_probs"].append(b_prob)
                comparison["updated_probs"].append(u_prob)
                comparison["probability_diffs"].append({
                    "molecule": mol_name,
                    "baseline_class": b_class_val,
                    "updated_class": u_class_val,
                    "baseline_prob": b_prob,
                    "updated_prob": u_prob,
                    "diff": abs(b_prob - u_prob),
                })
    
    # Calculate class agreement rate
    if comparison["total_molecules"] > 0:
        comparison["agreement_rate"] = comparison["class_agreements"] / comparison["total_molecules"]
    else:
        comparison["agreement_rate"] = 0.0
    
    # Calculate probability statistics
    if comparison["probability_diffs"]:
        diffs = [d["diff"] for d in comparison["probability_diffs"]]
        comparison["avg_probability_diff"] = sum(diffs) / len(diffs)
        comparison["max_probability_diff"] = max(diffs)
        comparison["min_probability_diff"] = min(diffs)
    else:
        comparison["avg_probability_diff"] = 0.0
        comparison["max_probability_diff"] = 0.0
        comparison["min_probability_diff"] = 0.0
    
    # Check for suspicious lack of variance in predictions
    # This catches the case where all predictions are the same class
    comparison["variance_warnings"] = []
    
    if comparison["updated_classes"]:
        unique_updated = set(comparison["updated_classes"])
        if len(unique_updated) == 1:
            comparison["variance_warnings"].append(
                f"All updated predictions are '{list(unique_updated)[0]}' - model may be broken"
            )
    
    if comparison["updated_probs"]:
        # Check if all probabilities are the same (e.g., all 1.0)
        unique_probs = set(round(p, 2) for p in comparison["updated_probs"])
        if len(unique_probs) == 1:
            comparison["variance_warnings"].append(
                f"All updated probabilities are {list(unique_probs)[0]} - model may be broken"
            )
    
    # Check class distribution in baseline vs updated
    if comparison["baseline_classes"] and comparison["updated_classes"]:
        baseline_class_counts = {}
        for c in comparison["baseline_classes"]:
            baseline_class_counts[c] = baseline_class_counts.get(c, 0) + 1
        
        updated_class_counts = {}
        for c in comparison["updated_classes"]:
            updated_class_counts[c] = updated_class_counts.get(c, 0) + 1
        
        comparison["baseline_class_distribution"] = baseline_class_counts
        comparison["updated_class_distribution"] = updated_class_counts
    
    # Determine passing status with enhanced criteria:
    # 1. Class agreement rate >= 50%
    # 2. Average probability difference < 0.3 (probabilities should be similar)
    # 3. No critical variance warnings (unless baseline also had same issue)
    
    class_passing = comparison["agreement_rate"] >= 0.5
    prob_passing = comparison["avg_probability_diff"] < 0.3
    
    # Check if variance warnings are critical
    has_critical_warnings = bool(comparison["variance_warnings"])
    
    # If both baseline and updated have same single class, it's not necessarily broken
    if has_critical_warnings and comparison["baseline_classes"]:
        baseline_unique = set(comparison["baseline_classes"])
        updated_unique = set(comparison["updated_classes"]) if comparison["updated_classes"] else set()
        if baseline_unique == updated_unique and len(baseline_unique) == 1:
            has_critical_warnings = False
    
    comparison["class_passing"] = class_passing
    comparison["probability_passing"] = prob_passing
    comparison["passing"] = class_passing and prob_passing and not has_critical_warnings
    
    # Add reason if not passing
    if not comparison["passing"]:
        reasons = []
        if not class_passing:
            reasons.append(f"class agreement {comparison['agreement_rate']:.1%} < 50%")
        if not prob_passing:
            reasons.append(f"avg prob diff {comparison['avg_probability_diff']:.2f} >= 0.3")
        if has_critical_warnings:
            reasons.append("variance warnings present")
        comparison["failure_reasons"] = reasons
    
    return comparison


def run_tests(base_url: str, output_dir: str, baseline_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Run tests against all models and save results.
    
    Args:
        base_url: Base URL of the ADME server
        output_dir: Directory to save results
        baseline_path: Path to baseline predictions JSON
        
    Returns:
        Results dictionary
    """
    # Load baseline for comparison
    baseline = None
    if baseline_path:
        baseline = load_baseline(baseline_path)
    
    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'num_molecules': len(TEST_MOLECULES),
            'retrained_models': RETRAINED_MODELS,
            'new_models': NEW_MODELS,
            'baseline_available': baseline is not None,
            'baseline_date': baseline.get('metadata', {}).get('capture_date') if baseline else None,
        },
        'predictions': {},
        'comparisons': {},  # Only for retrained models
        'new_model_results': {},  # For new models (no comparison)
        'summary': {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'retrained_models_summary': {},
            'new_models_summary': {},
        }
    }
    
    print("=" * 70)
    print("RUNNING ADME TEST SUITE")
    print("=" * 70)
    print(f"Server: {base_url}")
    print(f"Test molecules: {len(TEST_MOLECULES)}")
    print(f"Retrained models (with baseline): {len(RETRAINED_MODELS)}")
    print(f"New models (no baseline): {len(NEW_MODELS)}")
    if baseline:
        print(f"Baseline date: {baseline.get('metadata', {}).get('capture_date', 'Unknown')}")
    print("=" * 70)
    
    # =========================================================================
    # Test RETRAINED models (compare to baseline)
    # =========================================================================
    print("\n" + "=" * 70)
    print("RETRAINED MODELS (Comparing to Baseline)")
    print("=" * 70)
    
    for model_idx, model in enumerate(RETRAINED_MODELS, 1):
        print(f"\n[{model_idx}/{len(RETRAINED_MODELS)}] Testing {model.upper()}...")
        model_results = []
        model_passed = 0
        model_failed = 0
        
        for mol_idx, (name, smiles) in enumerate(TEST_MOLECULES, 1):
            results['summary']['total_tests'] += 1
            
            try:
                resp = requests.get(
                    f"{base_url}/api/v1/predict",
                    params={'smiles': smiles, 'model': model},
                    timeout=120
                )
                
                result_entry = {
                    'molecule': name,
                    'smiles': smiles,
                    'status_code': resp.status_code,
                }
                
                if resp.status_code == 200:
                    response_data = resp.json()
                    
                    if model in response_data:
                        model_data = response_data[model]
                        result_entry['data'] = model_data.get('data', [])
                        result_entry['columns'] = model_data.get('columns', [])
                        result_entry['hasErrors'] = model_data.get('hasErrors', False)
                        result_entry['errorMessages'] = model_data.get('errorMessages', [])
                        
                        # Count as passed if we got valid prediction data
                        # (API may set hasErrors but still return valid predictions)
                        data = model_data.get('data', [])
                        has_valid_prediction = False
                        if data and len(data) > 0:
                            first_row = data[0]
                            # Check for standard 'Prediction' key (most models)
                            if 'Prediction' in first_row:
                                has_valid_prediction = True
                            # Check for CYP450-style columns (e.g., 'CYP2C9 Inhibition')
                            elif any(k.startswith('CYP') for k in first_row.keys()):
                                has_valid_prediction = True
                        
                        if has_valid_prediction:
                            model_passed += 1
                            results['summary']['passed'] += 1
                        else:
                            model_failed += 1
                            results['summary']['failed'] += 1
                    else:
                        result_entry['error'] = f"Model '{model}' not in response"
                        model_failed += 1
                        results['summary']['failed'] += 1
                else:
                    result_entry['error'] = resp.text[:200]
                    model_failed += 1
                    results['summary']['failed'] += 1
                    
            except requests.exceptions.Timeout:
                result_entry = {
                    'molecule': name,
                    'smiles': smiles,
                    'error': 'Request timeout',
                }
                model_failed += 1
                results['summary']['failed'] += 1
                
            except requests.exceptions.RequestException as e:
                result_entry = {
                    'molecule': name,
                    'smiles': smiles,
                    'error': str(e),
                }
                model_failed += 1
                results['summary']['failed'] += 1
            
            model_results.append(result_entry)
        
        results['predictions'][model] = model_results
        
        # Compare to baseline if available
        if baseline and model in baseline.get('predictions', {}):
            comparison = compare_model_to_baseline(model, model_results, baseline)
            results['comparisons'][model] = comparison
            
            print(f"  Predictions: {model_passed}/{len(TEST_MOLECULES)}")
            print(f"  Class agreement: {comparison['class_agreements']}/{comparison['total_molecules']} ({comparison['agreement_rate']:.1%})")
            print(f"  Avg probability diff: {comparison['avg_probability_diff']:.3f}")
            if comparison.get('variance_warnings'):
                for warn in comparison['variance_warnings']:
                    print(f"  WARNING: {warn}")
            if comparison['mismatches']:
                print(f"  Mismatches: {len(comparison['mismatches'])}")
            
            status = 'PASSING' if comparison['passing'] else 'FAILING'
            if not comparison['passing'] and comparison.get('failure_reasons'):
                status += f" ({', '.join(comparison['failure_reasons'])})"
            print(f"  Status: {status}")
            
            results['summary']['retrained_models_summary'][model] = {
                'predictions_passed': model_passed,
                'predictions_failed': model_failed,
                'baseline_agreement_rate': comparison['agreement_rate'],
                'avg_probability_diff': comparison['avg_probability_diff'],
                'variance_warnings': comparison.get('variance_warnings', []),
                'baseline_passing': comparison['passing'],
            }
        else:
            print(f"  Predictions: {model_passed}/{len(TEST_MOLECULES)}")
            print(f"  Baseline comparison: N/A (no baseline data)")
            
            results['summary']['retrained_models_summary'][model] = {
                'predictions_passed': model_passed,
                'predictions_failed': model_failed,
                'baseline_agreement_rate': None,
                'avg_probability_diff': None,
                'variance_warnings': [],
                'baseline_passing': None,
            }
    
    # =========================================================================
    # Test NEW models (no baseline comparison - just show results)
    # =========================================================================
    print("\n" + "=" * 70)
    print("NEW MODELS (No Baseline - Showing Results Only)")
    print("=" * 70)
    
    for model_idx, model in enumerate(NEW_MODELS, 1):
        print(f"\n[{model_idx}/{len(NEW_MODELS)}] Testing {model.upper()} (NEW)...")
        model_results = []
        model_passed = 0
        model_failed = 0
        
        for mol_idx, (name, smiles) in enumerate(TEST_MOLECULES, 1):
            results['summary']['total_tests'] += 1
            
            try:
                resp = requests.get(
                    f"{base_url}/api/v1/predict",
                    params={'smiles': smiles, 'model': model},
                    timeout=120
                )
                
                result_entry = {
                    'molecule': name,
                    'smiles': smiles,
                    'status_code': resp.status_code,
                }
                
                if resp.status_code == 200:
                    response_data = resp.json()
                    
                    if model in response_data:
                        model_data = response_data[model]
                        result_entry['data'] = model_data.get('data', [])
                        result_entry['columns'] = model_data.get('columns', [])
                        result_entry['hasErrors'] = model_data.get('hasErrors', False)
                        result_entry['errorMessages'] = model_data.get('errorMessages', [])
                        
                        # Count as passed if we got valid prediction data
                        data = model_data.get('data', [])
                        has_valid_prediction = False
                        if data and len(data) > 0:
                            first_row = data[0]
                            if 'Prediction' in first_row:
                                has_valid_prediction = True
                            elif any(k.startswith('CYP') for k in first_row.keys()):
                                has_valid_prediction = True
                        
                        if has_valid_prediction:
                            model_passed += 1
                            results['summary']['passed'] += 1
                        else:
                            model_failed += 1
                            results['summary']['failed'] += 1
                    else:
                        result_entry['error'] = f"Model '{model}' not in response"
                        model_failed += 1
                        results['summary']['failed'] += 1
                else:
                    result_entry['error'] = resp.text[:200]
                    model_failed += 1
                    results['summary']['failed'] += 1
                    
            except requests.exceptions.Timeout:
                result_entry = {
                    'molecule': name,
                    'smiles': smiles,
                    'error': 'Request timeout',
                }
                model_failed += 1
                results['summary']['failed'] += 1
                
            except requests.exceptions.RequestException as e:
                result_entry = {
                    'molecule': name,
                    'smiles': smiles,
                    'error': str(e),
                }
                model_failed += 1
                results['summary']['failed'] += 1
            
            model_results.append(result_entry)
        
        # Store in new_model_results section
        results['new_model_results'][model] = model_results
        results['predictions'][model] = model_results
        
        print(f"  Predictions: {model_passed}/{len(TEST_MOLECULES)}")
        
        # Show sample output for new models
        if model_results and model_passed > 0:
            sample = next((r for r in model_results if r.get('status_code') == 200 and r.get('data')), None)
            if sample and sample.get('data'):
                data = sample['data'][0] if isinstance(sample['data'], list) and sample['data'] else sample['data']
                if isinstance(data, dict):
                    print(f"  Sample output ({sample['molecule']}):")
                    for key, value in list(data.items())[:4]:
                        print(f"    {key}: {value}")
        
        results['summary']['new_models_summary'][model] = {
            'predictions_passed': model_passed,
            'predictions_failed': model_failed,
            'note': 'New model - no baseline comparison available',
        }
    
    # =========================================================================
    # Save results to timestamped directory
    # =========================================================================
    base_output = Path(output_dir)
    base_output.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped subdirectory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_path = base_output / timestamp
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Also update metadata with run directory
    results['metadata']['run_directory'] = str(output_path)
    
    # Save full predictions
    predictions_file = output_path / 'predictions.json'
    with open(predictions_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Generate and save report
    report = generate_report(results, baseline)
    report_file = output_path / 'report.txt'
    with open(report_file, 'w') as f:
        f.write(report)
    
    # Print report
    print("\n" + report)
    
    print(f"\nResults saved to: {output_path}")
    print(f"  - predictions.json (full data)")
    print(f"  - report.txt (summary report)")
    
    return results


def generate_report(results: Dict, baseline: Optional[Dict]) -> str:
    """Generate human-readable test report."""
    lines = []
    lines.append("=" * 70)
    lines.append("ADME MODEL TEST REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Test Date: {results['metadata']['timestamp']}")
    lines.append(f"Server: {results['metadata']['base_url']}")
    if baseline:
        lines.append(f"Baseline Date: {results['metadata'].get('baseline_date', 'Unknown')}")
    lines.append("")
    
    # Overall summary
    lines.append("OVERALL SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Total tests: {results['summary']['total_tests']}")
    lines.append(f"Passed: {results['summary']['passed']}")
    lines.append(f"Failed: {results['summary']['failed']}")
    if results['summary']['total_tests'] > 0:
        rate = results['summary']['passed'] / results['summary']['total_tests'] * 100
        lines.append(f"Success rate: {rate:.1f}%")
    lines.append("")
    
    # Retrained models section
    lines.append("=" * 70)
    lines.append("RETRAINED MODELS (Baseline Comparison)")
    lines.append("=" * 70)
    
    for model, summary in results['summary']['retrained_models_summary'].items():
        lines.append(f"\n{model.upper()}")
        lines.append(f"  Predictions: {summary['predictions_passed']}/{summary['predictions_passed'] + summary['predictions_failed']}")
        
        if summary['baseline_agreement_rate'] is not None:
            lines.append(f"  Class agreement: {summary['baseline_agreement_rate']:.1%}")
            if summary.get('avg_probability_diff') is not None:
                lines.append(f"  Avg probability diff: {summary['avg_probability_diff']:.3f}")
            
            # Show warnings
            if summary.get('variance_warnings'):
                for warn in summary['variance_warnings']:
                    lines.append(f"  WARNING: {warn}")
            
            lines.append(f"  Status: {'PASSING' if summary['baseline_passing'] else 'FAILING'}")
            
            # Show mismatches if any
            if model in results.get('comparisons', {}):
                comparison = results['comparisons'][model]
                
                # Show class distribution
                if comparison.get('baseline_class_distribution') and comparison.get('updated_class_distribution'):
                    lines.append(f"  Baseline class dist: {comparison['baseline_class_distribution']}")
                    lines.append(f"  Updated class dist: {comparison['updated_class_distribution']}")
                
                if comparison.get('mismatches'):
                    lines.append(f"  Mismatches ({len(comparison['mismatches'])}):")
                    for m in comparison['mismatches'][:5]:
                        lines.append(f"    - {m['molecule']}: {m['baseline']} -> {m['updated']}")
                    if len(comparison['mismatches']) > 5:
                        lines.append(f"    ... and {len(comparison['mismatches']) - 5} more")
                
                # Show failure reasons
                if not comparison['passing'] and comparison.get('failure_reasons'):
                    lines.append(f"  Failure reasons: {', '.join(comparison['failure_reasons'])}")
        else:
            lines.append("  Baseline comparison: N/A")
    
    # New models section
    lines.append("")
    lines.append("=" * 70)
    lines.append("NEW MODELS (No Baseline)")
    lines.append("=" * 70)
    
    for model, summary in results['summary']['new_models_summary'].items():
        lines.append(f"\n{model.upper()} (NEW)")
        lines.append(f"  Predictions: {summary['predictions_passed']}/{summary['predictions_passed'] + summary['predictions_failed']}")
        lines.append(f"  Note: {summary['note']}")
        
        # Show sample predictions for new models
        if model in results.get('new_model_results', {}):
            model_results = results['new_model_results'][model]
            successful = [r for r in model_results if r.get('status_code') == 200 and r.get('data')]
            if successful:
                lines.append("  Sample predictions:")
                for result in successful[:3]:
                    data = result['data'][0] if isinstance(result['data'], list) and result['data'] else result['data']
                    if isinstance(data, dict):
                        pred = data.get('Prediction', data.get('Predicted Class (Probability)', 'N/A'))
                        lines.append(f"    - {result['molecule']}: {pred}")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Run full ADME test suite with baseline comparison"
    )
    parser.add_argument(
        '--url',
        default='http://localhost:5000',
        help='Base URL of the ADME server (default: http://localhost:5000)'
    )
    parser.add_argument(
        '--output',
        default='/results',
        help='Output directory for results (default: /results)'
    )
    parser.add_argument(
        '--baseline',
        default=None,
        help='Path to baseline predictions JSON (default: auto-detect from testing/baseline_predictions.json)'
    )
    args = parser.parse_args()
    
    # Try to find baseline file
    baseline_path = None
    if args.baseline:
        baseline_path = Path(args.baseline)
    else:
        # Try common locations
        possible_paths = [
            Path('/opt/adme/testing/baseline_predictions.json'),  # In container
            Path('testing/baseline_predictions.json'),  # Relative
            Path(__file__).parent.parent.parent / 'testing' / 'baseline_predictions.json',  # Script relative
        ]
        for p in possible_paths:
            if p.exists():
                baseline_path = p
                print(f"Found baseline at: {baseline_path}")
                break
    
    results = run_tests(args.url, args.output, baseline_path)
    
    # Exit with error if any retrained models are failing baseline comparison
    for model, summary in results['summary']['retrained_models_summary'].items():
        if summary.get('baseline_passing') is False:
            print(f"\nWARNING: {model} is failing baseline comparison")
            sys.exit(1)
    
    # Exit with error if too many prediction failures
    if results['summary']['failed'] > results['summary']['passed']:
        print("\nERROR: More failures than successes")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
