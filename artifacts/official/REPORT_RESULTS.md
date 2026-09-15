# Measured results - AmazonHelp support agent

## Results

| System | Intent macro-F1 | Auto coverage | Unsafe auto | Escalation recall |
| --- | ---: | ---: | ---: | ---: |
| B0 | 0.086 | 0.0% | N/A (0 auto) | 100.0% |
| B1 | 0.289 | 81.3% | 120/122 | 18.9% |
| B2 | 0.289 | 0.0% | N/A (0 auto) | 100.0% |

## Observed failure categories and representative examples

Routing/intent failures use the full test split; reply-only failures use the human-rated subset. Counts are not directly comparable across these denominators. Categories are automated triage, not a substitute for inspecting root causes.

Only 2 categories observed by this harness. Inspect examples for finer root causes; do not invent five modes.
### 1. Intent misclassification (73 observed) - amazon_test_002

Customer: え.........Amazonのギフト券買ってないし、誰からも貰ってないのに勝手に5000円分入ってるんだけど😨怖いから使わないようにしよ。これは新手の詐欺なのか？誰か教えて〜😱 [URL]

Expected: intent `other_unclear`, route `ESCALATE`.

Predicted: intent `payment_charge`, route `ESCALATE`; reasons `INSUFFICIENT_EVIDENCE`.

Draft: I’m sorry you’re dealing with this. Human support needs to review your request. I cannot check account details or perform account actions.

Retrieved evidence IDs: amazon_2290678, amazon_987352, amazon_435164, amazon_304574, amazon_1380233.

Hypothesis: Weak training labels, overlapping intents, or limited language coverage likely caused the error.

### 2. Over-escalation (2 observed) - amazon_test_003

Customer: Just got off the phone with an Amazon Customer Service Rep from Honduras and my order is on way? and I'm pretty sure I'm engaged now.

Expected: intent `other_unclear`, route `AUTO_HANDLE`.

Predicted: intent `order_change`, route `ESCALATE`; reasons `INSUFFICIENT_EVIDENCE`.

Draft: I’m sorry you’re dealing with this. Human support needs to review your request. I cannot check account details or perform account actions.

Retrieved evidence IDs: amazon_1119594, amazon_1868732, amazon_2275970, amazon_1645642, amazon_1205460.

Hypothesis: The safety gate was too conservative or the retrieved evidence was too weak.

## Reply quality and judge-human agreement

PENDING: supply --agreement and --human-ratings after blind review. This report is not submission-complete.

## What is misleading about my headline number?

Macro-F1 gives every intent equal weight but does not describe reply quality or routing safety. Coverage must be shown beside unsafe-auto outcomes because an always-escalate system can appear safe while doing no useful automatic work. The challenge slice is deliberately oversampled, so its mixed score is not a natural-traffic estimate. Historical Twitter replies are behavior evidence, not current policy. A zero unsafe count is not proof of zero risk; report its exact denominator and one-sided bound.

## One more week

I would review retrieval misses, compare a dense/hybrid retriever only where BM25 fails semantically, add owner-approved current policy, expand blind human safety ratings, test injection and outage cases, and run a larger shadow evaluation before enabling any delivery action.
