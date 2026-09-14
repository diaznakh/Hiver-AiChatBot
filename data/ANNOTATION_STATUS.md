# Annotation status

The revised workbook is imported at data/golden_set.xlsx.
All 200 rows pass required-field, taxonomy and review-flag validation:
50 development and 150 held-out test examples, reviewed by Zaid Khan.

Development routes: 41 ESCALATE, nine AUTO_HANDLE.
Test routes: 148 ESCALATE, two AUTO_HANDLE.
All 200 human_reviewed flags are YES.

Excel numeric ID representations are normalized exactly; source messages,
IDs and splits match the original data. The XLSX is authoritative for labels.
The committed data/golden_set.csv remains the original source snapshot.

AI label suggestions and review guidance were used during development.
The reviewer reports completing the labels himself. Validation does not
independently establish semantic correctness or an independent annotation process.

The held-out evaluation is recorded in artifacts/official/README.md.
The 60 blinded reply ratings and live judge agreement remain pending.
