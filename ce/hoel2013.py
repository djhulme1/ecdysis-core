"""Effective information can peak at a macro scale: Hoel, Albantakis & Tononi (2013), its two spatial examples built
and computed exactly, with every permitted spatial coarse-graining searched.

Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:d6f6cc4d018ab423) is from Hoel, Albantakis
and Tononi, "Quantifying causal emergence shows that macro can beat micro", Proc. Natl Acad. Sci. USA 110(49),
19790-19795 (2013), its Significance statement: "Although in the example systems the macro mechanisms are completely
specified by their underlying micro mechanisms, EI can nevertheless peak at a macro spatiotemporal scale."

The paper, read in PMC's text (PMC3856819). A system's TPM is obtained by perturbing it into all n states with equal
probability; effective information EI is the expected effect information over all states, the Kullback-Leibler
divergence of each state's effect repertoire from the unconstrained effect repertoire, which is the mutual information
between all possible causes and their effects; effectiveness Eff = EI / log2(n), split into a determinism and a
degeneracy coefficient. Macro levels group micro elements into macro elements, "exhaustive and disjunctive over micro
elements", "such that no micro-level information is available at the macro level (the identity of the micro elements
grouped into a macro element is lost)": "[[00, 01, 10] = off, [11] = on] is permitted, whereas the grouping [[00, 01],
[10, 11]] is not"; a macro state is assessed by "a macro perturbation", setting S into each of its micro states with
equal probability and averaging the effects; "Causal analysis was performed across all coarse grains of a system [only
the S_M with maximal EI(S) is shown in the figures]"; CE = EI(S_M) - EI(S_m) = Delta I_Eff + Delta I_Size.

Fig. 2: "a system of four binary elements S_m = {ABCD}. Each micro mechanism is an AND-gate (two inputs) operating over
some intrinsic noise." Its text prints EI(S_m) = 1.15 bits, Eff 0.29; the macro of two elements alpha and beta, AB to
alpha and CD to beta, EI(S_M) = 1.55 bits, CE 0.40, Eff 0.78, Delta I_Eff 0.97, Delta I_Size -0.57, determinism 0.34
and 0.78, degeneracy 0.05 and 0.006, 91% of the gain from determinism and 9% from degeneracy; for state [0001], 0.83
bits of cause and 0.43 of effect information, and for [off, off] 2 and 1.35. The noise is drawn, not printed. Hoel,
Albantakis, Marshall & Tononi 2016 (Neuroscience of Consciousness, niw012) analyse "a four-element system S_m = {ABCD}
... where each micro mechanism operates as an AND gate (with two inputs) under noisy conditions ... In Hoel et al.
(2013), this system showed spatial causal emergence in terms of EI", and their Fig. 6 legend gives the noise ("the
probability of {A} = 1 at t increases from 0.3 to 0.9"); Hanson & Walker's notebook for that system (nb_hoel.ipynb in
elife-asu/pyphi-spectrum, sha256 513c4c6f...) codes it: A and B read C and D, C and D read A and B, each on for certain
when both its inputs are on and with probability 0.3 otherwise. That is the system built here.

Fig. 4: "micro elements A-F are deterministic AND gates connected in a way that ensures high degeneracy (determinism
coef. = 1; degeneracy coef. = 0.6), resulting in Eff(S_m) = 0.4 and EI(S_m) = 2.43 bits. The optimal macro groups the
six micro AND gates into three macro COPY gates (alpha beta gamma) ... Delta I_Eff = 1.79 bits > -Delta I_Size = 1.22
bits ... Eff(S_M) = 1, EI(S_M) = 3 bits ... (CE = 0.57 bits)"; its legend, "The cycle of AND gates is mapped onto a
cycle of COPY gates at the macro level"; Hoel et al. 2016's Fig. 4 maps each macro element's [00, 01, 10] to OFF and
[11] to ON. Built here as pairs AB, CD and EF, both gates of a pair an AND of the previous pair's two outputs (AB of
EF, CD of AB, EF of CD): the wiring under which pairs so mapped are COPY gates in a cycle.

Before these rules were committed two printed values were worked out by hand, to identify the systems the paper only
draws: Fig. 2's macro EI under Hoel et al. 2016's rule (1.55 bits) and Fig. 4's micro EI under the pair wiring (2.43
bits). Nothing else was computed before the commit.

Rules:

1. The systems: Fig. 2 and Fig. 4 as above, elements in alphabetical order, a state a tuple of 0s and 1s ([0001] is
   A = B = C = 0, D = 1). A micro row is the product over elements of each element's probability of its next value,
   in exact fractions.
2. EI of a model with n states under uniform perturbation: (1/n) times the sum over states of D_KL(row || mean row),
   in bits, from exact rows with logarithms to 40 digits; Eff = EI / log2(n); the determinism coefficient is
   1 - (mean entropy of the rows) / log2(n), the degeneracy coefficient 1 - H(mean row) / log2(n), so that
   Eff = determinism - degeneracy; Delta I_Eff = (Eff_M - Eff_m) log2(n_M) and Delta I_Size = Eff_m (log2(n_M) -
   log2(n_m)), whose sum is CE.
3. Spatial coarse-grainings: a partition of the elements into groups, each group one macro element whose state is a
   function of how many of its elements are on (identity lost), with at least two states, the model's states fewer
   than the micro's. A macro state's row is the mean over its micro states of their rows, mapped to macro states.
4. The paper's macro: the pairs (AB and CD in Fig. 2; AB, CD and EF in Fig. 4), each on only when both are on.
5. Conditions: (i) in Fig. 2, EI at the paper's macro exceeds EI at the micro level; (ii) the same in Fig. 4; (iii)
   Fig. 2's micro and macro EI equal the printed 1.15 and 1.55 at two decimals, rounded or cut; (iv) Fig. 4's equal
   2.43 and 3.00. The test passes when all four hold.

Beside the test, not counted: (a) Eff, the determinism and degeneracy coefficients, Delta I_Eff, Delta I_Size and the
share of the gain from determinism, against the printed; (b) Fig. 2's state-dependent cause and effect information for
[0001] and [off, off] (the cause repertoire by Bayes' rule from a uniform prior, the effect repertoire against the
unconstrained one); (c) the search over every permitted coarse-graining: how many there are, the largest EI and the
models that reach it, whether the paper's macro is among them, and how many models beat the micro; (d) the same
search with one-state macro elements allowed.

Controls (controls_passed of controls_total):
 (a) The paper's Fig. 1 systems: two COPY gates (EI 2 bits, Eff 1, determinism 1, degeneracy 0), completely noisy
     (EI 0, determinism 0, degeneracy 0) and completely degenerate (EI 0, determinism 1, degeneracy 1).
 (b) EI two ways, the mean divergence and H(mean row) minus the mean row entropy, in floating point against the
     40-digit value, within 1e-12, on the reported models and every 97th model of each search.
 (c) The number of coarse-grainings against an independent count, the sum over partitions of the elements of the
     product over groups of (Bell(k + 1) - 1) for a group of k elements, less one for the micro level itself, for four
     and six elements (and with Bell(k + 1) for the one-state variant).
 (d) A planted bijection (four elements shifted cyclically): no permitted coarse-graining's EI reaches the micro's 4
     bits.
 (e) The claim's systems as built: Fig. 4's macro TPM is a deterministic cycle of COPY gates (alpha from gamma, beta
     from alpha, gamma from beta) and Fig. 2's macro TPM factorises into alpha's row given beta and beta's given alpha,
     in exact fractions.

Changed after the first trial (seed sha256("imago trial hoel2013 18 October"), whose outputs were seen): control
(b) compared Eff with determinism minus degeneracy within 1e-30 using Python's default decimal context, whose 28
digits leave errors of about 4e-29, so it failed on Fig. 2 and Fig. 4 though the 50-digit values agree; it now does
that arithmetic in the module's 50-digit context, within 1e-40. No condition, value or other control changed.

Writes results/outputs.json (the values a receipt carries) and results/detail.json (every value computed).
Run with: python3 ce/hoel2013.py (the pinned python image, standard library).
"""

import decimal
import itertools
import json
import math
import os
import re
import sys
from fractions import Fraction

DIGITS = 40
CTX = decimal.Context(prec=DIGITS + 10)
P_NOISE = Fraction(3, 10)
PRINTED = {
    "fig2": {"ei_m": "1.15", "ei_M": "1.55", "ce": "0.40", "eff_m": "0.29", "eff_M": "0.78", "dIeff": "0.97",
             "dIsize": "-0.57", "det_m": "0.34", "det_M": "0.78", "deg_m": "0.05", "deg_M": "0.006",
             "share_det": "0.91", "cause_0001": "0.83", "effect_0001": "0.43", "cause_offoff": "2",
             "effect_offoff": "1.35"},
    "fig4": {"ei_m": "2.43", "ei_M": "3", "ce": "0.57", "eff_m": "0.4", "eff_M": "1", "dIeff": "1.79",
             "dIsize": "-1.22", "det_m": "1", "deg_m": "0.6"},
}
TEST = ("Refuted if, in either of the paper's spatial examples built from its text and Hoel et al. 2016 (Fig. 2: A and B "
        "each an AND of C and D, C and D of A and B, on for certain when both inputs are on and with probability 0.3 "
        "otherwise; Fig. 4: six deterministic AND gates in three pairs, each gate taking the previous pair's outputs, in "
        "a cycle), EI under uniform perturbation at the paper's macro level (each pair one element, on only when both "
        "are on) does not exceed EI at the micro level, or the four EI values differ from the printed 1.15, 1.55, 2.43 "
        "and 3 bits at two decimals, rounded or cut.")
OUTPUTS = ("ei_micro_fig2", "ei_macro_fig2", "ce_fig2", "ei_micro_fig4", "ei_macro_fig4", "ce_fig4", "printed_fig2",
           "printed_fig4", "states_fig2", "search_fig2", "search_fig4", "one_state", "conditions_met",
           "conditions_total", "test_passed", "controls_passed", "controls_total")


class Refused(Exception):
    pass


# ---------------------------------------------------------------- rule 1: the systems

def states(n):
    return list(itertools.product((0, 1), repeat=n))


def micro_tpm(n, p_on):
    """p_on(state, i) -> probability (Fraction) that element i is on next. Returns {state: {next: prob}}."""
    out = {}
    for s in states(n):
        ps = [p_on(s, i) for i in range(n)]
        row = {}
        for t in states(n):
            p = Fraction(1)
            for i in range(n):
                p *= ps[i] if t[i] else 1 - ps[i]
                if p == 0:
                    break
            if p:
                row[t] = p
        out[s] = row
    return out


def fig2_tpm(noise=P_NOISE):
    def p_on(s, i):
        a, b = (s[2], s[3]) if i < 2 else (s[0], s[1])
        return Fraction(1) if (a and b) else noise
    return micro_tpm(4, p_on)


def fig4_tpm():
    prev = {0: (4, 5), 1: (4, 5), 2: (0, 1), 3: (0, 1), 4: (2, 3), 5: (2, 3)}

    def p_on(s, i):
        a, b = prev[i]
        return Fraction(1) if (s[a] and s[b]) else Fraction(0)
    return micro_tpm(6, p_on)


def shift_tpm(n=4):
    def p_on(s, i):
        return Fraction(s[(i - 1) % n])
    return micro_tpm(n, p_on)


# ---------------------------------------------------------------- rule 2: EI and its parts

def dlog2(x):
    """log2 of a positive Fraction to DIGITS digits, as a Decimal."""
    num = CTX.divide(decimal.Decimal(x.numerator), decimal.Decimal(x.denominator))
    return CTX.divide(num.ln(CTX), decimal.Decimal(2).ln(CTX))


def exact_measures(rows):
    """rows: list of {col: Fraction}. EI, Eff, determinism and degeneracy (Decimal) by rule 2, two ways for EI."""
    n = len(rows)
    mean = {}
    for r in rows:
        for c, p in r.items():
            mean[c] = mean.get(c, Fraction(0)) + p / n
    ei = decimal.Decimal(0)
    for r in rows:
        for c, p in r.items():
            ei = CTX.add(ei, CTX.multiply(CTX.divide(decimal.Decimal(p.numerator), decimal.Decimal(p.denominator)),
                                          dlog2(p / mean[c])))
    ei = CTX.divide(ei, decimal.Decimal(n))
    h_rows = decimal.Decimal(0)
    for r in rows:
        for p in r.values():
            h_rows = CTX.subtract(h_rows, CTX.multiply(CTX.divide(decimal.Decimal(p.numerator),
                                                                  decimal.Decimal(p.denominator)), dlog2(p)))
    h_rows = CTX.divide(h_rows, decimal.Decimal(n))
    h_mean = decimal.Decimal(0)
    for p in mean.values():
        h_mean = CTX.subtract(h_mean, CTX.multiply(CTX.divide(decimal.Decimal(p.numerator),
                                                              decimal.Decimal(p.denominator)), dlog2(p)))
    logn = dlog2(Fraction(n))
    if logn == 0:                                       # one state: nothing to perturb between
        zero = decimal.Decimal(0)
        return {"ei": ei, "ei2": CTX.subtract(h_mean, h_rows), "eff": zero, "det": zero, "deg": zero, "n": n,
                "log2n": logn}
    return {"ei": ei, "ei2": CTX.subtract(h_mean, h_rows), "eff": CTX.divide(ei, logn),
            "det": CTX.subtract(decimal.Decimal(1), CTX.divide(h_rows, logn)),
            "deg": CTX.subtract(decimal.Decimal(1), CTX.divide(h_mean, logn)), "n": n, "log2n": logn}


def float_ei(rows):
    """rows: list of lists of floats over the same columns. EI in bits, two ways."""
    n = len(rows)
    k = len(rows[0])
    mean = [sum(r[j] for r in rows) / n for j in range(k)]
    ei = 0.0
    hr = 0.0
    for r in rows:
        for j, p in enumerate(r):
            if p > 0:
                ei += p * math.log2(p / mean[j])
                hr -= p * math.log2(p)
    hm = -sum(p * math.log2(p) for p in mean if p > 0)
    return ei / n, hm - hr / n


# ---------------------------------------------------------------- rule 3: coarse-grainings

def set_partitions(items):
    items = list(items)
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for part in set_partitions(rest):
        yield [[first]] + part
        for i in range(len(part)):
            yield part[:i] + [[first] + part[i]] + part[i + 1:]


def class_maps(k, min_classes=2):
    """Every partition of the counts 0..k into classes, as a tuple: count -> class label (restricted growth)."""
    out = []

    def rec(prefix, top):
        if len(prefix) == k + 1:
            if top + 1 >= min_classes:
                out.append(tuple(prefix))
            return
        for lab in range(top + 2):
            rec(prefix + [lab], max(top, lab))
    rec([0], 0)
    return out


def models(n, min_classes=2):
    """Every permitted coarse-graining of n elements: a list of groups, each (elements, class map); the micro level
    itself (every element alone, two states) is left out, as is any model with no fewer states."""
    out = []
    for part in set_partitions(range(n)):
        part = sorted(tuple(sorted(g)) for g in part)
        options = [class_maps(len(g), min_classes) for g in part]
        for combo in itertools.product(*options):
            size = 1
            for cm in combo:
                size *= max(cm) + 1
            if size >= 2 ** n:
                continue
            out.append(tuple(zip(part, combo)))
    return out


def macro_index(model):
    """A function from a micro state to its macro state (a tuple of class labels), and the macro states."""
    radices = [max(cm) + 1 for _, cm in model]

    def f(s):
        return tuple(cm[sum(s[i] for i in g)] for g, cm in model)
    return f, list(itertools.product(*[range(r) for r in radices]))


def macro_rows(tpm, model):
    """Exact macro rows by rule 3: {macro state: {macro next: Fraction}}."""
    f, macro = macro_index(model)
    members = {m: [] for m in macro}
    for s in tpm:
        members[f(s)].append(s)
    rows = {}
    for m in macro:
        row = {}
        w = Fraction(1, len(members[m]))
        for s in members[m]:
            for t, p in tpm[s].items():
                mt = f(t)
                row[mt] = row.get(mt, Fraction(0)) + w * p
        rows[m] = row
    return rows


def float_macro_ei(tpm_float, micro_list, model):
    """EI of a coarse-graining in floating point (the search): tpm_float maps a micro index to [(next index, p)]."""
    f, macro = macro_index(model)
    pos = {m: j for j, m in enumerate(macro)}
    idx = [pos[f(s)] for s in micro_list]
    counts = [0] * len(macro)
    for j in idx:
        counts[j] += 1
    rows = [[0.0] * len(macro) for _ in macro]
    for si, j in enumerate(idx):
        w = 1.0 / counts[j]
        r = rows[j]
        for ti, p in tpm_float[si]:
            r[idx[ti]] += w * p
    return float_ei(rows)


def paper_macro(pairs):
    return tuple((g, (0, 0, 1)) for g in pairs)


def search(tpm, n, min_classes=2, sample=97):
    micro_list = list(tpm)
    pos = {s: i for i, s in enumerate(micro_list)}
    tpm_float = [[(pos[t], float(p)) for t, p in tpm[s].items()] for s in micro_list]
    ms = models(n, min_classes)
    eis = []
    checks = []
    for k, m in enumerate(ms):
        a, b = float_macro_ei(tpm_float, micro_list, m)
        eis.append(a)
        if k % sample == 0:
            checks.append((m, a, b))
    return ms, eis, checks


# ---------------------------------------------------------------- the analysis

def describe(model):
    names = "ABCDEFGH"
    return "+".join("".join(names[i] for i in g) + ":" + "".join(str(c) for c in cm) for g, cm in model)


def two_decimals(x, printed):
    """Does the Decimal x equal the printed value at its decimals, rounded or cut?"""
    p = decimal.Decimal(printed)
    q = decimal.Decimal(1).scaleb(p.as_tuple().exponent)
    return x.quantize(q, rounding=decimal.ROUND_HALF_UP) == p or x.quantize(q, rounding=decimal.ROUND_DOWN) == p


def state_info(tpm_rows, s0):
    """Cause and effect information (bits, Decimal) of state s0 in a model {state: {next: Fraction}}."""
    n = len(tpm_rows)
    col = {s: r.get(s0, Fraction(0)) for s, r in tpm_rows.items()}
    tot = sum(col.values())
    cause = decimal.Decimal(0)
    for s, p in col.items():
        if p:
            q = p / tot
            cause = CTX.add(cause, CTX.multiply(CTX.divide(decimal.Decimal(q.numerator), decimal.Decimal(q.denominator)),
                                                dlog2(q * n)))
    mean = {}
    for r in tpm_rows.values():
        for c, p in r.items():
            mean[c] = mean.get(c, Fraction(0)) + p / n
    eff = decimal.Decimal(0)
    for c, p in tpm_rows[s0].items():
        eff = CTX.add(eff, CTX.multiply(CTX.divide(decimal.Decimal(p.numerator), decimal.Decimal(p.denominator)),
                                        dlog2(p / mean[c])))
    return cause, eff


def analyse(tpm, n, pairs):
    rows_m = list(tpm.values())
    mm = exact_measures(rows_m)
    pm = paper_macro(pairs)
    mrows = macro_rows(tpm, pm)
    mM = exact_measures(list(mrows.values()))
    ce = CTX.subtract(mM["ei"], mm["ei"])
    d_eff = CTX.multiply(CTX.subtract(mM["eff"], mm["eff"]), mM["log2n"])
    d_size = CTX.multiply(mm["eff"], CTX.subtract(mM["log2n"], mm["log2n"]))
    gain = CTX.subtract(mM["eff"], mm["eff"])
    share_det = CTX.divide(CTX.subtract(mM["det"], mm["det"]), gain) if gain else decimal.Decimal(0)
    return {"micro": mm, "macro": mM, "ce": ce, "dIeff": d_eff, "dIsize": d_size, "share_det": share_det,
            "macro_rows": mrows, "paper_model": pm}


def fig1_controls():
    copy = micro_tpm(2, lambda s, i: Fraction(s[1 - i]))
    noisy = {s: {t: Fraction(1, 4) for t in states(2)} for s in states(2)}
    degen = {s: {(1, 1): Fraction(1)} for s in states(2)}
    a = exact_measures(list(copy.values()))
    b = exact_measures(list(noisy.values()))
    c = exact_measures(list(degen.values()))
    one, zero = decimal.Decimal(1), decimal.Decimal(0)

    def near(x, y):
        return abs(x - y) < decimal.Decimal("1e-30")
    return (near(a["ei"], decimal.Decimal(2)) and near(a["eff"], one) and near(a["det"], one) and near(a["deg"], zero)
            and near(b["ei"], zero) and near(b["det"], zero) and near(b["deg"], zero)
            and near(c["ei"], zero) and near(c["det"], one) and near(c["deg"], one))


def bell(m):
    row = [1]
    for _ in range(m):
        nxt = [row[-1]]
        for v in row:
            nxt.append(nxt[-1] + v)
        row = nxt
    return row[0]


def count_models(n, one_state=False):
    total = 0
    for part in set_partitions(range(n)):
        prod = 1
        for g in part:
            prod *= bell(len(g) + 1) - (0 if one_state else 1)
        total += prod
    return total - 1


def assess():
    t2, t4 = fig2_tpm(), fig4_tpm()
    a2 = analyse(t2, 4, ((0, 1), (2, 3)))
    a4 = analyse(t4, 6, ((0, 1), (2, 3), (4, 5)))
    cond = {
        "(i) Fig. 2: EI at the paper's macro exceeds the micro's": a2["macro"]["ei"] > a2["micro"]["ei"],
        "(ii) Fig. 4: EI at the paper's macro exceeds the micro's": a4["macro"]["ei"] > a4["micro"]["ei"],
        "(iii) Fig. 2's EI are the printed 1.15 and 1.55 bits": (two_decimals(a2["micro"]["ei"], "1.15")
                                                               and two_decimals(a2["macro"]["ei"], "1.55")),
        "(iv) Fig. 4's EI are the printed 2.43 and 3 bits": (two_decimals(a4["micro"]["ei"], "2.43")
                                                           and two_decimals(a4["macro"]["ei"], "3.00")),
    }

    # beside (b): state-dependent values, Fig. 2
    c_m, e_m = state_info(t2, (0, 0, 0, 1))
    c_M, e_M = state_info(a2["macro_rows"], (0, 0))

    # beside (c) and (d): the searches
    found = {}
    for name, tpm, n, a in (("fig2", t2, 4, a2), ("fig4", t4, 6, a4)):
        for one in (False, True):
            ms, eis, checks = search(tpm, n, 1 if one else 2)
            best = max(eis)
            top = [describe(m) for m, e in zip(ms, eis) if e >= best - 1e-12]
            paper_e = float(a["macro"]["ei"])
            micro_e = float(a["micro"]["ei"])
            found[(name, one)] = {"models": len(ms), "best": best, "top": top,
                                  "paper_is_best": describe(a["paper_model"]) in top,
                                  "beat_micro": sum(1 for e in eis if e > micro_e + 1e-12), "paper_ei": paper_e,
                                  "rank_paper": 1 + sum(1 for e in eis if e > paper_e + 1e-12), "checks": checks}

    # controls
    ctl = {}
    ctl["Fig. 1's systems: two COPY gates EI 2, Eff 1, determinism 1, degeneracy 0; noisy and degenerate EI 0"] = (
        fig1_controls())
    ok = True
    reported = [(t2, None), (t4, None), (t2, a2["paper_model"]), (t4, a4["paper_model"])]
    for tpm, m in reported:
        rows = list(tpm.values()) if m is None else list(macro_rows(tpm, m).values())
        ex = exact_measures(rows)
        cols = sorted({c for r in rows for c in r})
        fl = float_ei([[float(r.get(c, 0)) for c in cols] for r in rows])
        ok = ok and abs(CTX.subtract(ex["ei"], ex["ei2"])) < decimal.Decimal("1e-40")
        ok = ok and abs(fl[0] - float(ex["ei"])) < 1e-12 and abs(fl[1] - float(ex["ei"])) < 1e-12
        ok = ok and abs(CTX.subtract(ex["eff"], CTX.subtract(ex["det"], ex["deg"]))) < decimal.Decimal("1e-40")
    for (name, one), v in found.items():
        tpm = t2 if name == "fig2" else t4
        for m, a, b in v["checks"]:
            ex = exact_measures(list(macro_rows(tpm, m).values()))
            ok = ok and abs(a - float(ex["ei"])) < 1e-12 and abs(b - float(ex["ei"])) < 1e-12
    ctl["EI two ways, floating point against 40 digits, on the reported models and every 97th model searched"] = ok
    ctl["the number of coarse-grainings against an independent count, for 4 and 6 elements, both variants"] = (
        found[("fig2", False)]["models"] == count_models(4) and found[("fig4", False)]["models"] == count_models(6)
        and found[("fig2", True)]["models"] == count_models(4, True)
        and found[("fig4", True)]["models"] == count_models(6, True))
    ms, eis, _ = search(shift_tpm(4), 4, 2)
    ctl["a planted bijection: no permitted coarse-graining reaches the micro level's 4 bits"] = (
        max(eis) < 4 - 1e-9 and abs(float(exact_measures(list(shift_tpm(4).values()))["ei"]) - 4) < 1e-12)
    m4 = a4["macro_rows"]
    cyc = all(len(r) == 1 and list(r.values())[0] == 1 for r in m4.values()) and all(
        list(r)[0] == (s[2], s[0], s[1]) for s, r in m4.items())
    m2 = a2["macro_rows"]
    fac = True
    for (al, be), r in m2.items():
        pa = {x: sum(p for (y, z), p in r.items() if y == x) for x in (0, 1)}
        pb = {x: sum(p for (y, z), p in r.items() if z == x) for x in (0, 1)}
        fac = fac and all(r.get((x, y), Fraction(0)) == pa[x] * pb[y] for x in (0, 1) for y in (0, 1))

    def p_alpha(al, be):
        return sum(p for (y, z), p in m2[(al, be)].items() if y == 1)

    def p_beta(al, be):
        return sum(p for (y, z), p in m2[(al, be)].items() if z == 1)
    fac = fac and all(p_alpha(0, be) == p_alpha(1, be) for be in (0, 1))      # alpha reads beta only
    fac = fac and all(p_beta(al, 0) == p_beta(al, 1) for al in (0, 1))        # beta reads alpha only
    ctl["the systems as built: Fig. 4's macro a deterministic COPY cycle, Fig. 2's macro two factorised channels"] = (
        cyc and fac)

    def f2(x):
        return f"{float(x):.4f}"

    pr = PRINTED
    s2, s4 = found[("fig2", False)], found[("fig4", False)]
    o2, o4 = found[("fig2", True)], found[("fig4", True)]
    values = {
        "ei_micro_fig2": float(a2["micro"]["ei"]), "ei_macro_fig2": float(a2["macro"]["ei"]),
        "ce_fig2": float(a2["ce"]), "ei_micro_fig4": float(a4["micro"]["ei"]),
        "ei_macro_fig4": float(a4["macro"]["ei"]), "ce_fig4": float(a4["ce"]),
        "printed_fig2": (f"Eff {f2(a2['micro']['eff'])}>{f2(a2['macro']['eff'])} [0.29 0.78] det "
                         f"{f2(a2['micro']['det'])}>{f2(a2['macro']['det'])} [0.34 0.78] deg {f2(a2['micro']['deg'])}"
                         f">{f2(a2['macro']['deg'])} [0.05 0.006] dIeff {f2(a2['dIeff'])} dIsize {f2(a2['dIsize'])} "
                         f"[0.97 -0.57] det share {f2(a2['share_det'])} [0.91]"),
        "printed_fig4": (f"Eff {f2(a4['micro']['eff'])}>{f2(a4['macro']['eff'])} [0.4 1] det {f2(a4['micro']['det'])} "
                         f"deg {f2(a4['micro']['deg'])} [1 0.6] dIeff {f2(a4['dIeff'])} dIsize {f2(a4['dIsize'])} "
                         f"[1.79 -1.22] CE {f2(a4['ce'])} [0.57]"),
        "states_fig2": (f"[0001] cause {f2(c_m)} effect {f2(e_m)} [0.83 0.43]; [off,off] cause {f2(c_M)} effect "
                        f"{f2(e_M)} [2 1.35]"),
        "search_fig2": (f"{s2['models']} models, best EI {s2['best']:.4f} by {len(s2['top'])} ({s2['top'][0]}), paper's "
                        f"best {int(s2['paper_is_best'])} rank {s2['rank_paper']}, {s2['beat_micro']} beat micro"),
        "search_fig4": (f"{s4['models']} models, best EI {s4['best']:.4f} by {len(s4['top'])} ({s4['top'][0]}), paper's "
                        f"best {int(s4['paper_is_best'])} rank {s4['rank_paper']}, {s4['beat_micro']} beat micro"),
        "one_state": (f"fig2 {o2['models']} models best {o2['best']:.4f} ({o2['top'][0]}) beat {o2['beat_micro']}; "
                      f"fig4 {o4['models']} best {o4['best']:.4f} ({o4['top'][0]}) beat {o4['beat_micro']}"),
        "conditions_met": sum(cond.values()), "conditions_total": len(cond), "test_passed": int(all(cond.values())),
        "controls_passed": sum(ctl.values()), "controls_total": len(ctl),
    }
    out = {k: values[k] for k in OUTPUTS}
    for k, v in out.items():
        if isinstance(v, str) and len(v) > 200:
            raise AssertionError(f"{k}: longer than 200 characters ({len(v)}): {v}")
        if isinstance(v, float) and not math.isfinite(v):
            raise AssertionError(f"{k}: not finite")

    def meas(x):
        return {k: (str(v) if isinstance(v, decimal.Decimal) else v) for k, v in x.items()}

    detail = {"test": TEST, "conditions": cond, "controls": ctl, "printed": PRINTED,
              "fig2": {"micro": meas(a2["micro"]), "macro": meas(a2["macro"]), "ce": str(a2["ce"]),
                       "dIeff": str(a2["dIeff"]), "dIsize": str(a2["dIsize"]), "share_det": str(a2["share_det"]),
                       "states": {"0001": [str(c_m), str(e_m)], "off_off": [str(c_M), str(e_M)]},
                       "macro_tpm": {"".join(map(str, k)): {"".join(map(str, kk)): str(vv) for kk, vv in v.items()}
                                     for k, v in a2["macro_rows"].items()}},
              "fig4": {"micro": meas(a4["micro"]), "macro": meas(a4["macro"]), "ce": str(a4["ce"]),
                       "dIeff": str(a4["dIeff"]), "dIsize": str(a4["dIsize"])},
              "search": {f"{k[0]}{'_one_state' if k[1] else ''}": {kk: vv for kk, vv in v.items() if kk != "checks"}
                         for k, v in found.items()}}
    return out, detail


# ---------------------------------------------------------------- the run

def run(seed, results="results"):
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        raise Refused("the seed must be 64 hex characters")
    out, detail = assess()
    os.makedirs(results, exist_ok=True)
    with open(os.path.join(results, "outputs.json"), "w", encoding="ascii") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(results, "detail.json"), "w", encoding="utf-8") as fh:
        json.dump(detail, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    return out, detail


def main():
    seed = os.environ.get("ECDYSIS_SEED", "")
    if not re.fullmatch(r"[0-9a-f]{64}", seed):
        sys.exit("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    try:
        out, _ = run(seed)
    except Refused as e:
        sys.exit(f"hoel2013: refused: {e}")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
