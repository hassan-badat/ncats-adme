#!/usr/bin/env python
"""
Comprehensive feature generator for DNN/RF models.

Generates all feature types needed by the retrained cytosol stability models:
- Morgan fingerprints (2048-bit, radius 2)
- RDKit fingerprints (2048-bit)
- Atom Pair fingerprints (2048-bit)
- Avalon fingerprints (2048-bit)
- MACCS Keys (167-bit)
- RDKit 2D descriptors (named, scaled)
- Mordred 2D descriptors (named, scaled)

Uses feature_cols from the model to select the right subset,
and scaler_dict to scale descriptor features.
"""
import warnings
import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import Descriptors, MACCSkeys, rdFingerprintGenerator
from rdkit.Avalon import pyAvalonTools

# Lazy-loaded mordred calculator (expensive to initialize)
_mordred_calc = None


def _get_mordred_calculator():
    """Get or create a cached mordred Calculator instance."""
    global _mordred_calc
    if _mordred_calc is None:
        from mordred import Calculator, descriptors
        _mordred_calc = Calculator(descriptors, ignore_3D=True)
    return _mordred_calc


def _generate_fingerprint(mol, fp_type, nBits=2048):
    """Generate a single fingerprint type and return as dict of named features."""
    features = {}

    if fp_type == 'morgan_fp':
        gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=nBits)
        arr = gen.GetFingerprintAsNumPy(mol)
    elif fp_type == 'rdkit_fp':
        gen = rdFingerprintGenerator.GetRDKitFPGenerator(fpSize=nBits)
        arr = gen.GetFingerprintAsNumPy(mol)
    elif fp_type == 'atompair_fp':
        gen = rdFingerprintGenerator.GetAtomPairGenerator(fpSize=nBits)
        arr = gen.GetFingerprintAsNumPy(mol)
    elif fp_type == 'avalon_fp':
        fp = pyAvalonTools.GetAvalonFP(mol, nBits=nBits)
        arr = np.zeros(nBits, dtype=np.int8)
        DataStructs.ConvertToNumpyArray(fp, arr)
    elif fp_type == 'maccs':
        fp = MACCSkeys.GenMACCSKeys(mol)
        arr = np.zeros(167, dtype=np.int8)
        DataStructs.ConvertToNumpyArray(fp, arr)
        for i in range(167):
            features[f'maccs_{i}'] = int(arr[i])
        return features
    else:
        raise ValueError(f'Unknown fingerprint type: {fp_type}')

    for i in range(len(arr)):
        features[f'{fp_type}_{nBits}_{i}'] = int(arr[i])

    return features


def _generate_rdkit_descriptors(mol):
    """Generate all RDKit 2D descriptors for a molecule."""
    features = {}
    for name, func in Descriptors.descList:
        try:
            val = func(mol)
            features[f'rdkit_ds_{name}'] = float(val) if val is not None else 0.0
        except Exception:
            features[f'rdkit_ds_{name}'] = 0.0
    return features


def _generate_mordred_descriptors(mol):
    """Generate all Mordred 2D descriptors for a molecule."""
    calc = _get_mordred_calculator()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = calc(mol)

    features = {}
    for desc, val in zip(calc.descriptors, result):
        name = str(desc)
        try:
            fval = float(val)
            features[f'mordred_ds_{name}'] = fval if np.isfinite(fval) else 0.0
        except (TypeError, ValueError):
            features[f'mordred_ds_{name}'] = 0.0
    return features


# Map feature prefixes to their generator info
_FP_TYPES = {
    'morgan_fp_2048_': 'morgan_fp',
    'rdkit_fp_2048_': 'rdkit_fp',
    'atompair_fp_2048_': 'atompair_fp',
    'avalon_fp_2048_': 'avalon_fp',
    'maccs_': 'maccs',
}


def generate_features(smiles_list, feature_cols, scaler_dict=None):
    """
    Generate the exact feature matrix needed by a model.

    Parameters:
        smiles_list: List of SMILES strings
        feature_cols: List of feature column names from the model
        scaler_dict: Optional dict mapping prefix to StandardScaler

    Returns:
        numpy array of shape (n_molecules, len(feature_cols))
    """
    # Determine which feature types are needed
    need_fp = {}
    for prefix, fp_type in _FP_TYPES.items():
        if any(c.startswith(prefix) for c in feature_cols):
            need_fp[fp_type] = True

    need_rdkit_ds = any(c.startswith('rdkit_ds_') for c in feature_cols)
    need_mordred_ds = any(c.startswith('mordred_ds_') for c in feature_cols)

    # Generate features for each molecule
    all_rows = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            # Return zeros for invalid molecules
            all_rows.append({col: 0.0 for col in feature_cols})
            continue

        row = {}

        # Generate fingerprints
        for fp_type in need_fp:
            row.update(_generate_fingerprint(mol, fp_type))

        # Generate RDKit descriptors
        if need_rdkit_ds:
            row.update(_generate_rdkit_descriptors(mol))

        # Generate Mordred descriptors
        if need_mordred_ds:
            row.update(_generate_mordred_descriptors(mol))

        all_rows.append(row)

    # Build DataFrame with all generated features
    df = pd.DataFrame(all_rows)

    # Apply scaling to descriptor columns using their respective scalers
    if scaler_dict is not None:
        for prefix, scaler in scaler_dict.items():
            if hasattr(scaler, 'feature_names_in_'):
                # Scaler knows which columns it expects
                scaler_cols = list(scaler.feature_names_in_)
                # Ensure all scaler columns exist in df (fill missing with 0)
                for col in scaler_cols:
                    if col not in df.columns:
                        df[col] = 0.0

                # Transform using the scaler's expected column order
                raw_values = df[scaler_cols].values
                # Replace NaN with 0 before scaling
                raw_values = np.nan_to_num(raw_values, nan=0.0, posinf=0.0, neginf=0.0)
                scaled_values = scaler.transform(raw_values)
                df[scaler_cols] = scaled_values

    # Select only the columns the model needs, in the right order
    result = np.zeros((len(smiles_list), len(feature_cols)), dtype=np.float64)
    for i, col in enumerate(feature_cols):
        if col in df.columns:
            values = df[col].values
            # Replace any remaining NaN
            values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
            result[:, i] = values

    return result

