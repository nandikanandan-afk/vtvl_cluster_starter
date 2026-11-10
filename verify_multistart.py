"""Re-optimise selected reusable baseline cases from nearby pitch-kick starts.

Usage:
    python verify_multistart.py
    python verify_multistart.py --baseline results/20261109_1839_baseline --workers 4
"""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from vtvl.study import DEFAULT_KICK, run_parallel, write_csv

ENGINE_COUNTS = (7, 9, 21)
KICK_OFFSETS = ((-0.25, 0.0), (0.25, 0.0), (0.0, -0.05), (0.0, 0.05))
PAYLOAD_TOLERANCE_KG = 10.0


def _read_baselines(path: Path) -> dict[int, dict]:
    with (path / "cases.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    baseline = {}
    for row in rows:
        if (row.get("mode") == "reusable" and row.get("status") == "feasible"
                and row.get("tag") == "baseline" and int(row["n_engines"]) in ENGINE_COUNTS):
            n = int(row["n_engines"])
            if n in baseline:
                raise ValueError(f"multiple feasible reusable baseline rows for N={n}")
            baseline[n] = row
    missing = sorted(set(ENGINE_COUNTS) - set(baseline))
    if missing:
        raise ValueError(f"missing feasible reusable baseline cases for N={missing}")
    return baseline


def _starts(baseline_kick: tuple[float, float]) -> list[tuple[str, tuple[float, float]]]:
    candidates = [("original_default", DEFAULT_KICK), ("baseline_solution", baseline_kick)]
    candidates.extend(
        (f"nearby_{dt:+.2f}s_{dd:+.2f}deg",
         (baseline_kick[0] + dt, baseline_kick[1] + dd))
        for dt, dd in KICK_OFFSETS
    )
    starts = []
    seen = set()
    for label, kick in candidates:
        if kick in seen:
            continue
        seen.add(kick)
        starts.append((label, kick))
    return starts


def _outcome(row: dict) -> str:
    if row.get("status") == "infeasible_proven":
        return "physical_infeasibility_proven"
    if row.get("status") != "feasible":
        return "optimizer_or_payload_solver_failure"
    if not row.get("optimizer_success", False):
        return "optimizer_non_success_with_feasible_candidate"
    return "success"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path(r"results\20261109_1839_baseline"))
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    baseline_dir = args.baseline
    manifest = json.loads((baseline_dir / "manifest.json").read_text(encoding="utf-8"))
    baselines = _read_baselines(baseline_dir)

    jobs = []
    metadata = []
    for n in ENGINE_COUNTS:
        base = baselines[n]
        base_kick = (float(base["kick_t_s"]), float(base["kick_delta_deg"]))
        for label, kick in _starts(base_kick):
            jobs.append({
                "overrides": manifest["frozen_calibration"],
                "n": n,
                "mode": "reusable",
                "tag": f"multistart_{label}",
                "kick0": kick,
            })
            metadata.append({
                "initial_guess": label,
                "initial_kick_t_s": kick[0],
                "initial_kick_delta_deg": kick[1],
                "baseline_payload_kg": float(base["payload_kg"]),
                "baseline_kick_t_s": base_kick[0],
                "baseline_kick_delta_deg": base_kick[1],
            })

    rows = run_parallel(jobs, args.workers)
    for row, meta in zip(rows, metadata):
        row.update(meta)
        row["start_outcome"] = _outcome(row)
        if row.get("status") == "feasible":
            delta = float(row["payload_kg"]) - meta["baseline_payload_kg"]
            row["payload_change_from_baseline_kg"] = delta
            row["payload_difference_over_10kg"] = abs(delta) > PAYLOAD_TOLERANCE_KG
        else:
            row["payload_change_from_baseline_kg"] = ""
            row["payload_difference_over_10kg"] = ""

    out_dir = args.out_dir or Path("results") / (
        datetime.now().strftime("%Y%m%d_%H%M") + "_multistart_verification"
    )
    out_dir.mkdir(parents=True, exist_ok=False)
    write_csv(out_dir / "multistart_results.csv", rows)
    (out_dir / "manifest.json").write_text(json.dumps({
        "baseline_dir": str(baseline_dir),
        "baseline_mode": manifest.get("mode"),
        "frozen_calibration": manifest["frozen_calibration"],
        "engine_counts": ENGINE_COUNTS,
        "initial_guess_count_per_case": len(metadata) // len(ENGINE_COUNTS),
        "nearby_kick_offsets_s_deg": KICK_OFFSETS,
        "original_default_guess_s_deg": DEFAULT_KICK,
        "payload_difference_threshold_kg": PAYLOAD_TOLERANCE_KG,
        "failure_classification": {
            "physical_infeasibility_proven": "status=infeasible_proven",
            "optimizer_or_payload_solver_failure": "status is not feasible and not infeasible_proven",
            "optimizer_non_success_with_feasible_candidate": "feasible payload candidate, but COBYLA success is false",
        },
    }, indent=2) + "\n", encoding="utf-8")

    for row in rows:
        n = row["n_engines"]
        start = row["initial_guess"]
        if row["status"] == "feasible":
            print(f"N={n} {start}: {row['start_outcome']}; payload={row['payload_kg']:.1f} kg; "
                  f"change={row['payload_change_from_baseline_kg']:+.1f} kg; "
                  f">10 kg={row['payload_difference_over_10kg']}")
        else:
            print(f"N={n} {start}: {row['start_outcome']}; status={row['status']}; "
                  f"optimizer={row.get('optimizer_status')}; reason={row.get('reason')}")
    print(f"Results: {out_dir}")


if __name__ == "__main__":
    main()
