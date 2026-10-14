/* Jain & Krishna (2001), "A model for the emergence of cooperation, interdependence, and structure in evolving
   networks" (PNAS 98, 543-547; arXiv:nlin/0005039): the model as its Model section specifies it, for alife/jk.py.

   s species; c_ij (the link from j to i) nonzero with probability p, then uniform in [-1, 1] for i != j and in [-1, 0]
   for i = j. The populations follow equation (1) for a time T between graph updates: xdot_i = f_i, held at 0 while
   x_i = 0 and f_i < 0, with f_i = sum_j c_ij x_j - x_i sum_kj c_kj x_j. That is the linear system ydot = C y with the
   same holding rule, x = y / sum y (the normalising term rescales every x_i alike and never changes their ratios, nor
   which are zero), integrated here by the classical fourth-order Runge-Kutta method with step dt, a component that
   would go below 0 set to 0, and every 100 steps rescaled to sum 1 (values below 1e-250 set to 0). X_i = x_i(T); a
   node with X_i <= eps counts as 0. A graph update removes one least fit node at random (all with X_i <= eps tied at
   0, if any; else those with the least X_i) and puts a new species in its place, its links drawn by the same rule, its
   population x0, the others rescaled to sum 1 - x0.

   The maximal ACS of a graph (the union of its autocatalytic sets: every member has an incoming positive link from a
   member) is found by pruning: strike off every node with no positive link from a node not yet struck off, until none
   is left to strike. The graph contains an ACS when that leaves any node, and is entirely an ACS when it leaves all.

   Modes (generator state: four 64-bit words in hex, xoshiro256**):
     run   w0 w1 w2 w3 s p x0 T dt eps cap      one run, until the graph is entirely an ACS or cap updates;
                                                prints one line of results
     trace w0 w1 w2 w3 s p x0 T dt eps n        n updates: each update's removed node, maximal ACS and X (as IEEE
                                                bits), for the plain implementation in jk.py to match bit for bit
     graph s T dt eps m i j c ...               X after T on a given graph (m links i <- j of strength c) from
                                                uniform populations
   No input is read but the arguments. */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define SMAX 200
#define RENORM 100
#define FLUSH 1e-250

static uint64_t st[4];
static int s;
static double p, x0, T, dt, eps;
static double C[SMAX][SMAX];
static double x[SMAX];

static inline uint64_t rotl(uint64_t v, int k) { return (v << k) | (v >> (64 - k)); }

static uint64_t next64(void) {
    uint64_t r = rotl(st[1] * 5, 7) * 9, t = st[1] << 17;
    st[2] ^= st[0];
    st[3] ^= st[1];
    st[1] ^= st[2];
    st[0] ^= st[3];
    st[2] ^= t;
    st[3] = rotl(st[3], 45);
    return r;
}

static double unif(void) { return (double)(next64() >> 11) * 0x1.0p-53; }

static int below(int m) {
    int k = (int)(unif() * (double)m);
    return k < m ? k : m - 1;
}

static double draw(int diag) {
    double u = unif();
    if (!(u < p)) return 0.0;
    double v = unif();
    return diag ? -v : 2.0 * v - 1.0;
}

static void init_graph(void) {
    for (int i = 0; i < s; i++)
        for (int j = 0; j < s; j++) C[i][j] = draw(i == j);
    for (int i = 0; i < s; i++) x[i] = unif();
    double tot = 0.0;
    for (int i = 0; i < s; i++) tot += x[i];
    for (int i = 0; i < s; i++) x[i] = x[i] / tot;
}

/* ---------------------------------------------------------------- population dynamics */

static int nact, act[SMAX], rowst[SMAX + 1], col[SMAX * SMAX];
static double val[SMAX * SMAX];

static void build_rows(void) {
    int e = 0;
    nact = 0;
    for (int i = 0; i < s; i++) {
        int start = e;
        for (int j = 0; j < s; j++)
            if (C[i][j] != 0.0) {
                col[e] = j;
                val[e] = C[i][j];
                e++;
            }
        if (e > start) {
            act[nact] = i;
            rowst[nact] = start;
            nact++;
        }
    }
    rowst[nact] = e;
}

static void deriv(const double *y, double *k) {
    for (int a = 0; a < nact; a++) {
        int i = act[a];
        double f = 0.0;
        for (int e = rowst[a]; e < rowst[a + 1]; e++) f += val[e] * y[col[e]];
        if (!(y[i] > 0.0) && f < 0.0) f = 0.0;
        k[i] = f;
    }
}

static void renorm(double *y, double *yt) {
    double tot = 0.0;
    for (int i = 0; i < s; i++) tot += y[i];
    if (!(tot > 0.0)) {
        fprintf(stderr, "jk: every population is zero\n");
        exit(3);
    }
    for (int i = 0; i < s; i++) {
        double v = y[i] / tot;
        if (v < FLUSH) v = 0.0;
        y[i] = v;
        yt[i] = v;
    }
}

/* y holds x on entry and X = x(T), normalised, on return. */
static void evolve(double *y) {
    static double k1[SMAX], k2[SMAX], k3[SMAX], k4[SMAX], yt[SMAX];
    build_rows();
    long steps = lround(T / dt);
    double h2 = 0.5 * dt, h6 = dt / 6.0;
    for (int i = 0; i < s; i++) yt[i] = y[i];
    for (long n = 1; n <= steps; n++) {
        deriv(y, k1);
        for (int a = 0; a < nact; a++) {
            int i = act[a];
            yt[i] = y[i] + h2 * k1[i];
        }
        deriv(yt, k2);
        for (int a = 0; a < nact; a++) {
            int i = act[a];
            yt[i] = y[i] + h2 * k2[i];
        }
        deriv(yt, k3);
        for (int a = 0; a < nact; a++) {
            int i = act[a];
            yt[i] = y[i] + dt * k3[i];
        }
        deriv(yt, k4);
        for (int a = 0; a < nact; a++) {
            int i = act[a];
            double inc = k1[i] + 2.0 * k2[i];
            inc = inc + 2.0 * k3[i];
            inc = inc + k4[i];
            double v = y[i] + h6 * inc;
            y[i] = v > 0.0 ? v : 0.0;
            yt[i] = y[i];
        }
        if (n % RENORM == 0) renorm(y, yt);
    }
    renorm(y, yt);
}

static int populated(const double *X) {
    int c = 0;
    for (int i = 0; i < s; i++)
        if (X[i] > eps) c++;
    return c;
}

/* ---------------------------------------------------------------- graph updates */

static int least_fit(const double *X) {
    int z[SMAX], nz = 0;
    for (int i = 0; i < s; i++)
        if (X[i] <= eps) z[nz++] = i;
    if (nz == 0) {
        double m = X[0];
        for (int i = 1; i < s; i++)
            if (X[i] < m) m = X[i];
        for (int i = 0; i < s; i++)
            if (X[i] == m) z[nz++] = i;
    }
    return z[below(nz)];
}

static void replace(int i0, double *X) {
    double rest = 0.0;
    for (int i = 0; i < s; i++)
        if (i != i0) rest += X[i];
    if (!(rest > 0.0)) {
        fprintf(stderr, "jk: nothing left to rescale\n");
        exit(3);
    }
    double f = (1.0 - x0) / rest;
    for (int i = 0; i < s; i++)
        if (i != i0) X[i] = X[i] * f;
    X[i0] = x0;
    for (int j = 0; j < s; j++) C[i0][j] = draw(j == i0);
    for (int j = 0; j < s; j++)
        if (j != i0) C[j][i0] = draw(0);
}

/* The maximal ACS by pruning; marks members in in[] and returns their number. */
static int max_acs(unsigned char *in) {
    int cnt[SMAX], q[SMAX], qh = 0, qt = 0, left = s;
    for (int i = 0; i < s; i++) {
        cnt[i] = 0;
        in[i] = 1;
        for (int j = 0; j < s; j++)
            if (j != i && C[i][j] > 0.0) cnt[i]++;
    }
    for (int i = 0; i < s; i++)
        if (cnt[i] == 0) {
            in[i] = 0;
            q[qt++] = i;
            left--;
        }
    while (qh < qt) {
        int j = q[qh++];
        for (int i = 0; i < s; i++)
            if (in[i] && i != j && C[i][j] > 0.0 && --cnt[i] == 0) {
                in[i] = 0;
                q[qt++] = i;
                left--;
            }
    }
    return left;
}

static void links(int *pos, int *neg) {
    *pos = 0;
    *neg = 0;
    for (int i = 0; i < s; i++)
        for (int j = 0; j < s; j++) {
            if (C[i][j] > 0.0) (*pos)++;
            if (C[i][j] < 0.0) (*neg)++;
        }
}

static void read_state(char **w) {
    for (int k = 0; k < 4; k++) st[k] = strtoull(w[k], NULL, 16);
    if (!(st[0] | st[1] | st[2] | st[3])) {
        fprintf(stderr, "jk: an all-zero generator state\n");
        exit(2);
    }
}

static void read_params(char **a) {
    s = atoi(a[0]);
    p = strtod(a[1], NULL);
    x0 = strtod(a[2], NULL);
    T = strtod(a[3], NULL);
    dt = strtod(a[4], NULL);
    eps = strtod(a[5], NULL);
    if (s < 2 || s > SMAX || !(p > 0.0 && p < 1.0) || !(x0 > 0.0 && x0 < 1.0) || !(T >= 0.0) || !(dt > 0.0)) {
        fprintf(stderr, "jk: bad parameters\n");
        exit(2);
    }
}

static uint64_t bits(double v) {
    uint64_t b;
    memcpy(&b, &v, sizeof b);
    return b;
}

static int mode_run(char **a) {
    read_state(a);
    read_params(a + 4);
    long cap = atol(a[10]);
    unsigned char in[SMAX];
    init_graph();
    int lp0, ln0;
    links(&lp0, &ln0);
    int acs = max_acs(in), prev = acs;
    long n1 = -1, m1 = -1, n2 = -1, n = 0, losses = 0;
    int a_n1 = 0, a_m1 = 0, s1_n1 = -1, s1_n2 = -1;
    double pre_sum = 0.0;
    long pre_cnt = 0;
    double fn = 0.0, fx = 0.0, fy = 0.0, fxx = 0.0, fxy = 0.0;   /* least squares of ln a(n) on n - m1 */
    if (acs > 0) {
        n1 = m1 = 0;
        a_n1 = a_m1 = acs;
        fn = 1.0;
        fy = log((double)acs);
    }
    if (acs == s) n2 = 0;
    while (n2 < 0 && n < cap) {
        evolve(x);                                       /* the attractor of the graph after update n */
        int pop = populated(x);
        if (n1 < 0) {
            pre_sum += pop;
            pre_cnt++;
        }
        if (n == n1) s1_n1 = pop;
        int i0 = least_fit(x);
        replace(i0, x);
        n++;
        acs = max_acs(in);
        if (acs > 0 && prev == 0) {
            if (n1 < 0) {
                n1 = n;
                a_n1 = acs;
            }
            m1 = n;
            a_m1 = acs;
            fn = fx = fy = fxx = fxy = 0.0;
        }
        if (acs == 0 && prev > 0) losses++;
        if (acs > 0) {
            double u = (double)(n - m1), v = log((double)acs);
            fn += 1.0;
            fx += u;
            fy += v;
            fxx += u * u;
            fxy += u * v;
        }
        if (acs == s) n2 = n;
        prev = acs;
    }
    if (n2 >= 0) {
        evolve(x);
        s1_n2 = populated(x);
        if (n2 == n1) s1_n1 = s1_n2;
    }
    int lp, ln;
    links(&lp, &ln);
    double den = fn * fxx - fx * fx;
    double slope = den > 0.0 ? (fn * fxy - fx * fy) / den : 0.0;
    printf("n1 %ld a_n1 %d s1_n1 %d m1 %ld a_m1 %d n2 %ld losses %ld s1_n2 %d lp %d ln %d lp0 %d ln0 %d "
           "pre_mean %.6f slope %.9e updates %ld\n",
           n1, a_n1, s1_n1, m1, a_m1, n2, losses, s1_n2, lp, ln, lp0, ln0,
           pre_cnt ? pre_sum / (double)pre_cnt : -1.0, slope, n);
    return 0;
}

static int mode_trace(char **a) {
    read_state(a);
    read_params(a + 4);
    int updates = atoi(a[10]);
    unsigned char in[SMAX];
    init_graph();
    printf("start %d", max_acs(in));
    for (int i = 0; i < s; i++) printf(" %016llx", (unsigned long long)bits(x[i]));
    printf("\n");
    for (int n = 1; n <= updates; n++) {
        evolve(x);
        printf("X");
        for (int i = 0; i < s; i++) printf(" %016llx", (unsigned long long)bits(x[i]));
        int i0 = least_fit(x);
        replace(i0, x);
        int acs = max_acs(in);
        printf("\nupdate %d removed %d acs %d members", n, i0, acs);
        for (int i = 0; i < s; i++)
            if (in[i]) printf(" %d", i);
        printf("\n");
    }
    return 0;
}

static int mode_graph(int argc, char **a) {
    s = atoi(a[0]);
    T = strtod(a[1], NULL);
    dt = strtod(a[2], NULL);
    eps = strtod(a[3], NULL);
    int m = atoi(a[4]);
    if (s < 1 || s > SMAX || argc != 5 + 3 * m || !(dt > 0.0)) {
        fprintf(stderr, "jk: bad graph\n");
        return 2;
    }
    for (int i = 0; i < s; i++)
        for (int j = 0; j < s; j++) C[i][j] = 0.0;
    for (int k = 0; k < m; k++) C[atoi(a[5 + 3 * k])][atoi(a[6 + 3 * k])] = strtod(a[7 + 3 * k], NULL);
    for (int i = 0; i < s; i++) x[i] = 1.0 / (double)s;
    evolve(x);
    printf("populated %d", populated(x));
    for (int i = 0; i < s; i++) printf(" %.17g", x[i]);
    printf("\n");
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 2 && !strcmp(argv[1], "run") && argc == 13) return mode_run(argv + 2);
    if (argc >= 2 && !strcmp(argv[1], "trace") && argc == 13) return mode_trace(argv + 2);
    if (argc >= 7 && !strcmp(argv[1], "graph")) return mode_graph(argc - 2, argv + 2);
    fprintf(stderr, "usage: jk run|trace w0 w1 w2 w3 s p x0 T dt eps cap|n, or jk graph s T dt eps m i j c ...\n");
    return 2;
}
