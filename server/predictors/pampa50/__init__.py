import sys
import traceback

from ..utilities.utilities import load_gcnn_model_local

pampa_model_file_path = './models/pampa50/gcnn_model.ckpt'


def load_model():
    """Load PAMPA 5.0 GCNN model from models directory."""
    print('Loading PAMPA 5.0 graph convolutional neural network model', file=sys.stdout)
    sys.stdout.flush()

    scaler = None
    model = None

    try:
        scaler, model, _ = load_gcnn_model_local(pampa_model_file_path)
        print(f'Successfully loaded PAMPA 5.0 GCNN model', file=sys.stdout)
    except FileNotFoundError as e:
        print(f'ERROR: PAMPA 5.0 model file not found: {e}', file=sys.stderr)
    except ModuleNotFoundError as e:
        print(f'ERROR: PAMPA 5.0 model requires missing module: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    except Exception as e:
        print(f'ERROR: Failed to load PAMPA 5.0 model: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print('Finished loading PAMPA 5.0 models', file=sys.stdout)
    sys.stdout.flush()
    return scaler, model


pampa_gcnn_scaler, pampa_gcnn_model = load_model()
