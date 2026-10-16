/* IIT 3.0's small phi as PyPhi 0.8.1 defines it, for every mechanism of a system of up to five binary nodes and
 * every state of that mechanism, from the system's state-by-node TPM: the integrated information structure (IIS)
 * of Leung, Cohen, van Swinderen and Tsuchiya (2021), for iit/leung2021.py. Built at run time with gcc together with
 * flow.c, whose transport() gives the earth mover's distances exactly; called through ctypes.
 *
 * Conventions, as PyPhi 0.8.1 has them (its subsystem.py and utils.py, read as text):
 *   - tpm[s * n + j] is the probability that node j is on after system state s, s in LOLI order (node i is bit i);
 *     the connectivity matrix is all ones and every perturbation probability is 1/2 (PyPhi's defaults).
 *   - cause repertoire of mechanism M in state sigma over purview P: for each m in M, P(m = sigma_m | x) averaged
 *     over the nodes outside P, multiplied over M and normalised; empty M gives the uniform distribution over P.
 *   - effect repertoire: for each q in P, P(q on | M = sigma) averaged over the nodes outside M, multiplied over P.
 *   - a mechanism's partitions over a purview are mip_bipartitions(): every bipartition of M (one part never holding
 *     M's last node) with every directed bipartition of P, neither part empty in both; the partitioned repertoire is
 *     the product of the parts' repertoires.
 *   - phi of a partition is the earth mover's distance (Hamming costs) between the repertoire and the partitioned
 *     one, rounded to 6 decimals; the MIP's phi is 0 as soon as one partition gives 0, else the least; the core
 *     cause's (effect's) phi is the greatest over all purviews; the concept's phi is the lesser of the two.
 *   - effect distances use the sum over purview nodes of |difference of P(on)|, which equals the earth mover's
 *     distance between two product distributions with Hamming costs (the tests compare the two).
 *
 * phis(n, tpm, out_phi, out_cause, out_effect): for mechanism bitmask M (1 .. 2^n - 1) and system state s
 * (0 .. 2^n - 1), out[(M - 1) * 2^n + s] = the concept's phi (and the core cause's and core effect's) for M in the
 * state that s gives it. Results depend on s only through s restricted to M; each is computed once.
 */
#include <math.h>
#include <string.h>

#define MAXN 5
#define MAXS 32

double transport(int n1, int n2, const double *a, const double *b, const double *C);

static int N, NS;
static double T[MAXS][MAXN];
static double CREP[MAXS][MAXS][MAXS][MAXS];   /* cause repertoire of M in state sig (sig within M) over P */
static double EON[MAXS][MAXS][MAXN];           /* P(q on | M = sig), the rest averaged */

/* the compact index of state x over the nodes of mask P (ascending) */
static int compact(int x, int P) {
    int out = 0, t = 0;
    for (int i = 0; i < N; i++) if ((P >> i) & 1) { if ((x >> i) & 1) out |= 1 << t; t++; }
    return out;
}

static int popc(int x) { return __builtin_popcount((unsigned)x); }

/* cause repertoire of mechanism M in state sig (bits over the system, only M's used) over purview P */
static void cause_rep(int M, int sig, int P, double *rep) {
    int m = popc(P), K = 1 << m;
    if (P == 0) { rep[0] = 1.0; return; }
    if (M == 0) { for (int p = 0; p < K; p++) rep[p] = 1.0 / K; return; }
    double joint[MAXS];
    for (int p = 0; p < K; p++) joint[p] = 1.0;
    double f = (double)(1 << (N - m));
    for (int i = 0; i < N; i++) if ((M >> i) & 1) {
        double acc[MAXS];
        for (int p = 0; p < K; p++) acc[p] = 0.0;
        int on = (sig >> i) & 1;
        for (int x = 0; x < NS; x++) {
            double v = on ? T[x][i] : 1.0 - T[x][i];
            acc[compact(x, P)] += v;
        }
        for (int p = 0; p < K; p++) joint[p] *= acc[p] / f;
    }
    double s = 0;
    for (int p = 0; p < K; p++) s += joint[p];
    if (s != 0) for (int p = 0; p < K; p++) rep[p] = joint[p] / s;
    else for (int p = 0; p < K; p++) rep[p] = joint[p];
}

/* P(node q on | M = sig), the nodes outside M averaged */
static double effect_on(int M, int sig, int q) {
    double tot = 0; int cnt = 0;
    for (int x = 0; x < NS; x++) {
        if ((x & M) != (sig & M)) continue;
        tot += T[x][q]; cnt++;
    }
    return tot / cnt;
}

static double hamming_emd(int m, const double *p, const double *q) {
    int K = 1 << m;
    double a[MAXS], b[MAXS], C[MAXS * MAXS];
    int ia[MAXS], ib[MAXS], n1 = 0, n2 = 0;
    for (int s = 0; s < K; s++) {
        double d = p[s] - q[s];
        if (d > 0) { a[n1] = d; ia[n1++] = s; }
        else if (d < 0) { b[n2] = -d; ib[n2++] = s; }
    }
    if (n1 == 0 || n2 == 0) return 0.0;
    for (int i = 0; i < n1; i++) for (int j = 0; j < n2; j++) C[i * n2 + j] = (double)popc(ia[i] ^ ib[j]);
    return transport(n1, n2, a, b, C);
}

static double round6(double x) { return round(x * 1e6) / 1e6; }

/* the partitioned cause repertoire over P from parts (M0 over P0) and (M1 over P1), P0 | P1 = P */
static void cause_partitioned(int M0, int P0, int M1, int P1, int sig, int P, double *out) {
    const double *r0 = CREP[M0][sig & M0][P0], *r1 = CREP[M1][sig & M1][P1];
    int K = 1 << popc(P);
    for (int c = 0; c < K; c++) {
        /* expand c (compact over P) to system bits, then compact over P0 and P1 */
        int x = 0, t = 0;
        for (int i = 0; i < N; i++) if ((P >> i) & 1) { if ((c >> t) & 1) x |= 1 << i; t++; }
        out[c] = r0[compact(x, P0)] * r1[compact(x, P1)];
    }
}

/* the last (highest) node of M */
static int last_node(int M) { int h = -1; for (int i = 0; i < N; i++) if ((M >> i) & 1) h = i; return h; }

static double mip_phi_cause(int M, int sig, int P) {
    int m = popc(P);
    double part[MAXS];
    const double *rep = CREP[M][sig & M][P];
    int hi = last_node(M);
    int rest = M & ~(1 << hi);          /* part 0 of M's bipartitions never holds M's last node */
    double best = INFINITY;
    /* numerators in PyPhi's order: subsets of rest; denominators: every subset of P (directed) */
    for (int n0 = rest;; n0 = (n0 - 1) & rest) {
        int n1 = M & ~n0;
        for (int d0 = P;; d0 = (d0 - 1) & P) {
            int d1 = P & ~d0;
            if ((n0 | d0) != 0 && (n1 | d1) != 0) {
                cause_partitioned(n0, d0, n1, d1, sig, P, part);
                double phi = round6(hamming_emd(m, rep, part));
                if (phi == 0) return 0.0;
                if (phi < best) best = phi;
            }
            if (d0 == 0) break;
        }
        if (n0 == 0) break;
    }
    return best;
}

static double mip_phi_effect(int M, int sig, int P) {
    double g[MAXN];
    for (int q = 0; q < N; q++) if ((P >> q) & 1) g[q] = EON[M][sig & M][q];
    int hi = last_node(M);
    int rest = M & ~(1 << hi);
    double best = INFINITY;
    for (int n0 = rest;; n0 = (n0 - 1) & rest) {
        int n1 = M & ~n0;
        for (int d0 = P;; d0 = (d0 - 1) & P) {
            int d1 = P & ~d0;
            if ((n0 | d0) != 0 && (n1 | d1) != 0) {
                double d = 0;
                for (int q = 0; q < N; q++) {
                    if (!((P >> q) & 1)) continue;
                    double gp = ((d0 >> q) & 1) ? EON[n0][sig & n0][q] : EON[n1][sig & n1][q];
                    d += fabs(g[q] - gp);
                }
                double phi = round6(d);
                if (phi == 0) return 0.0;
                if (phi < best) best = phi;
            }
            if (d0 == 0) break;
        }
        if (n0 == 0) break;
    }
    return best;
}

int phis(int n, const double *tpm, double *out_phi, double *out_cause, double *out_effect) {
    if (n < 1 || n > MAXN) return -1;
    N = n; NS = 1 << n;
    for (int s = 0; s < NS; s++) for (int j = 0; j < n; j++) T[s][j] = tpm[s * n + j];
    for (int M = 0; M < NS; M++)
        for (int sig = M;; sig = (sig - 1) & M) {
            for (int P = 0; P < NS; P++) cause_rep(M, sig, P, CREP[M][sig][P]);
            for (int q = 0; q < n; q++) EON[M][sig][q] = effect_on(M, sig, q);
            if (sig == 0) break;
        }
    for (int M = 1; M < NS; M++) {
        /* each state of M once: sig ranges over the subsets of M */
        for (int sig = M;; sig = (sig - 1) & M) {
            double pc = 0, pe = 0;
            for (int P = 1; P < NS; P++) {
                double c = mip_phi_cause(M, sig, P);
                double e = mip_phi_effect(M, sig, P);
                if (c > pc) pc = c;
                if (e > pe) pe = e;
            }
            double phi = pc < pe ? pc : pe;
            for (int s = 0; s < NS; s++) if ((s & M) == sig) {
                out_phi[(M - 1) * NS + s] = phi;
                out_cause[(M - 1) * NS + s] = pc;
                out_effect[(M - 1) * NS + s] = pe;
            }
            if (sig == 0) break;
        }
    }
    return 0;
}

/* the exact earth mover's distance with Hamming costs between two distributions over 2^m states, for the tests */
double emd_hamming(int m, const double *p, const double *q) { return hamming_emd(m, p, q); }
