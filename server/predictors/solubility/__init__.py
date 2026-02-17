import sys
import traceback

from ..utilities.utilities import load_gcnn_model_local

solubility_model_file_path = './models/solubility/gcnn_model.ckpt'


def load_model():
    """Load Solubility GCNN model from models directory."""
    print('Loading Solubility graph convolutional neural network model', file=sys.stdout)
    sys.stdout.flush()

    scaler = None
    model = None
    model_version = 'unknown'

    try:
        scaler, model, model_version = load_gcnn_model_local(solubility_model_file_path)
        print(f'Successfully loaded Solubility GCNN model version: {model_version}', file=sys.stdout)
    except FileNotFoundError as e:
        print(f'ERROR: Solubility model file not found: {e}', file=sys.stderr)
    except ModuleNotFoundError as e:
        print(f'ERROR: Solubility model requires missing module: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    except Exception as e:
        print(f'ERROR: Failed to load Solubility model: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print('Finished loading Solubility models', file=sys.stdout)
    sys.stdout.flush()
    return scaler, model, model_version


solubility_gcnn_scaler, solubility_gcnn_model, solubility_gcnn_model_version = load_model()
