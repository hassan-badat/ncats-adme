# ADME Model Testing

This directory contains tools for testing ADME prediction models against a baseline to ensure model behavior remains consistent after updates or retraining.

## Directory Structure

```
testing/
├── README.md                    # This file
├── baseline_predictions.json    # Source of truth (DO NOT DELETE OR REGENERATE)
├── runs/                        # Test run outputs (timestamped directories)
│   └── YYYY-MM-DD_HHMMSS/
│       ├── predictions.json     # Raw predictions from the test run
│       ├── comparison.json      # Detailed comparison metrics
│       └── report.txt           # Human-readable report
└── scripts/
    ├── test_retrained_models.py     # Main testing script
    ├── verify_predictions.py        # Utility to compare two prediction files
    └── create_baseline_predictions.py  # Script used to create baseline (reference only)
```

## Quick Start

### Running Tests

From the `ncats-adme/` directory:

```bash
# Start your ADME server first (default: localhost:5000)
python testing/scripts/test_retrained_models.py
```

This will:
1. Create a timestamped directory under `testing/runs/`
2. Run predictions against all working models
3. Compare results with the baseline
4. Generate a report

### Output

Each test run creates a directory like `testing/runs/2026-01-25_143022/` containing:

| File | Description |
|------|-------------|
| `predictions.json` | Raw prediction data from all models |
| `comparison.json` | Detailed comparison metrics against baseline |
| `report.txt` | Human-readable performance summary |

## Scripts

### test_retrained_models.py

Main testing script that runs predictions and compares against baseline.

```bash
# Default usage (localhost:5000)
python testing/scripts/test_retrained_models.py

# Custom server URL
python testing/scripts/test_retrained_models.py --url http://localhost:5001

# Skip server healthcheck
python testing/scripts/test_retrained_models.py --skip-healthcheck

# Only capture predictions (no comparison)
python testing/scripts/test_retrained_models.py --skip-comparison

# Custom baseline file
python testing/scripts/test_retrained_models.py --baseline /path/to/baseline.json
```

**Retrained Models (compared to baseline):**
- `rlm` - Rat Liver Microsome
- `hlm` - Human Liver Microsome
- `pampa` - PAMPA pH 7.4
- `pampa50` - PAMPA pH 5.0
- `pampabbb` - PAMPA Blood-Brain Barrier
- `solubility` - Aqueous Solubility
- `hlc` - Human Liver Cytosol
- `cyp450` - CYP450 Inhibition (6 endpoints)

**New Models (no baseline - results only):**
- `mlc` - Mouse Liver Cytosol (NEW in upgrade)
- `rlc` - Rat Liver Cytosol (NEW in upgrade)

### verify_predictions.py

Utility script for comparing two prediction files.

```bash
python testing/scripts/verify_predictions.py baseline.json updated.json
python testing/scripts/verify_predictions.py baseline.json updated.json --tolerance 0.01
```

### create_baseline_predictions.py

Script originally used to create `baseline_predictions.json`. Kept for reference only.

**WARNING:** Do not run this script. The baseline file should never be regenerated.

## Important Files

### baseline_predictions.json

This file contains predictions from the original backend before any refactors. It serves as the source of truth for testing.

**CRITICAL:** Never delete or regenerate this file. All testing comparisons are made against it.

The baseline was captured on 2025-12-03 and includes:
- 21 test molecules (common drugs and chemical compounds)
- 8 model endpoints
- Complete prediction data for validation

## Interpreting Results

### Agreement Rate

Each model is evaluated on "class agreement rate" - the percentage of molecules where the predicted class matches the baseline.

- **>=50%**: PASSING - Model behavior is reasonably consistent
- **<50%**: FAILING - Significant divergence from baseline

### Probability Differences

The comparison also tracks average probability differences to detect subtle changes in model confidence even when classes match.

### Example Report Output

```
======================================================================
RETRAINED MODEL PERFORMANCE REPORT
======================================================================

Run directory: testing/runs/2026-01-25_143022
Baseline captured: 2025-12-03T19:28:09.835973
Updated captured: 2026-01-25T14:30:22.123456

OVERALL SUMMARY
----------------------------------------------------------------------
Models tested: 7
Models passing (>=50% agreement): 7
Models failing: 0

PER-MODEL STATISTICS
----------------------------------------------------------------------

RLM
  Total molecules: 21
  Class agreements: 21
  Class disagreements: 0
  Agreement rate: 100.00%
  Avg probability difference: 0.0234
  Status: PASSING
```

## Test Molecules

The test suite uses 21 diverse molecules covering:
- Simple molecules (ethanol, methanol, acetone)
- Aromatic compounds (benzaldehyde, phenol, toluene)
- Common drugs (aspirin, caffeine, ibuprofen, paracetamol, etc.)
- Heterocyclic compounds (pyridine, imidazole, thiophene)
- Amino acids and organic acids (glycine, acetic acid)
- Larger drug-like molecules (omeprazole, atorvastatin)

## Troubleshooting

### Server Not Running

```
ERROR: Cannot connect to http://localhost:5000/healthcheck
```

Start your ADME server before running tests, or use `--skip-healthcheck` if the healthcheck endpoint differs.

### Baseline Not Found

```
WARNING: Baseline file not found: testing/baseline_predictions.json
```

Ensure you're running from the `ncats-adme/` directory or provide the full path with `--baseline`.

### Model Failures

If a model shows failures, check:
1. Model files are properly loaded
2. Dependencies are installed correctly
3. Server logs for specific errors

