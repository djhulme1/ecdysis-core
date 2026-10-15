/* snn/babadi.c: Babadi & Abbott's integrate-and-fire neuron under shifted, nearest-neighbour pair STDP.
 *
 * Imago's laboratory; the engine of snn/babadi.py (Babadi & Abbott 2010, ext:e5149bd6f1025244), whose docstring
 * states the rules. The model is the paper's (Methods and Table 1): tau_m dV/dt = (V_r - V) + I_ex - I_in, reset to
 * V_r at V_th; each presynaptic spike makes its input jump by the synapse's strength (mV), decaying with tau_s; the
 * excitatory strengths change by F(dt) = -A_minus exp((dt - d)/tau_minus) for dt <= d and A_plus exp(-(dt - d)/tau_plus)
 * for dt > d, dt = t_post - t_pre, only between spikes adjacent in the order of events: a postsynaptic spike pairs with
 * a synapse's last presynaptic spike only if no postsynaptic spike came between them, and a presynaptic spike with the
 * last postsynaptic spike only if no presynaptic spike came at that synapse between them (the paper's nearest-neighbour
 * pairs, whose interval density decays at the sum of the two rates, its equation 12).
 *
 *   babadi run PARAMS     inputs drawn from the program's generator (xoshiro256** seeded by PARAMS' seed);
 *   babadi replay PARAMS SPIKES   inputs read from SPIKES (lines "k type index": step k, type 0 excitatory, 1
 *                         inhibitory), for the comparison with the module's plain implementation.
 *
 * PARAMS is a file of "key value" lines (keys below); winit names a file of N_ex initial strengths and wout the file
 * the final strengths are written to. Output lines: "cp t mean sd m3 frac0 max spikes" at each checkpoint (strength
 * statistics, then the postsynaptic spikes in the window), "runaway t" if a stop condition fired, "spike n" for each
 * postsynaptic spike in replay mode (n the step at whose start it falls, counted from the run's start), and
 * "end t spikes inputs_ex inputs_in meanV" at the end.
 *
 * Each step k of dt, from t = k dt: (1) the step's presynaptic spikes, at t, each adding its strength to its input
 * and, with plasticity, changing its synapse by F(t_lastpost - t) when the neuron has fired since that synapse's last
 * presynaptic spike; (2) the exact solution of the linear membrane and input equations over [t, t + dt]; (3) a
 * postsynaptic spike at t + dt if V >= V_th: V is reset and, with plasticity, every synapse that has received a
 * presynaptic spike since the previous postsynaptic spike (kept in a list as they arrive) is changed by
 * F(t + dt - t_lastpre). Strengths are kept at 0 or above, and at w_max or below when w_max > 0.
 *
 * Spike times are kept as whole steps (a presynaptic spike of step k at k, a postsynaptic spike at the end of step k at
 * k + 1) and intervals counted in steps, n dt, so that an interval of exactly d is the same at every time of a run and
 * depresses, as F's dt <= d says. (Times held in milliseconds as floating-point numbers rounded such intervals above or
 * below d according to the times' magnitude, so that they potentiated in some stretches of a run and depressed in
 * others.) k0, 0 unless set, starts the step count elsewhere: the results must not depend on it.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int nex, nin, plastic, fire;
    long long k0;
    double rex, rin, tau_m, vth, vr, tau_s, win, ap, am, tp, tn, d, wmax, T, dt, cp, stop_rate, stop_mean;
    uint64_t seed;
    char winit[512], wout[512];
} Par;

static uint64_t s[4];
static uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t next(void) {
    uint64_t r = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
    return r;
}
static void seed_rng(uint64_t x) {
    for (int i = 0; i < 4; i++) {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        s[i] = z ^ (z >> 31);
    }
}
static double uni(void) { return (next() >> 11) * 0x1.0p-53; }
static int poisson(double L) { /* L = exp(-mean) */
    int k = 0;
    double p = 1.0;
    do { k++; p *= uni(); } while (p > L);
    return k - 1;
}

static void die(const char *m) { fprintf(stderr, "babadi: %s\n", m); exit(2); }

static void read_par(const char *path, Par *P) {
    FILE *f = fopen(path, "r");
    char k[64], v[512];
    if (!f) die("cannot open params");
    memset(P, 0, sizeof *P);
    while (fscanf(f, "%63s %511s", k, v) == 2) {
#define D(name) else if (!strcmp(k, #name)) P->name = atof(v)
#define I(name) else if (!strcmp(k, #name)) P->name = atoi(v)
        if (0) {}
        I(nex); I(nin); I(plastic); I(fire);
        D(rex); D(rin); D(tau_m); D(vth); D(vr); D(tau_s); D(win); D(ap); D(am); D(tp); D(tn); D(d); D(wmax);
        D(T); D(dt); D(cp); D(stop_rate); D(stop_mean);
        else if (!strcmp(k, "seed")) P->seed = strtoull(v, NULL, 10);
        else if (!strcmp(k, "k0")) P->k0 = strtoll(v, NULL, 10);
        else if (!strcmp(k, "winit")) strncpy(P->winit, v, 511);
        else if (!strcmp(k, "wout")) strncpy(P->wout, v, 511);
        else die("unknown key");
    }
    fclose(f);
    if (P->nex < 1 || P->nex > 100000 || P->nin < 0 || P->dt <= 0 || P->T <= 0 || P->cp <= 0 || P->tau_s == P->tau_m ||
        P->k0 < 0 || P->k0 > 1000000000000LL)
        die("bad params");
}

static Par P;
static double *w, Iex = 0, Iin = 0, V;
static long long nspk = 0, nin_ex = 0, nin_in = 0, win_spk = 0, *postidx, *lastpre, lastpost = 0;
static int *pending, *flag, npend = 0;

static double F(long long n) { /* n = t_post - t_pre in steps */
    double dtt = n * P.dt;
    return dtt <= P.d + 1e-9 * P.dt ? -P.am * exp((dtt - P.d) / P.tn) : P.ap * exp(-(dtt - P.d) / P.tp);
}
static void clip(int i) {
    if (w[i] < 0) w[i] = 0;
    if (P.wmax > 0 && w[i] > P.wmax) w[i] = P.wmax;
}
static void pre_ex(int i, long long k) {
    Iex += w[i];
    nin_ex++;
    if (P.plastic && nspk > postidx[i]) { w[i] += F(lastpost - k); clip(i); }
    lastpre[i] = k;
    postidx[i] = nspk;
    if (!flag[i]) { flag[i] = 1; pending[npend++] = i; }
}
static void stats(double t) {
    double m = 0, v = 0, m3 = 0, mx = 0;
    long z = 0;
    for (int i = 0; i < P.nex; i++) { m += w[i]; if (w[i] > mx) mx = w[i]; if (w[i] == 0) z++; }
    m /= P.nex;
    for (int i = 0; i < P.nex; i++) { double e = w[i] - m; v += e * e; m3 += e * e * e; }
    v /= P.nex; m3 /= P.nex;
    printf("cp %.3f %.12g %.12g %.12g %.12g %.12g %lld\n", t / 1000.0, m, sqrt(v), m3, (double)z / P.nex, mx, win_spk);
}

int main(int argc, char **argv) {
    if (argc < 3) die("usage: babadi run PARAMS | babadi replay PARAMS SPIKES");
    int replay = !strcmp(argv[1], "replay");
    if (!replay && strcmp(argv[1], "run")) die("unknown mode");
    read_par(argv[2], &P);
    w = malloc(sizeof(double) * P.nex);
    lastpre = calloc(P.nex, sizeof(long long));
    postidx = calloc(P.nex, sizeof(long long));
    pending = malloc(sizeof(int) * P.nex);
    flag = calloc(P.nex, sizeof(int));
    FILE *fw = fopen(P.winit, "r");
    if (!fw) die("cannot open winit");
    for (int i = 0; i < P.nex; i++) {
        if (fscanf(fw, "%lf", &w[i]) != 1) die("short winit");
    }
    fclose(fw);
    FILE *fs = NULL;
    long long nk = -1;
    int ntype = 0, nidx = 0;
    if (replay) {
        if (argc < 4) die("replay needs SPIKES");
        fs = fopen(argv[3], "r");
        if (!fs) die("cannot open spikes");
        if (fscanf(fs, "%lld %d %d", &nk, &ntype, &nidx) != 3) nk = -1;
    }
    seed_rng(P.seed);
    V = P.vr;
    const double dt = P.dt, em = exp(-dt / P.tau_m), es = exp(-dt / P.tau_s), C = P.tau_s / (P.tau_s - P.tau_m);
    const double Le = exp(-P.nex * P.rex * dt / 1000.0), Li = exp(-P.nin * P.rin * dt / 1000.0);
    const long long steps = (long long)llround(P.T * 1000.0 / dt), cpk = (long long)llround(P.cp * 1000.0 / dt);
    double sumV = 0;
    long long k;
    for (k = 0; k < steps; k++) {
        const long long ka = P.k0 + k;
        if (replay) {
            while (nk == k) {
                if (ntype == 0) { if (nidx < 0 || nidx >= P.nex) die("bad index"); pre_ex(nidx, ka); }
                else { Iin += P.win; nin_in++; }
                if (fscanf(fs, "%lld %d %d", &nk, &ntype, &nidx) != 3) nk = -1;
            }
        } else {
            int ne = poisson(Le);
            for (int j = 0; j < ne; j++) pre_ex((int)(uni() * P.nex), ka);
            int ni = poisson(Li);
            Iin += P.win * ni;
            nin_in += ni;
        }
        double J = Iex - Iin;
        V = P.vr + (V - P.vr) * em + J * C * (es - em);
        Iex *= es;
        Iin *= es;
        sumV += V;
        if (P.fire && V >= P.vth) {
            const long long kp = ka + 1;
            V = P.vr;
            nspk++;
            win_spk++;
            if (replay) printf("spike %lld\n", kp - P.k0);
            for (int j = 0; j < npend; j++) {
                int i = pending[j];
                if (P.plastic) { w[i] += F(kp - lastpre[i]); clip(i); }
                flag[i] = 0;
            }
            npend = 0;
            lastpost = kp;
        }
        if ((k + 1) % cpk == 0) {
            double tt = (k + 1) * dt;
            stats(tt);
            double mean = 0;
            for (int i = 0; i < P.nex; i++) mean += w[i];
            mean /= P.nex;
            double rate = win_spk / P.cp;
            win_spk = 0;
            if ((P.stop_rate > 0 && rate > P.stop_rate) || (P.stop_mean > 0 && mean > P.stop_mean)) {
                printf("runaway %.3f\n", tt / 1000.0);
                k++;
                break;
            }
        }
    }
    printf("end %.3f %lld %lld %lld %.12g\n", k * dt / 1000.0, nspk, nin_ex, nin_in, sumV / (k > 0 ? k : 1));
    if (P.wout[0]) {
        FILE *fo = fopen(P.wout, "w");
        if (!fo) die("cannot write wout");
        for (int i = 0; i < P.nex; i++) fprintf(fo, "%.17g\n", w[i]);
        fclose(fo);
    }
    return 0;
}
