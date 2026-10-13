/* The network of Diehl & Cook (Front. Comput. Neurosci. 9:99, 2015) as the authors' released code builds it
   (peter-u-diehl/stdp-mnist at d527ca3, Diehl&Cook_spiking_MNIST.py, read as data), written afresh in C.
   Imago's laboratory; stdp/check.py states the rules, writes the jobs and reads the results.

   usage:  dcnet <job file> <output file>

   A job is one run of the released script: a fresh network presented with a list of digits, learning or not.
   job (little-endian): "DCJ1"; int32 ne, nex, learning, passes; double theta_plus (mV); uint64 seed;
                        double w[784 ne] (input i to neuron j at i ne + j); double theta[ne] (mV);
                        uint8 delay[784 ne] (steps of 0.5 ms); uint8 img[nex 784]
   output:              "DCO1"; int32 ne, nex, passes; double w[784 ne]; double theta[ne];
                        int32 counts[nex ne] (when not learning); int32 repeats[nex passes]; int64 steps
   The digits are presented in order, passes times over.

   Each step of 0.5 ms, in this order (Brian 1's: state update, threshold, propagation, reset):
   1. Euler steps of every neuron, from the old values of all its variables:
        excitatory  v += (dt / 100) ((-65 - v) + ge (0 - v) + gi (-100 - v));  inhibitory the same with -60, -85, 10 ms;
        ge *= 1 - dt / 1 (0.5); gi *= 1 - dt / 2 (0.75); while learning, theta *= 1 - dt / 1e7.
   2. Thresholds: excitatory v > theta - 72 mV (theta - offset + v_thresh), inhibitory v > -40 mV, neither within its
      refractory period (Brian 1's next allowed spike time: 5 ms less 0.25 ms after a spike for excitatory neurons,
      so the 9 steps after one are barred, and 2 ms less 0.25 ms for inhibitory ones, the 3 steps after).
   3. This step's input spikes join the history of the last 21 steps.
   4. Arrivals: every input spike reaches neuron j after its synapse's delay (whole steps, d / dt truncated, as Brian 1
      takes it); in order of delay, input and target,
      ge_j += w_ij and, while learning, the synapse's presynaptic trace is set to 1 and w_ij -= 0.0001 post1_j,
      clipped at 0.
   5. Excitatory spikes: the neuron's inhibitory partner gets ge += 10.4; while learning, every input synapse of the
      neuron gets w_ij += 0.01 pre_ij post2_j (post2 before the spike), clipped at 1; then post1 and post2 are 1.
   6. Inhibitory spikes: every excitatory neuron but the partner gets gi += 17.0.
   7. Resets: excitatory v = -65 mV (and theta += theta_plus while learning), once: the script's reset is a string of
      three statements, which Brian 1 applies without clamping, so v integrates freely while the neuron may not fire;
      inhibitory v = -45 mV, clamped there in the step of the spike and the 4 after (Brian 1's Refractoriness, period
      int(2 ms / dt) + 1 steps).
   Traces decay exactly: after k steps a trace set to 1 is exp(-k dt / tau), tau 20 ms (pre and post1) and 40 ms
   (post2).

   Each digit, as the script presents it: while learning, every input column of weights is first scaled to sum to 78;
   input i fires as a Poisson process of rate pixel_i / 8 x intensity Hz (intensity 2) for 350 ms (each step a spike
   with probability rate x dt, drawn as geometric gaps from xoshiro256** seeded by splitmix64); the spikes each
   neuron fired since the end of the last presentation are its count; under 5 spikes in all, the intensity rises by
   1 and, after 150 ms of rest, the digit is presented again; otherwise the counts are kept and 150 ms of rest follow.

   Runaways. The Euler step of an excitatory neuron is unstable once ge + gi exceeds 2 / (dt / 100 ms) - 1 = 399, and
   a volley of about 24 excitatory spikes within a millisecond takes gi there through their inhibitory partners: v then
   swings past both reversal potentials, every neuron allowed to fire does, and the network never recovers (the first
   sealed run of stdp/check.py, receipt 6d2aeda8..., met one at digit 5,469). The released code integrates the same
   equations with the same step. So a presentation that draws more than 10 spikes per excitatory neuron (350 ms shown
   and the 150 ms rest after it), or leaves any value not finite, stops the run: the output is then
   "DCR1"; int32 ne, digit (over the passes, from 0), repeat (of that digit, from 0); int64 spikes (that presentation's),
   steps; and the status is 3. */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NIN 784
#define PRES 700
#define REST 300
#define ND 21
#define TAB 8192

static const double DT = 0.5;
static const double VREST_E = -65.0, VRESET_E = -65.0, THR_E = -72.0, TAU_E = 100.0, EINH_E = -100.0;
static const double VREST_I = -60.0, VRESET_I = -45.0, VTHR_I = -40.0, TAU_I = 10.0, EINH_I = -85.0;
static const double TAU_GE = 1.0, TAU_GI = 2.0, TC_THETA = 1e7;
static const int BLOCK_E = 9, BLOCK_I = 3, CLAMP_I = 4;   /* steps after a spike: barred from firing; inhibitory v clamped */
static const double TC_PRE = 20.0, TC_POST1 = 20.0, TC_POST2 = 40.0;
static const double NU_PRE = 0.0001, NU_POST = 0.01, WMAX = 1.0;
static const double W_EI = 10.4, W_IE = 17.0, NORM = 78.0;
static double KE, KI, DGE, DGI, DTH;   /* dt / tau, and the Euler factors of the conductances and the threshold */

static uint64_t rs[4];
static inline uint64_t rotl(const uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t next(void) {                                   /* xoshiro256** */
    const uint64_t result = rotl(rs[1] * 5, 7) * 9;
    const uint64_t t = rs[1] << 17;
    rs[2] ^= rs[0]; rs[3] ^= rs[1]; rs[1] ^= rs[2]; rs[0] ^= rs[3]; rs[2] ^= t; rs[3] = rotl(rs[3], 45);
    return result;
}
static uint64_t splitmix(uint64_t *x) {
    uint64_t z = (*x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
static double unif(void) { return (double)(next() >> 11) * (1.0 / 9007199254740992.0); }

static int ne, nex, learning, passes;
static double theta_plus;
static double *w, *theta, *ve, *gee, *gie, *vi, *gei, *gii;
static int *blke, *blki, *clmi;
static int32_t *last_arr, *last_post;
static int64_t *tot, *prev;
static uint8_t *delay, *img;
static int16_t *tgt;                 /* targets of input i sorted by delay: tgt[i ne + k] */
static int32_t *off;                 /* off[i (ND + 1) + d]: first k of delay d */
static int16_t hist[ND][NIN];
static int hn[ND];
static double tpre[TAB], tp1[TAB], tp2[TAB];
static int spk_e[4096], spk_i[4096];
static int32_t step_cnt[PRES + 1];
static int16_t step_in[PRES * NIN + 1];

static void die(const char *m) { fprintf(stderr, "dcnet: %s\n", m); exit(2); }

static double trace(const double *tab, int32_t since, int32_t now) {
    if (since < 0) return 0.0;
    int32_t k = now - since;
    return k < TAB ? tab[k] : 0.0;
}

static double *colsum, *p1now;
static void normalise(void) {             /* each column summed over i ascending, then scaled to 78 */
    for (int j = 0; j < ne; j++) colsum[j] = 0.0;
    for (int i = 0; i < NIN; i++) for (int j = 0; j < ne; j++) colsum[j] += w[(size_t)i * ne + j];
    for (int j = 0; j < ne; j++) colsum[j] = NORM / colsum[j];
    for (int i = 0; i < NIN; i++) for (int j = 0; j < ne; j++) w[(size_t)i * ne + j] *= colsum[j];
}

/* the input spikes of one presentation, as per-step lists (inputs in ascending order) */
static void inputs(const uint8_t *px, int intensity) {
    static int32_t ts[PRES * NIN];
    static int16_t is[PRES * NIN];
    int n = 0;
    for (int i = 0; i < NIN; i++) {
        double rate = (double)px[i] / 8.0 * (double)intensity;
        double p = rate * DT / 1000.0;
        if (p <= 0.0) continue;
        if (p >= 1.0) { for (int t = 0; t < PRES; t++) { ts[n] = t; is[n] = (int16_t)i; n++; } continue; }
        double lq = log1p(-p);
        int t = -1;
        for (;;) {
            double u = 1.0 - unif();
            double g = floor(log(u) / lq);
            if (g >= (double)PRES) break;
            t += 1 + (int)g;
            if (t >= PRES) break;
            ts[n] = t; is[n] = (int16_t)i; n++;
        }
    }
    memset(step_cnt, 0, sizeof step_cnt);
    for (int k = 0; k < n; k++) step_cnt[ts[k] + 1]++;
    for (int t = 0; t < PRES; t++) step_cnt[t + 1] += step_cnt[t];
    static int32_t fill[PRES];
    for (int t = 0; t < PRES; t++) fill[t] = step_cnt[t];
    for (int k = 0; k < n; k++) step_in[fill[ts[k]]++] = is[k];   /* k runs over i ascending, so each step's list is sorted */
}

static void step(int32_t s, const int16_t *in_now, int n_now) {
    /* 1 */
    if (learning) for (int j = 0; j < ne; j++) theta[j] = theta[j] * DTH;
    for (int j = 0; j < ne; j++) {
        double v = ve[j], ge = gee[j], gi = gie[j];
        ve[j] = v + KE * ((VREST_E - v) + ge * (0.0 - v) + gi * (EINH_E - v));
        gee[j] = ge * DGE;
        gie[j] = gi * DGI;
    }
    for (int j = 0; j < ne; j++) {
        double v = vi[j], ge = gei[j], gi = gii[j];
        vi[j] = v + KI * ((VREST_I - v) + ge * (0.0 - v) + gi * (EINH_I - v));
        gei[j] = ge * DGE;
        gii[j] = gi * DGI;
    }
    /* 2 */
    int ns_e = 0, ns_i = 0;
    for (int j = 0; j < ne; j++) {
        if (blke[j] == 0 && ve[j] > theta[j] + THR_E) spk_e[ns_e++] = j;
        if (blki[j] == 0 && vi[j] > VTHR_I) spk_i[ns_i++] = j;
    }
    /* 3 */
    int slot = s % ND;
    for (int k = 0; k < n_now; k++) hist[slot][k] = in_now[k];
    hn[slot] = n_now;
    /* 4 */
    if (learning) for (int j = 0; j < ne; j++) p1now[j] = trace(tp1, last_post[j], s);
    for (int d = 0; d < ND; d++) {
        int src = (s - d) % ND;
        if (src < 0) src += ND;
        if (s - d < 0) continue;
        for (int q = 0; q < hn[src]; q++) {
            int i = hist[src][q];
            const int32_t *o = off + (size_t)i * (ND + 1);
            for (int k = o[d]; k < o[d + 1]; k++) {
                int j = tgt[(size_t)i * ne + k];
                size_t idx = (size_t)i * ne + j;
                gee[j] += w[idx];
                if (learning) {
                    last_arr[idx] = s;
                    double nw = w[idx] - NU_PRE * p1now[j];
                    w[idx] = nw < 0.0 ? 0.0 : nw;
                }
            }
        }
    }
    /* 5 */
    for (int q = 0; q < ns_e; q++) {
        int j = spk_e[q];
        gei[j] += W_EI;
        if (learning) {
            double p2 = trace(tp2, last_post[j], s);
            for (int i = 0; i < NIN; i++) {
                size_t idx = (size_t)i * ne + j;
                double nw = w[idx] + NU_POST * trace(tpre, last_arr[idx], s) * p2;
                w[idx] = nw > WMAX ? WMAX : nw;
            }
        }
        last_post[j] = s;
        tot[j]++;
    }
    /* 6 */
    for (int q = 0; q < ns_i; q++) {
        int i = spk_i[q];
        for (int j = 0; j < ne; j++) if (j != i) gie[j] += W_IE;
    }
    /* 7 */
    for (int j = 0; j < ne; j++) {
        if (blke[j] > 0) blke[j]--;
        if (blki[j] > 0) blki[j]--;
        if (clmi[j] > 0) { vi[j] = VRESET_I; clmi[j]--; }
    }
    for (int q = 0; q < ns_e; q++) {
        int j = spk_e[q];
        ve[j] = VRESET_E;
        if (learning) theta[j] += theta_plus;
        blke[j] = BLOCK_E;
    }
    for (int q = 0; q < ns_i; q++) {
        int i = spk_i[q];
        vi[i] = VRESET_I;
        blki[i] = BLOCK_I;
        clmi[i] = CLAMP_I;
    }
}

static void *grab(size_t n) { void *p = calloc(n ? n : 1, 1); if (!p) die("out of memory"); return p; }

#define RUNAWAY 10                   /* spikes per excitatory neuron in one presentation */
static int finite_state(void) {
    for (int j = 0; j < ne; j++)
        if (!isfinite(ve[j]) || !isfinite(gee[j]) || !isfinite(gie[j]) || !isfinite(vi[j]) || !isfinite(gei[j])
            || !isfinite(gii[j]) || !isfinite(theta[j])) return 0;
    return 1;
}
static void ran_away(const char *path, int ep, int rep, int64_t drawn, int64_t steps) {
    FILE *o = fopen(path, "wb");
    if (!o) die("cannot write the output");
    int32_t h[3] = {ne, ep, rep};
    if (fwrite("DCR1", 1, 4, o) != 4 || fwrite(h, 4, 3, o) != 3 || fwrite(&drawn, 8, 1, o) != 1
        || fwrite(&steps, 8, 1, o) != 1) die("short write");
    fclose(o);
    fprintf(stderr, "dcnet: ran away at digit %d (repeat %d): %lld spikes in one presentation\n", ep, rep, (long long)drawn);
    exit(3);
}

int main(int argc, char **argv) {
    if (argc != 3) die("usage: dcnet <job> <output>");
    FILE *f = fopen(argv[1], "rb");
    if (!f) die("cannot open the job");
    char magic[4];
    int32_t head[4];
    uint64_t seed;
    if (fread(magic, 1, 4, f) != 4 || memcmp(magic, "DCJ1", 4)) die("not a job file");
    if (fread(head, 4, 4, f) != 4 || fread(&theta_plus, 8, 1, f) != 1 || fread(&seed, 8, 1, f) != 1) die("short header");
    ne = head[0]; nex = head[1]; learning = head[2]; passes = head[3];
    if (ne < 2 || ne > 4096 || nex < 0 || (learning != 0 && learning != 1) || passes < 1 || passes > 100) die("bad header");
    size_t nw = (size_t)NIN * ne;
    w = grab(nw * 8); theta = grab((size_t)ne * 8); delay = grab(nw); img = grab((size_t)nex * NIN);
    if (fread(w, 8, nw, f) != nw || fread(theta, 8, ne, f) != (size_t)ne || fread(delay, 1, nw, f) != nw
        || fread(img, 1, (size_t)nex * NIN, f) != (size_t)nex * NIN) die("short job");
    char extra;
    if (fread(&extra, 1, 1, f) != 0) die("job longer than its header says");
    fclose(f);
    for (size_t k = 0; k < nw; k++) if (delay[k] >= ND) die("a delay beyond 20 steps");

    ve = grab((size_t)ne * 8); gee = grab((size_t)ne * 8); gie = grab((size_t)ne * 8);
    vi = grab((size_t)ne * 8); gei = grab((size_t)ne * 8); gii = grab((size_t)ne * 8);
    blke = grab((size_t)ne * sizeof(int)); blki = grab((size_t)ne * sizeof(int)); clmi = grab((size_t)ne * sizeof(int));
    last_arr = grab(nw * 4); last_post = grab((size_t)ne * 4);
    tot = grab((size_t)ne * 8); prev = grab((size_t)ne * 8);
    tgt = grab(nw * 2); off = grab((size_t)NIN * (ND + 1) * 4);
    colsum = grab((size_t)ne * 8); p1now = grab((size_t)ne * 8);
    for (int j = 0; j < ne; j++) { ve[j] = VREST_E - 40.0; vi[j] = VREST_I - 40.0; last_post[j] = -1; }
    for (size_t k = 0; k < nw; k++) last_arr[k] = -1;
    for (int i = 0; i < NIN; i++) {                      /* targets sorted by delay, then by index */
        int32_t *o = off + (size_t)i * (ND + 1);
        int k = 0;
        for (int d = 0; d < ND; d++) {
            o[d] = k;
            for (int j = 0; j < ne; j++) if (delay[(size_t)i * ne + j] == d) tgt[(size_t)i * ne + k++] = (int16_t)j;
        }
        o[ND] = k;
    }
    KE = DT / TAU_E; KI = DT / TAU_I; DGE = 1.0 - DT / TAU_GE; DGI = 1.0 - DT / TAU_GI; DTH = 1.0 - DT / TC_THETA;
    for (int k = 0; k < TAB; k++) {
        tpre[k] = exp(-(double)k * DT / TC_PRE);
        tp1[k] = exp(-(double)k * DT / TC_POST1);
        tp2[k] = exp(-(double)k * DT / TC_POST2);
    }
    uint64_t sm = seed;
    for (int k = 0; k < 4; k++) rs[k] = splitmix(&sm);

    size_t ncount = learning ? 0 : (size_t)nex * ne;
    int32_t *counts = grab(ncount * 4);
    int32_t *repeats = grab((size_t)nex * passes * 4);
    int32_t s = 0;
    const char *prog = getenv("DCNET_PROGRESS");          /* a line on stderr every so many digits */
    int every = prog ? atoi(prog) : 0;
    int64_t spikes_mark = 0, steps_mark = 0;
    for (int ep = 0; ep < nex * passes; ep++) {
        int e = ep % nex;
        if (every > 0 && ep > 0 && ep % every == 0) {
            int64_t all = 0;
            for (int j = 0; j < ne; j++) all += tot[j];
            double tmax = theta[0];
            for (int j = 1; j < ne; j++) if (theta[j] > tmax) tmax = theta[j];
            fprintf(stderr, "dcnet: %d digits, %.1f spikes and %.0f steps per digit since the last line, theta max %.2f\n", ep,
                    (double)(all - spikes_mark) / every, (double)(s - steps_mark) / every, tmax);
            spikes_mark = all; steps_mark = s;
        }
        int intensity = 2;
        for (;;) {
            int64_t at_start = 0;
            for (int j = 0; j < ne; j++) at_start += tot[j];
            if (learning) normalise();
            inputs(img + (size_t)e * NIN, intensity);
            for (int t = 0; t < PRES; t++) {
                step(s, step_in + step_cnt[t], step_cnt[t + 1] - step_cnt[t]);
                if (s == INT32_MAX) die("too many steps");
                s++;
            }
            int64_t sum = 0;
            for (int j = 0; j < ne; j++) sum += tot[j] - prev[j];
            int ok = sum >= 5;
            if (ok && !learning) for (int j = 0; j < ne; j++) counts[(size_t)e * ne + j] = (int32_t)(tot[j] - prev[j]);
            for (int j = 0; j < ne; j++) prev[j] = tot[j];
            for (int t = 0; t < REST; t++) { step(s, NULL, 0); s++; }
            int64_t drawn = -at_start;
            for (int j = 0; j < ne; j++) drawn += tot[j];
            if (drawn > (int64_t)RUNAWAY * ne || !finite_state()) ran_away(argv[2], ep, repeats[ep], drawn, s);
            if (ok) break;
            intensity++;
            repeats[ep]++;
            if (repeats[ep] > 1000) die("a digit drew under 5 spikes a thousand times");
        }
    }

    FILE *o = fopen(argv[2], "wb");
    if (!o) die("cannot write the output");
    int32_t oh[3] = {ne, nex, passes};
    int64_t steps = s;
    size_t nrep = (size_t)nex * passes;
    if (fwrite("DCO1", 1, 4, o) != 4 || fwrite(oh, 4, 3, o) != 3 || fwrite(w, 8, nw, o) != nw
        || fwrite(theta, 8, ne, o) != (size_t)ne || fwrite(counts, 4, ncount, o) != ncount
        || fwrite(repeats, 4, nrep, o) != nrep || fwrite(&steps, 8, 1, o) != 1) die("short write");
    fclose(o);
    return 0;
}
