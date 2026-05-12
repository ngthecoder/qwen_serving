"""
Sprint 7: vLLM vs bare implementation benchmark visualization.

Usage:
cd ~/code/sprints/qwen_serving
source .bench-venv/bin/activate
uv pip install matplotlib numpy
python analysis/plot_matrix.py
"""

import matplotlib.pyplot as plt
import numpy as np

CONCURRENCY = [1, 5, 10, 20]

DATA = {
    ("bare", "short"): {
        "ttft_ms": [182.4, 2298.9, 3867.1, np.nan],
        "itl_ms": [6.0, 98.0, 165.1, np.nan],
        "outtok_s": [101.8, 29.3, 19.1, 0.0],
        "completed": [48, 14, 8, 0],
    },
    ("bare", "long"): {
        "ttft_ms": [694.1, 2466.2, 9464.5, np.nan],
        "itl_ms": [5.8, 107.6, 226.5, np.nan],
        "outtok_s": [85.7, 25.4, 18.0, 0.0],
        "completed": [40, 11, 7, 0],
    },
    ("vllm", "short"): {
        "ttft_ms": [86.8, 144.7, 157.1, 199.5],
        "itl_ms": [20.2, 20.0, 20.0, 25.1],
        "outtok_s": [48.4, 238.1, 482.4, 765.8],
        "completed": [23, 111, 201, 345],
    },
    ("vllm", "long"): {
        "ttft_ms": [117.0, 247.4, 222.7, 291.3],
        "itl_ms": [19.5, 20.1, 25.2, 25.1],
        "outtok_s": [50.0, 234.3, 403.0, 723.6],
        "completed": [24, 107, 181, 324],
    },
}

# ============================================================
# Style — color = engine, linestyle = prompt length
# ============================================================

STYLES = {
    ("bare", "short"): dict(
        color="#d62728", linestyle="-", marker="o", label="bare × short"
    ),
    ("bare", "long"): dict(
        color="#d62728", linestyle="--", marker="s", label="bare × long"
    ),
    ("vllm", "short"): dict(
        color="#1f77b4", linestyle="-", marker="o", label="vLLM × short"
    ),
    ("vllm", "long"): dict(
        color="#1f77b4", linestyle="--", marker="s", label="vLLM × long"
    ),
}

# ============================================================
# Build figure
# ============================================================

fig, axes = plt.subplots(2, 2, figsize=(13, 10))
fig.suptitle(
    "Sprint 7: vLLM vs bare implementation — Qwen2-1.5B on g4dn.xlarge (T4)",
    fontsize=14,
    fontweight="bold",
)

# (axis, metric_key, ylabel, yscale)
panels = [
    (axes[0, 0], "ttft_ms", "TTFT median (ms, log scale)", "log"),
    (axes[0, 1], "itl_ms", "ITL median (ms)", "linear"),
    (axes[1, 0], "outtok_s", "Output Tokens / sec (server side)", "linear"),
    (axes[1, 1], "completed", "Completed requests in 120s window", "linear"),
]

for ax, metric, ylabel, yscale in panels:
    for key, style in STYLES.items():
        values = DATA[key][metric]
        ax.plot(CONCURRENCY, values, markersize=9, linewidth=2, **style)
    ax.set_xlabel("Concurrency (virtual users)")
    ax.set_ylabel(ylabel)
    ax.set_yscale(yscale)
    ax.set_xticks(CONCURRENCY)
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(fontsize=9, loc="best")

# Annotation: mark bare c=20 broken cells
for ax, metric, _, _ in panels:
    if metric in ("outtok_s", "completed"):
        ax.annotate(
            "bare c=20\nunmeasurable",
            xy=(20, 0),
            xytext=(15, ax.get_ylim()[1] * 0.3),
            fontsize=8,
            color="#d62728",
            ha="center",
            arrowprops=dict(arrowstyle="->", color="#d62728", alpha=0.6),
        )

plt.tight_layout()

# Save
output_path = "analysis/matrix_results.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"Saved: {output_path}")

plt.show()
