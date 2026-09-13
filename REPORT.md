# Report: AmazonHelp AI support agent

**Evaluation status:** Prototype and evaluation workflow implemented; submission evidence incomplete. Final headline results remain blank until the candidate personally reviews the golden set. Diagnostic weak-label scores are intentionally excluded.

## 1. Problem framing

The agent handles AmazonHelp messages from the Customer Support on Twitter dataset. A good result has three properties: the intent is useful, the reply is supported by similar historical AmazonHelp conversations, and account-specific or unsafe requests are escalated with an understandable reason.

I chose not to build tweet delivery, account lookup, refunds, cancellation execution, or current-policy lookup. `AUTO_HANDLE` is a recommendation only. Historical responses show how AmazonHelp replied in 2017; they do not prove current policy or the status of a customer's account.

## 2. Data and sampling

- Source: Customer Support on Twitter (`twcs.csv`)
- Full CSV records: 2,811,774
- AmazonHelp replies: 169,840
- Direct customer-brand pairs: 154,976
- Conversation groups: 86,643
- Exact duplicate customer messages removed: 3,691
- Eligible partitions: 107,099 train, 22,150 development, and 22,036 test
- Bundled training/retrieval subset: 5,600 balanced, redacted training cases
- Golden set: 50 development and 150 locked test examples

Whole conversation roots were ordered by time and assigned 70/15/15 to train, development, and test. Exact message duplicates were removed globally. Each golden split contains 70% random cases and 30% challenge cases. The training index contains no golden target or available-history tweet IDs.

The classifier uses weak heuristic labels on the separate training subset. Those labels do not count as the hand-labelled golden set.

## 3. Systems compared

| System | Description |
| --- | --- |
| B0 | Constant delivery_tracking intent, fixed acknowledgement, always escalate |
| B1 | Naive Bayes intent classifier, nearest BM25 historical reply, simple risk rule |
| B2 | Same classifier, top-five BM25 evidence, response-conditioned allowlisted guidance, deterministic validation and escalation |

Using the same classifier for B1 and B2 isolates the effect of evidence packaging, drafting, and routing rather than changing every component at once.

## 4. Results

Run `bash scripts/evaluate.sh` after completing `data/golden_set.xlsx`. The command generates the measured table below in `artifacts/official/REPORT_RESULTS.md`.

| System | Intent macro-F1 | Auto coverage | Unsafe auto | Escalation recall |
| --- | ---: | ---: | ---: | ---: |
| B0 | Pending human labels | Pending | Pending | Pending |
| B1 | Pending human labels | Pending | Pending | Pending |
| B2 | Pending human labels | Pending | Pending | Pending |

Reply quality is evaluated blindly on 60 outputs using human and LLM ratings for groundedness, relevance, helpfulness, tone, and four safety flags. Weighted and binary kappa measure judge-human agreement.

## 5. Expected failure modes to verify on the locked test

These hypotheses come from inspecting real sampled cases. They are not presented as measured test findings.

1. **Very short or context-free requests.** Example: `[HANDLE] how do I make this stop [URL]`. The classifier lacks enough information; escalation is safer than a confident guess.
2. **Mixed intent messages.** Example: broken earphones followed by an exchange-or-refund request. A single primary label hides the product and refund combination.
3. **Unsupported languages.** Several Japanese and Spanish messages enter `other_unclear`. Language detection or multilingual representations may improve classification.
4. **Account-specific delivery cases.** “Delivered but not received” resembles ordinary tracking text but needs an account investigation. Keyword confidence alone can route it unsafely.
5. **Weak historical outcomes.** Many old brand replies only direct the customer to a private channel. They establish tone and handoff behavior, not that the issue was resolved.

After the locked evaluation, replace these hypotheses with the five highest-frequency observed modes and include representative predictions, retrieved evidence, and correction experiments.

## 6. What is misleading about my headline number?

Intent macro-F1 does not measure reply quality or routing safety. An always-escalate system can produce zero unsafe automatic replies while automating nothing, so safety must be reported with coverage and its denominator. The golden set deliberately oversamples difficult cases and is not a natural-traffic estimate. The classifier is trained on weak labels. Historical replies may be incomplete handoffs and may not reflect current policy. A zero observed unsafe count is not proof of zero risk. LLM-judge results are secondary unless agreement with blinded human ratings is adequate.

## 7. What I would do with one more week

I would inspect the locked retrieval misses, add multilingual handling, label a small clean classifier-training set, compare hybrid retrieval only where BM25 fails, add approved current knowledge with validity dates, expand blind human ratings, and run a larger shadow evaluation before enabling any delivery action.
