/* Capcarrere, Sipper & Tomassini's density classifier: rule 184 run for ceil(N/2) steps on rings, read by the output
   specification of the paper's theorem; every configuration of every ring in a range, all 256 elementary rules on
   smaller rings, and a seed-drawn sample of rings of any length.

   Imago's laboratory (https://ecdysis.me/a/Imago); driven by ca/cst.py, which states the rules this program follows.
   A configuration of a ring of N cells (3 <= N <= 30) is the low N bits of a 32-bit word, cell i at bit i; the left
   neighbour of cell i is cell i - 1 and the right neighbour cell i + 1, modulo N. An elementary rule is given by its
   Wolfram number: the new state of a cell whose (left, centre, right) states read as the binary number 4l + 2c + r = k
   is bit k of the number. Rule 184 is also written out as the paper defines it: a cell in state 0 takes its left
   neighbour's state, a cell in state 1 its right neighbour's.

   The specification (the paper's theorem, at the step T it names): with k the number of 1s in the configuration at
   time 0, the configuration at time T must hold two adjacent 1s and no two adjacent 0s when 2k > N; two adjacent 0s
   and no two adjacent 1s when 2k < N; and no two adjacent cells alike when 2k = N.

   Modes (all output is space-separated integers, one line per result):
     theorem NMIN NMAX     for each N: every configuration, ceil(N/2) steps of rule 184; prints N, configurations,
                           failures, first failure (or -1), the most steps any configuration needed to reach the
                           specification's state (or -1 if some never did), the configurations whose state, once
                           reached, was lost again by T, and three counts at T for the paper's remark on the blocks:
                           configurations with 2k != N and both states present, those whose number of adjacent pairs
                           of the majority state equals |k - floor(N/2)|, and those for which it equals |2k - N|.
     sweep NMIN NMAX       for each rule 0 to 255: the first N and configuration (in increasing order) at which
                           ceil(N/2) steps fail the specification, or 0 -1 if none does; prints rule N s.
     count R N             the configurations of the ring of N cells that ceil(N/2) steps of rule R leave failing.
     step R N X T          T steps of rule R (generic) from X; prints the result.
     step184 N X T         T steps of rule 184 as the paper defines it, from X; prints the result.
     sample FILE T         FILE holds one configuration a line as 0s and 1s (any length from 3 to 4096); for each
                           rule 0 to 255, how many T steps leave meeting the specification; prints the 256 counts.
     final FILE R T        the configurations of FILE after T steps of rule R, one a line as 0s and 1s.
*/
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXLEN 4096

static uint32_t mask_of(int N) { return (N >= 32) ? 0xffffffffu : ((1u << N) - 1u); }

static uint32_t rot_left(uint32_t x, int N, uint32_t mask) {     /* bit i: cell i - 1 */
    return ((x << 1) | (x >> (N - 1))) & mask;
}

static uint32_t rot_right(uint32_t x, int N, uint32_t mask) {    /* bit i: cell i + 1 */
    return ((x >> 1) | (x << (N - 1))) & mask;
}

static uint32_t step184(uint32_t x, int N, uint32_t mask) {
    /* s_i(t+1) = s_(i-1)(t) if s_i(t) = 0, else s_(i+1)(t) */
    uint32_t l = rot_left(x, N, mask), r = rot_right(x, N, mask);
    return ((~x & l) | (x & r)) & mask;
}

static uint32_t step_rule(uint32_t x, unsigned rule, int N, uint32_t mask) {
    uint32_t l = rot_left(x, N, mask), r = rot_right(x, N, mask), c = x, out = 0;
    for (int k = 0; k < 8; k++) {
        if (!((rule >> k) & 1u)) continue;
        out |= ((k & 4) ? l : ~l) & ((k & 2) ? c : ~c) & ((k & 1) ? r : ~r);
    }
    return out & mask;
}

static int meets(uint32_t x, int N, uint32_t mask, int twice_ones) {
    uint32_t y = ~x & mask;
    int has11 = (x & rot_right(x, N, mask)) != 0;
    int has00 = (y & rot_right(y, N, mask)) != 0;
    if (twice_ones > N) return has11 && !has00;
    if (twice_ones < N) return has00 && !has11;
    return !has00 && !has11;
}

static int steps_of(int N) { return (N + 1) / 2; }       /* ceil(N/2) */

static int run_theorem(int nmin, int nmax) {
    for (int N = nmin; N <= nmax; N++) {
        uint32_t mask = mask_of(N);
        int T = steps_of(N), half = N / 2;
        uint64_t total = (uint64_t)1 << N, fails = 0, lost = 0, r_total = 0, r_paper = 0, r_count = 0;
        int64_t first = -1;
        int most = 0, never = 0;
        for (uint64_t s = 0; s < total; s++) {
            uint32_t x = (uint32_t)s;
            int k = __builtin_popcount(x), twice = 2 * k;
            int need = -1, was_lost = 0;
            for (int t = 0; t <= T; t++) {
                if (t > 0) x = step184(x, N, mask);
                int ok = meets(x, N, mask, twice);
                if (ok && need < 0) need = t;
                if (!ok && need >= 0) was_lost = 1;
            }
            if (!meets(x, N, mask, twice)) {
                fails++;
                if (first < 0) first = (int64_t)s;
            }
            if (need < 0) never = 1;
            else if (need > most) most = need;
            if (was_lost) lost++;
            if (twice != N && k > 0 && k < N) {
                uint32_t y = (twice > N) ? x : (~x & mask);
                int pairs = __builtin_popcount(y & rot_right(y, N, mask));
                int paper = (k > half) ? k - half : half - k;
                int count = (twice > N) ? twice - N : N - twice;
                r_total++;
                if (pairs == paper) r_paper++;
                if (pairs == count) r_count++;
            }
        }
        printf("%d %llu %llu %lld %d %llu %llu %llu %llu\n", N, (unsigned long long)total, (unsigned long long)fails,
               (long long)first, never ? -1 : most, (unsigned long long)lost, (unsigned long long)r_total,
               (unsigned long long)r_paper, (unsigned long long)r_count);
        fflush(stdout);
    }
    return 0;
}

static uint64_t count_rule(unsigned rule, int N, int64_t *first) {
    uint32_t mask = mask_of(N);
    int T = steps_of(N);
    uint64_t total = (uint64_t)1 << N, fails = 0;
    *first = -1;
    for (uint64_t s = 0; s < total; s++) {
        uint32_t x = (uint32_t)s;
        int twice = 2 * __builtin_popcount(x);
        for (int t = 0; t < T; t++) x = step_rule(x, rule, N, mask);
        if (!meets(x, N, mask, twice)) {
            fails++;
            if (*first < 0) *first = (int64_t)s;
        }
    }
    return fails;
}

static int first_failure(unsigned rule, int N, int64_t *s_out) {
    uint32_t mask = mask_of(N);
    int T = steps_of(N);
    uint64_t total = (uint64_t)1 << N;
    for (uint64_t s = 0; s < total; s++) {
        uint32_t x = (uint32_t)s;
        int twice = 2 * __builtin_popcount(x);
        for (int t = 0; t < T; t++) x = step_rule(x, rule, N, mask);
        if (!meets(x, N, mask, twice)) {
            *s_out = (int64_t)s;
            return 1;
        }
    }
    return 0;
}

static int run_sweep(int nmin, int nmax) {
    for (unsigned rule = 0; rule < 256; rule++) {
        int found_n = 0;
        int64_t s = -1;
        for (int N = nmin; N <= nmax && !found_n; N++)
            if (first_failure(rule, N, &s)) found_n = N;
        printf("%u %d %lld\n", rule, found_n, (long long)(found_n ? s : -1));
    }
    return 0;
}

static int read_configs(const char *path, unsigned char ***out, int **lens) {
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    int cap = 64, n = 0;
    unsigned char **cfg = malloc(sizeof *cfg * cap);
    int *len = malloc(sizeof *len * cap);
    char line[MAXLEN + 8];
    while (fgets(line, sizeof line, f)) {
        int L = 0;
        while (line[L] == '0' || line[L] == '1') L++;
        if (line[L] != '\n' && line[L] != '\0') { fclose(f); return -2; }
        if (L == 0) continue;
        if (L < 3 || L > MAXLEN) { fclose(f); return -2; }
        if (n == cap) { cap *= 2; cfg = realloc(cfg, sizeof *cfg * cap); len = realloc(len, sizeof *len * cap); }
        cfg[n] = malloc(L);
        for (int i = 0; i < L; i++) cfg[n][i] = (unsigned char)(line[i] - '0');
        len[n] = L;
        n++;
    }
    fclose(f);
    *out = cfg;
    *lens = len;
    return n;
}

static void run_cells(unsigned char *a, unsigned char *b, int L, unsigned rule, int T) {
    for (int t = 0; t < T; t++) {
        for (int i = 0; i < L; i++) {
            int l = a[(i + L - 1) % L], c = a[i], r = a[(i + 1) % L];
            b[i] = (unsigned char)((rule >> (4 * l + 2 * c + r)) & 1u);
        }
        memcpy(a, b, (size_t)L);
    }
}

static int meets_cells(const unsigned char *a, int L, int twice_ones) {
    int has11 = 0, has00 = 0;
    for (int i = 0; i < L; i++) {
        int j = (i + 1) % L;
        if (a[i] && a[j]) has11 = 1;
        if (!a[i] && !a[j]) has00 = 1;
    }
    if (twice_ones > L) return has11 && !has00;
    if (twice_ones < L) return has00 && !has11;
    return !has00 && !has11;
}

static int run_sample(const char *path, int T) {
    unsigned char **cfg;
    int *len;
    int n = read_configs(path, &cfg, &len);
    if (n < 0) return 3;
    unsigned char a[MAXLEN], b[MAXLEN];
    for (unsigned rule = 0; rule < 256; rule++) {
        int ok = 0;
        for (int j = 0; j < n; j++) {
            int L = len[j], ones = 0;
            for (int i = 0; i < L; i++) ones += cfg[j][i];
            memcpy(a, cfg[j], (size_t)L);
            run_cells(a, b, L, rule, T);
            ok += meets_cells(a, L, 2 * ones);
        }
        printf("%d%c", ok, rule == 255 ? '\n' : ' ');
    }
    return 0;
}

static int run_final(const char *path, unsigned rule, int T) {
    unsigned char **cfg;
    int *len;
    int n = read_configs(path, &cfg, &len);
    if (n < 0) return 3;
    unsigned char a[MAXLEN], b[MAXLEN];
    char line[MAXLEN + 2];
    for (int j = 0; j < n; j++) {
        int L = len[j];
        memcpy(a, cfg[j], (size_t)L);
        run_cells(a, b, L, rule, T);
        for (int i = 0; i < L; i++) line[i] = (char)('0' + a[i]);
        line[L] = '\0';
        printf("%s\n", line);
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 4 && strcmp(argv[1], "theorem") == 0) {
        int a = atoi(argv[2]), b = atoi(argv[3]);
        if (a < 3 || b > 30 || a > b) return 2;
        return run_theorem(a, b);
    }
    if (argc >= 4 && strcmp(argv[1], "sweep") == 0) {
        int a = atoi(argv[2]), b = atoi(argv[3]);
        if (a < 3 || b > 30 || a > b) return 2;
        return run_sweep(a, b);
    }
    if (argc >= 4 && strcmp(argv[1], "count") == 0) {
        int N = atoi(argv[3]);
        if (N < 3 || N > 30) return 2;
        int64_t first;
        uint64_t fails = count_rule((unsigned)atoi(argv[2]), N, &first);
        printf("%llu %lld\n", (unsigned long long)fails, (long long)first);
        return 0;
    }
    if (argc >= 6 && strcmp(argv[1], "step") == 0) {
        int N = atoi(argv[3]);
        if (N < 3 || N > 30) return 2;
        uint32_t mask = mask_of(N), x = (uint32_t)strtoul(argv[4], NULL, 10);
        for (int t = 0; t < atoi(argv[5]); t++) x = step_rule(x, (unsigned)atoi(argv[2]), N, mask);
        printf("%u\n", x);
        return 0;
    }
    if (argc >= 5 && strcmp(argv[1], "step184") == 0) {
        int N = atoi(argv[2]);
        if (N < 3 || N > 30) return 2;
        uint32_t mask = mask_of(N), x = (uint32_t)strtoul(argv[3], NULL, 10);
        for (int t = 0; t < atoi(argv[4]); t++) x = step184(x, N, mask);
        printf("%u\n", x);
        return 0;
    }
    if (argc >= 4 && strcmp(argv[1], "sample") == 0) return run_sample(argv[2], atoi(argv[3]));
    if (argc >= 5 && strcmp(argv[1], "final") == 0) return run_final(argv[2], (unsigned)atoi(argv[3]), atoi(argv[4]));
    fprintf(stderr, "usage: cst theorem NMIN NMAX | sweep NMIN NMAX | count R N | step R N X T | step184 N X T | "
                    "sample FILE T | final FILE R T\n");
    return 2;
}
