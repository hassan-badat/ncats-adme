import os
import pandas as pd
from pandas import DataFrame
import numpy as np
from numpy import array
from rdkit import Chem
from ..features.comprehensive_features import generate_features
from ..mlc import get_mlc_model, get_mlc_feature_cols, get_mlc_scaler_dict, get_mlc_status
import time
import csv
from datetime import timezone
import datetime


class MLCPredictor:
    """
    Makes Mouse Liver Cytosol Stability predictions

    Attributes:
        df (DataFrame): DataFrame containing column with smiles
        smiles_column_index (int): index of column containing smiles
        predictions_df (DataFrame): DataFrame hosting all predictions
    """

    _columns_dict = {
        'Predicted Class (Probability)': {
            'order': 1,
            'description': 'random forest prediction',
            'isSmilesColumn': False
        },
        'Prediction': {
            'order': 2,
            'description': 'class label',
            'isSmilesColumn': False
        }
    }

    def __init__(self, kekule_smiles: array = None, morgan_fp: array = None, smiles: array = None):
        """
        Constructor for MLCPredictor class

        Parameters:
            kekule_mols (array): n x 1 array of RDKit molecule objects kekulized
            morgan_fp_matrix (array): optional numpy array of morgan fingerprints for each molecule,
            smiles (array): optional n x 1 array of SMILES used to record raw predictions in raw_predictions_df property
        """

        if len(kekule_smiles) == 0:
            raise ValueError('Please provide valid SMILES')

        self.kekule_smiles = kekule_smiles

        # create dataframe to be filled with predictions
        columns = self._columns_dict.keys()
        self.predictions_df = pd.DataFrame(columns=columns)
        self.raw_predictions_df = pd.DataFrame()

        self.smiles = smiles
        self.has_errors = False
        self.model_errors = []

    def get_predictions(self):

        start = time.time()

        mlc_model = get_mlc_model()
        feature_cols = get_mlc_feature_cols()
        scaler_dict = get_mlc_scaler_dict()

        if mlc_model is None:
            self.has_errors = True
            status = get_mlc_status()
            if status['status'] == 'loading':
                self.model_errors.append('MLC model is still loading - please try again later')
            elif status['status'] == 'failed':
                self.model_errors.append(f'MLC model failed to load: {status["error"]}')
            else:
                self.model_errors.append('MLC model not loaded')
            return self.predictions_df

        if feature_cols is None:
            self.has_errors = True
            self.model_errors.append('MLC feature_cols not available')
            return self.predictions_df

        # Generate comprehensive features matching the model's expected input
        features = generate_features(
            list(self.kekule_smiles),
            feature_cols,
            scaler_dict
        )

        pred_probs = mlc_model.predict_proba(features).T[1]

        self.predictions_df['Predicted Class (Probability)'] = pd.Series(
            pd.Series(pred_probs).round().astype(int).astype(str) + ' (' +
            pd.Series(np.where(np.asarray(pred_probs) >= 0.5, np.asarray(pred_probs), (1-np.asarray(pred_probs)))).round(2).astype(str) + ')'
        )
        self.predictions_df['Prediction'] = pd.Series(
            pd.Series(np.where(np.asarray(pred_probs) >= 0.5, 'unstable', 'stable'))
        )

        # populate raw df for recording preds
        if self.smiles is not None:
            dt = datetime.datetime.now(timezone.utc)
            utc_time = dt.replace(tzinfo=timezone.utc)
            utc_timestamp = utc_time.timestamp()
            self.raw_predictions_df = pd.concat([
                self.raw_predictions_df,
                pd.DataFrame(
                    {'SMILES': self.smiles, 'model': 'mlc', 'prediction': pred_probs, 'timestamp': utc_timestamp}
                )
            ], ignore_index=True)

        end = time.time()
        print(f'MLC: {end - start} seconds to predict {len(self.raw_predictions_df.index)} molecules')

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
