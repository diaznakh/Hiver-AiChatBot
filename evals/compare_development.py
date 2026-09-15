"""Optional classifier comparison. Never reads test rows into fitting or scoring."""
import json
import re
from pathlib import Path

from .run import load_examples, validate_reviewed_examples
from .metrics import macro_f1


def main():
    import sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.svm import LinearSVC

    train = [json.loads(line) for line in Path("data/labels/train_weak.jsonl").read_text().splitlines()]
    dev = load_examples("data/golden_set.xlsx", "dev")
    validate_reviewed_examples(dev)
    clean = lambda text: re.sub(r"\[[A-Z_]+\]", " ", text)
    x = [clean(row["text"]) for row in train]
    y = [row["label"] for row in train]
    query = [clean(row["message"]) for row in dev]
    gold = [row["labels"]["primary_intent"] for row in dev]
    candidates = {
        "word_tfidf_logistic": make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), LogisticRegression(max_iter=500, random_state=42)),
        "word_tfidf_svm": make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), LinearSVC(random_state=42)),
        "character_tfidf_svm": make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=50000, sublinear_tf=True), LinearSVC(random_state=42)),
    }
    results = {}
    for name, model in candidates.items():
        model.fit(x, y)
        predicted = model.predict(query).tolist()
        f1, _ = macro_f1(gold, predicted)
        results[name] = {"accuracy": sum(a == b for a, b in zip(gold, predicted)) / len(gold), "macro_f1": f1}
    report = {"split": "dev", "examples": len(dev), "training_examples": len(train), "sklearn_version": sklearn.__version__, "results": results,
              "warning": "Exploratory development comparison on weak training labels. No test evaluation or production promotion. SVM scores are not calibrated routing probabilities."}
    output = Path("artifacts/experiments/classifier_development.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
