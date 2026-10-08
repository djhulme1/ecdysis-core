#!/usr/bin/env python3
"""Horvath's multi-tissue clock on healthy adult tissues it was not built from, for an Ecdysis receipt.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:887f30cba62322b7) is from Horvath, "DNA
methylation age of human tissues and cell types", Genome Biology 14:R115 (2013): "I developed a multi-tissue predictor
of age that allows one to estimate the DNA methylation age of most tissues and cell types." Its test, as corrected on
7 October 2026: refuted if the paper's predictor, with its published coefficients and normalisation, applied to
Illumina 27K or 450K data of healthy adult tissues not used to build it, fails in most of the tissue types tested; a
tissue fails when its DNA methylation ages correlate with chronological age below 0.7 or miss it by a median of more
than 10 years.

The inputs, each checked against its SHA-256 and size before it is read (see INPUTS): three of the paper's additional
files (22, the 21,368 calibration probes and their gold standard; 23, the predictor's 353 coefficients and intercept;
26, the tutorial's example data, 16 brain samples), and five series matrices from GEO, all Illumina 450K
(GPL13534): GSE64495 (blood, with Horvath's own DNA methylation ages: a conformance gate) and the four series that give
the five tissue units, none of them among the paper's training or test data (its Additional file 1).

Every rule below was fixed before any DNA methylation age was computed on the tissue units; the seed is not used, as
nothing here is random (R's set.seed(1), which the normalisation calls, is reproduced in horvath/bmiq.py).

1. The predictor, as the paper's tutorial (Additional files 20 and 25) applies it. Each sample's values for the 21,368
   probes of Additional file 22, in its order; a probe the series lacks counts as missing in every sample. Missing
   values are replaced by the probe's gold standard value (the tutorial's fastImputation branch; its default, KNN
   imputation, is not ported: these series miss at most 31 values of 21,368 in a sample, and no clock CpG in all of
   one). The sample is normalised by BMIQcalibration against the gold standard (horvath/bmiq.py, a port checked by
   rules 4 and 5). DNA methylation age = anti.trafo(intercept + sum of coefficient x normalised value) over the 353
   CpGs of Additional file 23, with anti.trafo(x) = 21 exp(x) - 1 for x < 0 and 21 x + 20 otherwise.
2. The units. Chronological ages are the series' own "age" characteristic; a sample is kept if its age is at least 18.
   saliva: GSE92767, tissue Saliva. dermis and epidermis: GSE51954, by its tissue characteristic. muscle: GSE50498
   (vastus lateralis of disease-free men), whose matrix holds M-values (it has values below 0 and above 1): beta =
   2^M / (1 + 2^M) before rule 1. cortex: GSE66351, cell type bulk and diagnosis CTRL. A unit fails when the Pearson
   correlation of DNA methylation age with age is below 0.7, or the median of |DNA methylation age - age| is above
   10 years.
3. The verdict. test_passed is 1 unless at least three of the five units fail (most of the tissue types tested).
4. Gate 1, the tutorial. The example's 16 samples must give the 20 normalised values the tutorial prints (8
   significant figures) within 1e-8, and its 16 DNA methylation ages to the 2 significant figures it prints.
5. Gate 2, Horvath's own ages. GSE64495's 113 blood samples carry the DNA methylation ages Horvath computed. Their
   median absolute difference from the ages here must be at most 0.01 years, and the largest at most 0.5 (the series
   misses 8 values, which his software imputed by KNN). gates_passed counts the two gates; the verdict stands
   regardless, and a failed gate is reported beside it.

What it cannot check:
- other platforms (EPIC arrays, sequencing) or tissues beyond these five;
- the paper's own test sets, which it does not re-run;
- the cause of a failure: a tissue can fail because the clock does not hold there, because the series was processed
  in a way the gold standard does not undo (GSE66351 was ComBat-corrected; GSE50498 quantile-normalised), or because
  its ages span too little for a correlation (GSE51954's donors are either young or old).

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every sample's ages).
"""

import csv
import gzip
import hashlib
import io
import json
import math
import multiprocessing
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bmiq  # noqa: E402

ESM = "https://static-content.springer.com/esm/art%3A10.1186%2Fgb-2013-14-10-r115/MediaObjects/13059_2013_3156_"
INPUTS = (
    ("AdditionalFile22.csv", "e4ea35396c429df1ea3ee64a3c0a012be16eba365ca5b8ae17328bbee13d2dd5", 1052047,
     ESM + "MOESM22_ESM.csv"),
    ("AdditionalFile23.csv", "14caeca93a4e44fcc5ccc53b888e08f684cf862c34e3ffae1ab4c96487e98c2f", 134178,
     ESM + "MOESM23_ESM.csv"),
    ("AdditionalFile26.csv", "0dcacab22264f4c89f5248aa1ac877759c53856685161d4f5b93d94eb47cebdc", 5576794,
     ESM + "MOESM26_ESM.csv"),
)
SERIES = ("GSE64495", "GSE92767", "GSE51954", "GSE50498", "GSE66351")
SERIES_FILES = {g: f"{g}_series_matrix.txt.gz" for g in SERIES}
GEO = "https://ftp.ncbi.nlm.nih.gov/geo/series/"
INPUTS_GEO = (                             # GEO regenerates these files now and then; the hashes are of 8 October 2026
    ("GSE64495", "30114290d102c8b8f78110f9b5341580614c03b3c933389cbb71d456decb69f9", 275855955),
    ("GSE92767", "51d5bc1991a77a281fec50488bcf9086ed098099143a139170c7299dd8a443f7", 111779264),
    ("GSE51954", "96a150de8cfdd0be69c89745c7f3413f5a44b541f2db5a828abad0ad39160b49", 310614949),
    ("GSE50498", "b59843c381e1e11f15ee57783189d992c40436fd052dcdfd0374ec7e8a61c3f3", 133921383),
    ("GSE66351", "09558aa3726e59554cfd43957a167552c25f0d902131fdd5a34aed630a642817", 265017010),
)


def geo_url(g):
    return f"{GEO}{g[:-3]}nnn/{g}/matrix/{g}_series_matrix.txt.gz"
ADULT = 18
R_MIN, MAE_MAX = 0.7, 10.0
UNITS = ("saliva", "dermis", "epidermis", "muscle", "cortex")

# Gate 1: the tutorial's printed values (Additional file 20): datMethUsedNormalized for its first five probes and four
# samples, and signif(datout$DNAmAge, 2).
TUTORIAL_NORMALISED = {
    "cg00000292": (0.67564060, 0.70119361, 0.67919958, 0.71834583),
    "cg00002426": (0.31489068, 0.31818404, 0.35098754, 0.32295065),
    "cg00003994": (0.06801064, 0.03221467, 0.03634316, 0.05610162),
    "cg00005847": (0.19903216, 0.18919720, 0.19286406, 0.17821503),
    "cg00007981": (0.12023727, 0.12412725, 0.11628779, 0.12483555),
}
TUTORIAL_AGES = (60.00, 43.00, 28.00, 38.00, 8.20, 20.00, 4.80, 38.00, 6.80, 3.60, 31.00, 0.98, 62.00, 24.00, 8.00, 43.00)
GATE2_MEDIAN, GATE2_MAX = 0.01, 0.5
LIMIT = 200
WORKERS = 2

OUTPUTS = (
    "gate1_normalised_max_diff", "gate1_ages_matched", "gate2_samples", "gate2_median_abs_diff", "gate2_max_abs_diff",
    "gates_passed", "saliva", "dermis", "epidermis", "muscle", "cortex", "units_failed", "failed_units",
    "samples_used", "values_imputed", "clock_values_imputed", "test_passed",
)


class Refused(Exception):
    """An input that is not what the rules say it must be."""


# ---------------------------------------------------------------- inputs

def sha256_of(path):
    h, size = hashlib.sha256(), 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def checked(directory, name, sha, size):
    path = os.path.join(directory, name)
    got, n = sha256_of(path)
    if got != sha or n != size:
        raise Refused(f"{path}: sha256 {got} and {n} bytes, not the committed {sha} and {size}")
    return path


def read_gold(path):
    names, values = [], []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            names.append(r["Name"])
            values.append(float(r["goldstandard2"]))
    if len(names) != 21368 or len(set(names)) != len(names):
        raise Refused(f"{path}: {len(names)} probes, not 21,368 distinct ones")
    return names, np.array(values)


def read_clock(path):
    with open(path, newline="", encoding="latin-1") as f:
        rows = list(csv.reader(f))
    if rows[0][:2] != ["CpGmarker", "CoefficientTraining"] or rows[1][0] != "(Intercept)":
        raise Refused(f"{path}: not the predictor's table")
    intercept = float(rows[1][1])
    coef = [(r[0], float(r[1])) for r in rows[2:] if r and r[0]]
    if len(coef) != 353 or not all(c.startswith("cg") for c, _ in coef):
        raise Refused(f"{path}: {len(coef)} CpGs, not 353")
    return intercept, coef


def read_example(path, names):
    with open(path, newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        rows = {r[0]: r[1:] for r in rd}
    missing = [n for n in names if n not in rows]
    if missing:
        raise Refused(f"{path}: {len(missing)} calibration probes absent")
    M = np.array([[float(v) if v not in ("", "NA") else math.nan for v in rows[n]] for n in names])
    return header[1:], M


def read_series(path, names):
    """A GEO series matrix, streamed: the samples' characteristics and their values for the calibration probes
    (NaN where missing or absent)."""
    want = {n: i for i, n in enumerate(names)}
    chars, accession = [], None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("!series_matrix_table_begin"):
                header = [x.strip('"') for x in next(fh).rstrip("\n").split("\t")]
                break
            key = line.split("\t", 1)[0]
            vals = [x.strip().strip('"') for x in line.rstrip("\n").split("\t")[1:]]
            if key == "!Sample_characteristics_ch1":
                chars.append(vals)
            elif key == "!Sample_geo_accession":
                accession = vals
        else:
            raise Refused(f"{path}: no data table")
        samples = header[1:]
        if accession != samples:
            raise Refused(f"{path}: the table's columns are not the samples' accessions")
        M = np.full((len(names), len(samples)), np.nan)
        seen = np.zeros(len(names), dtype=bool)
        for line in fh:
            if line.startswith("!series_matrix_table_end"):
                break
            parts = line.rstrip("\n").split("\t")
            i = want.get(parts[0].strip('"'))
            if i is None:
                continue
            if seen[i]:
                raise Refused(f"{path}: probe {parts[0]} twice")
            seen[i] = True
            for j, v in enumerate(parts[1:]):
                v = v.strip('"')
                if v not in ("", "NA", "null", "NaN"):
                    M[i, j] = float(v)
    per_sample = []
    for j in range(len(samples)):
        d = {}
        for c in chars:
            k, _, v = c[j].partition(":")
            d[k.strip().lower()] = v.strip()
        per_sample.append(d)
    return samples, per_sample, M, int((~seen).sum())


# ---------------------------------------------------------------- the predictor

def anti_trafo(x, adult=20):
    return (1 + adult) * math.exp(x) - 1 if x < 0 else (1 + adult) * x + adult


_WORK = {}


def _age_of(j):
    nb, _ = bmiq.normalise(_WORK["M"][:, j], _WORK["gf"])
    x = _WORK["intercept"] + float(np.dot(_WORK["coefs"], nb[_WORK["clock_idx"]]))
    return anti_trafo(x), nb


def predict(M, gold, gf, intercept, coef, names, keep_normalised=False):
    """Rule 1 for every column of M: (ages, values imputed, clock values imputed, normalised matrix or None)."""
    idx = {n: i for i, n in enumerate(names)}
    clock_idx = np.array([idx[c] for c, _ in coef])
    M = M.copy()
    miss = np.isnan(M)
    imputed = int(miss.sum())
    clock_imputed = int(miss[clock_idx].sum())
    for j in range(M.shape[1]):
        M[miss[:, j], j] = gold[miss[:, j]]
    _WORK.update(M=M, gf=gf, intercept=intercept, coefs=np.array([v for _, v in coef]), clock_idx=clock_idx)
    cols = list(range(M.shape[1]))
    try:
        ctx = multiprocessing.get_context("fork")
        with ctx.Pool(WORKERS) as pool:
            res = pool.map(_age_of, cols, chunksize=1)
    except (OSError, ValueError):
        res = [_age_of(j) for j in cols]
    ages = [a for a, _ in res]
    norm = np.column_stack([nb for _, nb in res]) if keep_normalised else None
    return ages, imputed, clock_imputed, norm


def pearson(x, y):
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    dx, dy = x - x.mean(), y - y.mean()
    return float((dx * dy).sum() / math.sqrt((dx * dx).sum() * (dy * dy).sum()))


def median_abs(a, b):
    return float(np.median(np.abs(np.asarray(a) - np.asarray(b))))


def signif2(x):
    return float(f"{x:.2g}")


# ---------------------------------------------------------------- the units

def age_of(meta, path):
    raw = meta.get("age")
    if raw is None or not re.fullmatch(r"\d+(\.\d+)?", raw):
        raise Refused(f"{path}: a sample's age is {raw!r}")
    return float(raw)


def units_from(series):
    """Rule 2: {unit: (sample ids, ages, column indices, series)}."""
    out = {}
    def pick(g, test):
        samples, metas, _, _ = series[g]
        cols = [j for j, m in enumerate(metas) if test(m) and age_of(m, g) >= ADULT]
        return [samples[j] for j in cols], [age_of(metas[j], g) for j in cols], cols
    out["saliva"] = pick("GSE92767", lambda m: m.get("tissue") == "Saliva") + ("GSE92767",)
    out["dermis"] = pick("GSE51954", lambda m: m.get("tissue") == "dermis") + ("GSE51954",)
    out["epidermis"] = pick("GSE51954", lambda m: m.get("tissue") == "epidermis") + ("GSE51954",)
    out["muscle"] = pick("GSE50498", lambda m: True) + ("GSE50498",)
    out["cortex"] = pick("GSE66351", lambda m: m.get("cell type") == "bulk" and m.get("diagnosis") == "CTRL") + ("GSE66351",)
    return out


def m_to_beta(M):
    with np.errstate(over="ignore"):
        p = np.power(2.0, M)
    return p / (1 + p)


# ---------------------------------------------------------------- the run

def summarise(values):
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > LIMIT:
            raise AssertionError(f"{k}: longer than {LIMIT} characters")
    return out


def run(inputs="inputs", results="results", log=print):
    started = time.monotonic()
    paths = {name: checked(inputs, name, sha, size) for name, sha, size, _ in INPUTS}
    for g, sha, size in INPUTS_GEO:
        paths[g] = checked(inputs, SERIES_FILES[g], sha, size)
    names, gold = read_gold(paths["AdditionalFile22.csv"])
    intercept, coef = read_clock(paths["AdditionalFile23.csv"])
    missing_clock = [c for c, _ in coef if c not in set(names)]
    if missing_clock:
        raise Refused(f"{len(missing_clock)} clock CpGs are not calibration probes")
    gf = bmiq.gold_fit(gold)
    log(f"horvath: gold standard fitted (thresholds {gf['th']}, modes {gf['mod']}) at {time.monotonic() - started:.0f} s")
    values, detail = {}, {"inputs": [{"name": n, "sha256": s, "bytes": b, "url": u} for n, s, b, u in INPUTS] +
                          [{"name": SERIES_FILES[g], "sha256": s, "bytes": b} for g, s, b in INPUTS_GEO]}

    # Gate 1: the tutorial.
    ex_samples, EX = read_example(paths["AdditionalFile26.csv"], names)
    ex_ages, _, _, ex_norm = predict(EX, gold, gf, intercept, coef, names, keep_normalised=True)
    idx = {n: i for i, n in enumerate(names)}
    diffs = [abs(ex_norm[idx[p], j] - v) for p, row in TUTORIAL_NORMALISED.items() for j, v in enumerate(row)]
    matched = sum(1 for a, printed in zip(ex_ages, TUTORIAL_AGES) if signif2(a) == printed)
    values.update({"gate1_normalised_max_diff": float(f"{max(diffs):.3e}"), "gate1_ages_matched": matched})
    gate1 = max(diffs) <= 1e-8 and matched == len(TUTORIAL_AGES)
    detail["gate1"] = {"samples": ex_samples, "ages": ex_ages, "printed_ages": TUTORIAL_AGES, "normalised_diffs": diffs}
    log(f"horvath: gate 1: normalised values within {max(diffs):.2e}, {matched} of 16 ages as printed")

    # The series.
    series = {}
    for g in SERIES:
        samples, metas, M, absent = read_series(paths[g], names)
        if g == "GSE50498":
            if not (np.nanmin(M) < 0 and np.nanmax(M) > 1):
                raise Refused("GSE50498: expected M-values (below 0 and above 1)")
            M = m_to_beta(M)
        elif np.nanmin(M) < -0.05 or np.nanmax(M) > 1.05:
            raise Refused(f"{g}: values outside the beta range")
        series[g] = (samples, metas, M, absent)
        log(f"horvath: {g}: {len(samples)} samples, {absent} calibration probes absent, "
            f"{int(np.isnan(M).sum())} values missing")

    # Gate 2: GSE64495 against Horvath's own ages.
    samples, metas, M, _ = series["GSE64495"]
    printed = [float(m["dna methylation age"]) for m in metas]
    ages, imp, cimp, _ = predict(M, gold, gf, intercept, coef, names)
    d = [abs(a - p) for a, p in zip(ages, printed)]
    med, mx = float(np.median(d)), max(d)
    values.update({"gate2_samples": len(ages), "gate2_median_abs_diff": float(f"{med:.3e}"),
                   "gate2_max_abs_diff": float(f"{mx:.3e}")})
    gate2 = med <= GATE2_MEDIAN and mx <= GATE2_MAX
    values["gates_passed"] = int(gate1) + int(gate2)
    detail["gate2"] = {"samples": samples, "ages": ages, "printed": printed, "values_imputed": imp,
                       "clock_values_imputed": cimp}
    log(f"horvath: gate 2: {len(ages)} samples, median |diff| {med:.2e}, max {mx:.2e}, at {time.monotonic() - started:.0f} s")

    # The units.
    units = units_from(series)
    failed, used, imputed, clock_imputed = [], 0, 0, 0
    detail["units"] = {}
    for u in UNITS:
        ids, chron, cols, g = units[u]
        M = series[g][2][:, cols]
        ages, imp, cimp, _ = predict(M, gold, gf, intercept, coef, names)
        r, mae = pearson(ages, chron), median_abs(ages, chron)
        fails = r < R_MIN or mae > MAE_MAX
        if fails:
            failed.append(u)
        used += len(ids)
        imputed += imp
        clock_imputed += cimp
        values[u] = f"{g} n={len(ids)} r={r:.4f} MAE={mae:.2f} {'fails' if fails else 'holds'}"
        detail["units"][u] = {"series": g, "samples": ids, "age": chron, "dnam_age": ages, "r": r, "mae": mae,
                              "fails": fails, "values_imputed": imp, "clock_values_imputed": cimp,
                              "age_range": [min(chron), max(chron)]}
        log(f"horvath: {u}: {values[u]}")
    values.update({"units_failed": len(failed), "failed_units": ",".join(failed) or "none", "samples_used": used,
                   "values_imputed": imputed, "clock_values_imputed": clock_imputed,
                   "test_passed": int(len(failed) < 3)})
    detail["seconds"] = round(time.monotonic() - started, 1)
    return summarise(values), detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, detail = run(log=lambda line: print(line, file=sys.stderr, flush=True))
    except Refused as e:
        sys.exit(f"horvath/clock.py: refused: {e}")
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join("results", "detail.json"), "w", encoding="ascii") as f:
        json.dump(detail, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
