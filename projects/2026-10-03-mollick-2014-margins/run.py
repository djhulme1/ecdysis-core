"""Mollick (2014) margins on a 2026 Web Robots crawl of Kickstarter (see PLAN.md).

Reads the crawl at inputs/kickstarter-2026-09-10.zip (an inputs/0.1 input the runner fetched and verified
by hash), keeps the first row per project id, keeps decided campaigns (failed or successful) with a positive
goal, and writes results/outputs.json: numbers only. All randomness comes from ECDYSIS_SEED; the clock is
never read. Standard library only.
"""
import csv
import io
import json
import math
import os
import random
import sys
import zipfile
from datetime import datetime, timezone

INPUT = "inputs/kickstarter-2026-09-10.zip"
RESAMPLES = 200


def nearest_rank(sorted_values, p):
    """The p-th percentile by the nearest-rank method on an ascending list."""
    k = max(1, math.ceil(p * len(sorted_values)))
    return sorted_values[k - 1]


def main():
    seed_hex = os.environ["ECDYSIS_SEED"]
    if len(seed_hex) != 64:
        sys.exit("ECDYSIS_SEED must be 64 hex characters")
    rng = random.Random(int(seed_hex[:16], 16))

    rows = 0
    seen = set()
    failed = []        # r = pledged / goal, failed campaigns
    success_over = []  # r - 1, successful campaigns
    agree = 0
    first_launch = None
    last_deadline = None
    with zipfile.ZipFile(INPUT) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv"):
                continue
            reader = csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8", newline=""))
            for row in reader:
                rows += 1
                pid = row.get("id", "")
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                state = row.get("state", "")
                if state not in ("failed", "successful"):
                    continue
                try:
                    goal = float(row["goal"])
                    pledged = float(row["pledged"])
                except (KeyError, ValueError):
                    continue
                if not (goal > 0 and pledged >= 0 and math.isfinite(goal) and math.isfinite(pledged)):
                    continue
                r = pledged / goal
                try:
                    pf = float(row.get("percent_funded", "nan"))
                    if math.isfinite(pf) and abs(100.0 * r - pf) <= 1.0:
                        agree += 1
                except ValueError:
                    pass
                for key, keep_min in (("launched_at", True), ("deadline", False)):
                    try:
                        year = datetime.fromtimestamp(int(float(row[key])), tz=timezone.utc).year
                    except (KeyError, ValueError, OverflowError, OSError):
                        continue
                    if keep_min:
                        first_launch = year if first_launch is None else min(first_launch, year)
                    else:
                        last_deadline = year if last_deadline is None else max(last_deadline, year)
                if state == "failed":
                    failed.append(r)
                else:
                    success_over.append(r - 1.0)

    n_failed, n_success = len(failed), len(success_over)
    n_decided = n_failed + n_success
    if n_failed == 0 or n_success == 0:
        sys.exit("no decided campaigns found")

    failed_sorted = sorted(failed)
    over_sorted = sorted(success_over)
    share = lambda xs, pred: sum(1 for x in xs if pred(x)) / len(xs)

    failed_mean_ratio = sum(failed) / n_failed
    failed_share_ge30 = share(failed, lambda x: x >= 0.30)
    failed_share_ge50 = share(failed, lambda x: x >= 0.50)
    success_p25_over = nearest_rank(over_sorted, 0.25)
    success_median_over = nearest_rank(over_sorted, 0.50)
    success_share_le3over = share(success_over, lambda x: x <= 0.03)
    success_share_le10over = share(success_over, lambda x: x <= 0.10)

    # Bootstrap standard errors: resample each project set with replacement, from the seed and nothing else.
    def bootstrap(values, statistic):
        n = len(values)
        draws = []
        for _ in range(RESAMPLES):
            sample = [values[rng.randrange(n)] for _ in range(n)]
            draws.append(statistic(sample))
        mean = sum(draws) / RESAMPLES
        return math.sqrt(sum((d - mean) ** 2 for d in draws) / (RESAMPLES - 1))

    se_failed_share_ge30 = bootstrap(failed_sorted, lambda s: share(s, lambda x: x >= 0.30))
    se_success_median_over = bootstrap(over_sorted, lambda s: nearest_rank(sorted(s), 0.50))

    out = {
        "n_rows": rows,
        "n_projects": len(seen),
        "n_decided": n_decided,
        "n_failed": n_failed,
        "n_successful": n_success,
        "success_rate": round(n_success / n_decided, 6),
        "failed_mean_ratio": round(failed_mean_ratio, 6),
        "failed_share_ge30": round(failed_share_ge30, 6),
        "failed_share_ge50": round(failed_share_ge50, 6),
        "success_p25_over": round(success_p25_over, 6),
        "success_median_over": round(success_median_over, 6),
        "success_share_le3over": round(success_share_le3over, 6),
        "success_share_le10over": round(success_share_le10over, 6),
        "percent_funded_agreement": round(agree / n_decided, 6),
        "se_failed_share_ge30": round(se_failed_share_ge30, 6),
        "se_success_median_over": round(se_success_median_over, 6),
        "first_launch_year": first_launch if first_launch is not None else -1,
        "last_deadline_year": last_deadline if last_deadline is not None else -1,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/outputs.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
