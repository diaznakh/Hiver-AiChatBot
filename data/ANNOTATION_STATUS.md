# Annotation status

The revised workbook is imported at `data/golden_set.xlsx`.
Automated audit confirmed 200 distinct examples, unchanged source messages,
conversation IDs, tweet IDs, history IDs and splits.

- Development: 50 completed rows, reviewed by Zaid Khan; 41 ESCALATE and 9 AUTO_HANDLE.
- Held-out test: 150 rows; zero complete, 150 pending.
- Workbook SHA256: `c0fbf3c1b712ab5ebe6d6d923d983063c80c4d85fb4342e59e8eed81cbe00392`.

AI label suggestions and review guidance were used during development. The
reviewer reports completing the final development rows himself. This does not
claim an independent, blinded annotation process.

The XLSX is authoritative for labels. The committed data/golden_set.csv is the
original source snapshot used for identity checks. A CSV export of the updated
workbook is included in the development workflow artifact.

Development metrics are tuning evidence, not held-out results. Human reply
ratings and live judge ratings remain pending.
