#!/usr/bin/env python
"""
Capture baseline predictions from all ADME models.

Run this BEFORE making any code changes to establish ground truth.
This script calls the prediction API for all 8 models with a set of
diverse test molecules and saves the complete responses.

Usage:
    python testing/create_baseline_predictions.py [--output testing/baseline_predictions.json] [--url http://localhost:5001]

Requirements:
    pip install requests
"""

import json
import requests
import argparse
from datetime import datetime
import sys

# Configuration
DEFAULT_BASE_URL = "http://localhost:5001"
API_ENDPOINT = "/api/v1/predict"

# All 8 models in the system
MODELS = [
    "rlm",        # Rat Liver Microsome - GCNN (Chemprop)
    "hlm",        # Human Liver Microsome - XGBoost + RLM
    "pampa",      # PAMPA pH 7.4 - GCNN (Chemprop)
    "pampa50",    # PAMPA pH 5.0 - GCNN (Chemprop)
    "pampabbb",   # PAMPA Blood-Brain Barrier - GCNN + RDKit
    "solubility", # Aqueous Solubility - GCNN (Chemprop)
    "hlc",        # Human Liver Cytosol - Ensemble RF (3 models)
    "cyp450",     # CYP450 (6 endpoints) - Ensemble RF (384 models)
]

# Diverse test molecules covering different chemical classes
# Each tuple is (name, SMILES)
TEST_MOLECULES = [
    # Simple molecules
    ("Ethanol", "CCO"),
    ("Methanol", "CO"),
    ("Acetone", "CC(=O)C"),
    
    # Aromatic compounds
    ("Benzaldehyde", "C1=CC=C(C=C1)C=O"),
    ("Phenol", "C1=CC=C(C=C1)O"),
    ("Toluene", "CC1=CC=CC=C1"),
    
    # Common drugs - diverse structures
    ("Aspirin", "CC(=O)OC1=CC=CC=C1C(=O)O"),
    ("Caffeine", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"),
    ("Ibuprofen", "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"),
    ("Paracetamol", "CC(=O)NC1=CC=C(C=C1)O"),
    ("Metformin", "CN(C)C(=N)NC(=N)N"),
    ("Warfarin", "CC(=O)CC(C1=CC=CC=C1)C2=C(C3=CC=CC=C3OC2=O)O"),
    
    # Heterocyclic compounds
    ("Pyridine", "C1=CC=NC=C1"),
    ("Imidazole", "C1=CN=CN1"),
    ("Thiophene", "C1=CSC=C1"),
    
    # Molecules with various functional groups
    ("Glycine", "NCC(=O)O"),
    ("Acetic_acid", "CC(=O)O"),
    ("Ethylamine", "CCN"),
    ("Diethyl_ether", "CCOCC"),
    
    # Larger drug-like molecules
    ("Omeprazole", "CC1=CN=C(C(=C1OC)C)CS(=O)C2=NC3=C(N2)C=CC(=C3)OC"),
    ("Atorvastatin", "CC(C)C1=C(C(=C(N1CCC(CC(CC(=O)O)O)O)C2=CC=C(C=C2)F)C3=CC=CC=C3)C(=O)NC4=CC=CC=C4"),
]

# Invalid SMILES to test error handling
INVALID_MOLECULES = [
    ("Invalid_random", "INVALID_SMILES_12345"),
    ("Invalid_chars", "XYZ123!!!"),
    ("Empty_string", ""),
]


def make_single_prediction(base_url: str, smiles: str, model: str, timeout: int = 300) -> dict:
    """
    Make a prediction API call for a single molecule and model.
    
    Args:
        base_url: Base URL of the API
        smiles: Single SMILES string
        model: Model name
        timeout: Request timeout in seconds (default 5 min for CYP450)
    
    Returns:
        Dictionary with status_code and response
    """
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


def capture_baseline(base_url: str) -> dict:
    """
    Capture predictions from all models for all test molecules.
    Sends one molecule at a time to work with the current API.
    
    Args:
        base_url: Base URL of the API
    
    Returns:
        Dictionary containing all results
    """
    results = {
        "metadata": {
            "capture_date": datetime.now().isoformat(),
            "base_url": base_url,
            "api_endpoint": API_ENDPOINT,
            "models_tested": MODELS,
            "num_valid_molecules": len(TEST_MOLECULES),
            "num_invalid_molecules": len(INVALID_MOLECULES),
            "script_version": "1.1.0",
        },
        "test_molecules": {name: smiles for name, smiles in TEST_MOLECULES},
        "invalid_molecules": {name: smiles for name, smiles in INVALID_MOLECULES},
        "predictions": {},
        "error_handling_tests": {},
        "summary": {
            "models_successful": [],
            "models_failed": [],
        }
    }
    
    # Test each model with valid molecules
    print("=" * 70)
    print("CAPTURING BASELINE PREDICTIONS")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print(f"Test molecules: {len(TEST_MOLECULES)}")
    print(f"Models to test: {len(MODELS)}")
    print("=" * 70)
    
    for i, model in enumerate(MODELS, 1):
        print(f"\n[{i}/{len(MODELS)}] {model.upper()}")
        print(f"    Testing {len(TEST_MOLECULES)} molecules (one at a time)...")
        
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
            print(f"    Columns: {model_results['columns']}")
            results["summary"]["models_successful"].append(model)
        else:
            print(f"    ⚠ Partial: {model_results['successful_count']}/{len(TEST_MOLECULES)} succeeded, {model_results['failed_count']} failed")
            if model_results["successful_count"] > 0:
                results["summary"]["models_successful"].append(model)
            else:
                results["summary"]["models_failed"].append(model)
    
    # Test error handling with invalid molecules
    print("\n" + "=" * 70)
    print("TESTING ERROR HANDLING")
    print("=" * 70)
    
    for model in ["rlm", "hlm"]:
        print(f"\n[{model.upper()}] Testing with invalid SMILES...")
        
        for mol_name, smiles in INVALID_MOLECULES:
            if smiles:
                result = make_single_prediction(base_url, smiles, model, timeout=60)
                results["error_handling_tests"][f"{model}_{mol_name}"] = {
                    "smiles": smiles,
                    "status_code": result["status_code"],
                    "response": result["response"],
                }
                print(f"    {mol_name}: status={result['status_code']}")
    
    # Test with no model specified
    print(f"\nTesting API error handling (no model)...")
    try:
        response = requests.get(f"{base_url}{API_ENDPOINT}", params=[("smiles", "CCO")], timeout=30)
        results["error_handling_tests"]["no_model"] = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text,
        }
        print(f"    Status: {response.status_code}")
    except Exception as e:
        results["error_handling_tests"]["no_model"] = {"error": str(e)}
        print(f"    Error: {e}")
    
    # Test with no SMILES specified
    print(f"Testing API error handling (no SMILES)...")
    try:
        response = requests.get(f"{base_url}{API_ENDPOINT}", params=[("model", "rlm")], timeout=30)
        results["error_handling_tests"]["no_smiles"] = {
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text,
        }
        print(f"    Status: {response.status_code}")
    except Exception as e:
        results["error_handling_tests"]["no_smiles"] = {"error": str(e)}
        print(f"    Error: {e}")
    
    return results


def check_server(base_url: str) -> bool:
    """Check if the server is running and accessible."""
    try:
        response = requests.get(f"{base_url}/healthcheck", timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Capture baseline predictions from all ADME models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Default: localhost:5001, output to testing/baseline_predictions.json
    python testing/create_baseline_predictions.py
    
    # Custom URL and output file
    python testing/create_baseline_predictions.py --url http://adme-server:5000 --output my_baseline.json
    
    # Skip server check (if healthcheck endpoint is different)
    python testing/create_baseline_predictions.py --skip-healthcheck
        """
    )
    parser.add_argument(
        "--output", "-o",
        default="testing/baseline_predictions.json",
        help="Output file path (default: testing/baseline_predictions.json)"
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
    args = parser.parse_args()
    
    base_url = args.url.rstrip("/")
    
    # Check if server is running
    if not args.skip_healthcheck:
        print(f"Checking server at {base_url}...")
        if not check_server(base_url):
            print(f"\nERROR: Cannot connect to {base_url}/healthcheck")
            print("\nMake sure the server is running:")
            print("    docker run -p 5001:5000 ncats-adme-backend")
            print("\nOr use --skip-healthcheck to bypass this check.")
            return 1
        print("Server is running!\n")
    else:
        print(f"Skipping healthcheck, connecting to {base_url}...\n")
    
    # Capture baseline
    results = capture_baseline(base_url)
    
    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Models successful: {len(results['summary']['models_successful'])}/{len(MODELS)}")
    print(f"  - {', '.join(results['summary']['models_successful']) or 'None'}")
    print(f"Models failed: {len(results['summary']['models_failed'])}/{len(MODELS)}")
    print(f"  - {', '.join(results['summary']['models_failed']) or 'None'}")
    print(f"\nBaseline saved to: {args.output}")
    print("=" * 70)
    
    # Return error code if any models failed
    if results["summary"]["models_failed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

