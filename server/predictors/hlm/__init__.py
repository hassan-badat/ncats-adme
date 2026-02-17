import warnings
warnings.filterwarnings("ignore")
import os
import sys
import pandas as pd
import pickle
import traceback

hlm_model_file_path = './models/hlm/model.pkl'
hlm_rdkit_desc_path = 'predictors/hlm/rdkit_desc.csv'


def load_model():
    """Load HLM XGBoost model from models directory."""
    print('Loading HLM XGBoost model', file=sys.stdout)
    sys.stdout.flush()

    hlm_model = None

    try:
        if os.path.exists(hlm_model_file_path) and os.path.getsize(hlm_model_file_path) > 0:
            with open(hlm_model_file_path, 'rb') as pkl_file:
                hlm_model = pickle.load(pkl_file)
            print(f'Successfully loaded HLM model: {type(hlm_model).__name__}', file=sys.stdout)
        else:
            print(f'ERROR: HLM model file not found at {hlm_model_file_path}', file=sys.stderr)
    except ModuleNotFoundError as e:
        print(f'ERROR: HLM model requires missing module: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    except Exception as e:
        print(f'ERROR: Failed to load HLM model: {type(e).__name__}: {e}', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print('Finished loading HLM models', file=sys.stdout)
    sys.stdout.flush()
    return hlm_model


hlm_model_dict = {}
hlm_model_dict['hlm_model'] = load_model()

df_rdkit_desc = pd.read_csv(hlm_rdkit_desc_path, header=None)
hlm_rdkit_desc = df_rdkit_desc[0].tolist()
