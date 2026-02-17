import numpy as np
import pandas as pd
from pandas import DataFrame
import warnings
warnings.filterwarnings('ignore')
from numpy import array
from . import pampa_gcnn_model
from ..base.gcnn import GcnnBase
import time


class PAMPABBBPredictior(GcnnBase):
    """
    Makes PAMPA BBB permeability predictions

    Attributes:
        df (DataFrame): DataFrame containing column with smiles
        smiles_column_index (int): index of column containing smiles
        predictions_df (DataFrame): DataFrame hosting all predictions
    """

    def __init__(self, kekule_smiles: array = None, smiles: array = None):
        """
        Constructor for PAMPA BBB Predictior class

        Parameters:
            kekule_smiles (Array): numpy array of RDkit molecules
        """

        GcnnBase.__init__(self, kekule_smiles, column_dict_key='Predicted Class (Probability)', columns_dict_order=1, smiles=smiles)

        # Note: model was trained without extra descriptors (d_vd=0),
        # so we do not pass additional_features

        self._columns_dict['Prediction'] = {
            'order': 2,
            'description': 'class label',
            'isSmilesColumn': False
        }

        self.model_name = 'pampabbb'

    def get_predictions(self) -> DataFrame:
        """
        Function that calculates consensus predictions

        Returns:
            Predictions (DataFrame): DataFrame with all predictions
        """

        if len(self.kekule_smiles) > 0:

            start = time.time()
            gcnn_predictions, gcnn_labels = self.gcnn_predict(pampa_gcnn_model)
            print(f'PAMPA BBB predictions: {gcnn_predictions}')
            end = time.time()
            print(f'PAMPA BBB: {end - start} seconds to predict {len(self.predictions_df.index)} molecules')

            self.predictions_df['Prediction'] = pd.Series(
                pd.Series(np.where(gcnn_predictions >= 0.5, 'moderate or high permeability', 'low permeability'))
            )

        return self.predictions_df
