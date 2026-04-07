import pytest
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../models/model_v1"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../models/model_v2"))


def get_test_data():
    data = load_breast_cancer()
    _, X_test, _, y_test = train_test_split(
        data.data, data.target, test_size=0.2, random_state=42, stratify=data.target
    )
    return X_test, y_test


def test_model_v1_accuracy():
    """Model V1 should achieve > 90% accuracy on breast cancer dataset."""
    import joblib
    from pathlib import Path

    model_path = Path(__file__).parent.parent / "models" / "model_v1" / "model_v1.pkl"
    if not model_path.exists():
        pytest.skip("model_v1.pkl not found — run train.py first")

    model = joblib.load(model_path)
    X_test, y_test = get_test_data()
    acc = np.mean(model.predict(X_test) == y_test)
    assert acc > 0.90, f"Model V1 accuracy {acc:.4f} below threshold"


def test_model_v2_accuracy():
    """Model V2 should achieve > 92% accuracy."""
    import joblib
    from pathlib import Path

    model_path = Path(__file__).parent.parent / "models" / "model_v2" / "model_v2.pkl"
    if not model_path.exists():
        pytest.skip("model_v2.pkl not found — run train.py first")

    model = joblib.load(model_path)
    X_test, y_test = get_test_data()
    acc = np.mean(model.predict(X_test) == y_test)
    assert acc > 0.92, f"Model V2 accuracy {acc:.4f} below threshold"


def test_feature_count():
    """Features must have exactly 30 dimensions (breast cancer dataset)."""
    data = load_breast_cancer()
    assert data.data.shape[1] == 30


def test_model_v1_output_shape():
    import joblib
    from pathlib import Path

    model_path = Path(__file__).parent.parent / "models" / "model_v1" / "model_v1.pkl"
    if not model_path.exists():
        pytest.skip("model_v1.pkl not found")

    model = joblib.load(model_path)
    X_test, _ = get_test_data()
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)
    assert preds.shape == (len(X_test),)
    assert probs.shape == (len(X_test), 2)
    assert all(p in [0, 1] for p in preds)
