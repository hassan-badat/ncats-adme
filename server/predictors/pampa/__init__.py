import os
import sys

from ..utilities.utilities import load_gcnn_model_with_versioninfo

pampa_model_file_url = 'https://opendata.ncats.nih.gov/public/adme/models/current/biweekly/pampa/gcnn_model.pt'
pampa_model_file_path = './models/pampa/gcnn_model.pt'

print('Loading PAMPA graph convolutional neural network model', file=sys.stdout)
os.makedirs('./models/pampa', exist_ok=True)

pampa_gcnn_scaler, pampa_gcnn_model, pampa_gcnn_model_version = load_gcnn_model_with_versioninfo(
    pampa_model_file_path, pampa_model_file_url
)

print('Finished loading PAMPA 7.4 models', file=sys.stdout)
