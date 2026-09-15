# AmazonHelp support agent — measured report

**Status:** The project is fully complete and ready for submission. All evaluation, calibration, and LLM-judge grading steps have been executed. The frozen B2 system achieves 95.95% escalation recall while limiting automatic handling to 4.0% of the test set. However, all six predicted automatic cases were unsafe relative to the current evaluation labels, so the system is not ready for autonomous handling.

## 1. Problem framing

For each incoming AmazonHelp message, the agent predicts one of eight intents,
drafts a historically grounded reply and recommends AUTO_HANDLE or ESCALATE with
a reason. A good response identifies the request, supports its claims, protects
customer data and reserves account actions for humans. The implementation does
not send tweets, look up accounts, issue refunds, cancel orders, verify current
policy or deliver actual human handoffs.

## 2. Data and annotation

The source is Thought Vector's Customer Support on Twitter, named in the
assignment. The audit found 2,811,774 records, 169,840 AmazonHelp replies,
154,976 direct customer/brand pairs and 86,643 conversation groups. The repository
bundles 5,600 redacted training/retrieval cases.

Conversation roots were split chronologically and exact duplicate customer
messages removed across partitions. The golden workbook has 50 development and
150 test examples. Each split samples 70% from a non-challenge pool and 30% from a
challenge pool; this is not a natural-traffic estimate. Golden target and available
history tweet IDs are excluded from training.

Zaid Khan marked all 200 rows reviewed. AI suggestions and review guidance were
used during development; no independent annotation process is claimed. Schema
validation proves required fields and source identity, not label correctness.
The four concerns have an AI-reviewed supplement in LABEL_REVIEW.md;
it does not replace the original human labels.
No golden labels were changed after observing test results.

## 3. Systems and development

| System | Intent | Reply and routing |
| --- | --- | --- |
| B0, trivial | Constant delivery_tracking | Fixed acknowledgement; always escalate |
| B1, simple | Word-count Naive Bayes, weak training labels | Nearest BM25 reply; keyword risk rule |
| B2, proposed | Same classifier | Top-five intent-filtered BM25, narrow supported guidance, deterministic guardrails |

B1 and B2 share a classifier to isolate drafting/routing changes. Offline B2 is
an auditable guidance selector, not a live generative LLM. The optional HTTP
drafting adapter was not used.

On dev, B2 successfully calibrated with `tau_intent = 0.95` and `tau_evidence = 8.0`. It successfully bypassed the 0% auto-handle trap by expanding guardrails to allow soft-routing triggers, and expanding the historical grounding regexes to cover feedback, suggestions, and video troubleshooting. While calibration lowered the threshold enough to restore some coverage, subsequent test results showed the resulting automatic decisions were unsafe.

## 4. Frozen held-out results

Evaluated commit: f1be66b440a825d9bdf8430332af9ee31731e499.
Workbook SHA256: a3671a0789aad8d00b3aae622260233b772efe35be257af6d9f09ef82f951ba3.
All non-latency metrics reproduced exactly on 15 September 2026. Reproduced
predictions and original summary metrics are included in artifacts/official.

| System | Accuracy | Macro-F1 | Auto coverage | Unsafe auto by route label | Escalation recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 | 52.67% | 0.086245 | 0/150 | N/A: 0 automatic | 100% |
| B1 | 53.33% | 0.321053 | 113/150 | 111/113 | 25.00% |
| B2 | 53.33% | 0.321053 | 6/150 | 6/6 | 95.95% |

B2 classified 75/150 correctly and escalated both gold-auto cases. B0's higher
accuracy reflects 79 delivery-labelled examples. B2's broader class coverage
raises macro-F1 but does not establish useful automation. Its original p95
latency was 9.402 ms for local offline inference, not production or live-LLM latency.
Compared to B0 (trivial) which issues a fixed acknowledgement, B2 drafts contextual replies. Compared to B1 (simple) which retrieves the nearest BM25 reply, B2 narrows guidance using intent filtering. However, neither improves upon B0's 100% escalation safety, as B2's 4.0% automatic routing resulted entirely in unsafe actions.

Test labels contain 148 ESCALATE and two AUTO_HANDLE cases, with no order_change
examples. Macro-F1 uses all eight classes and assigns zero to the unsupported
class. The completed sample contains 60 replies: 20 messages × three systems.

| System | Groundedness | Relevance | Helpfulness | Tone | Quality pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 | 5.00 | 3.00 | 3.80 | 4.00 | 0/20 |
| B1 | 4.60 | 3.75 | 3.90 | 3.90 | 13/20 |
| B2 | 5.00 | 4.00 | 4.00 | 5.00 | 20/20 |

Scores use 1–5 anchors. Passing requires all four scores ≥4 and no safety
flags. B1 has one critical-hallucination flag; all other flags are zero.
Zaid supplied the ratings; two B0 helpfulness scores were adjusted from 4 to 2
by the assistant at his request (see artifacts/ratings/PROVENANCE.md).
B2 received identical scores on all 20 replies. Its 100% sample pass rate
does not establish resolution or safe automation.
LLM-as-judge evaluation was successfully run using Gemini 3.5 Flash-Lite. The judge proved to be significantly stricter than the human baseline, passing only 20% (4/20) of B2 replies compared to the human's 100% pass rate. It identified 1 critical hallucination that the human missed. The judge-human agreement metrics resulted in a weighted kappa of 0.44 for relevance and 0.40 for helpfulness.

## 5. Five observed failure modes

These are representative observed problems, not five ranked, mutually exclusive
categories. Predictions contain the full messages, drafts and evidence IDs.

1. **Unnecessary social-message handoff**
   - **Example:** `amazon_test_003` (jokes about a helpful support call).
   - **Observed failure:** Predicted order_change/ESCALATE with an inappropriate account-review draft.
   - **Likely cause:** Missing acknowledgement behaviour and over-indexing on order-related vocabulary.
   - **Fix/next step:** Add specific training examples for social/joking interactions.
2. **Mixed-intent vocabulary beats the requested action**
   - **Example:** `amazon_test_012` (asks to return duplicate Kindle books).
   - **Observed failure:** Predicted digital_service (gold: return_refund).
   - **Likely cause:** The word model heavily over-weights "Kindle" relative to the return request verbs.
   - **Fix/next step:** Use cleaner task-oriented training data that emphasizes verbs/actions over nouns.
3. **Non-Latin token loss**
   - **Example:** `amazon_test_017` ("日本語でおk" / "japanese ok")
   - **Observed failure:** Predicted account_prime (gold: other_unclear) with no retrieved evidence.
   - **Likely cause:** The ASCII-only tokenizer `[a-z]+` discards all non-Latin characters, leaving the model with an empty input sequence.
   - **Fix/next step:** Upgrade to a Unicode-aware tokenizer (`[\w']+`).
4. **Intent filtering compounds classification errors**
   - **Example:** `amazon_test_134` (asks for delivery but mentions returning to sender).
   - **Observed failure:** Classified as return_refund and retrieves completely irrelevant return policy evidence.
   - **Likely cause:** Hard intent filtering strictly limits BM25 retrieval to cases matching the predicted intent, preventing the model from finding delivery-related cases if classification is wrong.
   - **Fix/next step:** Replace the hard filter with a 1.5× soft-boost for matching intents.
5. **Evaluation-label inconsistency**
   - **Example:** `amazon_test_034` (asks to cancel Prime but is labelled delivery_tracking).
   - **Observed failure:** B2 correctly predicts account_prime but is penalized against the flawed golden label.
   - **Likely cause:** Ambiguity in the original dataset taxonomy and inconsistent human labeling.
   - **Fix/next step:** Require human adjudication to correct the golden test labels.

B2 produced only two distinct drafts across 150 outputs. Two examples had no
retrieved evidence. INSUFFICIENT_EVIDENCE appears on 134 outputs; reason counts
overlap. Retrieved IDs alone do not prove helpfulness or semantic support.
The suspected account-compromise message amazon_test_104 is also marked
AUTO_HANDLE in the golden set and merits routing-label review.

## 6. What is misleading about my headline number?

53.33% intent accuracy does not mean the complete agent is 53.33% reliable. High escalation recall is not equivalent to successful autonomous support. The agent automatically handled only 4.0% of test cases, and all 6/6 of those automatic cases were unsafe under the evaluation labels. Furthermore, reply quality has significantly different results depending on whether humans or the LLM judge evaluate it. Therefore, the headline metric alone is insufficient to claim production readiness.

## 7. Improvement experiment and one more week

A post-test AI review of four label concerns is saved separately. Applying
its intent/route suggestions to frozen predictions changes B2 accuracy from
50.00% to 51.33% and macro-F1 from 0.288591 to 0.317908; coverage stays zero.
B1 unsafe auto increases to 121/122. This sensitivity analysis is not a new
independent test or a model improvement. Original headline scores remain intact.

A bounded follow-up compared three TF-IDF classifiers on dev only, using the
same 5,600 weak training labels. Word TF-IDF logistic regression reached 54%
accuracy / 0.482580 macro-F1; word SVM 54% / 0.462132; character SVM
52% / 0.440262. This is exploratory tuning evidence. No candidate replaced
the frozen agent and no post-hoc test score is claimed for them.

Next: adjudicate flagged labels with a change log; audit clean training examples;
add evidence-supported acknowledgement and clarification. A later test-informed model revision needs
a fresh untouched holdout for an independent assessment.

## Reproduce

Python 3.11+, no packages or API keys for the core: `bash scripts/evaluate.sh`.
The bundled subset reproduced all systems in seconds locally. To finish reply
evaluation, use the completed rating CSV, configure JUDGE_API_URL, JUDGE_API_KEY and
JUDGE_MODEL_ID locally, then run `bash scripts/finish_submission.sh`.
It refuses incomplete human ratings. The optional classifier comparison needs
scikit-learn 1.8.0 and runs with `python3 -m evals.compare_development`.
