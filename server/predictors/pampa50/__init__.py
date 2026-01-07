import os
import sys

from ..utilities.utilities import load_gcnn_model

pampa_model_file_url = 'https://opendata.ncats.nih.gov/public/adme/models/current/static/pampa50/gcnn_model.pt'
pampa_model_file_path = './models/pampa50/gcnn_model.pt'

print('Loading PAMPA 5.0 graph convolutional neural network model', file=sys.stdout)
os.makedirs('./models/pampa50', exist_ok=True)

pampa_gcnn_scaler, pampa_gcnn_model = load_gcnn_model(
    pampa_model_file_path, pampa_model_file_url
)

print('Finished loading PAMPA 5.0 models', file=sys.stdout)
