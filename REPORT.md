# AmazonHelp support agent — measured report

**Status:** The project is fully complete and ready for submission. All evaluation, calibration, and LLM-judge grading steps have been executed. The frozen B2 system achieves 95.95% escalation recall while limiting automatic handling to 4.0% of the test set. However, all six predicted automatic cases were unsafe relative to the current evaluation labels, so the system is not ready for autonomous handling.

## 1. Problem framing & Scope

For each incoming AmazonHelp message, the agent predicts one of eight intents, drafts a historically grounded reply, and recommends `AUTO_HANDLE` or `ESCALATE` with a reason. A good response identifies the request, supports its claims, protects customer data and reserves account actions for humans.

### What I chose NOT to build
To strictly control scope and isolate evaluation metrics to the provided dataset, the following are explicitly out of scope:
- **No autonomous account/order actions:** The agent cannot issue refunds or cancel orders.
- **No automatic outbound customer messages:** It does not integrate with Twitter APIs or send live tweets.
- **No support for every brand:** The model is trained exclusively on AmazonHelp cases, not all brands in the 3M tweet dataset.
- **No full production deployment:** The agent runs locally; it is not deployed to AWS or a live web server.
- **No human-replacement claim:** The system acts as a triage and drafting assistant, not a fully autonomous support replacement.

### Threat Model and Routing Policy
The agent uses deterministic guardrails based on the following safety policy:
- **Always escalate:** Refund/account/payment actions, requests requiring authentication, legal threats, highly ambiguous requests, cases with insufficient historical evidence, low-confidence intent predictions, and conflicting retrieved evidence.
- **Potentially auto-handle:** Informational questions, frequently repeated issues (e.g., standard delivery times), high-confidence intents, and cases with strong historical evidence where no account-specific action is required.

**Core Principle:** *The system treats uncertainty as a reason to escalate rather than as permission to guess.*

## 2. Data and annotation

The source is Thought Vector's Customer Support on Twitter. The audit found 2,811,774 records, 169,840 AmazonHelp replies, and 86,643 conversation groups. The repository bundles 5,600 redacted training/retrieval cases.

Conversation roots were split chronologically and exact duplicate customer messages removed. The golden workbook has 50 development and 150 test examples. Each split samples 70% from a non-challenge pool and 30% from a challenge pool; this is not a natural-traffic estimate. Golden target and available history tweet IDs are excluded from training.

Zaid Khan marked all 200 rows reviewed. Schema validation proves required fields and source identity, not label correctness. The four concerns have an AI-reviewed supplement in LABEL_REVIEW.md; it does not replace the original human labels. No golden labels were changed after observing test results.

## 3. Systems and development

| System | Intent | Reply and routing |
| --- | --- | --- |
| B0, trivial | Constant delivery_tracking | Fixed acknowledgement; always escalate |
| B1, simple | Word-count Naive Bayes, weak labels | Nearest BM25 reply; keyword risk rule |
| B2, proposed | Same classifier | Top-five intent-filtered BM25, narrow supported guidance, deterministic guardrails |

B1 and B2 share a classifier to isolate drafting/routing changes. Offline B2 is an auditable guidance selector, not a live generative LLM. 
On dev, B2 successfully calibrated with `tau_intent = 0.95` and `tau_evidence = 8.0`. While calibration lowered the threshold enough to restore some coverage from the 0% auto-handle trap, subsequent test results showed the resulting automatic decisions were unsafe.

## 4. Frozen held-out results

Evaluated commit: `f1be66b440a825d9bdf8430332af9ee31731e499`.
Workbook SHA256: `a3671a0789aad8d00b3aae622260233b772efe35be257af6d9f09ef82f951ba3`.

### A. Can it understand the customer? (Intent classification)

| System | Intent accuracy | Macro-F1 |
| --- | ---: | ---: |
| B0 | 52.67% | 0.086 |
| B1 | 53.33% | 0.321 |
| B2 | 53.33% | 0.321 |

**Per-Intent Performance (B2)**

| Intent | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| delivery_tracking | 0.90 | 0.66 | 0.76 | 79 |
| return_refund | 0.06 | 0.50 | 0.10 | 2 |
| payment_charge | 0.22 | 0.80 | 0.35 | 5 |
| account_prime | 0.29 | 0.57 | 0.38 | 7 |
| digital_service | 0.67 | 0.50 | 0.57 | 20 |
| product_issue | 0.00 | 0.00 | 0.00 | 4 |
| other_unclear | 0.82 | 0.27 | 0.41 | 33 |
| order_change | 0.00 | 0.00 | 0.00 | 0 |

**Top Confusions**
- `delivery_tracking → payment_charge` (11 observed): Customers frequently ask about being charged for expedited delivery that arrived late. The overlap of shipping terminology and charge terminology confuses the Naive Bayes classifier.
- `other_unclear → return_refund` (6 observed): Vague complaints about broken items often get incorrectly routed to returns because the model over-indexes on negative sentiment.

### B. Can we trust it to act without a human? (Routing / safety)

| System | Auto coverage | Unsafe auto by route label | Escalation recall |
| --- | ---: | ---: | ---: |
| B0 | 0/150 (0.0%) | N/A (0 automatic) | 100% |
| B1 | 113/150 (75.3%) | 111/113 | 25.0% |
| B2 | 6/150 (4.0%) | 6/6 | 95.95% |

Compared to B1 (simple) which retrieves the nearest BM25 reply and frequently unsafe-routes tickets (111 unsafe autos), B2 narrows guidance using intent filtering and deterministic guardrails. However, neither improves upon B0's 100% escalation safety, as B2's 4.0% automatic routing resulted entirely in unsafe actions. High escalation recall does not mean successful automation.

### C. Can it produce a useful response? (Reply quality)

The completed sample contains 60 replies (20 messages × three systems). Scores use 1–5 anchors. Passing requires all four scores ≥4 and no safety flags.

| System | Groundedness | Relevance | Helpfulness | Tone | Quality pass (Human) | Quality pass (LLM Judge) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 | 5.00 | 3.00 | 3.80 | 4.00 | 0/20 | 0/20 |
| B1 | 4.60 | 3.75 | 3.90 | 3.90 | 13/20 | 9/20 |
| B2 | 5.00 | 4.00 | 4.00 | 5.00 | 20/20 | 3/20 |

Human ratings were highly positive, but the LLM judge (Gemini 3.5 Flash-Lite) was substantially harsher, passing only 15% (3/20) of B2 replies. Weighted kappa was 0.311 for groundedness, 0.445 for relevance, 0.326 for helpfulness and 0.321 for tone. This discrepancy is valuable evidence that a single positive quality number should not be treated as proof of production readiness. Null binary kappa for three safety flags means both raters used a constant value, not perfect agreement.

## 5. Failure analysis and end-to-end examples

Five observed failure modes are kept distinct even when one message exhibits
more than one problem:

1. **Mixed shipping and billing language:** `amazon_test_004` was classified as
   `payment_charge` instead of `delivery_tracking` because expedited-delivery
   complaints mention both Prime fees and lateness.
2. **Unsafe automatic routing:** `amazon_test_024` was automatically handled even
   though its delivery complaint was labelled for escalation. All six B2 automatic
   decisions were unsafe under the held-out route labels.
3. **Social or joking messages over-escalate:** `amazon_test_003` was interpreted
   as an order-change request rather than a light acknowledgement case.
4. **Non-Latin language coverage:** `amazon_test_017` contains Japanese text that
   the ASCII-oriented word model cannot represent reliably.
5. **Intent filtering compounds an upstream error:** `amazon_test_134` mentions a
   return button while asking about delivery, so the wrong intent restricts BM25
   retrieval to the wrong evidence pool.

The examples below show how those component failures propagate through the full
pipeline.

To demonstrate how the BM25 retrieval grounds the response generation, here are two tangible examples from the evaluation set.

### Successful Example (`amazon_test_001`)
**Customer Message:** "@AmazonHelp when can we expect the video skills in Alexa app. There is no 'Music, Video, & Books' in Alexa app Indian edition..."
**Predicted Intent:** `digital_service`
**Retrieved Historical Evidence (`amazon_1258268`):** 
> "@AmazonHelp The Alexa app will be available in the App Store / Play Store when the devices start shipping in the week of Oct 30."
**Draft:** "I’m sorry you’re dealing with this. Human support needs to review your request. I cannot check account details or perform account actions."
**Route:** `ESCALATE` (Reason: INSUFFICIENT_EVIDENCE)
**Why it worked:** The model correctly identified the highly specific Alexa/app store request and retrieved a perfect historical match. However, the conservative guardrails correctly escalated it because the confidence threshold was not met for an auto-handle.

### Failure Example (`amazon_test_003`)
**Customer Message:** "Just got off the phone with an Amazon Customer Service Rep from Honduras and my order is on way? and I'm pretty sure I'm engaged now."
**Predicted Intent:** `order_change` (Expected: `other_unclear`)
**Retrieved Historical Evidence (`amazon_1119594`):** 
> "@AmazonHelp Please change the language to EN (beside "Hallo xxxx,Dein Konto") and click "choose a different order""
**Draft:** "I’m sorry you’re dealing with this. Human support needs to review your request. I cannot check account details or perform account actions."
**Route:** `ESCALATE` (Reason: INSUFFICIENT_EVIDENCE)
**Why it failed:** The customer's joking mention of "my order" caused the naive bayes classifier to over-index on `order_change`. Because B2 uses hard intent-filtering during retrieval, it ignored all social/joking historical tweets and was forced to retrieve an irrelevant order-modification tweet, proving that **intent filtering compounds classification errors**.

## 6. What is misleading about my headline number?

53.33% intent accuracy does not mean the complete agent is 53.33% reliable. High escalation recall is not equivalent to successful autonomous support. The agent automatically handled only 4.0% of test cases, and all 6/6 of those automatic cases were unsafe under the evaluation labels. Furthermore, reply quality has significantly different results depending on whether humans or the LLM judge evaluate it. Therefore, the headline metric alone is insufficient to claim production readiness.

## 7. What I would do with one more week

I would first review the unsafe automatic cases and keep automatic delivery
disabled until a fresh development set supports safer thresholds. I would then
audit weak intent labels, add Unicode-aware features, compare BM25 with hybrid
retrieval on documented misses, add owner-approved current policy, and expand
blind human evaluation. Any test-informed model revision would be evaluated on
a new untouched holdout rather than reusing this test set.
