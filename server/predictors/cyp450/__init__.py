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

    cyp450_rf_model = pickle.load(BytesIO(cyp450_rf_pkl_file_request.content))
    return cyp450_rf_model


def load_models():
    """Load all CYP450 random forest models."""
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

    for model_name in tqdm(cyp450_models_dict.keys()):
        for model_number in tqdm(range(0, 64)):
            cyp450_model_path = f'./models/cyp450/{model_name}/model_{model_number}'
            if path.exists(cyp450_model_path) and os.path.getsize(cyp450_model_path) > 0:
                with open(cyp450_model_path, 'rb') as pkl_file:
                    cyp450_models_dict[model_name][f'model_{model_number}'] = pickle.load(pkl_file)
            else:
                os.makedirs(f'./models/cyp450/{model_name}', exist_ok=True)
                cyp450_models_dict[model_name][f'model_{model_number}'] = download_file(
                    base_url, model_name, model_number, cyp450_models_dict
                )

    print('Finished loading CYP450 model files', file=sys.stdout)
    return cyp450_models_dict


cyp450_models_dict = load_models()
