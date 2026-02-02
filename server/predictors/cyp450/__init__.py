import warnings
warnings.filterwarnings("ignore")
import os
import sys
import pickle
import traceback

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


def get_model_path(endpoint: str, model_number: int) -> str:
    """Get the file path for a specific CYP450 model."""
    return f'./models/cyp450/{endpoint}/model_{model_number}.pkl'


def load_model(endpoint: str, model_number: int):
    """
    Load a single CYP450 model on demand.
    
    Parameters:
        endpoint: One of the CYP450 endpoints (e.g., 'cyp2c9_inhib')
        model_number: Model number (0-63)
    
    Returns:
        Loaded model object, or None if loading fails
    """
    model_path = get_model_path(endpoint, model_number)
    
    if not os.path.exists(model_path):
        print(f'ERROR: CYP450 model not found at {model_path}', file=sys.stderr)
        return None
    
    try:
        with open(model_path, 'rb') as pkl_file:
            return pickle.load(pkl_file)
    except ModuleNotFoundError as e:
        print(f'ERROR: CYP450 {endpoint}/model_{model_number} requires missing module: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None
    except Exception as e:
        print(f'ERROR: Failed to load CYP450 {endpoint}/model_{model_number}: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None


def verify_models_exist() -> dict:
    """
    Verify that all CYP450 model files exist without loading them.
    
    Returns:
        Dictionary with endpoint names and count of existing models
    """
    status = {}
    for endpoint in CYP450_ENDPOINTS:
        count = 0
        for model_num in range(NUM_MODELS_PER_ENDPOINT):
            if os.path.exists(get_model_path(endpoint, model_num)):
                count += 1
        status[endpoint] = count
    return status


# Verify models exist at startup (doesn't load them, just checks paths)
print('Verifying CYP450 model files exist (lazy loading - models loaded on demand)', file=sys.stdout)
sys.stdout.flush()

model_status = verify_models_exist()
total_models = sum(model_status.values())
expected_total = len(CYP450_ENDPOINTS) * NUM_MODELS_PER_ENDPOINT

if total_models == expected_total:
    print(f'CYP450: All {total_models} model files found', file=sys.stdout)
else:
    print(f'WARNING: CYP450 found {total_models}/{expected_total} model files', file=sys.stderr)
    for endpoint, count in model_status.items():
        if count != NUM_MODELS_PER_ENDPOINT:
            print(f'  {endpoint}: {count}/{NUM_MODELS_PER_ENDPOINT} models', file=sys.stderr)

print('CYP450 models will be loaded on-demand during prediction', file=sys.stdout)
sys.stdout.flush()
