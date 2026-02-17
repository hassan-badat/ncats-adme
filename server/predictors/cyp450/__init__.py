import warnings
warnings.filterwarnings("ignore")
import os
import sys
import joblib
import traceback
import time

# CYP450 model endpoints
CYP450_ENDPOINTS = [
    'cyp2c9_inhib',
    'cyp2c9_subs',
    'cyp2d6_inhib',
    'cyp2d6_subs',
    'cyp3a4_inhib',
    'cyp3a4_subs'
]

NUM_MODELS_PER_ENDPOINT = 64

# Global model cache: { 'cyp2c9_inhib': { 0: model, 1: model, ... }, ... }
_model_cache = {}


def get_model_path(endpoint: str, model_number: int) -> str:
    """Get the file path for a specific CYP450 model."""
    return f'./models/cyp450/{endpoint}/model_{model_number}.pkl'


def _load_model_from_disk(endpoint: str, model_number: int):
    """
    Load a single CYP450 model from disk.

    Parameters:
        endpoint: One of the CYP450 endpoints (e.g., 'cyp2c9_inhib')
        model_number: Model number (0-63)

    Returns:
        Loaded model object, or None if loading fails
    """
    model_path = get_model_path(endpoint, model_number)

    if not os.path.exists(model_path):
        return None

    try:
        return joblib.load(model_path)
    except ModuleNotFoundError as e:
        print(f'ERROR: CYP450 {endpoint}/model_{model_number} requires missing module: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None
    except Exception as e:
        print(f'ERROR: Failed to load CYP450 {endpoint}/model_{model_number}: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None


def load_model(endpoint: str, model_number: int):
    """
    Get a CYP450 model from the pre-loaded cache.

    Parameters:
        endpoint: One of the CYP450 endpoints (e.g., 'cyp2c9_inhib')
        model_number: Model number (0-63)

    Returns:
        Loaded model object, or None if not available
    """
    return _model_cache.get(endpoint, {}).get(model_number, None)


def load_all_models() -> dict:
    """
    Pre-load all 384 CYP450 models into memory.

    Returns:
        Dictionary with endpoint names and count of successfully loaded models
    """
    global _model_cache

    print('CYP450: Pre-loading all models into memory...', file=sys.stdout)
    sys.stdout.flush()
    start = time.time()

    status = {}
    total_loaded = 0

    for endpoint in CYP450_ENDPOINTS:
        _model_cache[endpoint] = {}
        count = 0
        for model_num in range(NUM_MODELS_PER_ENDPOINT):
            model = _load_model_from_disk(endpoint, model_num)
            if model is not None:
                _model_cache[endpoint][model_num] = model
                count += 1
        status[endpoint] = count
        total_loaded += count
        print(f'  {endpoint}: {count}/{NUM_MODELS_PER_ENDPOINT} models loaded', file=sys.stdout)
        sys.stdout.flush()

    elapsed = time.time() - start
    expected_total = len(CYP450_ENDPOINTS) * NUM_MODELS_PER_ENDPOINT

    if total_loaded == expected_total:
        print(f'CYP450: All {total_loaded} models loaded in {elapsed:.1f}s', file=sys.stdout)
    else:
        print(f'WARNING: CYP450 loaded {total_loaded}/{expected_total} models in {elapsed:.1f}s', file=sys.stderr)

    sys.stdout.flush()
    return status


def get_model_status() -> dict:
    """Get the number of loaded models per endpoint."""
    return {endpoint: len(models) for endpoint, models in _model_cache.items()}


# Pre-load all models at import time
load_all_models()
