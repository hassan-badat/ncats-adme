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

mlc_model_path = './models/mlc/model.pkl'


class ModelStatus(Enum):
    NOT_STARTED = "not_started"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"


class LazyMLCModel:
    """Lazy loader for MLC model - loads in background thread to avoid blocking startup."""
    
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
            "model": "mlc",
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
        print('MLC model loading started in background thread', file=sys.stdout)
        sys.stdout.flush()
    
    def wait_for_completion(self, timeout: float = None) -> bool:
        """Wait for the model to finish loading. Returns True if loaded successfully."""
        if self._load_thread is not None:
            self._load_thread.join(timeout=timeout)
        return self._status == ModelStatus.LOADED
    
    def _load_model(self) -> None:
        """Load the model (runs in background thread)."""
        print('Loading Mouse Liver Cytosol stability model (background)', file=sys.stdout)
        sys.stdout.flush()
        
        if not os.path.exists(mlc_model_path) or os.path.getsize(mlc_model_path) == 0:
            self._error = f'MLC model file not found at {mlc_model_path}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            return
        
        try:
            with self._lock:
                model_data = joblib.load(mlc_model_path)
                if isinstance(model_data, dict):
                    self._model = model_data.get('model')
                    self._feature_cols = model_data.get('feature_cols')
                    self._scaler_dict = model_data.get('scaler_dict')
                else:
                    self._model = model_data
            self._status = ModelStatus.LOADED
            model_type = type(self._model).__name__ if self._model else 'None'
            print(f'Successfully loaded MLC model: {model_type}', file=sys.stdout)
        except ModuleNotFoundError as e:
            self._error = f'MLC model requires missing module: {e}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        except Exception as e:
            self._error = f'Failed to load MLC model: {type(e).__name__}: {e}'
            self._status = ModelStatus.FAILED
            print(f'ERROR: {self._error}', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        
        print('Finished loading Mouse Liver Cytosol stability model', file=sys.stdout)
        sys.stdout.flush()


# Global lazy loader instance
mlc_lazy_loader = LazyMLCModel()

# NOTE: Loading is NOT started automatically - call start_mlc_loading() after HLC is loaded
# This prevents resource contention during startup

# For backwards compatibility - will be None until loaded
mlc_model = None


def start_mlc_loading() -> None:
    """Start loading the MLC model in background. Call after HLC is loaded."""
    mlc_lazy_loader.start_loading()


def wait_for_mlc() -> bool:
    """Wait for MLC model to finish loading. Returns True if successful."""
    return mlc_lazy_loader.wait_for_completion()


def get_mlc_model():
    """Get the MLC model, returns None if not yet loaded."""
    return mlc_lazy_loader.model


def get_mlc_feature_cols():
    """Get the MLC feature columns, returns None if not yet loaded."""
    return mlc_lazy_loader.feature_cols


def get_mlc_scaler_dict():
    """Get the MLC scaler dictionary, returns None if not yet loaded."""
    return mlc_lazy_loader.scaler_dict


def get_mlc_status():
    """Get the current loading status of the MLC model."""
    return mlc_lazy_loader.get_status_dict()
