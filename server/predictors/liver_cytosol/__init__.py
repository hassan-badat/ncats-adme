import warnings
warnings.filterwarnings("ignore")
import os
import sys
import joblib
import traceback
import threading
from enum import Enum
from typing import Optional, Dict

# Ensure the predictors directory is on sys.path so that modules referenced
# inside pickled models (e.g. functions_for_cytosol) can be resolved by joblib.load()
_predictors_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _predictors_dir not in sys.path:
    sys.path.insert(0, _predictors_dir)
import functions_for_cytosol  # noqa: F401 - required for joblib to unpickle the model

hlc_model_path = './models/liver_cytosol/model.pkl'


class ModelStatus(Enum):
    NOT_STARTED = "not_started"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"


class LazyHLCModel:
    """Lazy loader for HLC model - loads in background thread to avoid blocking startup."""
    
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
            "model": "hlc",
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
        print('HLC model loading started in background thread', file=sys.stdout)
        sys.stdout.flush()
    
    def wait_for_completion(self, timeout: float = None) -> bool:
        """Wait for the model to finish loading. Returns True if loaded successfully."""
        if self._load_thread is not None:
            self._load_thread.join(timeout=timeout)
        return self._status == ModelStatus.LOADED
    
    def _load_model(self) -> None:
        """Load the model (runs in background thread)."""
        print('Loading Human Liver Cytosol stability model (background)', file=sys.stdout)
        sys.stdout.flush()
        
        if not os.path.exists(hlc_model_path) or os.path.getsize(hlc_model_path) == 0:
            self._error = f'HLC model file not found at {hlc_model_path}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            return
        
        try:
            with self._lock:
                model_data = joblib.load(hlc_model_path)
                if isinstance(model_data, dict):
                    self._model = model_data.get('model')
                    self._feature_cols = model_data.get('feature_cols')
                    self._scaler_dict = model_data.get('scaler_dict')
                else:
                    self._model = model_data
            self._status = ModelStatus.LOADED
            model_type = type(self._model).__name__ if self._model else 'None'
            print(f'Successfully loaded HLC model: {model_type}', file=sys.stdout)
        except ModuleNotFoundError as e:
            self._error = f'HLC model requires missing module: {e}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        except Exception as e:
            self._error = f'Failed to load HLC model: {type(e).__name__}: {e}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        
        print('Finished loading Human Liver Cytosol stability model', file=sys.stdout)
        sys.stdout.flush()


# Global lazy loader instance
hlc_lazy_loader = LazyHLCModel()

# NOTE: Loading is NOT started automatically - call start_hlc_loading() after other models are loaded
# This prevents resource contention during startup

# For backwards compatibility - will be None until loaded
lc_models_dict = None


def start_hlc_loading() -> None:
    """Start loading the HLC model in background. Call after other models are loaded."""
    hlc_lazy_loader.start_loading()


def wait_for_hlc() -> bool:
    """Wait for HLC model to finish loading. Returns True if successful."""
    return hlc_lazy_loader.wait_for_completion()


def get_hlc_model():
    """Get the HLC model, returns None if not yet loaded."""
    return hlc_lazy_loader.model


def get_hlc_feature_cols():
    """Get the HLC feature columns, returns None if not yet loaded."""
    return hlc_lazy_loader.feature_cols


def get_hlc_scaler_dict():
    """Get the HLC scaler dictionary, returns None if not yet loaded."""
    return hlc_lazy_loader.scaler_dict


def get_hlc_status():
    """Get the current loading status of the HLC model."""
    return hlc_lazy_loader.get_status_dict()
