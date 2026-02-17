#!/usr/bin/env python
"""
Test CYP450 substrate models against external benchmark data.

Compares our CYP450 substrate predictions (cyp2c9_subs, cyp2d6_subs, cyp3a4_subs)
against ground truth benchmark classifications.

Usage:
    python test_cyp_benchmarks.py --url http://localhost:5001 --data-dir ../../cyp_test_data

    # Or from inside Docker container:
    python test_cyp_benchmarks.py --url http://localhost:5000 --data-dir /opt/adme/testing/cyp_test_data
"""

import csv
import json
import requests
import argparse
import sys
import re
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Benchmark files and their corresponding CYP450 API output columns
BENCHMARKS = {
    'cyp2c9_subs_benchmark.csv': {
        'column': 'CYP2C9 Substrate',
        'endpoint': 'cyp2c9_subs',
        'label': 'CYP2C9 Substrate',
    },
    'cyp2d6_subs_benchmark.csv': {
        'column': 'CYP2D6 Substrate',
        'endpoint': 'cyp2d6_subs',
        'label': 'CYP2D6 Substrate',
    },
    'cyp3a4_subs_benchmark.csv': {
        'column': 'CYP3A4 Substrate',
        'endpoint': 'cyp3a4_subs',
        'label': 'CYP3A4 Substrate',
    },
}

API_ENDPOINT = "/api/v1/predict"


def parse_prediction(pred_str: str) -> Tuple[Optional[int], Optional[float]]:
    """
    Parse CYP450 prediction string like '1 (0.85)' into (class, probability).
    Returns (None, None) if parsing fails.
    """
    match = re.match(r'(\d+)\s*\(([0-9.]+)\)', str(pred_str))
    if match:
        return int(match.group(1)), float(match.group(2))
    return None, None


def load_benchmark(filepath: Path) -> List[Dict[str, Any]]:
    """Load benchmark CSV and return list of dicts with Sample, SMILES, Substrate Class."""
    molecules = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            smiles = row['SMILES'].strip()
            if not smiles:
                continue
            molecules.append({
                'sample': row['Sample'],
                'smiles': smiles,
                'true_class': int(row['Substrate Class']),
            })
    return molecules


def predict_molecule(base_url: str, smiles: str, timeout: int = 600) -> Optional[Dict]:
    """Call the CYP450 prediction API for a single molecule."""
    params = [("smiles", smiles), ("model", "cyp450")]
    url = f"{base_url}{API_ENDPOINT}"

    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.exceptions.Timeout:
        print(f"  Request timed out after {timeout}s")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  Request error: {e}")
        return None


def calculate_metrics(true_labels: List[int], pred_labels: List[int]) -> Dict[str, Any]:
    """Calculate classification metrics (accuracy, precision, recall, F1, confusion matrix)."""
    n = len(true_labels)
    if n == 0:
        return {
            'accuracy': 0, 'precision': 0, 'recall': 0, 'f1': 0,
            'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0,
            'n': 0, 'n_positive': 0, 'n_negative': 0,
        }

    tp = sum(1 for t, p in zip(true_labels, pred_labels) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(true_labels, pred_labels) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(true_labels, pred_labels) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(true_labels, pred_labels) if t == 1 and p == 0)

    accuracy = (tp + tn) / n if n > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
        'n': n,
        'n_positive': tp + fn,
        'n_negative': tn + fp,
    }


def run_benchmark(base_url: str, data_dir: Path, output_dir: Optional[Path] = None) -> Dict:
    """Run all CYP benchmark tests and return results."""
    all_results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'data_dir': str(data_dir),
        },
        'benchmarks': {},
        'summary': {},
    }

    print("=" * 70)
    print("CYP450 SUBSTRATE BENCHMARK TEST")
    print("=" * 70)
    print(f"Server: {base_url}")
    print(f"Data directory: {data_dir}")
    print(f"Benchmarks: {len(BENCHMARKS)}")
    print("=" * 70)

    for filename, config in BENCHMARKS.items():
        filepath = data_dir / filename
        if not filepath.exists():
            print(f"\nWARNING: {filename} not found at {filepath}, skipping...")
            continue

        molecules = load_benchmark(filepath)
        column = config['column']
        label = config['label']

        n_substrates = sum(1 for m in molecules if m['true_class'] == 1)
        n_non_substrates = sum(1 for m in molecules if m['true_class'] == 0)

        print(f"\n{'=' * 70}")
        print(f"  {label}")
        print(f"  File: {filename}")
        print(f"  Molecules: {len(molecules)}")
        print(f"  Class distribution: {n_substrates} substrate, {n_non_substrates} non-substrate")
        print(f"{'=' * 70}")

        true_labels = []
        pred_labels = []
        pred_probs = []
        details = []

        for i, mol in enumerate(molecules, 1):
            smiles = mol['smiles']
            true_class = mol['true_class']
            sample = mol['sample']

            print(f"  [{i:>3}/{len(molecules)}] {sample}...", end=" ", flush=True)

            response = predict_molecule(base_url, smiles)

            if response and 'cyp450' in response:
                cyp_data = response['cyp450']
                if not cyp_data.get('hasErrors', True) and cyp_data.get('data'):
                    # data is a list of row-dicts
                    row = cyp_data['data'][0]

                    pred_str = None
                    if isinstance(row, dict):
                        pred_str = row.get(column)
                    elif isinstance(row, list):
                        # Fall back to column index
                        columns = cyp_data.get('columns', [])
                        if column in columns:
                            col_idx = columns.index(column)
                            pred_str = row[col_idx]

                    if pred_str:
                        pred_class, pred_prob = parse_prediction(pred_str)
                        if pred_class is not None:
                            true_labels.append(true_class)
                            pred_labels.append(pred_class)
                            pred_probs.append(pred_prob)

                            match = "✓" if pred_class == true_class else "✗"
                            print(f"{match} pred={pred_class} (p={pred_prob:.3f}) true={true_class}")

                            details.append({
                                'sample': sample,
                                'smiles': smiles,
                                'true_class': true_class,
                                'pred_class': pred_class,
                                'pred_prob': pred_prob,
                                'correct': pred_class == true_class,
                            })
                            continue

            print("ERROR - no prediction returned")
            details.append({
                'sample': sample,
                'smiles': smiles,
                'true_class': true_class,
                'pred_class': None,
                'pred_prob': None,
                'correct': None,
            })

        # Calculate metrics
        metrics = calculate_metrics(true_labels, pred_labels)

        print(f"\n  --- {label} Results ---")
        print(f"  Predictions obtained: {len(true_labels)}/{len(molecules)}")
        print(f"  Accuracy:  {metrics['accuracy']:.1%} ({metrics['tp'] + metrics['tn']}/{metrics['n']})")
        print(f"  Precision: {metrics['precision']:.1%}")
        print(f"  Recall:    {metrics['recall']:.1%}")
        print(f"  F1 Score:  {metrics['f1']:.3f}")
        print(f"  Confusion Matrix:")
        print(f"    TP={metrics['tp']}  FP={metrics['fp']}")
        print(f"    FN={metrics['fn']}  TN={metrics['tn']}")

        # Show misclassifications
        misclassified = [d for d in details if d['correct'] is False]
        if misclassified:
            print(f"\n  Misclassified ({len(misclassified)}):")
            for m in misclassified:
                if m['pred_class'] == 1:
                    direction = "FP (predicted substrate, actually non-substrate)"
                else:
                    direction = "FN (predicted non-substrate, actually substrate)"
                print(f"    {m['sample']}: {direction}, prob={m['pred_prob']:.3f}")

        all_results['benchmarks'][config['endpoint']] = {
            'filename': filename,
            'label': label,
            'metrics': metrics,
            'details': details,
        }

    # Overall summary
    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    print(f"{'Endpoint':<20} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'N':>5}")
    print("-" * 70)

    total_correct = 0
    total_n = 0

    for endpoint, bench in all_results['benchmarks'].items():
        m = bench['metrics']
        print(f"{bench['label']:<20} {m['accuracy']:>9.1%} {m['precision']:>9.1%} "
              f"{m['recall']:>9.1%} {m['f1']:>9.3f} {m['n']:>5}")
        total_correct += m['tp'] + m['tn']
        total_n += m['n']

    if total_n > 0:
        print("-" * 70)
        print(f"{'Overall':<20} {total_correct / total_n:>9.1%} {'':>10} {'':>10} {'':>10} {total_n:>5}")

    print("=" * 70)

    all_results['summary'] = {
        'total_molecules': total_n,
        'total_correct': total_correct,
        'overall_accuracy': total_correct / total_n if total_n > 0 else 0,
    }

    # Save results
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

        # Save JSON results
        output_file = output_dir / f"cyp_benchmark_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\nJSON results saved to: {output_file}")

        # Save human-readable report
        report_file = output_dir / f"cyp_benchmark_{timestamp}_report.txt"
        with open(report_file, 'w') as f:
            f.write("CYP450 Substrate Benchmark Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Server: {base_url}\n")
            f.write(f"Data directory: {data_dir}\n\n")

            for endpoint, bench in all_results['benchmarks'].items():
                m = bench['metrics']
                f.write(f"{bench['label']}:\n")
                f.write(f"  Accuracy:  {m['accuracy']:.1%} ({m['tp'] + m['tn']}/{m['n']})\n")
                f.write(f"  Precision: {m['precision']:.1%}\n")
                f.write(f"  Recall:    {m['recall']:.1%}\n")
                f.write(f"  F1 Score:  {m['f1']:.3f}\n")
                f.write(f"  Confusion: TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']}\n")

                misclassified = [d for d in bench['details'] if d['correct'] is False]
                if misclassified:
                    f.write(f"  Misclassified ({len(misclassified)}):\n")
                    for mc in misclassified:
                        if mc['pred_class'] == 1:
                            direction = "FP"
                        else:
                            direction = "FN"
                        f.write(f"    {mc['sample']}: {direction} pred={mc['pred_class']} "
                                f"(p={mc['pred_prob']:.3f}) true={mc['true_class']}\n")
                f.write("\n")

            if total_n > 0:
                f.write(f"Overall: {total_correct}/{total_n} correct "
                        f"({total_correct / total_n:.1%} accuracy)\n")

        print(f"Report saved to: {report_file}")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Test CYP450 substrate models against benchmark data"
    )
    parser.add_argument(
        '--url', default='http://localhost:5001',
        help='Base URL of the ADME server (default: http://localhost:5001)'
    )
    parser.add_argument(
        '--data-dir', required=True,
        help='Directory containing benchmark CSV files'
    )
    parser.add_argument(
        '--output', default=None,
        help='Output directory for results (optional)'
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        sys.exit(1)

    # Verify benchmark files exist
    found = 0
    for filename in BENCHMARKS:
        fpath = data_dir / filename
        if fpath.exists():
            found += 1
        else:
            print(f"WARNING: Missing benchmark file: {fpath}")

    if found == 0:
        print(f"ERROR: No benchmark files found in {data_dir}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else None
    results = run_benchmark(args.url, data_dir, output_dir)

    # Exit code based on whether predictions were obtained
    total_predicted = sum(
        b['metrics']['n'] for b in results['benchmarks'].values()
    )
    if total_predicted == 0:
        print("\nERROR: No predictions obtained from any benchmark")
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()

