"""
generate_dataset.py
═══════════════════
Generates a synthetic labelled dataset (2 000 rows) for training
the EduSentinel student risk-prediction model.

Output schema
─────────────
  student_id            int      Unique student identifier (10001 …)
  attendance_percentage float    % classes attended          0 – 100
  internal_score        float    Aggregate internal assessment score 0 – 100
  assignment_score      float    Average assignment score    0 – 100
  lms_activity          float    Composite LMS engagement score 0 – 100
  engagement_time       float    Weekly hours on LMS         0 – 20
  previous_gpa          float    GPA from prior semester     0.0 – 10.0
  risk_label            str      Predicted risk: HIGH | MEDIUM | LOW

Class distribution
──────────────────
  HIGH   20 %  →   400 students
  MEDIUM 25 %  →   500 students
  LOW    55 %  → 1 100 students

Usage
─────
  python generate_dataset.py                    # writes to ./training_data.csv
  python generate_dataset.py --rows 5000        # custom size
  python generate_dataset.py --out path/to.csv  # custom output path
  python generate_dataset.py --seed 7           # different random seed
  python generate_dataset.py --plot             # show EDA plots (requires matplotlib)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Class proportions (must sum to 1.0)
CLASS_FRACTIONS = {
    "HIGH":   0.20,
    "MEDIUM": 0.25,
    "LOW":    0.55,
}

# Feature distributions per risk class
# Each entry: (mean, std, clip_lo, clip_hi)
FEATURE_PARAMS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "HIGH": {
        "attendance_percentage": (46.0,  14.0,  0.0, 100.0),
        "internal_score":        (32.0,  11.0,  0.0, 100.0),
        "assignment_score":      (36.0,  13.0,  0.0, 100.0),
        "lms_activity":          (12.0,   9.0,  0.0, 100.0),
        "engagement_time":       ( 1.2,   0.8,  0.0,  20.0),
        "previous_gpa":          ( 4.2,   1.5,  0.0,  10.0),
    },
    "MEDIUM": {
        "attendance_percentage": (65.0,  10.0,  0.0, 100.0),
        "internal_score":        (51.0,  10.0,  0.0, 100.0),
        "assignment_score":      (54.0,  11.0,  0.0, 100.0),
        "lms_activity":          (35.0,  14.0,  0.0, 100.0),
        "engagement_time":       ( 3.2,   1.4,  0.0,  20.0),
        "previous_gpa":          ( 5.8,   1.2,  0.0,  10.0),
    },
    "LOW": {
        "attendance_percentage": (83.0,   8.0,  0.0, 100.0),
        "internal_score":        (72.0,  11.0,  0.0, 100.0),
        "assignment_score":      (74.0,  11.0,  0.0, 100.0),
        "lms_activity":          (65.0,  15.0,  0.0, 100.0),
        "engagement_time":       ( 6.5,   2.5,  0.0,  20.0),
        "previous_gpa":          ( 7.5,   1.2,  0.0,  10.0),
    },
}

FEATURE_COLS = [
    "attendance_percentage",
    "internal_score",
    "assignment_score",
    "lms_activity",
    "engagement_time",
    "previous_gpa",
]

# Correlation nudges within each class (keeps features realistic)
# lms_activity ↑  →  engagement_time ↑  (r ≈ 0.65)
# internal_score ↑ → assignment_score ↑ (r ≈ 0.55)
# attendance ↑    → internal_score ↑   (r ≈ 0.45)
_CORR_MATRICES: dict[str, np.ndarray] = {
    label: np.array([
        # att   int   asgn  lms   eng   gpa
        [1.00, 0.45, 0.35, 0.30, 0.25, 0.40],  # attendance_percentage
        [0.45, 1.00, 0.55, 0.35, 0.30, 0.50],  # internal_score
        [0.35, 0.55, 1.00, 0.40, 0.35, 0.40],  # assignment_score
        [0.30, 0.35, 0.40, 1.00, 0.65, 0.30],  # lms_activity
        [0.25, 0.30, 0.35, 0.65, 1.00, 0.25],  # engagement_time
        [0.40, 0.50, 0.40, 0.30, 0.25, 1.00],  # previous_gpa
    ])
    for label in ("HIGH", "MEDIUM", "LOW")
}


# ─────────────────────────────────────────────────────────────────────────────
#  Generator helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cholesky_safe(corr: np.ndarray) -> np.ndarray:
    """Return Cholesky factor; fall back to nearest PSD if matrix is not PD."""
    try:
        return np.linalg.cholesky(corr)
    except np.linalg.LinAlgError:
        # Nearest positive-definite via eigenvalue clipping
        eigvals, eigvecs = np.linalg.eigh(corr)
        eigvals = np.clip(eigvals, 1e-6, None)
        psd = eigvecs @ np.diag(eigvals) @ eigvecs.T
        return np.linalg.cholesky(psd)


def _generate_class(
    label: str,
    n: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Generate n rows for a single risk class using correlated Gaussians.

    Strategy:
      1. Draw standard normals Z ~ N(0, I)
      2. Apply Cholesky decomposition of target correlation matrix
      3. Scale each column to target (mean, std)
      4. Clip to valid domain
    """
    params = FEATURE_PARAMS[label]
    means  = np.array([params[f][0] for f in FEATURE_COLS])
    stds   = np.array([params[f][1] for f in FEATURE_COLS])
    clips  = np.array([[params[f][2], params[f][3]] for f in FEATURE_COLS])
    corr   = _CORR_MATRICES[label]

    # Standard normal samples
    Z = rng.standard_normal((n, len(FEATURE_COLS)))

    # Introduce correlations via Cholesky
    L = _cholesky_safe(corr)
    Z_corr = Z @ L.T

    # Scale to target distribution
    X = Z_corr * stds + means

    # Clip to valid range
    for i, (lo, hi) in enumerate(clips):
        X[:, i] = np.clip(X[:, i], lo, hi)

    df = pd.DataFrame(X, columns=FEATURE_COLS)
    df["risk_label"] = label
    return df


def _inject_missing(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """
    Inject realistic missing values to mirror real-world data quality issues.

    LMS fields are missing more often (students who never logged in
    produce NULL records in the DB). Score fields occasionally missing
    for students who withdrew from an exam.
    """
    df = df.copy()
    missing_rates = {
        "lms_activity":    0.06,   # 6 % – students with no LMS account
        "engagement_time": 0.06,
        "internal_score":  0.02,   # 2 % – exam absentees
        "assignment_score": 0.03,
    }
    for col, rate in missing_rates.items():
        mask = rng.random(len(df)) < rate
        df.loc[mask, col] = np.nan
    return df


def _round_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Round float columns to 2 d.p. for cleaner CSV output."""
    float_cols = df.select_dtypes(include="float").columns
    df[float_cols] = df[float_cols].round(2)
    return df


# ─────────────────────────────────────────────────────────────────────────────
#  Main generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_dataset(
    n_samples: int = 2000,
    random_seed: int = 42,
    inject_missing: bool = True,
    start_student_id: int = 10001,
) -> pd.DataFrame:
    """
    Generate synthetic labelled student data.

    Parameters
    ----------
    n_samples        : Total number of rows.
    random_seed      : Reproducibility seed.
    inject_missing   : Whether to introduce realistic NaN values.
    start_student_id : Starting value for the student_id sequence.

    Returns
    -------
    pd.DataFrame with columns:
        student_id, attendance_percentage, internal_score,
        assignment_score, lms_activity, engagement_time,
        previous_gpa, risk_label
    """
    rng = np.random.default_rng(random_seed)

    # Compute exact per-class counts (last class absorbs rounding remainder)
    counts: dict[str, int] = {}
    total_assigned = 0
    labels = list(CLASS_FRACTIONS.keys())
    for label in labels[:-1]:
        counts[label] = round(n_samples * CLASS_FRACTIONS[label])
        total_assigned += counts[label]
    counts[labels[-1]] = n_samples - total_assigned

    # Generate each class
    frames = [_generate_class(label, counts[label], rng) for label in labels]
    df = pd.concat(frames, ignore_index=True)

    # Shuffle
    df = df.sample(frac=1, random_state=random_seed).reset_index(drop=True)

    # Assign student IDs
    df.insert(0, "student_id", range(start_student_id, start_student_id + len(df)))

    # Inject NaN
    if inject_missing:
        df = _inject_missing(df, rng)

    # Clean up
    df = _round_columns(df)

    # Reorder columns to match the requested schema
    df = df[
        [
            "student_id",
            "attendance_percentage",
            "internal_score",
            "assignment_score",
            "lms_activity",
            "engagement_time",
            "previous_gpa",
            "risk_label",
        ]
    ]

    return df


# ─────────────────────────────────────────────────────────────────────────────
#  Optional EDA plots
# ─────────────────────────────────────────────────────────────────────────────

def plot_eda(df: pd.DataFrame) -> None:
    """Render exploratory data analysis charts for the generated dataset."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed – skipping plots.")
        return

    numeric_df = df.drop(columns=["student_id"])
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    fig.suptitle("Synthetic Dataset – EDA Overview", fontsize=14, fontweight="bold")

    palette = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}
    feature_cols = [c for c in FEATURE_COLS]

    # ── Feature distributions by risk label (box plots) ──────────────────────
    for idx, feat in enumerate(feature_cols):
        ax = axes[idx // 3][idx % 3]
        data_by_label = [
            df.loc[df["risk_label"] == lbl, feat].dropna().values
            for lbl in ["HIGH", "MEDIUM", "LOW"]
        ]
        bp = ax.boxplot(
            data_by_label,
            labels=["HIGH", "MEDIUM", "LOW"],
            patch_artist=True,
            widths=0.5,
            medianprops=dict(color="white", linewidth=2),
        )
        for patch, color in zip(bp["boxes"], palette.values()):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)
        ax.set_title(feat.replace("_", " ").title(), fontsize=11)
        ax.set_ylabel("Value")
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    # ── Class distribution (bar) ─────────────────────────────────────────────
    ax_class = axes[2][1]
    label_counts = df["risk_label"].value_counts().reindex(["HIGH", "MEDIUM", "LOW"])
    bars = ax_class.bar(
        label_counts.index,
        label_counts.values,
        color=list(palette.values()),
        alpha=0.8,
        width=0.5,
    )
    for bar, val in zip(bars, label_counts.values):
        ax_class.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 5,
            f"{val}\n({val / len(df) * 100:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax_class.set_title("Class Distribution", fontsize=11)
    ax_class.set_ylabel("Count")
    ax_class.grid(axis="y", linestyle="--", alpha=0.4)

    # ── Attendance vs Internal Score scatter ─────────────────────────────────
    ax_scatter = axes[2][2]
    for lbl, color in palette.items():
        subset = df[df["risk_label"] == lbl]
        ax_scatter.scatter(
            subset["attendance_percentage"],
            subset["internal_score"],
            c=color,
            label=lbl,
            alpha=0.35,
            s=8,
        )
    ax_scatter.axvline(75, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax_scatter.axhline(50, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax_scatter.set_xlabel("Attendance (%)")
    ax_scatter.set_ylabel("Internal Score")
    ax_scatter.set_title("Attendance vs Internal Score", fontsize=11)
    ax_scatter.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(Path(__file__).parent / "dataset_eda.png", dpi=150, bbox_inches="tight")
    print("EDA plot saved to data/dataset_eda.png")
    plt.show()


# ─────────────────────────────────────────────────────────────────────────────
#  Stats summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    """Print a concise summary of the generated dataset."""
    print(f"\n{'=' * 56}")
    print(f"  Dataset summary  ({len(df):,} rows)")
    print(f"{'=' * 56}")

    print("\n  Class distribution:")
    counts = df["risk_label"].value_counts().reindex(["HIGH", "MEDIUM", "LOW"])
    for label, n in counts.items():
        bar = "#" * int(n / len(df) * 40)
        print(f"    {label:<8} {n:>5}  ({n/len(df)*100:5.1f}%)  {bar}")

    print(f"\n  {'Feature':<28}  {'Mean':>7}  {'Std':>6}  {'Min':>6}  {'Max':>6}  {'NaN%':>5}")
    print(f"  {'-' * 28}  {'-' * 7}  {'-' * 6}  {'-' * 6}  {'-' * 6}  {'-' * 5}")
    for col in FEATURE_COLS:
        s = df[col]
        print(
            f"  {col:<28}  "
            f"{s.mean():>7.2f}  "
            f"{s.std():>6.2f}  "
            f"{s.min():>6.2f}  "
            f"{s.max():>6.2f}  "
            f"{s.isna().mean()*100:>4.1f}%"
        )
    print()


# ─────────────────────────────────────────────────────────────────────────────
#  CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic student dataset for EduSentinel.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--rows", type=int, default=2000, metavar="N",
        help="Total number of student rows to generate",
    )
    parser.add_argument(
        "--out", type=str,
        default=str(Path(__file__).parent / "training_data.csv"),
        metavar="PATH",
        help="Output CSV file path",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--no-missing", action="store_true",
        help="Disable injection of missing values",
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="Show EDA plots after generation (requires matplotlib)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    print(f"Generating {args.rows:,} student records  (seed={args.seed}) …")
    df = generate_dataset(
        n_samples=args.rows,
        random_seed=args.seed,
        inject_missing=not args.no_missing,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved -> {out_path}")

    print_summary(df)

    if args.plot:
        plot_eda(df)
