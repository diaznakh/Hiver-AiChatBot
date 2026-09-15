# Measured results - AmazonHelp support agent

## Results

| System | Intent macro-F1 | Auto coverage | Unsafe auto | Escalation recall |
| --- | ---: | ---: | ---: | ---: |
| B0 | 0.086 | 0.0% | N/A (0 auto) | 100.0% |
| B1 | 0.321 | 75.3% | 111/113 | 25.0% |
| B2 | 0.321 | 4.0% | 6/6 | 95.9% |

## Observed failure categories and representative examples

Routing/intent failures use the full test split; reply-only failures use the human-rated subset. Counts are not directly comparable across these denominators. Categories are automated triage, not a substitute for inspecting root causes.

Only 3 categories observed by this harness. Inspect examples for finer root causes; do not invent five modes.
### 1. Intent misclassification (68 observed) - amazon_test_004

Customer: [HANDLE] are very happy to take my £8 a month for Prime but now it’s almost December their “one day delivery” takes 3 days!! What’s the point #cancelprime [URL]

Expected: intent `delivery_tracking`, route `ESCALATE`.

Predicted: intent `payment_charge`, route `ESCALATE`; reasons `INSUFFICIENT_EVIDENCE`.

Draft: I’m sorry you’re dealing with this. Human support needs to review your request. I cannot check account details or perform account actions.

Retrieved evidence IDs: amazon_1308066, amazon_2424500, amazon_2283529, amazon_2610733, amazon_224628.

Hypothesis: Weak training labels, overlapping intents, or limited language coverage likely caused the error.

### 2. Unsafe automatic routing (6 observed) - amazon_test_024

Customer: [HANDLE] stop advertising items as same-day delivery if you cannot make good on that

Expected: intent `delivery_tracking`, route `ESCALATE`.

Predicted: intent `delivery_tracking`, route `AUTO_HANDLE`; reasons `LOW_RISK_GROUNDED`.

Draft: I’m sorry you’re dealing with this. We apologize for the delay. Please check your order status for the latest information.

Retrieved evidence IDs: amazon_1576205, amazon_272686, amazon_2287543, amazon_1190307, amazon_429021.

Hypothesis: The risk rules or confidence threshold missed an account-specific or ambiguous request.

### 3. Over-escalation (2 observed) - amazon_test_003

Customer: Just got off the phone with an Amazon Customer Service Rep from Honduras and my order is on way? and I'm pretty sure I'm engaged now.

Expected: intent `other_unclear`, route `AUTO_HANDLE`.

Predicted: intent `order_change`, route `ESCALATE`; reasons `INSUFFICIENT_EVIDENCE`.

Draft: I’m sorry you’re dealing with this. Human support needs to review your request. I cannot check account details or perform account actions.

Retrieved evidence IDs: amazon_788267, amazon_820652, amazon_1645642, amazon_2488518, amazon_1270161.

Hypothesis: The safety gate was too conservative or the retrieved evidence was too weak.

## Reply quality and judge-human agreement

PENDING: configured LLM-judge run and judge–human agreement. Human scores above, when supplied, are measured separately. This report is not submission-complete.

## What is misleading about my headline number?

Macro-F1 gives every intent equal weight but does not describe reply quality or routing safety. Coverage must be shown beside unsafe-auto outcomes because an always-escalate system can appear safe while doing no useful automatic work. The challenge slice is deliberately oversampled, so its mixed score is not a natural-traffic estimate. Historical Twitter replies are behavior evidence, not current policy. A zero unsafe count is not proof of zero risk; report its exact denominator and one-sided bound.

## One more week

I would review retrieval misses, compare a dense/hybrid retriever only where BM25 fails semantically, add owner-approved current policy, expand blind human safety ratings, test injection and outage cases, and run a larger shadow evaluation before enabling any delivery action.
