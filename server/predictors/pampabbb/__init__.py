import sys
import traceback
import pandas as pd
from pickle import load

from ..utilities.utilities import load_gcnn_model_local

pampa_model_file_path = './models/pampabbb/gcnn_model.ckpt'
pampa_rdkit_desc_path = 'predictors/pampabbb/rdkit_desc.csv'
pampa_rdkit_desc_scaler_path = 'predictors/pampabbb/scaler.pkl'


def load_model():
    """Load PAMPA BBB GCNN model from models directory."""
    print('Loading PAMPA BBB graph convolutional neural network model', file=sys.stdout)
    sys.stdout.flush()

    scaler = None
    model = None

    try:
        scaler, model, _ = load_gcnn_model_local(pampa_model_file_path)
        print(f'Successfully loaded PAMPA BBB GCNN model', file=sys.stdout)
    except FileNotFoundError as e:
        print(f'ERROR: PAMPA BBB model file not found: {e}', file=sys.stderr)
    except ModuleNotFoundError as e:
        print(f'ERROR: PAMPA BBB model requires missing module: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    except Exception as e:
        print(f'ERROR: Failed to load PAMPA BBB model: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print('Finished loading PAMPA BBB models', file=sys.stdout)
    sys.stdout.flush()
    return scaler, model


pampa_gcnn_scaler, pampa_gcnn_model = load_model()

df_rdkit_desc = pd.read_csv(pampa_rdkit_desc_path, header=None)
pampa_rdkit_desc = df_rdkit_desc[0].tolist()
pampa_rdkit_desc_scaler = load(open(pampa_rdkit_desc_scaler_path, 'rb'))
