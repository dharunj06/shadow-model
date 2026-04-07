"""
Train Model V2 — XGBoost on Breast Cancer dataset.
Saves model_v2.pkl and logs to MLflow.
"""
import os
import mlflow
import mlflow.xgboost
import joblib
import numpy as np
from pathlib import Path
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment("shadow-ml")

OUTPUT_PATH = Path(__file__).parent / "model_v2.pkl"


def train():
    data = load_breast_cancer()
    X, y = data.data, data.target
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    params = {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "use_label_encoder": False,
        "eval_metric": "logloss",
        "random_state": 42,
    }

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", XGBClassifier(**params)),
    ])

    with mlflow.start_run(run_name="model_v2_xgboost"):
        mlflow.log_params(params)
        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        mlflow.log_metric("accuracy", acc)
        mlflow.sklearn.log_model(pipeline, "model_v2")

        print(f"\n✅ Model V2 Accuracy: {acc:.4f}")
        print(classification_report(y_test, y_pred, target_names=data.target_names))

    joblib.dump(pipeline, OUTPUT_PATH)
    print(f"💾 Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    train()
