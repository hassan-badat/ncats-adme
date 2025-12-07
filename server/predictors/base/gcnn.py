from numpy import array
import numpy as np
import pandas as pd
from rdkit import Chem
from typing import Tuple
from datetime import timezone
import datetime
import torch

from chemprop.data import MoleculeDatapoint, MoleculeDataset, build_dataloader
from chemprop.nn import BinaryClassificationFFN
from chemprop.models import MPNN

from .base import PredictorBase


class GcnnBase(PredictorBase):

    def __init__(self, kekule_smiles: array = None, additional_features: array = None, column_dict_key='GCNN', columns_dict_order: int = 1, smiles: array = None):
        PredictorBase.__init__(self)

        if kekule_smiles is None or len(kekule_smiles) == 0:
            raise ValueError('Please provide a list of kekule smiles')

        self.kekule_smiles = kekule_smiles

        self.additional_features = additional_features

        self.column_dict_key = column_dict_key

        self._columns_dict[column_dict_key] = {
            'order': columns_dict_order,
            'description': 'graph convolutional neural network prediction',
            'isSmilesColumn': False
        }

        self.smiles = smiles
        self.model_name = None
        self.model_version = None

    def gcnn_predict(self, model: MPNN, scaler=None) -> Tuple[array, array]:
        """
        Function that handles graph convolutional neural network predictions using Chemprop 2.x

        Parameters:
            model (MPNN): Chemprop 2.x MPNN model
            scaler: Optional scaler (may be embedded in model checkpoint)

        Returns:
            predictions, prediction_labels (Tuple[array, array]): predictions and labels
        """

        smiles_list = self.kekule_smiles.tolist()
        feat = self.additional_features

        # Build datapoints for each SMILES
        datapoints = []
        full_to_valid_indices = {}
        valid_index = 0

        for full_index, smi in enumerate(smiles_list):
            mol = Chem.MolFromSmiles(smi)
            if mol is not None:
                # Create datapoint with optional additional features
                if feat is not None:
                    dp = MoleculeDatapoint(
                        mol=mol,
                        x_d=feat[full_index] if full_index < len(feat) else None
                    )
                else:
                    dp = MoleculeDatapoint(mol=mol)
                datapoints.append(dp)
                full_to_valid_indices[full_index] = valid_index
                valid_index += 1

        # Create dataset and dataloader
        dataset = MoleculeDataset(datapoints)
        dataloader = build_dataloader(dataset, batch_size=64, num_workers=0, shuffle=False)

        # Run prediction
        model.eval()
        with torch.no_grad():
            model_preds = model.predict(dataloader)

        # Map predictions back to original indices
        predictions = np.ma.empty(len(smiles_list))
        predictions.mask = True

        labels = np.ma.empty(len(smiles_list), dtype=np.int32)
        labels.mask = True

        for full_index, valid_idx in full_to_valid_indices.items():
            pred_value = model_preds[valid_idx][0] if len(model_preds[valid_idx]) > 0 else model_preds[valid_idx]
            predictions[full_index] = float(pred_value)
            labels[full_index] = int(np.round(float(pred_value), 0))

        # Record raw predictions if smiles provided
        if self.smiles is not None:
            dt = datetime.datetime.now(timezone.utc)
            utc_time = dt.replace(tzinfo=timezone.utc)
            utc_timestamp = utc_time.timestamp()

            self.raw_predictions_df = pd.concat([
                self.raw_predictions_df,
                pd.DataFrame(
                    {'SMILES': self.smiles, 'model': self.model_name, 'prediction': predictions, 'timestamp': utc_timestamp}
                )
            ], ignore_index=True)

        # Format predictions for display
        self.predictions_df[self.column_dict_key] = pd.Series(
            pd.Series(labels).fillna('').astype(str) + ' (' +
            pd.Series(np.where(predictions >= 0.5, predictions, (1 - predictions))).round(2).astype(str) + ')'
        ).str.replace('(nan)', '', regex=False)

        if len(self.predictions_df.index) > len(predictions) or np.ma.count_masked(predictions) > 0:
            self.model_errors.append('graph convolutional neural network')
            self.has_errors = True

        return predictions, labels
