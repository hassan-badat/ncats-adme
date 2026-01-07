import warnings
warnings.filterwarnings("ignore")
import os
import sys
import pickle
from tqdm import tqdm
import requests
from io import BytesIO
from os import path


def download_file(base_url, model_name, model_number, models_dict):
    """Download CYP450 model file from URL."""
    cyp450_rf_pkl_url = f'{base_url}/{model_name}/model_{model_number}'
    cyp450_model_path = f'./models/cyp450/{model_name}/model_{model_number}'
    cyp450_rf_pkl_file_request = requests.get(cyp450_rf_pkl_url)
    with tqdm.wrapattr(
        open(os.devnull, "wb"),
        "write",
        miniters=1,
        desc=f'{model_name}-model_{model_number}',
        total=int(cyp450_rf_pkl_file_request.headers.get('content-length', 0))
    ) as fout:
        for chunk in cyp450_rf_pkl_file_request.iter_content(chunk_size=4096):
            fout.write(chunk)
    with open(cyp450_model_path, 'wb') as cyp450_rf_pkl_file_writer:
        cyp450_rf_pkl_file_writer.write(cyp450_rf_pkl_file_request.content)

    try:
        cyp450_rf_model = pickle.load(BytesIO(cyp450_rf_pkl_file_request.content))
    except (ValueError, TypeError) as e:
        # Handle scikit-learn version incompatibility
        if 'incompatible dtype' in str(e) or 'node array' in str(e):
            print(f'WARNING: Model {model_name}/model_{model_number} has scikit-learn version incompatibility. '
                  f'This model may not work correctly. Error: {e}', file=sys.stderr)
            # Try loading from file instead (sometimes helps)
            try:
                with open(cyp450_model_path, 'rb') as f:
                    cyp450_rf_model = pickle.load(f)
            except Exception:
                # If still fails, return None and let caller handle it
                print(f'ERROR: Could not load {model_name}/model_{model_number} even from file', file=sys.stderr)
                return None
        else:
            raise
    return cyp450_rf_model


def load_models():
    """Load all CYP450 random forest models.

    Inhibitor endpoints (cyp2c9_inhib, cyp2d6_inhib, cyp3a4_inhib) use local .pkl files.
    Substrate endpoints (cyp2c9_subs, cyp2d6_subs, cyp3a4_subs) download from server.
    """
    base_url = 'https://opendata.ncats.nih.gov/public/adme/models/current/static/cyp450/'
    print('Loading CYP450 random forest models', file=sys.stdout)

    cyp450_models_dict = {
        'cyp2c9_inhib': {},
        'cyp2c9_subs': {},
        'cyp2d6_inhib': {},
        'cyp2d6_subs': {},
        'cyp3a4_inhib': {},
        'cyp3a4_subs': {}
    }

    # Endpoints with local updated models (use .pkl extension)
    local_model_endpoints = ['cyp2c9_inhib', 'cyp2d6_inhib', 'cyp3a4_inhib']

    for model_name in tqdm(cyp450_models_dict.keys()):
        for model_number in tqdm(range(0, 64)):
            # Determine file path based on endpoint type
            if model_name in local_model_endpoints:
                # Local models have .pkl extension
                cyp450_model_path = f'./models/cyp450/{model_name}/model_{model_number}.pkl'
            else:
                # Server models don't have extension
                cyp450_model_path = f'./models/cyp450/{model_name}/model_{model_number}'

            if path.exists(cyp450_model_path) and os.path.getsize(cyp450_model_path) > 0:
                try:
                    with open(cyp450_model_path, 'rb') as pkl_file:
                        cyp450_models_dict[model_name][f'model_{model_number}'] = pickle.load(pkl_file)
                except (ValueError, TypeError) as e:
                    if 'incompatible dtype' in str(e) or 'node array' in str(e):
                        print(f'WARNING: Local model {model_name}/model_{model_number} has scikit-learn version incompatibility. '
                              f'Attempting to download fresh copy...', file=sys.stderr)
                        # Try downloading fresh copy
                        os.makedirs(f'./models/cyp450/{model_name}', exist_ok=True)
                        downloaded_model = download_file(base_url, model_name, model_number, cyp450_models_dict)
                        if downloaded_model is not None:
                            cyp450_models_dict[model_name][f'model_{model_number}'] = downloaded_model
                        else:
                            print(f'ERROR: Could not load {model_name}/model_{model_number}', file=sys.stderr)
                    else:
                        raise
            else:
                os.makedirs(f'./models/cyp450/{model_name}', exist_ok=True)
                downloaded_model = download_file(base_url, model_name, model_number, cyp450_models_dict)
                if downloaded_model is not None:
                    cyp450_models_dict[model_name][f'model_{model_number}'] = downloaded_model
                else:
                    print(f'WARNING: Failed to load {model_name}/model_{model_number}', file=sys.stderr)

    print('Finished loading CYP450 model files', file=sys.stdout)
    return cyp450_models_dict


cyp450_models_dict = load_models()
