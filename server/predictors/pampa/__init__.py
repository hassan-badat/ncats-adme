import sys
import traceback

from ..utilities.utilities import load_gcnn_model_local

pampa_model_file_path = './models/pampa/gcnn_model.ckpt'


def load_model():
    """Load PAMPA GCNN model from models directory."""
    print('Loading PAMPA graph convolutional neural network model', file=sys.stdout)
    sys.stdout.flush()

    scaler = None
    model = None
    model_version = 'unknown'

    try:
        scaler, model, model_version = load_gcnn_model_local(pampa_model_file_path)
        print(f'Successfully loaded PAMPA GCNN model version: {model_version}', file=sys.stdout)
    except FileNotFoundError as e:
        print(f'ERROR: PAMPA model file not found: {e}', file=sys.stderr)
    except ModuleNotFoundError as e:
        print(f'ERROR: PAMPA model requires missing module: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    except Exception as e:
        print(f'ERROR: Failed to load PAMPA model: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print('Finished loading PAMPA 7.4 models', file=sys.stdout)
    sys.stdout.flush()
    return scaler, model, model_version


pampa_gcnn_scaler, pampa_gcnn_model, pampa_gcnn_model_version = load_model()
