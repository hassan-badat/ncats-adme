import os
import pandas as pd
from pandas import DataFrame
import numpy as np
from numpy import array
from rdkit import Chem
from ..features.morgan_fp import MorganFPGenerator
from ..features.rdkit_descriptors import RDKitDescriptorsGenerator
from . import load_model, CYP450_ENDPOINTS, NUM_MODELS_PER_ENDPOINT
import time
import csv
from datetime import timezone
import datetime

# RDKit descriptors used during model training (must match exactly)
_CYP450_RDKIT_DESCRIPTORS = ['MolLogP', 'TPSA', 'ExactMolWt', 'NumHDonors', 'NumHAcceptors']


class CYP450Predictor:
    """
    Makes CYP450 predictions for 6 endpoints:
    - cyp2c9_inhib: CYP2C9 Inhibition
    - cyp2c9_subs: CYP2C9 Substrate
    - cyp2d6_inhib: CYP2D6 Inhibition
    - cyp2d6_subs: CYP2D6 Substrate
    - cyp3a4_inhib: CYP3A4 Inhibition
    - cyp3a4_subs: CYP3A4 Substrate

    Each endpoint uses 64 Random Forest models with consensus voting.
    Models are pre-loaded at startup and served from an in-memory cache.

    Feature vector (1029 features per molecule):
    - 1024-bit count-based Morgan fingerprints (radius=2)
    - 5 RDKit descriptors: MolLogP, TPSA, ExactMolWt, NumHDonors, NumHAcceptors
    """

    _columns_dict = {
        'CYP2C9 Inhibition': {
            'order': 1,
            'description': 'CYP2C9 inhibition prediction (consensus of 64 models)',
            'isSmilesColumn': False
        },
        'CYP2C9 Substrate': {
            'order': 2,
            'description': 'CYP2C9 substrate prediction (consensus of 64 models)',
            'isSmilesColumn': False
        },
        'CYP2D6 Inhibition': {
            'order': 3,
            'description': 'CYP2D6 inhibition prediction (consensus of 64 models)',
            'isSmilesColumn': False
        },
        'CYP2D6 Substrate': {
            'order': 4,
            'description': 'CYP2D6 substrate prediction (consensus of 64 models)',
            'isSmilesColumn': False
        },
        'CYP3A4 Inhibition': {
            'order': 5,
            'description': 'CYP3A4 inhibition prediction (consensus of 64 models)',
            'isSmilesColumn': False
        },
        'CYP3A4 Substrate': {
            'order': 6,
            'description': 'CYP3A4 substrate prediction (consensus of 64 models)',
            'isSmilesColumn': False
        }
    }

    # Mapping from endpoint names to display names
    _endpoint_to_column = {
        'cyp2c9_inhib': 'CYP2C9 Inhibition',
        'cyp2c9_subs': 'CYP2C9 Substrate',
        'cyp2d6_inhib': 'CYP2D6 Inhibition',
        'cyp2d6_subs': 'CYP2D6 Substrate',
        'cyp3a4_inhib': 'CYP3A4 Inhibition',
        'cyp3a4_subs': 'CYP3A4 Substrate'
    }

    def __init__(self, kekule_mols: array = None, smiles: array = None):
        """
        Constructor for CYP450Predictor class

        Parameters:
            kekule_mols (array): n x 1 array of RDKit molecule objects
            smiles (array): optional n x 1 array of SMILES for recording predictions
        """
        if kekule_mols is None or len(kekule_mols) == 0:
            raise ValueError('Please provide valid molecules')

        self.kekule_mols = kekule_mols

        # Generate 1024-bit count-based Morgan fingerprints (matches model training)
        morgan_fp_generator = MorganFPGenerator(self.kekule_mols)
        morgan_fp_matrix = morgan_fp_generator.get_morgan_features()

        # Generate 5 RDKit descriptors (matches model training)
        rdkit_desc_generator = RDKitDescriptorsGenerator(self.kekule_mols)
        rdkit_desc_matrix = rdkit_desc_generator.get_rdkit_descriptors(_CYP450_RDKIT_DESCRIPTORS)

        # Concatenate to produce 1029-feature vector (1024 FP + 5 descriptors)
        self.features = np.append(morgan_fp_matrix, rdkit_desc_matrix, axis=1)

        # Create dataframe for predictions
        columns = self._columns_dict.keys()
        self.predictions_df = pd.DataFrame(columns=columns)
        self.raw_predictions_df = pd.DataFrame()

        self.smiles = smiles
        self.has_errors = False
        self.model_errors = []

    def _predict_endpoint(self, endpoint: str, features: array) -> array:
        """
        Make predictions for a single CYP450 endpoint using all 64 models.
        Models are read from the pre-loaded in-memory cache.

        Parameters:
            endpoint: The CYP450 endpoint name
            features: Morgan fingerprint features

        Returns:
            Array of averaged prediction probabilities
        """
        all_predictions = []
        models_used = 0

        for model_num in range(NUM_MODELS_PER_ENDPOINT):
            model = load_model(endpoint, model_num)
            if model is not None:
                try:
                    pred_probs = model.predict_proba(features)[:, 1]
                    all_predictions.append(pred_probs)
                    models_used += 1
                except Exception as e:
                    print(f'ERROR: Prediction failed for {endpoint}/model_{model_num}: {e}')

        if models_used == 0:
            self.model_errors.append(f'No models loaded for {endpoint}')
            return np.zeros(len(features))

        # Average predictions across all models
        avg_predictions = np.mean(all_predictions, axis=0)

        return avg_predictions

    def get_predictions(self) -> DataFrame:
        """
        Calculate predictions for all 6 CYP450 endpoints.

        Returns:
            DataFrame with predictions for all endpoints
        """
        if len(self.features) == 0:
            self.has_errors = True
            self.model_errors.append('No valid molecules to predict')
            return self.predictions_df

        features = self.features
        start = time.time()

        # Process each endpoint
        for endpoint in CYP450_ENDPOINTS:
            column_name = self._endpoint_to_column[endpoint]
            print(f'CYP450: Processing {endpoint}...', flush=True)

            pred_probs = self._predict_endpoint(endpoint, features)

            # Format predictions with class and probability
            # Use explicit >= 0.5 threshold (not round(), which uses banker's rounding)
            pred_classes = np.where(np.asarray(pred_probs) >= 0.5, 1, 0)
            pred_confidence = np.where(
                np.asarray(pred_probs) >= 0.5,
                np.asarray(pred_probs),
                (1 - np.asarray(pred_probs))
            )
            self.predictions_df[column_name] = pd.Series(
                pd.Series(pred_classes).astype(str) + ' (' +
                pd.Series(pred_confidence).round(2).astype(str) + ')'
            )

        # Populate raw predictions for recording
        if self.smiles is not None:
            dt = datetime.datetime.now(timezone.utc)
            utc_time = dt.replace(tzinfo=timezone.utc)
            utc_timestamp = utc_time.timestamp()

            for endpoint in CYP450_ENDPOINTS:
                column_name = self._endpoint_to_column[endpoint]
                # Extract just the probability from the formatted string
                probs = self.predictions_df[column_name].str.extract(r'\(([0-9.]+)\)')[0].astype(float)

                self.raw_predictions_df = pd.concat([
                    self.raw_predictions_df,
                    pd.DataFrame({
                        'SMILES': self.smiles,
                        'model': endpoint,
                        'prediction': probs.values,
                        'timestamp': utc_timestamp
                    })
                ], ignore_index=True)

        end = time.time()
        print(f'CYP450: {end - start:.2f} seconds to predict {len(features)} molecules across 6 endpoints')

        if self.model_errors:
            self.has_errors = True

        return self.predictions_df

    def _error_callback(self, error):
        print(error)

    def get_errors(self):
        return {
            'model_errors': self.model_errors
        }

    def columns_dict(self):
        return self._columns_dict.copy()

    def record_predictions(self, file_path):
        if len(self.raw_predictions_df.index) > 0:
            with open(file_path, 'a') as fw:
                rows = self.raw_predictions_df.values.tolist()
                cw = csv.writer(fw)
                cw.writerows(rows)
