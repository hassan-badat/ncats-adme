import sys
import traceback

from ..utilities.utilities import load_gcnn_model_local

rlm_model_file_path = './models/rlm/gcnn_model.ckpt'


def load_model():
    """Load RLM GCNN model from models directory."""
    print('Loading RLM graph convolutional neural network model', file=sys.stdout)
    sys.stdout.flush()

    scaler = None
    model = None
    model_version = 'unknown'

    try:
        scaler, model, model_version = load_gcnn_model_local(rlm_model_file_path)
        print(f'Successfully loaded RLM GCNN model version: {model_version}', file=sys.stdout)
    except FileNotFoundError as e:
        print(f'ERROR: RLM model file not found: {e}', file=sys.stderr)
    except ModuleNotFoundError as e:
        print(f'ERROR: RLM model requires missing module: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    except Exception as e:
        print(f'ERROR: Failed to load RLM model: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print('Finished loading RLM model files', file=sys.stdout)
    sys.stdout.flush()
    return scaler, model, f'rlm_{model_version}'


rlm_gcnn_scaler, rlm_gcnn_model, rlm_gcnn_model_version = load_model()
