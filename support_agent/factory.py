from __future__ import annotations

import json
import os
from pathlib import Path

from .classifier import KeywordIntentClassifier, NaiveBayesIntentClassifier
from .guardrails import GuardrailEngine
from .model_gateway import ChatCompletionsDraftGateway
from .orchestrator import SupportOrchestrator
from .retrieval import BM25Repository


def build_agent(root: str | Path = ".", config_path: str = "configs/app.json") -> SupportOrchestrator:
    root = Path(root)
    config = json.loads((root / config_path).read_text())
    brand = config["brand_id"]
    repository = BM25Repository.from_jsonl(root / config["index_path"], brand)
    model_path = root / config["classifier_path"]
    classifier = NaiveBayesIntentClassifier.load(model_path) if model_path.exists() else KeywordIntentClassifier()
    guardrails = GuardrailEngine(
        intent_threshold=config["policy"].get("tau_intent"),
        evidence_threshold=config["policy"].get("tau_evidence"),
    )
    model = None
    if os.getenv("SUPPORT_AGENT_GATEWAY") == "live":
        model = ChatCompletionsDraftGateway(
            url=os.environ.get("GENERATOR_API_URL", ""),
            api_key=os.environ.get("GENERATOR_API_KEY", ""),
            model=os.environ.get("GENERATOR_MODEL_ID", ""),
            prompt_path=root / "prompts/draft_v1.txt",
        )
    return SupportOrchestrator(classifier, repository, guardrails, model=model)
