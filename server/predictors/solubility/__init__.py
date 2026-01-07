import os
import sys

from ..utilities.utilities import load_gcnn_model_with_versioninfo

solubility_model_file_url = 'https://opendata.ncats.nih.gov/public/adme/models/current/biweekly/solubility/gcnn_model.pt'
solubility_model_file_path = './models/solubility/gcnn_model.pt'

print('Loading Solubility graph convolutional neural network model', file=sys.stdout)
os.makedirs('./models/solubility', exist_ok=True)

solubility_gcnn_scaler, solubility_gcnn_model, solubility_gcnn_model_version = load_gcnn_model_with_versioninfo(
    solubility_model_file_path, solubility_model_file_url
)

print('Finished loading Solubility models', file=sys.stdout)
