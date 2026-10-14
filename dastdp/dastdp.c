/* dastdp.c: Izhikevich's daspnet.m (Cerebral Cortex 17, 2443-2452, 2007), ported line for line to C.
 *
 * Imago's laboratory (https://ecdysis.me/a/Imago); the harness is dastdp/izh2007.py, which states the rules. The
 * MATLAB program is read as data and not run; this port follows it statement by statement, with its own seeded random
 * numbers in place of MATLAB's rand:
 *
 *   1000 neurons (800 regular spiking, a = 0.02, d = 8; 200 fast spiking, a = 0.1, d = 2; b = 0.2, c = -65), 100
 *   synapses each, targets drawn with replacement (excitatory neurons onto all 1000, inhibitory onto the 800), weights
 *   +1 and -1 mV, every delay 1 ms; each millisecond every neuron takes 13 (rand - 0.5) of noise, the spikes of the
 *   millisecond are delivered (a neuron's repeated targets take one of its weights only, as MATLAB's I(ind) =
 *   I(ind) + s assigns), and v takes two half-millisecond steps, then u one step.
 *   STDP: a spike sets its neuron's trace to 0.1, which decays by 0.95 a millisecond; a postsynaptic spike adds the
 *   presynaptic trace of the millisecond before to each excitatory synapse onto it (sd), and a presynaptic spike takes
 *   1.5 times the postsynaptic trace from each of its synapses, so that a pair in the same millisecond depresses.
 *   Every 10 ms each excitatory weight becomes max(0, min(4, s + (0.002 + DA) sd)) and sd decays by 0.99; DA decays by
 *   0.995 a millisecond and rises by 0.5 at each reward (once however many fall due at the same millisecond).
 *   A synapse is marked as having reached 4 mV whenever an update leaves it there (the weights are scanned only when
 *   some synapse other than the chosen one is at 4 mV).
 *   The chosen synapse (n1 to n2, excitatory to excitatory, set to 0 at the start) is rewarded 1001 to 3000 ms
 *   (1000 + ceil(2000 rand)) after each spike of n2 that comes 1 to interval - 1 ms after n1's last spike.
 *
 * Usage: dastdp <seed> <seconds> <interval_ms>   (seed: an unsigned 64-bit integer)
 *        dastdp selftest                         (known answers for the rule's pieces, against the formulas above)
 * Prints one line of key=value pairs.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NE 800
#define NI 200
#define N (NE + NI)
#define M 100
#define SM 4.0
#define RING 4096

static uint64_t st[4];

static uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }

static uint64_t next64(void) { /* xoshiro256** (Blackman and Vigna) */
    uint64_t r = rotl(st[1] * 5, 7) * 9, t = st[1] << 17;
    st[2] ^= st[0]; st[3] ^= st[1]; st[1] ^= st[2]; st[0] ^= st[3]; st[2] ^= t; st[3] = rotl(st[3], 45);
    return r;
}

static double urand(void) { return (double)(next64() >> 11) * 0x1.0p-53; }  /* [0, 1) */

static void seed_rng(uint64_t x) { /* splitmix64 fills the state */
    for (int i = 0; i < 4; i++) {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        st[i] = z ^ (z >> 31);
    }
}

static int post[N][M];
static double s[N][M], sd[N][M];
static unsigned char hit[NE][M];
static int pre_start[N + 1], pre_row[NE * M], pre_col[NE * M];
static double v[N], u[N], a[N], d[N], I[N], A[N], B[N];
static unsigned char due[RING];

/* MATLAB's I(ind) = I(ind) + w(ind) for one neuron's targets: every right-hand side is read first, then the
   assignments run in order, so a repeated target keeps its last synapse's sum only. */
static void deliver(double *cur, const int *targets, const double *w, int m) {
    double tmp[M];
    for (int c = 0; c < m; c++) tmp[c] = cur[targets[c]] + w[c];
    for (int c = 0; c < m; c++) cur[targets[c]] = tmp[c];
}

static void build_pre(void) {
    int count[N];
    memset(count, 0, sizeof count);
    for (int j = 0; j < NE; j++)
        for (int c = 0; c < M; c++) count[post[j][c]]++;
    pre_start[0] = 0;
    for (int i = 0; i < N; i++) pre_start[i + 1] = pre_start[i] + count[i];
    int fill[N];
    memcpy(fill, pre_start, sizeof fill);
    for (int c = 0; c < M; c++)          /* column-major, as MATLAB's find returns them */
        for (int j = 0; j < NE; j++) {
            int i = post[j][c], k = fill[i]++;
            pre_row[k] = j; pre_col[k] = c;
        }
}

static int selftest(void) {
    int fails = 0;
    /* deliver: repeated targets keep the last sum */
    double cur[4] = {0, 0, 0, 0};
    int tg[3] = {1, 2, 1};
    double w[3] = {0.5, 0.25, 2.0};
    deliver(cur, tg, w, 3);
    if (!(cur[0] == 0 && cur[1] == 2.0 && cur[2] == 0.25 && cur[3] == 0)) { puts("deliver"); fails++; }
    /* the trace: 0.1 at the spike, 0.1 * 0.95^k k ms later */
    double tr = 0.1;
    for (int k = 0; k < 5; k++) tr *= 0.95;
    if (tr != 0.1 * 0.95 * 0.95 * 0.95 * 0.95 * 0.95) { puts("trace"); fails++; }
    /* the clipping and the gate */
    double x = 3.9 + (0.002 + 0.5) * 1.0;
    x = x < SM ? x : SM; x = x > 0 ? x : 0;
    double y = 0.01 + (0.002 + 0.0) * -10.0;
    y = y < SM ? y : SM; y = y > 0 ? y : 0;
    if (!(x == 4.0 && y == 0.0)) { puts("clip"); fails++; }
    /* the random numbers: in [0, 1), and the same stream from the same seed */
    seed_rng(12345);
    double r1 = urand(), r2 = urand();
    seed_rng(12345);
    if (!(urand() == r1 && urand() == r2 && r1 >= 0 && r1 < 1 && r1 != r2)) { puts("rng"); fails++; }
    printf("selftest_failures=%d\n", fails);
    return fails ? 1 : 0;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "selftest") == 0) return selftest();
    if (argc != 4) { fprintf(stderr, "usage: dastdp <seed> <seconds> <interval_ms>\n"); return 2; }
    uint64_t seed = strtoull(argv[1], 0, 10);
    long T = strtol(argv[2], 0, 10);
    long interval = strtol(argv[3], 0, 10);
    if (T < 1 || interval < 2) { fprintf(stderr, "bad arguments\n"); return 2; }
    seed_rng(seed);

    for (int i = 0; i < N; i++) {
        a[i] = i < NE ? 0.02 : 0.1;
        d[i] = i < NE ? 8.0 : 2.0;
    }
    for (int j = 0; j < N; j++)               /* post=ceil([N*rand(Ne,M);Ne*rand(Ni,M)]) */
        for (int c = 0; c < M; c++) {
            post[j][c] = (int)((j < NE ? N : NE) * urand());
            s[j][c] = j < NE ? 1.0 : -1.0;
            sd[j][c] = 0.0;
        }
    build_pre();
    for (int i = 0; i < N; i++) { v[i] = -65.0; u[i] = 0.2 * v[i]; A[i] = 0.0; B[i] = 0.0; }

    /* the chosen synapse: an excitatory neuron and one of its synapses onto an excitatory neuron, by the seed */
    int n1, syn, n2, cand[M], nc;
    do {
        n1 = (int)(NE * urand());
        nc = 0;
        for (int c = 0; c < M; c++) if (post[n1][c] < NE) cand[nc++] = c;
    } while (nc == 0);
    syn = cand[(int)(nc * urand())];
    n2 = post[n1][syn];
    s[n1][syn] = 0.0;

    double DA = 0.0;
    long long n1f = -100, reached = -1, first_window = 600000, last_window_from = (long long)T * 1000 - 600000;
    long rewards_scheduled = 0, rewards_delivered = 0, rewards_before = -1, early = 0, late = 0;
    long long spikes_e = 0, spikes_i = 0;
    int fired[N], nf;
    memset(due, 0, sizeof due);
    memset(hit, 0, sizeof hit);

    for (long sec = 1; sec <= T; sec++) {
        for (int t = 1; t <= 1000; t++) {
            long long now = sec * 1000 + t;
            for (int i = 0; i < N; i++) I[i] = 13.0 * (urand() - 0.5);
            nf = 0;
            for (int i = 0; i < N; i++) if (v[i] >= 30.0) fired[nf++] = i;
            for (int k = 0; k < nf; k++) {
                int i = fired[k];
                v[i] = -65.0; u[i] += d[i]; B[i] = 0.1;
                if (i < NE) spikes_e++; else spikes_i++;
            }
            for (int k = 0; k < nf; k++) {     /* LTP: the presynaptic trace of the millisecond before */
                int i = fired[k];
                for (int p = pre_start[i]; p < pre_start[i + 1]; p++) sd[pre_row[p]][pre_col[p]] += A[pre_row[p]];
            }
            for (int k = nf - 1; k >= 0; k--) { /* delivery and LTD, the last spike of the millisecond first */
                int i = fired[k];
                deliver(I, post[i], s[i], M);
                for (int c = 0; c < M; c++) sd[i][c] -= 1.5 * B[post[i][c]];
            }
            for (int i = 0; i < N; i++) {
                v[i] += 0.5 * ((0.04 * v[i] + 5.0) * v[i] + 140.0 - u[i] + I[i]);
                v[i] += 0.5 * ((0.04 * v[i] + 5.0) * v[i] + 140.0 - u[i] + I[i]);
                u[i] += a[i] * (0.2 * v[i] - u[i]);
            }
            for (int i = 0; i < N; i++) { A[i] = B[i]; B[i] = 0.95 * B[i]; }
            DA *= 0.995;
            if (t % 10 == 0) {
                double g = 0.002 + DA;
                int at_max = 0;
                for (int j = 0; j < NE; j++)
                    for (int c = 0; c < M; c++) {
                        double x = s[j][c] + g * sd[j][c];
                        x = x < SM ? x : SM;
                        x = x > 0.0 ? x : 0.0;
                        s[j][c] = x;
                        sd[j][c] *= 0.99;
                        at_max += x >= SM;
                    }
                if (at_max > (s[n1][syn] >= SM))
                    for (int j = 0; j < NE; j++)
                        for (int c = 0; c < M; c++)
                            if (s[j][c] >= SM) hit[j][c] = 1;
                if (reached < 0 && s[n1][syn] >= SM) { reached = now; rewards_before = rewards_delivered; }
            }
            int f1 = 0, f2 = 0;
            for (int k = 0; k < nf; k++) { if (fired[k] == n1) f1 = 1; if (fired[k] == n2) f2 = 1; }
            if (f1) n1f = now;
            if (f2 && now - n1f < interval && now > n1f) {
                long delay = 1000 + 1 + (long)(2000 * urand());
                due[(now + delay) % RING] = 1;
                rewards_scheduled++;
                if (now - 1000 <= first_window) early++;
                if (now - 1000 > last_window_from) late++;
            }
            if (due[now % RING]) { DA += 0.5; rewards_delivered++; due[now % RING] = 0; }
        }
    }

    long others = 0, others_end = 0, below = 0;
    double total = 0.0;
    for (int j = 0; j < NE; j++)
        for (int c = 0; c < M; c++) {
            if (j == n1 && c == syn) continue;
            others += hit[j][c];
            others_end += s[j][c] >= SM;
            below += s[j][c] < 0.1;
            total += s[j][c];
        }
    printf("seed=%llu seconds=%ld interval=%ld n1=%d syn=%d n2=%d reached_ms=%lld rewards_before=%ld "
           "rewards_scheduled=%ld rewards_delivered=%ld rewards_first_600s=%ld rewards_last_600s=%ld "
           "final_weight=%.6f others_reached=%ld others_at_max_end=%ld mean_weight=%.6f share_below_0.1=%.6f "
           "rate_e=%.6f rate_i=%.6f\n",
           (unsigned long long)seed, T, interval, n1 + 1, syn + 1, n2 + 1, reached < 0 ? -1LL : reached - 1000,
           rewards_before, rewards_scheduled, rewards_delivered, early, late, s[n1][syn], others, others_end,
           total / (NE * M - 1), (double)below / (NE * M - 1), spikes_e / (double)NE / T, spikes_i / (double)NI / T);
    return 0;
}
