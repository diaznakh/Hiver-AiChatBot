# Focused annotation review

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
