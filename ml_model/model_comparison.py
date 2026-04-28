"""
Model Comparison Visualization Script
======================================
Generates publication-quality charts comparing ML model performance.
Outputs saved to ml_model/results/ for inclusion in the project report.

Charts generated:
    1. Model Performance Comparison (bar chart)
    2. Feature Importance (top 15, from tree-based models)
    3. Predicted vs Actual scatter plot
"""

import os
import sys
import json
import warnings

import pandas as pd
import numpy as np
import joblib
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

warnings.filterwarnings('ignore')

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

MODEL_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(MODEL_DIR, "results")


def set_plot_style():
    """Set a clean, professional matplotlib style."""
    plt.rcParams.update({
        'figure.facecolor': '#0f172a',
        'axes.facecolor': '#1e293b',
        'axes.edgecolor': '#334155',
        'axes.labelcolor': '#e2e8f0',
        'text.color': '#e2e8f0',
        'xtick.color': '#94a3b8',
        'ytick.color': '#94a3b8',
        'grid.color': '#334155',
        'grid.alpha': 0.5,
        'font.family': 'sans-serif',
        'font.size': 11,
        'axes.titlesize': 14,
        'axes.labelsize': 12,
        'figure.dpi': 150,
        'savefig.dpi': 150,
        'savefig.bbox': 'tight',
        'savefig.facecolor': '#0f172a',
    })


def plot_model_comparison(results_csv_path: str, output_path: str):
    """
    Generate a grouped bar chart comparing model metrics.
    """
    df = pd.read_csv(results_csv_path)
    if df.empty:
        print("No results to plot.")
        return

    set_plot_style()
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    models = df['Model'].tolist()
    colors = ['#6366f1', '#22d3ee', '#f59e0b', '#ef4444', '#10b981'][:len(models)]

    # R² Score
    ax = axes[0]
    bars = ax.bar(models, df['R²'], color=colors, edgecolor='none', width=0.6)
    ax.set_title('R² Score (higher is better)', fontweight='bold')
    ax.set_ylim(0, 1.05)
    for bar, val in zip(bars, df['R²']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f'{val:.4f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.tick_params(axis='x', rotation=15)

    # MAE / RMSE
    ax = axes[1]
    x = np.arange(len(models))
    w = 0.35
    bars1 = ax.bar(x - w / 2, df['MAE'], w, label='MAE', color='#6366f1', edgecolor='none')
    bars2 = ax.bar(x + w / 2, df['RMSE'], w, label='RMSE', color='#f59e0b', edgecolor='none')
    ax.set_title('MAE & RMSE (lower is better)', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=15)
    ax.legend(loc='upper right')

    # Directional Accuracy
    ax = axes[2]
    bars = ax.bar(models, df['Directional Accuracy (%)'], color=colors, edgecolor='none', width=0.6)
    ax.set_title('Directional Accuracy %', fontweight='bold')
    ax.set_ylim(0, 100)
    ax.axhline(y=50, color='#ef4444', linestyle='--', alpha=0.5, label='Random (50%)')
    for bar, val in zip(bars, df['Directional Accuracy (%)']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.legend(loc='upper right')
    ax.tick_params(axis='x', rotation=15)

    plt.suptitle('Stock Price Prediction — Model Comparison', fontsize=16,
                 fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    print(f"✅ Model comparison chart saved to {output_path}")


def plot_feature_importance(csv_path: str, output_path: str, model_name: str = "Model"):
    """
    Plot top 15 most important features as a horizontal bar chart.
    """
    if not os.path.exists(csv_path):
        print(f"  Skipping feature importance plot: {csv_path} not found")
        return

    df = pd.read_csv(csv_path)
    top = df.head(15).iloc[::-1]  # Reverse for horizontal bar

    set_plot_style()
    fig, ax = plt.subplots(figsize=(10, 7))

    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(top)))
    ax.barh(top['feature'], top['importance'], color=colors, edgecolor='none', height=0.7)
    ax.set_xlabel('Importance Score')
    ax.set_title(f'Top 15 Feature Importances — {model_name}', fontweight='bold')

    # Add value labels
    for i, (val, name) in enumerate(zip(top['importance'], top['feature'])):
        ax.text(val + max(top['importance']) * 0.01, i, f'{val:.4f}',
                va='center', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    print(f"✅ Feature importance chart saved to {output_path}")


def plot_metrics_radar(results_csv_path: str, output_path: str):
    """
    Generate a summary metrics table as an image (cleaner than radar for reports).
    """
    df = pd.read_csv(results_csv_path)
    if df.empty:
        return

    set_plot_style()
    fig, ax = plt.subplots(figsize=(12, 3 + len(df) * 0.5))
    ax.axis('off')

    # Create table
    cell_colors = []
    for i in range(len(df)):
        row_color = ['#1e293b'] * len(df.columns)
        cell_colors.append(row_color)

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc='center',
        loc='center',
        cellColours=cell_colors,
        colColours=['#6366f1'] * len(df.columns),
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.8)

    # Style cells
    for key, cell in table.get_celld().items():
        cell.set_edgecolor('#334155')
        cell.set_text_props(color='#e2e8f0')
        if key[0] == 0:  # Header
            cell.set_text_props(color='white', fontweight='bold')

    # Highlight best R² row
    if len(df) > 0:
        best_idx = df['R²'].idxmax() + 1  # +1 for header
        for col in range(len(df.columns)):
            table[best_idx, col].set_facecolor('#166534')

    ax.set_title('Model Performance Summary\n(Best model highlighted in green)',
                 fontweight='bold', fontsize=14, pad=20)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    print(f"✅ Metrics table image saved to {output_path}")


def generate_all_charts():
    """Generate all comparison charts from saved results."""
    print("\n" + "=" * 60)
    print("📊 Generating Model Comparison Charts")
    print("=" * 60)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    comparison_csv = os.path.join(RESULTS_DIR, "model_comparison.csv")
    if not os.path.exists(comparison_csv):
        print(f"❌ {comparison_csv} not found. Run train.py first.")
        return

    # 1. Model comparison bar charts
    plot_model_comparison(
        comparison_csv,
        os.path.join(RESULTS_DIR, "model_comparison_chart.png")
    )

    # 2. Feature importance plots
    for model_key, model_name in [("random_forest", "Random Forest"), ("xgboost", "XGBoost")]:
        csv_path = os.path.join(RESULTS_DIR, f"{model_key}_feature_importance.csv")
        plot_feature_importance(
            csv_path,
            os.path.join(RESULTS_DIR, f"{model_key}_feature_importance.png"),
            model_name
        )

    # 3. Metrics summary table
    plot_metrics_radar(
        comparison_csv,
        os.path.join(RESULTS_DIR, "metrics_summary_table.png")
    )

    print(f"\n✅ All charts saved to {RESULTS_DIR}/")
    print("   Use these in your project report!\n")


if __name__ == "__main__":
    generate_all_charts()
