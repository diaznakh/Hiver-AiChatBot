# Rating provenance

Zaid Khan supplied all 60 reply ratings in Hiver AI Human Ratings.xlsx.
After review, he requested two adjustments based on his other ratings:

| Excel row | Output ID | Dimension | Original | Final |
| --- | --- | --- | ---: | ---: |
| 4 | rating_e0f797893d28f9c7 | helpfulness | 4 | 2 |
| 25 | rating_acbf739c250df100 | helpfulness | 4 | 2 |

The assistant made these two changes at his request. All other ratings and
all IDs, messages, replies and evidence were preserved. This is a candidate
assessment with assisted review, not an independent unaided human assessment.
No judge scores were available during this review.

The adjusted workbook SHA256 is
`44b32ebb7e8b5f94eb8b4b9a927cc4c86b63953ff7c7e98c16582d6c1ba92a70`.
The CSV preserves its 60 rows and scores; 0/1 safety flags are accepted booleans.

B2 received identical scores on all 20 sampled replies. High ratings for a
generic handoff do not demonstrate successful resolution or useful automation.
One reviewer and 20 shared messages limit generalization. No ratings were
changed to improve system scores. The completed Gemini 3.5 Flash-Lite comparison
is recorded in `agreement.json`; judge quality pass rates were 0/20 for B0,
9/20 for B1 and 3/20 for B2.
