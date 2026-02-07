#!/usr/bin/env python
"""
Warmup script - runs during Docker build to pre-load models.
This reduces first-prediction latency at runtime.
Uses only local models (no server fetching).
"""
import sys
import os

# Set working directory to /opt/adme (where models are in container)
os.chdir('/opt/adme')
sys.path.insert(0, '/opt/adme')

print("=" * 60)
print("MODEL WARMUP - Pre-loading models during build")
print("=" * 60)

# Import each model loader to trigger initialization
models_loaded = []
models_failed = []

# GCNN models (Chemprop)
gcnn_models = [
    ('RLM', 'predictors.rlm'),
    ('PAMPA', 'predictors.pampa'),
    ('PAMPA50', 'predictors.pampa50'),
    ('PAMPABBB', 'predictors.pampabbb'),
    ('Solubility', 'predictors.solubility'),
]

print("\n--- Loading GCNN Models (Chemprop) ---")
for name, module in gcnn_models:
    try:
        print(f"Loading {name}...")
        __import__(module)
        models_loaded.append(name)
        print(f"  ✓ {name} loaded successfully")
    except Exception as e:
        print(f"  ⚠ Warning: {name} - {e}")
        models_failed.append(name)

# sklearn/XGBoost models
sklearn_models = [
    ('HLM', 'predictors.hlm'),
    ('CYP450', 'predictors.cyp450'),
]

print("\n--- Loading sklearn/XGBoost Models ---")
for name, module in sklearn_models:
    try:
        print(f"Loading {name}...")
        __import__(module)
        models_loaded.append(name)
        print(f"  ✓ {name} loaded successfully")
    except Exception as e:
        print(f"  ⚠ Warning: {name} - {e}")
        models_failed.append(name)

# Lazy-loaded models (DNN-based, loaded in background)
# These use joblib.load and need TensorFlow 2.20+
lazy_models = [
    ('HLC', 'predictors.liver_cytosol'),
    ('MLC', 'predictors.mlc'),
    ('RLC', 'predictors.rlc'),
]

print("\n--- Lazy-Loaded Models (DNN) ---")
for name, module in lazy_models:
    try:
        print(f"Initializing {name} loader...")
        __import__(module)
        models_loaded.append(f"{name} (lazy)")
        print(f"  ✓ {name} loader initialized")
    except Exception as e:
        print(f"  ⚠ Warning: {name} - {e}")
        models_failed.append(name)

print("\n" + "=" * 60)
print(f"WARMUP COMPLETE")
print(f"  Loaded: {len(models_loaded)} models")
print(f"  Warnings: {len(models_failed)} models")
if models_loaded:
    print(f"  Successful: {', '.join(models_loaded)}")
if models_failed:
    print(f"  Failed: {', '.join(models_failed)}")
print("=" * 60)

# Exit with success even if some models failed (they might work at runtime)
sys.exit(0)

