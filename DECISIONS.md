# Decision log

1. Select one brand after a data audit so response style and intent definitions remain coherent.
2. Derive and freeze the taxonomy from training data before test annotation.
3. Split whole conversation roots chronologically to reduce reply and future-context leakage.
4. Keep the 200-example golden set separate from classifier training labels.
5. Bundle only redacted real AmazonHelp examples; mark heuristic labels as weak and block them from official evaluation.
6. Start with explainable BM25 retrieval and earn dense retrieval through measured errors.
7. Use a bounded orchestrator and offline action allowlist conditioned on historical replies; this makes guidance auditable but deliberately sacrifices coverage.
8. Use in-process BM25 retrieval by default so the reviewer can reproduce results without running an extra service.
9. Let deterministic policy own the final route; the draft model cannot authorize auto-handling.
10. Treat account actions, credentials, missing evidence, and dependency failures as escalation conditions.
11. Keep automatic delivery disabled; `AUTO_HANDLE` is only a recommendation.
12. Use a constant delivery-intent B0 and fixed eight-class macro-F1 denominator; report zero unsafe auto-handles with zero coverage so safety is not mistaken for usefulness.
13. Validate judge-human agreement on blinded held-out outputs before treating judge scores as headline evidence.
14. Keep weak-label diagnostic and human-reviewed official modes visibly different so provisional results are not misrepresented.
15. Use a standard-library core for a fast clean-machine diagnostic run; keep the HTTP layer optional.
