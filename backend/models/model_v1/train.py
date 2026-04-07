"""
Train Model V1 — Logistic Regression on Breast Cancer dataset.
Saves model_v1.pkl and logs to MLflow.
"""
import os
import mlflow
import mlflow.sklearn
import joblib
import numpy as np
from pathlib import Path
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment("shadow-ml")

OUTPUT_PATH = Path(__file__).parent / "model_v1.pkl"


def train():
    data = load_breast_cancer()
    X, y = data.data, data.target
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, C=1.0, random_state=42)),
    ])

    with mlflow.start_run(run_name="model_v1_logistic_regression"):
        mlflow.log_params({"model_type": "LogisticRegression", "C": 1.0, "max_iter": 1000})
        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        mlflow.log_metric("accuracy", acc)
        mlflow.sklearn.log_model(pipeline, "model_v1")

        print(f"\n✅ Model V1 Accuracy: {acc:.4f}")
        print(classification_report(y_test, y_pred, target_names=data.target_names))

    joblib.dump(pipeline, OUTPUT_PATH)
    print(f"💾 Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    train()
