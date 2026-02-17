# Docker Configuration

This directory contains all Docker-related files for the NCATS ADME application.

## Dockerfiles

| File | Purpose | Use Case |
|------|---------|----------|
| `Dockerfile.test` | Autonomous testing with model warmup | **Local testing only** - not for deployment |
| `Dockerfile.backend` | Backend API only | Development, API testing |
| `Dockerfile.ncats` | Full stack (NCATS subdomain) | **All deployment environments** - Production: adme.ncats.nih.gov |
| `Dockerfile.opendata` | Full stack (OpenData subdomain) | Production: opendata.ncats.nih.gov/adme |

**Note:** `Dockerfile.ncats` should be used for all deployment environments. `Dockerfile.test` is only for local testing and model validation.

## Platform Requirements

All images are built for `linux/amd64` platform because:
- RDKit and FPSim2 conda packages are not available for ARM64
- On Apple Silicon Macs, images run via Rosetta 2 emulation

## Quick Start

### Run Local Tests (Dockerfile.test)

**Note:** `Dockerfile.test` is for local testing only, not for deployment.

```bash
cd ncats-adme
docker build -f docker/Dockerfile.test -t ncats-adme-test .
docker run -v $(pwd)/testing/results:/results ncats-adme-test
```

Results are saved to `./testing/results/<timestamp>/`:
- `predictions.json` - Full test data
- `report.txt` - Summary report
- `test_run.log` - Execution log

### Build Backend Only

```bash
docker build -f docker/Dockerfile.backend -t ncats-adme-backend .
docker run -p 5000:5000 ncats-adme-backend
```

### Build Deployment Images

**For all deployment environments, use `Dockerfile.ncats`:**

```bash
# Primary deployment image (use for all environments)
docker build -f docker/Dockerfile.ncats -t ncats-adme-ncats .
```

**For OpenData subdomain specifically:**

```bash
# OpenData subdomain only
docker build -f docker/Dockerfile.opendata -t ncats-adme-opendata .
```

## Layer Caching (Dockerfile.test)

The test Dockerfile is optimized for layer caching:

1. **Layer 1: Environment** - Only rebuilds when `environment.yml` changes
2. **Layer 2: Models** - Only rebuilds when model files change
3. **Layer 3: Predictors** - Static predictor files
4. **Layer 4: Application** - Rebuilds on code changes (fast)
5. **Layer 5: Scripts** - Test scripts and entrypoint
6. **Layer 6: Testing data** - Baseline predictions for comparison

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_TIMEOUT` | 1800 | Timeout for model loading (seconds) |
| `KEEP_RUNNING` | false | Keep server running after tests |
| `RESULTS_DIR` | /results | Directory for test results |

## Troubleshooting

### "Illegal instruction" on Apple Silicon

This occurs when running x86 Docker images on ARM64 Macs. The crash happens during `pickle.load()` of scikit-learn models that use AVX instructions.

**Workaround:** Use the `./scripts/test.sh local` command to run tests natively, or use a native x86 Linux machine.

### Build takes too long

The first build downloads all conda packages (~10-15 minutes). Subsequent builds use cached layers and are much faster.

To force a clean rebuild:
```bash
docker build --no-cache -f docker/Dockerfile.test -t ncats-adme-test .
```

