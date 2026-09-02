# Phase 2.2 — Pattern Analysis
Generated: 2026-08-27T12:54:03 UTC

## Pattern Performance Comparison

| Pattern | Phase 1 (frozen) | Phase 2.1 (frozen) | Phase 2.2 (final) | Delta vs 2.1 |
|---------|:----------------:|:------------------:|:-----------------:|:------------:|
| Pattern A (multi-account device-sharing) | 91.7% | 91.7% | **100.0%** | +8.3pp |
| Pattern B (cross-merchant instrument-sharing) | 100.0% | 100.0% | **100.0%** | +0.0pp |
| Pattern C (sparse-history, rotating accounts) | 0.0% | 0.0% | **37.5%** | +37.5pp |
| **Overall Ring Recall** | 62.5% | 62.5% | **79.2%** | +16.7pp |

### Pattern A
- **Structural signature**: Multiple accounts sharing hardware devices, coordinated cross-merchant activity.
- **Primary source**: Graph stream (unsupervised ring detection via device nodes).
- **Phase 2.2**: Protected pool does not displace graph candidates; Pattern A result reflects graph stream capacity.

### Pattern B
- **Structural signature**: Coordinated refund abuse across merchants using shared payment instruments.
- **Primary source**: Graph stream (instrument-sharing edges in the payment graph).
- **Phase 2.2**: Same analysis as Pattern A — graph stream governs B coverage.

### Pattern C
- **Structural signature**: Sparse-history accounts, limited prior edges, rotate instruments/IPs.
- **Primary source**: Phase 1 individual risk model (tabular anomaly signals).
- **Phase 2.1 failure**: Phase-1-only candidates scored ~0.10 composite vs graph candidates 0.26+, ranking outside K=1000.
- **Phase 2.2 fix**: P=150 protected slots guarantee Phase-1 high-confidence candidates reach investigation.
- **Investigation fix**: Isolated candidates (no ring topology) fall back to Phase-1 score for the flagging decision.

## Denominator Transparency
| Pattern | Total Rings (held-out) | Detected Rings | Recall |
|---------|:---------------------:|:--------------:|:------:|
| A | 12 | 12 | 100.0% |
| B | 4 | 4 | 100.0% |
| C | 8 | 3 | 37.5% |
| Total | 24 | 19 | 79.2% |
