# Earthquake Production Audit

## Scope
Earthquake module only. Flood and other modules are out of scope.

## Findings

### Critical
- None open after verification.

### High
- Dataset has only 30 positive cases; holdout has 6. Perfect holdout metrics are not sufficient evidence of real-world reliability.
- No probability calibration applied.
- No spatial/geographic cross-validation.

### Medium
- CORS is permissive (`allow_origins=["*"]`) in `backend/main.py`.
- No rate limiting or request size limits.
- No persistent prediction history (by design).

### Low
- pyarrow not installed; pandas deprecation warning only.
- Artifact integrity is based on successful deserialization, not a stored checksum.

### Informational
- Model loads lazily and is cached; startup preloading added.
- Health and readiness endpoints added.
- Logging added to earthquake service.

## Verified
- RandomForest only.
- No leakage features.
- Threshold 0.19 from OOF training data.
- Feature schema consistent.
- 11 earthquake tests pass.