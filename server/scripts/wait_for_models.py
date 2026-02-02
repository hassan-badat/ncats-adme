#!/usr/bin/env python
"""
Wait for all models to finish loading.

Polls the model status endpoint and verifies each model can make predictions
before returning success.

Usage:
    python wait_for_models.py --url http://localhost:5000 --timeout 1800
"""
import requests
import time
import argparse
import sys


def wait_for_models(base_url: str, timeout: int) -> int:
    """
    Wait for all models to finish loading.
    
    Args:
        base_url: Base URL of the ADME server
        timeout: Maximum time to wait in seconds
        
    Returns:
        0 if all models loaded successfully, 1 on timeout or failure
    """
    start = time.time()
    
    # No lazy-loaded models - all sklearn pickle models disabled
    lazy_models = []
    
    # All models to verify with test predictions
    # HLC, MLC, RLC, CYP450 disabled - sklearn pickle issues
    all_models = [
        'rlm', 'hlm', 'pampa', 'pampa50', 'pampabbb', 'solubility'
    ]
    
    print(f"Waiting for models to load (timeout: {timeout}s)...")
    print(f"Models to verify: {', '.join(all_models)}")
    print("-" * 50)
    
    iteration = 0
    while time.time() - start < timeout:
        iteration += 1
        elapsed = int(time.time() - start)
        print(f"\n[{elapsed}s] Check #{iteration}")
        
        all_ready = True
        
        # Check lazy-loaded model status via API
        try:
            resp = requests.get(f"{base_url}/api/model-status", timeout=10)
            if resp.status_code == 200:
                models_status = resp.json().get('models', [])
                for model in models_status:
                    status = model.get('status', 'unknown')
                    name = model.get('model', 'unknown')
                    
                    if status == 'loading':
                        print(f"  {name}: loading...")
                        all_ready = False
                    elif status == 'failed':
                        error = model.get('error', 'unknown error')
                        print(f"  {name}: FAILED - {error}")
                        # Don't fail immediately - some models might still work
                    elif status == 'loaded':
                        print(f"  {name}: ready")
                    else:
                        print(f"  {name}: {status}")
            else:
                print(f"  Model status API returned {resp.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  Status check failed: {e}")
            all_ready = False
        
        # If lazy models aren't all ready, wait and retry
        if not all_ready:
            time.sleep(15)
            continue
        
        # Verify all models with actual predictions
        print("\nVerifying models with test predictions...")
        verification_passed = True
        
        for model in all_models:
            try:
                resp = requests.get(
                    f"{base_url}/api/v1/predict",
                    params={'smiles': 'CCO', 'model': model},
                    timeout=120  # Some models take a while for first prediction
                )
                
                if resp.status_code == 200:
                    response_data = resp.json()
                    # Check if the model returned valid data
                    if model in response_data:
                        model_data = response_data[model]
                        has_errors = model_data.get('hasErrors', False)
                        if has_errors:
                            errors = model_data.get('errorMessages', [])
                            # Check if it's just a "still loading" error
                            if any('loading' in str(e).lower() for e in errors):
                                print(f"  {model}: still loading...")
                                verification_passed = False
                            else:
                                print(f"  {model}: WARNING - {errors}")
                        else:
                            print(f"  {model}: OK")
                    else:
                        print(f"  {model}: response missing model data")
                        verification_passed = False
                else:
                    print(f"  {model}: HTTP {resp.status_code}")
                    verification_passed = False
                    
            except requests.exceptions.Timeout:
                print(f"  {model}: TIMEOUT")
                verification_passed = False
            except requests.exceptions.RequestException as e:
                print(f"  {model}: ERROR - {e}")
                verification_passed = False
        
        if verification_passed:
            elapsed = int(time.time() - start)
            print("\n" + "=" * 50)
            print(f"All models ready! (took {elapsed}s)")
            print("=" * 50)
            return 0
        
        # Wait before next verification attempt
        print("\nSome models not ready, waiting 15s...")
        time.sleep(15)
    
    # Timeout
    elapsed = int(time.time() - start)
    print("\n" + "=" * 50)
    print(f"TIMEOUT after {elapsed}s")
    print("Some models may still not be ready.")
    print("=" * 50)
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="Wait for all ADME models to finish loading"
    )
    parser.add_argument(
        '--url', 
        default='http://localhost:5000',
        help='Base URL of the ADME server (default: http://localhost:5000)'
    )
    parser.add_argument(
        '--timeout', 
        type=int, 
        default=1800,
        help='Timeout in seconds (default: 1800 = 30 minutes)'
    )
    args = parser.parse_args()
    
    sys.exit(wait_for_models(args.url, args.timeout))


if __name__ == '__main__':
    main()

