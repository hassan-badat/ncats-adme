# NCATS ADME Dependency Upgrade Plan

**Author:** Hassan Badat  
**Date:** December 2, 2025  
**Status:** In Progress

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Models Overview](#models-overview)
4. [Dependency Audit](#dependency-audit)
5. [Scope of Work](#scope-of-work)
6. [Implementation Plan](#implementation-plan)
7. [Verification Strategy](#verification-strategy)
8. [Risk Assessment](#risk-assessment)
9. [Timeline](#timeline)

---

## Executive Summary

### Goal

Upgrade the NCATS ADME prediction application to resolve security vulnerabilities in outdated Python libraries while maintaining prediction accuracy and API compatibility.

### Key Challenges

- **Chemprop**: Version 0.0.4 (vendored) → 2.2.1 - Complete API rewrite
- **Scikit-learn**: Version 0.22 → 1.4.x - Pickle model incompatibility
- **PyTorch**: Version 1.6.0 → 2.x - Model serialization changes
- **Docker**: Base image continuumio/miniconda:4.7.12 → 25.3.1

### Division of Work

| Responsibility                              | Owner                |
| ------------------------------------------- | -------------------- |
| Backend code changes for new library syntax | Hassan Badat         |
| Automating data cleaning/training pipeline  | Hassan Badat         |
| Model retraining with new libraries         | Claire Weber's Team  |
| CYP450 retraining code                      | External group (TBD) |

---

## Current State Assessment

### Application Architecture

```
ncats-adme/
├── client/                 # Angular frontend
│   └── src/
├── server/                 # Flask Python backend
│   ├── app.py             # Main application & API routes
│   ├── predictors/        # ML model implementations
│   │   ├── base/          # Base predictor classes
│   │   ├── chemprop/      # Vendored Chemprop library (v0.0.4)
│   │   ├── rlm/           # Rat Liver Microsome
│   │   ├── hlm/           # Human Liver Microsome
│   │   ├── pampa/         # PAMPA pH 7.4
│   │   ├── pampa50/       # PAMPA pH 5.0
│   │   ├── pampabbb/      # PAMPA Blood-Brain Barrier
│   │   ├── solubility/    # Aqueous Solubility
│   │   ├── liver_cytosol/ # Human Liver Cytosol
│   │   ├── cyp450/        # CYP450 enzyme interactions
│   │   ├── features/      # Feature generators
│   │   └── utilities/     # Shared utilities
│   ├── train_data/        # Pre-computed fingerprint DBs (.h5)
│   ├── environment.yml    # Conda environment spec
│   └── models/            # Downloaded model files (gitignored)
├── Dockerfile-ncats       # Docker build for ncats subdomain
└── Dockerfile-opendata    # Docker build for opendata subdomain
```

### Current Environment Issues

1. Dev, test, and prod environments are not identical
2. Models trained in different environment than deployment
3. Biweekly training pipeline is broken
4. Pipeline runs on local machine (not containerized)

---

## Models Overview

### Model Summary Table

| Model      | Type                     | Input Features                     | Output                | Update Frequency |
| ---------- | ------------------------ | ---------------------------------- | --------------------- | ---------------- |
| RLM        | GCNN (Chemprop)          | SMILES → molecular graph           | stable/unstable       | Biweekly         |
| HLM        | XGBoost + RLM            | RDKit descriptors + RLM prediction | stable/unstable       | Biweekly         |
| PAMPA      | GCNN (Chemprop)          | SMILES → molecular graph           | high/low permeability | Biweekly         |
| PAMPA50    | GCNN (Chemprop)          | SMILES → molecular graph           | high/low permeability | Biweekly         |
| PAMPA-BBB  | GCNN + RDKit             | SMILES + scaled descriptors        | high/low permeability | Biweekly         |
| Solubility | GCNN (Chemprop)          | SMILES → molecular graph           | high/low solubility   | Biweekly         |
| HLC        | Ensemble RF (3 models)   | Morgan fingerprints                | stable/unstable       | Static           |
| CYP450     | Ensemble RF (384 models) | Morgan FP + RDKit descriptors      | 6 endpoints           | Static           |

### Model Details

#### RLM (Rat Liver Microsome Stability)

- **File**: `server/predictors/rlm/rlm_predictor.py`
- **Architecture**: Graph Convolutional Neural Network via Chemprop
- **Model Source**: `https://opendata.ncats.nih.gov/public/adme/models/current/biweekly/rlm/gcnn_model.pt`
- **Dependencies**: PyTorch, Chemprop

#### HLM (Human Liver Microsome Stability)

- **File**: `server/predictors/hlm/hlm_predictor.py`
- **Architecture**: XGBoost classifier using RLM predictions + RDKit descriptors as features
- **Model Source**: `https://opendata.ncats.nih.gov/public/adme/models/current/static/hlm/model.pkl`
- **Dependencies**: XGBoost, scikit-learn, RDKit, RLM model

#### PAMPA / PAMPA50 / PAMPA-BBB

- **Files**: `server/predictors/pampa*/pampa_predictor.py`
- **Architecture**: GCNN (PAMPA-BBB includes additional RDKit descriptor features)
- **Dependencies**: PyTorch, Chemprop, RDKit

#### Solubility

- **File**: `server/predictors/solubility/solubility_predictor.py`
- **Architecture**: GCNN via Chemprop
- **Dependencies**: PyTorch, Chemprop

#### HLC (Human Liver Cytosol Stability)

- **File**: `server/predictors/liver_cytosol/lc_predictor.py`
- **Architecture**: Ensemble of 3 Random Forest models (consensus averaging)
- **Input**: Morgan fingerprints (1024-bit)
- **Model Source**: `https://opendata.ncats.nih.gov/public/adme/models/current/static/liver_cytosol/`
- **Dependencies**: scikit-learn

#### CYP450 (Cytochrome P450 Enzyme Interactions)

- **File**: `server/predictors/cyp450/cyp450_predictor.py`
- **Architecture**: 64 Random Forest models × 6 endpoints = 384 models total
- **Endpoints**: CYP2C9_inhib, CYP2C9_subs, CYP2D6_inhib, CYP2D6_subs, CYP3A4_inhib, CYP3A4_subs
- **Input**: Morgan fingerprints + RDKit descriptors (MolLogP, TPSA, MW, NumHDonors, NumHAcceptors)
- **Model Source**: `https://opendata.ncats.nih.gov/public/adme/models/current/static/cyp450/`
- **Dependencies**: scikit-learn, multiprocessing
- **Note**: Retraining code coming from external group

---

## Dependency Audit

### Current vs Target Versions

| Package      | Current Version  | Target Version | Breaking Changes         | Action Required                     |
| ------------ | ---------------- | -------------- | ------------------------ | ----------------------------------- |
| Python       | ≥3.7             | 3.11           | Minor                    | Update environment                  |
| PyTorch      | 1.6.0            | 2.2.x          | Model loading changes    | Test model compatibility            |
| Chemprop     | 0.0.4 (vendored) | 2.2.1          | **Complete API rewrite** | Major code refactor                 |
| scikit-learn | 0.22             | 1.4.x          | Pickle incompatible      | Retrain models                      |
| XGBoost      | 2.0.3            | 2.0.3          | None                     | ✅ Already current                  |
| RDKit        | 2020.03          | 2024.03        | Some API changes         | Test descriptors                    |
| NumPy        | 1.18             | 1.26.x         | Deprecations             | Update code                         |
| Pandas       | 1.1.3            | 2.2.x          | `append()` removed       | **Fix immediately**                 |
| Flask        | 2.2.2            | 3.x            | Minor                    | Update                              |
| TensorFlow   | 2.2.0            | 2.16.x         | API changes              | **Keep - needed for new DNN model** |
| FPSim2       | 0.2.6            | 0.4.x          | API changes              | Test similarity calc                |

### Docker Image

| Component           | Current                      | Target                          |
| ------------------- | ---------------------------- | ------------------------------- |
| Base Image          | continuumio/miniconda:4.7.12 | continuumio/miniconda3:24.7.1-0 |
| Node.js             | 16                           | 20 LTS                          |
| Angular CLI         | 12                           | 17                              |
| Deprecated Commands | `apt-get install net-tools`  | Use `iproute2`                  |

---

## Scope of Work

### 🟢 Hassan's Deliverables (~1 Week)

These can be completed independently, without waiting for Claire's team.

#### 1.0 Capture Baseline Predictions

**Purpose:** Create a "ground truth" of current model outputs before making any changes.

**Process:**

1. Set up local environment: `conda env create -f environment.yml`
2. Start server: `python app.py` (models auto-download from NCATS servers)
3. Run baseline capture script against all 8 models
4. Save results to `baseline_predictions.json`

**Why this matters:** Any code changes can be verified by comparing new outputs to this baseline.

#### 1.1 Fix Pandas Deprecations

**Files to modify:**

- [x] `server/predictors/base/gcnn.py` (line 99)
- [x] `server/predictors/hlm/hlm_predictor.py` (line 105)
- [x] `server/predictors/liver_cytosol/lc_predictor.py` (line 100)
- [x] `server/predictors/cyp450/cyp450_predictor.py` (line 175)

**Change:**

```python
# BEFORE (deprecated in Pandas 2.0)
df = df.append(new_df, ignore_index=True)

# AFTER
df = pd.concat([df, new_df], ignore_index=True)
```

#### 1.2 Create Test Infrastructure

- [x] Create `scripts/` directory for testing tools
- [x] Create baseline prediction capture script
- [x] Create prediction comparison script
- [ ] Create individual predictor test script

#### 1.3 Create Modern Dockerfile (Proof of Concept)

- [ ] Create `Dockerfile.modern` with updated base image
- [ ] Create `server/environment_modern.yml` with target versions

#### 1.4 Documentation & Research

- [ ] Document Chemprop 0.x → 2.x API differences
- [ ] Create file-by-file migration notes
- [ ] Document testing methodology for handoff

---

### 🟡 Blocked: Waiting on Claire's Team

These require training scripts or retrained models from Claire.

#### 2.1 Chemprop Migration (Blocked: Need new models)

**Files requiring major changes:**

- [ ] `server/predictors/base/gcnn.py` - Core GCNN prediction logic
- [ ] `server/predictors/chemprop/` - Replace vendored library with pip package
- [ ] All GCNN-based predictors (RLM, PAMPA variants, Solubility)

**Key API changes to handle:**

```python
# OLD (Chemprop 0.x)
from chemprop.data.utils import get_data_from_smiles
from chemprop.data import MoleculeDataLoader, MoleculeDataset
from chemprop.train import predict

# NEW (Chemprop 2.x) - Completely different
from chemprop import data, featurizers, models
# Uses PyTorch Lightning, different model structure
```

#### 2.2 Scikit-learn Compatibility (Blocked: Need new models)

**Files affected:**

- [ ] `server/predictors/hlm/__init__.py` - XGBoost model loading
- [ ] `server/predictors/liver_cytosol/__init__.py` - RF model loading
- [ ] `server/predictors/cyp450/__init__.py` - RF model loading

#### 2.3 Training Pipeline Automation (Blocked: Need training scripts)

**Data Cleaning Pipeline:**

- [ ] Integrate Claire's data preprocessing scripts
- [ ] Document data format requirements
- [ ] Create validation checks for training data

**Training Pipeline:**

- [ ] Integrate training scripts for GCNN models
- [ ] Integrate training scripts for RF/XGB models
- [ ] Integrate with CI/CD

#### 2.4 Environment Standardization (Blocked: Need full testing)

- [ ] Ensure dev/test/prod use identical Docker images
- [ ] Document model training environment requirements
- [ ] Create environment validation scripts

---

## Verification Strategy

### Testing Methodology

#### Step 1: Capture Baseline (Before Any Changes)

```bash
cd server
python scripts/create_baseline_predictions.py
# Saves: baseline_predictions.json
```

#### Step 2: Test After Each Change

```bash
# After making changes, restart server and capture new predictions
python scripts/create_baseline_predictions.py --output updated_predictions.json

# Compare
python scripts/verify_predictions.py
```

### Test Molecules

Use diverse molecules covering different chemical classes:

```python
TEST_SMILES = [
    "CCO",                           # Ethanol (simple alcohol)
    "CC(=O)OC1=CC=CC=C1C(=O)O",      # Aspirin (aromatic, ester, carboxylic acid)
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine (heterocyclic, multiple N)
    "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", # Ibuprofen (aromatic, carboxylic acid)
    "C1=CC=C(C=C1)C=O",              # Benzaldehyde (aldehyde)
    "CC(=O)NC1=CC=C(C=C1)O",         # Paracetamol (amide, phenol)
    "INVALID_SMILES_12345",          # Invalid - test error handling
]
```

### API Endpoints to Test

| Endpoint                           | Method | Test Cases                         |
| ---------------------------------- | ------ | ---------------------------------- |
| `/api/v1/predict`                  | GET    | All 8 models, valid/invalid SMILES |
| `/api/v1/predict-file`             | POST   | CSV upload, multiple molecules     |
| `/api/v1/structure_image/{smiles}` | GET    | Valid molecule rendering           |
| `/api/v1/structure_image_glowing`  | GET    | Substructure highlighting          |
| `/healthcheck`                     | GET    | Server health                      |

### Verification Checklist

#### Pre-Change

- [ ] Baseline predictions captured
- [ ] Server runs without errors
- [ ] All endpoints respond correctly

#### Per-File Change

- [ ] File saves without syntax errors
- [ ] Imports resolve correctly
- [ ] Relevant predictor can be instantiated
- [ ] Predictions match expected format

#### Post-Change (Full Regression)

- [ ] All 8 models produce predictions
- [ ] Error handling works for invalid input
- [ ] API response structure unchanged
- [ ] Tanimoto similarity calculations work
- [ ] Performance not significantly degraded

---

## Risk Assessment

### High Risk

| Risk                              | Impact                 | Mitigation                                        |
| --------------------------------- | ---------------------- | ------------------------------------------------- |
| Chemprop API completely different | All GCNN models break  | Coordinate closely with Claire on model format    |
| Pickle models incompatible        | HLC, CYP450, HLM break | Wait for retrained models                         |
| PyTorch model loading fails       | All GCNN models break  | Test with exact PyTorch version used for training |

### Medium Risk

| Risk                     | Impact                 | Mitigation                       |
| ------------------------ | ---------------------- | -------------------------------- |
| RDKit descriptor changes | Feature values differ  | Validate descriptor calculations |
| FPSim2 API changes       | Similarity calc breaks | Test separately                  |
| NumPy deprecations       | Warnings or errors     | Address systematically           |

### Low Risk

| Risk           | Impact             | Mitigation                   |
| -------------- | ------------------ | ---------------------------- |
| Pandas changes | Minor code updates | Already identified, easy fix |
| Flask changes  | API adjustments    | Minimal impact expected      |

---

## Timeline

### Hassan's Deliverables (~1 Week)

All items below can be completed independently without waiting for Claire's team.

#### Baseline Capture (Before Any Code Changes)

- [x] Set up local development environment (`conda env create -f environment.yml`)
- [x] Run server locally (models auto-download from NCATS servers)
- [x] Create `scripts/` directory with test infrastructure
- [x] Create baseline prediction capture script
- [x] Create prediction comparison/verification script
- [x] **Capture baseline predictions from all 8 models** → `baseline_predictions.json`

#### Code Fixes

- [x] Fix Pandas deprecations in all 4 files (PR #1)
  - [x] `server/predictors/base/gcnn.py`
  - [x] `server/predictors/hlm/hlm_predictor.py`
  - [x] `server/predictors/liver_cytosol/lc_predictor.py`
  - [x] `server/predictors/cyp450/cyp450_predictor.py`
- [ ] Verify predictions still match baseline after fixes
- [ ] Document any other deprecation warnings found

#### Docker & Environment Modernization

- [ ] Create `Dockerfile.modern` (proof of concept)
- [ ] Create `server/environment_modern.yml` with updated package versions
- [ ] Document Chemprop 2.x API differences
- [ ] Create migration notes for each predictor file

#### Documentation & Handoff Prep

- [ ] Complete dependency audit with specific version targets
- [ ] Document testing methodology for Claire's team
- [ ] List all files requiring changes when new models are ready
- [ ] Update this plan with findings and recommendations

---

### Waiting on Claire's Team (No Fixed Timeline)

These items are **blocked** until Claire's team provides training scripts and/or retrained models:

- [ ] Receive training scripts for GCNN models (RLM, PAMPA, Solubility)
- [ ] Receive retrained models compatible with new library versions
- [ ] Receive CYP450 retraining code from external group

### After Receiving Models from Claire

- [ ] Update prediction code for new Chemprop 2.x API
- [ ] Update model loading code for new scikit-learn
- [ ] Full regression testing against baseline
- [ ] Integrate training scripts into automated pipeline
- [ ] CI/CD integration
- [ ] Environment standardization (dev = test = prod)

---

## Files Created/Modified

### New Files

| File                                     | Purpose                         |
| ---------------------------------------- | ------------------------------- |
| `UPGRADE_PLAN.md`                        | This document                   |
| `scripts/create_baseline_predictions.py` | Capture baseline predictions    |
| `scripts/verify_predictions.py`          | Compare predictions             |
| `server/environment_modern.yml`          | Updated conda environment       |
| `Dockerfile-ncats-modern`                | Modern Docker config (ncats)    |
| `Dockerfile-opendata-modern`             | Modern Docker config (opendata) |

### Modified Files

| File                                                   | Changes                       |
| ------------------------------------------------------ | ----------------------------- |
| `server/predictors/base/gcnn.py`                       | Rewritten for Chemprop 2.x    |
| `server/predictors/utilities/utilities.py`             | Updated model loading for 2.x |
| `server/predictors/rlm/__init__.py`                    | Updated for Chemprop 2.x      |
| `server/predictors/rlm/rlm_predictor.py`               | Cleaned up imports            |
| `server/predictors/pampa/__init__.py`                  | Updated for Chemprop 2.x      |
| `server/predictors/pampa/pampa_predictor.py`           | Cleaned up imports            |
| `server/predictors/pampa50/__init__.py`                | Updated for Chemprop 2.x      |
| `server/predictors/pampa50/pampa_predictor.py`         | Cleaned up imports            |
| `server/predictors/pampabbb/__init__.py`               | Updated for Chemprop 2.x      |
| `server/predictors/pampabbb/pampa_predictor.py`        | Cleaned up imports            |
| `server/predictors/solubility/__init__.py`             | Updated for Chemprop 2.x      |
| `server/predictors/solubility/solubility_predictor.py` | Cleaned up imports            |
| `server/predictors/hlm/__init__.py`                    | Cleaned up code               |
| `server/predictors/hlm/hlm_predictor.py`               | Cleaned up imports            |
| `server/predictors/liver_cytosol/__init__.py`          | Cleaned up code               |
| `server/predictors/liver_cytosol/lc_predictor.py`      | Cleaned up imports            |
| `server/predictors/cyp450/__init__.py`                 | Cleaned up code               |
| `server/predictors/cyp450/cyp450_predictor.py`         | Cleaned up imports            |

### Deleted Files

| File/Directory                | Reason                                   |
| ----------------------------- | ---------------------------------------- |
| `server/predictors/chemprop/` | Vendored library replaced by pip install |

---

## Communication Log

| Date        | With         | Topic                    | Outcome                                                                                                          |
| ----------- | ------------ | ------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Dec 2, 2025 | Claire Weber | Initial discussion       | Scope defined, training handled by her team                                                                      |
| Dec 8, 2025 | Claire Weber | Model retraining request | Requested retrained models: GCNN models with Chemprop 2.x (.ckpt), sklearn models with scikit-learn 1.4.x (.pkl) |

---

## References

- [Chemprop GitHub](https://github.com/chemprop/chemprop)
- [RDKit Documentation](https://www.rdkit.org/docs/)
- [Pandas Migration Guide](https://pandas.pydata.org/docs/whatsnew/)
- [PyTorch Model Loading](https://pytorch.org/docs/stable/generated/torch.load.html)
