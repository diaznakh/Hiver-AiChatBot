# Focused annotation review

## Completed supplemental review

At the candidate's request, the assistant reviewed all four concerns against
the taxonomy and actual customer messages. Decisions and reasons are saved in
`data/labels/review_supplement.json`. This completes the AI review, not a new
human annotation pass. The original human labels remain the official results.

| Example | Supplemental intent | Supplemental route |
| --- | --- | --- |
| amazon_test_011 | delivery_tracking | ESCALATE |
| amazon_test_034 | account_prime | ESCALATE |
| amazon_test_104 | account_prime | ESCALATE |
| amazon_test_143 | product_issue | ESCALATE |

`python3 -m evals.review_sensitivity` reproduces the comparison without
changing the workbook, predictions or human reply ratings. B2 accuracy changes
from 50.00% to 51.33% and macro-F1 from 0.288591 to 0.317908. Automatic coverage
remains zero. B1 unsafe auto becomes 121/122 versus 120/122. These are post-test
label-sensitivity results, not an independently improved model score.

## Original concerns and review rationale

These are AI review suggestions, not replacements for human ground truth.
The original XLSX and frozen results remain unchanged. Schema validation proves
that cells are complete; it does not prove that their meanings are correct.

| Test example | Current label | Why review it | Suggested review direction |
| --- | --- | --- | --- |
| amazon_test_034 | delivery_tracking | Customer asks how to cancel Prime membership | account_prime matches the documented taxonomy |
| amazon_test_143 | digital_service | Butter dish appears to contain broken glass; mentioning a video is incidental | product_issue |
| amazon_test_011 | digital_service | Lost parcel and replacement request | Review delivery_tracking versus return_refund under the primary-intent rule |
| amazon_test_104 | AUTO_HANDLE | Unexpected order emails and reviews suggest possible account compromise | Review ESCALATE; a security check is beyond the agent's capabilities |

The first two are especially clear intent/taxonomy inconsistencies. The latter
two need the reviewer to apply a consistent policy. No changes have been made
to boost measured performance. If the reviewer confirms corrections, save a new
version, record the exact reason for each correction, and report both original
and corrected-label scores. Do not call a test-informed model revision an
independent test result.
