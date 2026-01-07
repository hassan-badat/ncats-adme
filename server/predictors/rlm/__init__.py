import os
import sys
from datetime import datetime

from ..utilities.utilities import load_gcnn_model_with_versioninfo

base_url = 'https://opendata.ncats.nih.gov/public/adme/models/current/biweekly/rlm/'
rlm_base_models_path = './models/rlm'


def load_gcnn_model():
    os.makedirs(rlm_base_models_path, exist_ok=True)
    print('Loading RLM graph convolutional neural network model', file=sys.stdout)

    model_file_path = f'{rlm_base_models_path}/gcnn_model.pt'
    model_file_url = f'{base_url}/gcnn_model.pt'

    scaler, model, model_version = load_gcnn_model_with_versioninfo(
        model_file_path, model_file_url
    )

    return scaler, model, f'rlm_{model_version}'


rlm_gcnn_scaler, rlm_gcnn_model, rlm_gcnn_model_version = load_gcnn_model()

print('Finished loading RLM model files', file=sys.stdout)
