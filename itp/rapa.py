#!/usr/bin/env python3
"""Rapamycin and lifespan in the ITP's 2005 cohort, recomputed from the per-mouse data.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test is from Harrison et al.,
"Rapamycin fed late in life extends lifespan in genetically heterogeneous mice", Nature 460 (2009):
"On the basis of age at 90% mortality, rapamycin led to an increase of 14% for females and 9% for
males."

The NIA Interventions Testing Program released the cohort's per-mouse lifespans on the Mouse
Phenome Database (project ITP2005) as one workbook. This script reads it with the standard library
only (the workbook's XML is parsed as data), keeps the control and rapamycin groups as assigned,
pooled over the three sites, and computes by sex:

- Kaplan-Meier survival, with removed mice censored at their removal age; the age at 90% mortality
  is the first age at which survival is at or below 0.10, and the median the first at or below 0.5;
- the gain at 90% mortality and at the median, rapamycin over control;
- a log-rank test (pooled over sites) and a Wang-Allison test (the share of mice still alive at the
  sex's joint 90th percentile of deaths, removed mice excluded; Pearson chi-square, one degree of
  freedom, no continuity correction);
- a bootstrap interval for each gain at 90% mortality, resampling mice within each group with draws
  from ECDYSIS_SEED (SHA-256 in counter mode), the only randomness used.

test_passed applies the registered test: the gain at 90% mortality is at least half the reported
one, 7% for females and 4.5% for males.

Writes results/outputs.json.
"""

import hashlib
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

INPUT = ("itp_c2005_lifespan.xlsx", "0b17afe4bf172d1fb08dbe382f8f6abdddd2b6172ae5d1cf4b5678415cc1c019")
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
BOOTSTRAP = 1000


class Stream:
    """As in mm/check.py: SHA-256(seed || "|" || label || "|" || counter), 8 bytes at a time."""

    def __init__(self, seed_hex, label):
        self.seed, self.label, self.counter, self.buf = bytes.fromhex(seed_hex), label.encode("ascii"), 0, b""

    def u64(self):
        if len(self.buf) < 8:
            self.buf += hashlib.sha256(self.seed + b"|" + self.label + b"|" + str(self.counter).encode("ascii")).digest()
            self.counter += 1
        x, self.buf = int.from_bytes(self.buf[:8], "big"), self.buf[8:]
        return x

    def below(self, n):
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            x = self.u64()
            if x < limit:
                return x % n


def read_rows(path, sha256):
    """The workbook's first sheet as a list of dicts keyed by the header row (inline strings and numbers)."""
    with open(path, "rb") as f:
        data = f.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        sys.exit(f"{path}: sha256 {got}, not the committed {sha256}")
    import io
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("x:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["x"])))
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.find("x:sheetData", NS).findall("x:row", NS):
        cells = {}
        for c in row.findall("x:c", NS):
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            kind = c.get("t")
            if kind == "inlineStr":
                value = "".join(t.text or "" for t in c.iter("{%s}t" % NS["x"]))
            elif kind == "s":
                value = shared[int(c.find("x:v", NS).text)]
            else:
                v = c.find("x:v", NS)
                value = v.text if v is not None else None
            cells[col] = value
        rows.append(cells)
    header = rows[0]
    return [{header[k]: r.get(k) for k in header} for r in rows[1:]]


def km_quantile(mice, q):
    """The first age at which Kaplan-Meier survival is at or below 1 - q (q = 0.5: median, 0.9: 90% mortality)."""
    data = sorted(mice)
    at_risk, s, i = len(data), 1.0, 0
    while i < len(data):
        t = data[i][0]
        deaths = removed = 0
        while i < len(data) and data[i][0] == t:
            if data[i][1]:
                deaths += 1
            else:
                removed += 1
            i += 1
        if deaths:
            s *= 1 - deaths / at_risk
            if s <= 1 - q + 1e-12:
                return t
        at_risk -= deaths + removed
    return None


def logrank_p(a, b):
    """Two-sided log-rank p-value for groups a and b, lists of (age, died)."""
    times = sorted({t for t, d in a + b if d})
    o_minus_e = var = 0.0
    for t in times:
        na = sum(1 for x, _ in a if x >= t)
        nb = sum(1 for x, _ in b if x >= t)
        da = sum(1 for x, d in a if x == t and d)
        db = sum(1 for x, d in b if x == t and d)
        n, d = na + nb, da + db
        if n < 2:
            continue
        o_minus_e += da - d * na / n
        var += d * (na / n) * (1 - na / n) * (n - d) / (n - 1)
    chi2 = o_minus_e * o_minus_e / var
    return math.erfc(math.sqrt(chi2 / 2))


def wang_allison_p(a, b):
    """Share alive beyond the joint 90th percentile of deaths (removed mice excluded), Pearson chi-square, 1 df."""
    deaths = sorted(t for t, d in a + b if d)
    cut = deaths[math.ceil(0.9 * len(deaths)) - 1]
    rows = []
    for g in (a, b):
        kept = [t for t, d in g if d]
        alive = sum(1 for t in kept if t > cut)
        rows.append((alive, len(kept) - alive))
    total = sum(sum(r) for r in rows)
    cols = [rows[0][0] + rows[1][0], rows[0][1] + rows[1][1]]
    chi2 = 0.0
    for r in rows:
        for j in range(2):
            expected = sum(r) * cols[j] / total
            chi2 += (r[j] - expected) ** 2 / expected
    return math.erfc(math.sqrt(chi2 / 2)), rows


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    rows = read_rows(os.path.join("inputs", INPUT[0]), INPUT[1])
    groups = {}
    for r in rows:
        if r["group"] in ("Control", "Rapa"):
            groups.setdefault((r["group"], r["sex"]), []).append((int(float(r["age"])), int(float(r["dead"])) == 1))
    out, stream = {}, Stream(seed, "itp/bootstrap")
    for sex, name in (("f", "f"), ("m", "m")):
        ctl, rap = groups[("Control", sex)], groups[("Rapa", sex)]
        q90c, q90r = km_quantile(ctl, 0.9), km_quantile(rap, 0.9)
        medc, medr = km_quantile(ctl, 0.5), km_quantile(rap, 0.5)
        out[f"n_{name}_control"] = len(ctl)
        out[f"n_{name}_rapa"] = len(rap)
        out[f"q90_{name}_control"] = q90c
        out[f"q90_{name}_rapa"] = q90r
        out[f"inc90_{name}"] = round(q90r / q90c - 1, 6)
        out[f"median_inc_{name}"] = round(medr / medc - 1, 6)
        out[f"logrank_p_{name}"] = float(f"{logrank_p(rap, ctl):.3e}")
        out[f"wa_p_{name}"] = float(f"{wang_allison_p(rap, ctl)[0]:.3e}")
        boots = []
        for _ in range(BOOTSTRAP):
            bc = [ctl[stream.below(len(ctl))] for _ in ctl]
            br = [rap[stream.below(len(rap))] for _ in rap]
            qr, qc = km_quantile(br, 0.9), km_quantile(bc, 0.9)
            if qr is not None and qc is not None:   # a resample whose survival never reaches 0.10 is skipped
                boots.append(qr / qc - 1)
        boots.sort()
        out[f"boot_inc90_{name}_low"] = round(boots[int(0.025 * len(boots))], 6)
    out["censored"] = sum(1 for g in groups.values() for _, d in g if not d)
    out["test_passed"] = 1 if out["inc90_f"] >= 0.07 and out["inc90_m"] >= 0.045 else 0
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "outputs.json"), "w", encoding="ascii") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
