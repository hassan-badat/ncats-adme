import numpy as np
import pandas as pd
from pandas import DataFrame
from rdkit import Chem
import warnings
warnings.filterwarnings('ignore')
from numpy import array
from typing import Tuple
from ..utilities.utilities import get_processed_smi
from . import pampa_gcnn_scaler, pampa_gcnn_model
from ..base.gcnn import GcnnBase
import time


class PAMPA50Predictior(GcnnBase):
    """
    Makes PAMPA 5.0 stability predictions

    Attributes:
        df (DataFrame): DataFrame containing column with smiles
        smiles_column_index (int): index of column containing smiles
        predictions_df (DataFrame): DataFrame hosting all predictions
    """

    def __init__(self, kekule_smiles: array = None, smiles: array = None):
        """
        Constructor for PAMPA50Predictior class

        Parameters:
            kekule_smiles (Array): numpy array of RDkit molecules
        """

        GcnnBase.__init__(self, kekule_smiles, column_dict_key='Predicted Class (Probability)', columns_dict_order=1, smiles=smiles)

        self._columns_dict['Prediction'] = {
            'order': 2,
            'description': 'class label',
            'isSmilesColumn': False
        }

        self.model_name = 'pampa50'

    def get_predictions(self) -> DataFrame:
        """
        Function that calculates consensus predictions

        Returns:
            Predictions (DataFrame): DataFrame with all predictions
        """

        if len(self.kekule_smiles) > 0:

            start = time.time()
            gcnn_predictions, gcnn_labels = self.gcnn_predict(pampa_gcnn_model, pampa_gcnn_scaler)
            end = time.time()
            print(f'PAMPA 5.0: {end - start} seconds to predict {len(self.predictions_df.index)} molecules')

            self.predictions_df['Prediction'] = pd.Series(
                pd.Series(np.where(gcnn_predictions >= 0.5, 'low permeability', 'moderate or high permeability'))
            )

        return self.predictions_df
