# Golden-set labelling guide

Open `data/golden_set.xlsx` and review all 200 rows without looking at system predictions.

For each message:

1. Select the single best intent from the dropdown.
2. Choose `AUTO_HANDLE` only when a safe general reply can answer the message without an account check, private data, a policy decision, or missing context. Otherwise choose `ESCALATE`.
3. Write one to three ideas a good reply should contain, separated with `|`. Do not write a single required sentence; several replies can be correct.
4. List claims the reply must avoid, separated with `|`. Leave this blank when no special prohibition is needed.
5. Enter your name and change `human_reviewed` to `YES` only after checking the row.

The 200 examples are one per conversation group: 50 development and 150 locked test. Each split is 70% random traffic and 30% challenge cases. The agent must never receive the correct labels during inference.
