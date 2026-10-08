/* Exact-to-double transport (earth mover's) costs for iit/check.py, and the enumeration of every pair of
 * cause-effect structures for one cut. Built at run time with gcc; called through ctypes.
 *
 * transport(): the minimum cost of moving supplies a[0..n1) to demands b[0..n2) with unit costs C (row-major
 * n1 x n2), by successive shortest paths with Dijkstra and node potentials. Supplies and demands must balance;
 * nothing is rounded to integers (pyemd, which PyPhi uses, scales masses and costs to parts per million first).
 *
 * enumerate_cut(): every original structure (one concept per mechanism, from each mechanism's tied candidates)
 * against every partitioned one, the distance PyPhi's ces_distance defines: concepts present in both (same
 * canonical id, PyPhi's emd_eq) drop out; if one side has none left, the other side's phi times its distance to
 * its own null concept; otherwise the extended EMD, U1's phi to U2's phi or the null concept (which takes the
 * difference). Each distance is rounded to millionths and marked in a bitmap; min, max and counts come back.
 */
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define MAXN 72
#define EPS 1e-13

static double tr_solve(int n1, int n2, const double *a, const double *b, const double *C) {
    /* nodes: 0 = source, 1..n1 supplies, n1+1..n1+n2 demands, n1+n2+1 = sink */
    static double f[MAXN][MAXN];
    double caps[MAXN], capt[MAXN], pot[2 * MAXN + 2], dist[2 * MAXN + 2];
    int prev[2 * MAXN + 2], done[2 * MAXN + 2];
    int V = n1 + n2 + 2, S = 0, T = n1 + n2 + 1;
    double total = 0, cost = 0, scale = 0;
    for (int i = 0; i < n1; i++) { caps[i] = a[i]; total += a[i]; if (a[i] > scale) scale = a[i]; }
    for (int j = 0; j < n2; j++) { capt[j] = b[j]; if (b[j] > scale) scale = b[j]; }
    for (int i = 0; i < n1; i++) for (int j = 0; j < n2; j++) f[i][j] = 0;
    for (int v = 0; v < V; v++) pot[v] = 0;
    double tol = EPS * (scale > 1 ? scale : 1);
    double left = total;
    int guard = 0;
    while (left > tol && guard++ < 100000) {
        for (int v = 0; v < V; v++) { dist[v] = INFINITY; prev[v] = -1; done[v] = 0; }
        dist[S] = 0;
        for (;;) {
            int u = -1; double best = INFINITY;
            for (int v = 0; v < V; v++) if (!done[v] && dist[v] < best) { best = dist[v]; u = v; }
            if (u < 0) break;
            done[u] = 1;
            if (u == S) {
                for (int i = 0; i < n1; i++) if (caps[i] > tol) {
                    double d = dist[S] + pot[S] - pot[1 + i];
                    if (d < dist[1 + i]) { dist[1 + i] = d; prev[1 + i] = S; }
                }
            } else if (u <= n1) {
                int i = u - 1;
                for (int j = 0; j < n2; j++) {
                    double d = dist[u] + C[i * n2 + j] + pot[u] - pot[1 + n1 + j];
                    if (d < dist[1 + n1 + j] - 1e-15) { dist[1 + n1 + j] = d; prev[1 + n1 + j] = u; }
                }
            } else if (u < T) {
                int j = u - 1 - n1;
                for (int i = 0; i < n1; i++) if (f[i][j] > tol) {
                    double d = dist[u] - C[i * n2 + j] + pot[u] - pot[1 + i];
                    if (d < dist[1 + i] - 1e-15) { dist[1 + i] = d; prev[1 + i] = u; }
                }
                if (capt[j] > tol) {
                    double d = dist[u] + pot[u] - pot[T];
                    if (d < dist[T]) { dist[T] = d; prev[T] = u; }
                }
            }
        }
        if (prev[T] < 0) break;
        for (int v = 0; v < V; v++) if (dist[v] < INFINITY) pot[v] += dist[v];
        /* bottleneck */
        double push = left;
        for (int v = T; v != S; v = prev[v]) {
            int u = prev[v];
            if (u == S) { if (caps[v - 1] < push) push = caps[v - 1]; }
            else if (v == T) { if (capt[u - 1 - n1] < push) push = capt[u - 1 - n1]; }
            else if (u > n1) { int j = u - 1 - n1, i = v - 1; if (f[i][j] < push) push = f[i][j]; }
        }
        for (int v = T; v != S; v = prev[v]) {
            int u = prev[v];
            if (u == S) caps[v - 1] -= push;
            else if (v == T) capt[u - 1 - n1] -= push;
            else if (u <= n1) { int i = u - 1, j = v - 1 - n1; f[i][j] += push; cost += push * C[i * n2 + j]; }
            else { int j = u - 1 - n1, i = v - 1; f[i][j] -= push; cost -= push * C[i * n2 + j]; }
        }
        left -= push;
    }
    return cost;
}

double transport(int n1, int n2, const double *a, const double *b, const double *C) {
    if (n1 > MAXN || n2 > MAXN) return NAN;
    return tr_solve(n1, n2, a, b, C);
}

/* pyemd 0.5.1's emd() (FastEMD's emd_hat_gd_metric for doubles), which PyPhi 1.2 calls: mass common to a bin
 * stays at no cost, the rest is scaled so that the larger total is a million and rounded to integers, the costs so
 * that the largest is a million, and the integer problem is solved with any excess absorbed at no cost; the result
 * is scaled back, plus the difference of the totals times the largest cost. P and Q over the same n bins. */
static double emd_pyemd_sq(int n, const double *P, const double *Q, const double *C) {
    double sumP = 0, sumQ = 0, maxC = C[0];
    for (int i = 0; i < n; i++) {
        sumP += P[i]; sumQ += Q[i];
        for (int j = 0; j < n; j++) if (C[i * n + j] > maxC) maxC = C[i * n + j];
    }
    double minS = sumP < sumQ ? sumP : sumQ, maxS = sumP < sumQ ? sumQ : sumP;
    if (maxS <= 0 || maxC <= 0) return 0;
    double F = 1000000.0 / maxS, G = 1000000.0 / maxC;
    long long ip[MAXN], iq[MAXN];
    for (int i = 0; i < n; i++) {
        double p = P[i], q = Q[i];
        if (p < q) { q -= p; p = 0; } else { p -= q; q = 0; }
        ip[i] = (long long) floor(p * F + 0.5);
        iq[i] = (long long) floor(q * F + 0.5);
    }
    int si[MAXN], sj[MAXN], ns = 0, nt = 0;
    long long tp = 0, tq = 0;
    for (int i = 0; i < n; i++) { if (ip[i] != 0) { si[ns++] = i; tp += ip[i]; } if (iq[i] != 0) { sj[nt++] = i; tq += iq[i]; } }
    double d = 0;
    if (ns > 0 && nt > 0) {
        static double a[MAXN], b[MAXN + 1], Cm[MAXN * (MAXN + 1)];
        int n1, n2;
        if (tp >= tq) {
            n1 = ns; n2 = nt;
            for (int s = 0; s < ns; s++) a[s] = (double) ip[si[s]];
            for (int t = 0; t < nt; t++) b[t] = (double) iq[sj[t]];
            for (int s = 0; s < ns; s++) for (int t = 0; t < nt; t++)
                Cm[s * (nt + 1) + t] = floor(C[si[s] * n + sj[t]] * G + 0.5);
        } else {
            n1 = nt; n2 = ns;
            for (int s = 0; s < nt; s++) a[s] = (double) iq[sj[s]];
            for (int t = 0; t < ns; t++) b[t] = (double) ip[si[t]];
            for (int s = 0; s < nt; s++) for (int t = 0; t < ns; t++)
                Cm[s * (ns + 1) + t] = floor(C[si[t] * n + sj[s]] * G + 0.5);
        }
        long long ex = (tp >= tq ? tp - tq : tq - tp);
        b[n2] = (double) ex;
        for (int s = 0; s < n1; s++) Cm[s * (n2 + 1) + n2] = 0;
        d = tr_solve(n1, n2 + 1, a, b, Cm);
    }
    return d / F / G + (maxS - minS) * maxC;
}

double emd_pyemd(int n, const double *P, const double *Q, const double *C) {
    if (n > MAXN) return NAN;
    return emd_pyemd_sq(n, P, Q, C);
}

/* K mechanisms; for mechanism k, original candidates o_ids[o_off[k] .. o_off[k+1]) (none: the mechanism has no
 * concept) and partitioned candidates n_ids[n_off[k] .. n_off[k+1]). Concept ids index phi1/dnull1 (original
 * side) and phi2/dnull2 (partitioned side); D is the original-by-partitioned distance matrix (nd2 columns).
 * Canonical ids: canon1[id] and canon2[id]; equal canon means emd_eq. bitmap has nbits bits for millionths. */
int enumerate_cut(int K, const int *o_off, const int *o_ids, const int *n_off, const int *n_ids,
                  const double *phi1, const double *dnull1, const int *canon1,
                  const double *phi2, const double *dnull2, const int *canon2,
                  const double *D, int nd2, uint8_t *bitmap, int64_t nbits,
                  double *out_min, double *out_max, int64_t *out_pairs, int64_t *out_negative,
                  int64_t *out_simple, int mode) {
    static double Psq[MAXN], Qsq[MAXN], Msq[MAXN * MAXN];
    int oc[MAXN], nc[MAXN], osz[MAXN], nsz[MAXN];
    double a[MAXN], b[MAXN + 1], Cm[MAXN * (MAXN + 1)];
    int u1[MAXN], u2[MAXN];
    double mn = INFINITY, mx = -INFINITY;
    int64_t pairs = 0, negative = 0, simple = 0;
    if (K > MAXN) return -1;
    for (int k = 0; k < K; k++) { osz[k] = o_off[k + 1] - o_off[k]; nsz[k] = n_off[k + 1] - n_off[k]; oc[k] = 0; }
    for (;;) {                                   /* original structures */
        for (int k = 0; k < K; k++) nc[k] = 0;
        for (;;) {                               /* partitioned structures */
            int m1 = 0, m2 = 0;
            for (int k = 0; k < K; k++) {
                int hasO = osz[k] > 0, hasN = nsz[k] > 0;
                int oi = hasO ? o_ids[o_off[k] + oc[k]] : -1;
                int ni = hasN ? n_ids[n_off[k] + nc[k]] : -1;
                if (hasO && hasN && canon1[oi] == canon2[ni]) continue;
                if (hasO) u1[m1++] = oi;
                if (hasN) u2[m2++] = ni;
            }
            double v;
            if (m1 == 0 && m2 == 0) v = 0;
            else if (m1 == 0 || m2 == 0) {
                v = 0;
                if (m1 == 0) for (int t = 0; t < m2; t++) v += phi2[u2[t]] * dnull2[u2[t]];
                else for (int t = 0; t < m1; t++) v += phi1[u1[t]] * dnull1[u1[t]];
                simple++;
            } else {
                double s1 = 0, s2 = 0;
                for (int t = 0; t < m1; t++) { a[t] = phi1[u1[t]]; s1 += a[t]; }
                for (int t = 0; t < m2; t++) { b[t] = phi2[u2[t]]; s2 += b[t]; }
                double d0 = s1 - s2;
                if (mode == 1) {
                    /* PyPhi's square problem: U1, U2, then the null concept */
                    int N = m1 + m2 + 1;
                    double maxD = -INFINITY;
                    for (int s = 0; s < m1; s++) for (int t = 0; t < m2; t++) {
                        double x = D[u1[s] * nd2 + u2[t]]; if (x > maxD) maxD = x; }
                    for (int x = 0; x < N * N; x++) Msq[x] = maxD + 1;
                    for (int s = 0; s < m1; s++) for (int t = 0; t < m2; t++) {
                        double x = D[u1[s] * nd2 + u2[t]];
                        Msq[s * N + m1 + t] = x; Msq[(m1 + t) * N + s] = x; }
                    for (int s = 0; s < m1; s++) { Msq[(N - 1) * N + s] = dnull1[u1[s]]; Msq[s * N + N - 1] = dnull1[u1[s]]; }
                    for (int t = 0; t < m2; t++) { Msq[(N - 1) * N + m1 + t] = dnull2[u2[t]]; Msq[(m1 + t) * N + N - 1] = dnull2[u2[t]]; }
                    Msq[N * N - 1] = 0;
                    for (int x = 0; x < N; x++) { Psq[x] = 0; Qsq[x] = 0; }
                    for (int s = 0; s < m1; s++) Psq[s] = phi1[u1[s]];
                    for (int t = 0; t < m2; t++) Qsq[m1 + t] = phi2[u2[t]];
                    Qsq[N - 1] = d0;
                    if (d0 < -1e-12) negative++;
                    v = emd_pyemd_sq(N, Psq, Qsq, Msq);
                } else if (d0 >= -1e-12) {
                    b[m2] = d0 > 0 ? d0 : 0;
                    for (int s = 0; s < m1; s++) {
                        for (int t = 0; t < m2; t++) Cm[s * (m2 + 1) + t] = D[u1[s] * nd2 + u2[t]];
                        Cm[s * (m2 + 1) + m2] = dnull1[u1[s]];
                    }
                    /* rebalance rounding drift onto the null */
                    v = tr_solve(m1, m2 + 1, a, b, Cm);
                } else {
                    /* the partitioned side holds more phi: the null supplies the difference */
                    negative++;
                    a[m1] = -d0;
                    for (int s = 0; s < m1; s++) for (int t = 0; t < m2; t++) Cm[s * m2 + t] = D[u1[s] * nd2 + u2[t]];
                    for (int t = 0; t < m2; t++) Cm[m1 * m2 + t] = dnull2[u2[t]];
                    v = tr_solve(m1 + 1, m2, a, b, Cm);
                }
            }
            double r = nearbyint(v * 1e6) / 1e6;
            if (r < mn) mn = r;
            if (r > mx) mx = r;
            int64_t idx = (int64_t) nearbyint(v * 1e6);
            if (idx >= 0 && idx < nbits) bitmap[idx >> 3] |= (uint8_t) (1u << (idx & 7));
            pairs++;
            int k = 0;
            while (k < K) { if (nsz[k] > 0 && ++nc[k] < nsz[k]) break; nc[k] = 0; k++; }
            if (k == K) break;
        }
        int k = 0;
        while (k < K) { if (osz[k] > 0 && ++oc[k] < osz[k]) break; oc[k] = 0; k++; }
        if (k == K) break;
    }
    *out_min = mn; *out_max = mx; *out_pairs = pairs; *out_negative = negative; *out_simple = simple;
    return 0;
}
