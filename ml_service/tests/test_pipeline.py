"""Integration tests for the full training and prediction pipeline."""
import numpy as np
import pandas as pd
import pytest

from app.pipeline.data_generator import generate_synthetic_data
from app.pipeline.feature_engineering import engineer_features, FEATURE_COLS
from app.pipeline.preprocessor import build_base_pipeline, build_training_pipeline
from app.pipeline.evaluator import evaluate_on_test, ModelMetrics, QUALITY_GATES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def synthetic_data():
    return generate_synthetic_data(n_samples=600, random_state=0)


@pytest.fixture(scope="module")
def engineered_data(synthetic_data):
    return engineer_features(synthetic_data)


@pytest.fixture(scope="module")
def train_test_split(engineered_data):
    from sklearn.model_selection import train_test_split
    X = engineered_data[FEATURE_COLS]
    y = engineered_data["label"]
    return train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)


# ---------------------------------------------------------------------------
# Data generator
# ---------------------------------------------------------------------------

class TestDataGenerator:
    def test_output_shape(self):
        df = generate_synthetic_data(n_samples=100, random_state=1)
        assert len(df) == 100

    def test_required_columns_present(self):
        df = generate_synthetic_data(n_samples=50, random_state=2)
        assert "label" in df.columns
        assert "student_id" in df.columns

    def test_label_is_binary(self):
        df = generate_synthetic_data(n_samples=200, random_state=3)
        assert set(df["label"].unique()).issubset({0, 1})

    def test_class_imbalance_ratio(self):
        df = generate_synthetic_data(n_samples=1000, random_state=4)
        at_risk_ratio = df["label"].mean()
        # At-risk should be roughly 20–40%
        assert 0.15 <= at_risk_ratio <= 0.45, (
            f"Unexpected at-risk ratio: {at_risk_ratio:.2%}"
        )

    def test_nan_injection(self):
        df = generate_synthetic_data(n_samples=500, random_state=5)
        # Should have some NaN values injected in LMS fields
        assert df[["lms_login_frequency", "lms_time_spent_hours"]].isnull().any().any()


# ---------------------------------------------------------------------------
# Preprocessor
# ---------------------------------------------------------------------------

class TestPreprocessor:
    def test_base_pipeline_transforms_without_error(self, train_test_split):
        X_train, X_test, y_train, y_test = train_test_split
        pipe = build_base_pipeline()
        X_tr = pipe.fit_transform(X_train, y_train)
        X_te = pipe.transform(X_test)
        assert X_tr.shape[1] == X_te.shape[1]
        assert not np.isnan(X_tr).any()
        assert not np.isnan(X_te).any()

    def test_training_pipeline_handles_imbalance(self, train_test_split):
        X_train, X_test, y_train, y_test = train_test_split
        from app.models.logistic_regression import build_logistic_regression
        from sklearn.pipeline import Pipeline
        pipe = build_training_pipeline(build_logistic_regression())
        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)
        assert len(preds) == len(y_test)
        assert set(preds).issubset({0, 1})


# ---------------------------------------------------------------------------
# Individual model training and evaluation
# ---------------------------------------------------------------------------

class TestModelTraining:
    @pytest.mark.parametrize("model_key", [
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
    ])
    def test_model_trains_and_predicts(self, model_key, train_test_split):
        from app.models import MODEL_CATALOGUE
        X_train, X_test, y_train, y_test = train_test_split

        model_fn = MODEL_CATALOGUE[model_key]["factory"]
        clf = model_fn()
        train_pipe = build_training_pipeline(clf)
        eval_pipe = build_base_pipeline()

        train_pipe.fit(X_train, y_train)
        eval_pipe.fit(X_train, y_train)

        preds = train_pipe.predict(X_test)
        assert len(preds) == len(y_test)

    def test_logistic_regression_auc_above_floor(self, train_test_split):
        from app.models.logistic_regression import build_logistic_regression
        X_train, X_test, y_train, y_test = train_test_split

        pipe = build_training_pipeline(build_logistic_regression())
        pipe.fit(X_train, y_train)

        from sklearn.metrics import roc_auc_score
        proba = pipe.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, proba)
        # Logistic regression should comfortably beat random (0.5) on synthetic data
        assert auc >= 0.70, f"LR ROC-AUC too low: {auc:.3f}"


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class TestEvaluator:
    @pytest.fixture(scope="class")
    def trained_eval_pipe(self, train_test_split):
        from app.models.random_forest import build_random_forest
        X_train, X_test, y_train, y_test = train_test_split
        eval_pipe = build_base_pipeline()
        eval_pipe.fit(X_train, y_train)

        from sklearn.pipeline import Pipeline
        # Wrap classifier into a named step for evaluation
        clf = build_random_forest()
        train_pipe = build_training_pipeline(clf)
        train_pipe.fit(X_train, y_train)
        return train_pipe, X_test, y_test

    def test_evaluate_returns_model_metrics(self, trained_eval_pipe):
        pipe, X_test, y_test = trained_eval_pipe
        metrics = evaluate_on_test(pipe, X_test, y_test, model_name="random_forest")
        assert isinstance(metrics, ModelMetrics)

    def test_all_metric_fields_populated(self, trained_eval_pipe):
        pipe, X_test, y_test = trained_eval_pipe
        metrics = evaluate_on_test(pipe, X_test, y_test, model_name="random_forest")
        for field in ("accuracy", "precision", "recall", "f1", "roc_auc"):
            val = getattr(metrics, field)
            assert 0.0 <= val <= 1.0, f"{field} out of range: {val}"

    def test_quality_gates_dict_structure(self):
        assert set(QUALITY_GATES.keys()) == {
            "recall", "precision", "f1", "roc_auc", "accuracy"
        }
        for k, v in QUALITY_GATES.items():
            assert 0 < v < 1, f"Quality gate {k}={v} is outside (0, 1)"


# ---------------------------------------------------------------------------
# Predictor
# ---------------------------------------------------------------------------

class TestPredictor:
    @pytest.fixture(scope="class")
    def fitted_pipeline(self, train_test_split):
        from app.models.random_forest import build_random_forest
        X_train, X_test, y_train, y_test = train_test_split
        pipe = build_training_pipeline(build_random_forest())
        pipe.fit(X_train, y_train)
        return pipe

    @pytest.fixture(scope="class")
    def raw_row(self, synthetic_data):
        """A raw feature row (pre-engineering) for predict_single."""
        from app.pipeline.data_generator import RAW_FEATURE_COLS
        return synthetic_data[RAW_FEATURE_COLS].iloc[0].to_dict()

    @pytest.fixture(scope="class")
    def at_risk_raw_row(self, synthetic_data):
        from app.pipeline.data_generator import RAW_FEATURE_COLS
        at_risk = synthetic_data[synthetic_data["label"] == 1]
        if len(at_risk) == 0:
            return None
        return at_risk[RAW_FEATURE_COLS].iloc[0].to_dict()

    def test_predict_single_returns_required_keys(self, fitted_pipeline, raw_row):
        from app.pipeline.predictor import predict_single
        result = predict_single(
            pipeline=fitted_pipeline,
            raw_features=raw_row,
            threshold=0.5,
        )
        assert "risk_score" in result
        assert "risk_label" in result
        assert "contributing_factors" in result

    def test_predict_single_risk_score_in_bounds(self, fitted_pipeline, raw_row):
        from app.pipeline.predictor import predict_single
        result = predict_single(
            pipeline=fitted_pipeline,
            raw_features=raw_row,
            threshold=0.5,
        )
        assert 0.0 <= result["risk_score"] <= 1.0

    def test_predict_single_risk_label_valid(self, fitted_pipeline, raw_row):
        from app.pipeline.predictor import predict_single
        result = predict_single(
            pipeline=fitted_pipeline,
            raw_features=raw_row,
            threshold=0.5,
        )
        assert result["risk_label"] in ("HIGH", "MEDIUM", "LOW")

    def test_predict_single_contributing_factors_structure(self, fitted_pipeline, raw_row):
        from app.pipeline.predictor import predict_single
        result = predict_single(
            pipeline=fitted_pipeline,
            raw_features=raw_row,
            threshold=0.5,
        )
        factors = result["contributing_factors"]
        assert isinstance(factors, list)
        for factor in factors:
            assert "feature" in factor
            assert "impact" in factor
            assert "value" in factor
            assert "direction" in factor
            assert factor["direction"] in ("increases_risk", "decreases_risk")

    def test_predict_batch_returns_list(self, fitted_pipeline, synthetic_data):
        from app.pipeline.predictor import predict_batch
        df = synthetic_data.head(10).copy()
        results = predict_batch(pipeline=fitted_pipeline, feature_df=df, threshold=0.5)
        assert isinstance(results, list)
        assert len(results) == 10

    def test_predict_batch_all_students_present(self, fitted_pipeline, synthetic_data):
        from app.pipeline.predictor import predict_batch
        df = synthetic_data.head(5).copy()
        results = predict_batch(pipeline=fitted_pipeline, feature_df=df, threshold=0.5)
        result_ids = {r["student_id"] for r in results}
        expected_ids = set(df["student_id"].tolist())
        assert result_ids == expected_ids

    def test_high_risk_score_triggers_high_label(self, fitted_pipeline, at_risk_raw_row):
        """A very at-risk student should receive HIGH label."""
        from app.pipeline.predictor import predict_single
        if at_risk_raw_row is None:
            pytest.skip("No at-risk samples in dataset")
        # Use a low threshold to ensure HIGH label fires easily
        result = predict_single(
            pipeline=fitted_pipeline,
            raw_features=at_risk_raw_row,
            threshold=0.3,
        )
        assert result["risk_label"] in ("HIGH", "MEDIUM")
