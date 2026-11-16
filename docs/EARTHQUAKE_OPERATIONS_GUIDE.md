# Earthquake Operations Guide

## Monitoring
- Logs: `disasterguard.earthquake` logger.
- Track prediction latency, errors, validation failures.
- Readiness endpoint verifies model availability.

## Model update
1. Run `python backend/ml/train_earthquake.py`.
2. Verify artifacts and tests.
3. Back up old artifacts.
4. Replace artifacts.
5. Restart service.
6. Check `/ready`.

## Troubleshooting
- Missing model: run training script.
- 503 from endpoints: model artifact missing/corrupt.
- Validation errors: check input ranges.

## Limitations
- 30 positive cases; metrics unstable.
- No calibration or drift monitoring implemented.