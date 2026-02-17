import warnings
warnings.filterwarnings("ignore")
import os
import sys
import joblib
import traceback
import threading
from enum import Enum
from typing import Optional, Dict

rlc_model_path = './models/rlc/model.pkl'


class ModelStatus(Enum):
    NOT_STARTED = "not_started"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"


class LazyRLCModel:
    """Lazy loader for RLC model - loads in background thread to avoid blocking startup."""
    
    def __init__(self):
        self._model: Optional[object] = None
        self._feature_cols: Optional[list] = None
        self._scaler_dict: Optional[Dict] = None
        self._status: ModelStatus = ModelStatus.NOT_STARTED
        self._error: Optional[str] = None
        self._lock = threading.Lock()
        self._load_thread: Optional[threading.Thread] = None
    
    @property
    def status(self) -> ModelStatus:
        return self._status
    
    @property
    def error(self) -> Optional[str]:
        return self._error
    
    @property
    def is_ready(self) -> bool:
        return self._status == ModelStatus.LOADED
    
    @property
    def model(self) -> Optional[object]:
        return self._model
    
    @property
    def feature_cols(self) -> Optional[list]:
        return self._feature_cols
    
    @property
    def scaler_dict(self) -> Optional[Dict]:
        return self._scaler_dict
    
    def get_status_dict(self) -> dict:
        """Get status information as a dictionary for API responses."""
        return {
            "model": "rlc",
            "status": self._status.value,
            "is_ready": self.is_ready,
            "error": self._error
        }
    
    def start_loading(self) -> None:
        """Start loading the model in a background thread."""
        if self._status != ModelStatus.NOT_STARTED:
            return
        
        self._status = ModelStatus.LOADING
        self._load_thread = threading.Thread(target=self._load_model, daemon=True)
        self._load_thread.start()
        print('RLC model loading started in background thread', file=sys.stdout)
        sys.stdout.flush()
    
    def _load_model(self) -> None:
        """Load the model (runs in background thread)."""
        print('Loading Rat Liver Cytosol stability model (background)', file=sys.stdout)
        sys.stdout.flush()
        
        if not os.path.exists(rlc_model_path) or os.path.getsize(rlc_model_path) == 0:
            self._error = f'RLC model file not found at {rlc_model_path}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            return
        
        try:
            with self._lock:
                model_data = joblib.load(rlc_model_path)
                if isinstance(model_data, dict):
                    self._model = model_data.get('model')
                    self._feature_cols = model_data.get('feature_cols')
                    self._scaler_dict = model_data.get('scaler_dict')
                else:
                    self._model = model_data
            self._status = ModelStatus.LOADED
            model_type = type(self._model).__name__ if self._model else 'None'
            print(f'Successfully loaded RLC model: {model_type}', file=sys.stdout)
        except ModuleNotFoundError as e:
            self._error = f'RLC model requires missing module: {e}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        except Exception as e:
            self._error = f'Failed to load RLC model: {type(e).__name__}: {e}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        
        print('Finished loading Rat Liver Cytosol stability model', file=sys.stdout)
        sys.stdout.flush()


# Global lazy loader instance
rlc_lazy_loader = LazyRLCModel()

# Start loading immediately but don't block
rlc_lazy_loader.start_loading()

# For backwards compatibility - will be None until loaded
rlc_model = None


def get_rlc_model():
    """Get the RLC model, returns None if not yet loaded."""
    return rlc_lazy_loader.model


def get_rlc_feature_cols():
    """Get the RLC feature columns, returns None if not yet loaded."""
    return rlc_lazy_loader.feature_cols


def get_rlc_scaler_dict():
    """Get the RLC scaler dictionary, returns None if not yet loaded."""
    return rlc_lazy_loader.scaler_dict


def get_rlc_status():
    """Get the current loading status of the RLC model."""
    return rlc_lazy_loader.get_status_dict()
