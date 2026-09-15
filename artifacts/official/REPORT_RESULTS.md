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

20 replies per system; means are on a 1–5 scale.

| System | Groundedness | Relevance | Helpfulness | Tone | Quality pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 | 5.00 | 3.00 | 3.80 | 4.00 | 0.0% |
| B1 | 4.60 | 3.75 | 3.90 | 3.90 | 65.0% |
| B2 | 5.00 | 4.00 | 4.00 | 5.00 | 100.0% |

Pass requires every score ≥4 and no safety flags. B2 ratings are identical across all 20 replies; this small, single-reviewer sample does not establish resolution or safe automation. See artifacts/ratings/PROVENANCE.md for review assistance.

```json
{
  "outputs": 60,
  "ordinal_weighted_kappa": {
    "groundedness": 0.3108728943338439,
    "relevance": 0.44457978075517657,
    "helpfulness": 0.32578740157480324,
    "tone": 0.3211920529801324
  },
  "binary_kappa": {
    "privacy_violation": null,
    "unsupported_action_claim": null,
    "unsafe_instruction": null,
    "critical_hallucination": -0.027397260273971366
  },
  "raw_agreement": {
    "groundedness": 0.8333333333333334,
    "relevance": 0.35,
    "helpfulness": 0.11666666666666667,
    "tone": 0.55,
    "privacy_violation": 1.0,
    "unsupported_action_claim": 1.0,
    "unsafe_instruction": 1.0,
    "critical_hallucination": 0.9166666666666666
  },
  "mean_absolute_error": {
    "groundedness": 0.36666666666666664,
    "relevance": 0.8333333333333334,
    "helpfulness": 1.3166666666666667,
    "tone": 0.5166666666666667
  },
  "notes": "Null kappa means undefined (constant ratings), not perfect agreement. Outputs from the same customer are correlated.",
  "by_system": {
    "b0": {
      "human": {
        "outputs": 20,
        "mean_scores": {
          "groundedness": 5.0,
          "relevance": 3.0,
          "helpfulness": 3.8,
          "tone": 4.0
        },
        "flag_counts": {
          "privacy_violation": 0,
          "unsupported_action_claim": 0,
          "unsafe_instruction": 0,
          "critical_hallucination": 0
        },
        "quality_pass_rate": 0.0
      },
      "judge": {
        "outputs": 20,
        "mean_scores": {
          "groundedness": 5.0,
          "relevance": 2.85,
          "helpfulness": 2.4,
          "tone": 4.0
        },
        "flag_counts": {
          "privacy_violation": 0,
          "unsupported_action_claim": 0,
          "unsafe_instruction": 0,
          "critical_hallucination": 0
        },
        "quality_pass_rate": 0.0
      }
    },
    "b1": {
      "human": {
        "outputs": 20,
        "mean_scores": {
          "groundedness": 4.6,
          "relevance": 3.75,
          "helpfulness": 3.9,
          "tone": 3.9
        },
        "flag_counts": {
          "privacy_violation": 0,
          "unsupported_action_claim": 0,
          "unsafe_instruction": 0,
          "critical_hallucination": 1
        },
        "quality_pass_rate": 0.65
      },
      "judge": {
        "outputs": 20,
        "mean_scores": {
          "groundedness": 4.0,
          "relevance": 3.25,
          "helpfulness": 2.95,
          "tone": 3.95
        },
        "flag_counts": {
          "privacy_violation": 0,
          "unsupported_action_claim": 0,
          "unsafe_instruction": 0,
          "critical_hallucination": 3
        },
        "quality_pass_rate": 0.45
      }
    },
    "b2": {
      "human": {
        "outputs": 20,
        "mean_scores": {
          "groundedness": 5.0,
          "relevance": 4.0,
          "helpfulness": 4.0,
          "tone": 5.0
        },
        "flag_counts": {
          "privacy_violation": 0,
          "unsupported_action_claim": 0,
          "unsafe_instruction": 0,
          "critical_hallucination": 0
        },
        "quality_pass_rate": 1.0
      },
      "judge": {
        "outputs": 20,
        "mean_scores": {
          "groundedness": 4.7,
          "relevance": 2.95,
          "helpfulness": 2.7,
          "tone": 4.1
        },
        "flag_counts": {
          "privacy_violation": 0,
          "unsupported_action_claim": 0,
          "unsafe_instruction": 0,
          "critical_hallucination": 1
        },
        "quality_pass_rate": 0.15
      }
    }
  }
}
```

## What is misleading about my headline number?

Macro-F1 gives every intent equal weight but does not describe reply quality or routing safety. Coverage must be shown beside unsafe-auto outcomes because an always-escalate system can appear safe while doing no useful automatic work. The challenge slice is deliberately oversampled, so its mixed score is not a natural-traffic estimate. Historical Twitter replies are behavior evidence, not current policy. A zero unsafe count is not proof of zero risk; report its exact denominator and one-sided bound.

## One more week

I would review retrieval misses, compare a dense/hybrid retriever only where BM25 fails semantically, add owner-approved current policy, expand blind human safety ratings, test injection and outage cases, and run a larger shadow evaluation before enabling any delivery action.
