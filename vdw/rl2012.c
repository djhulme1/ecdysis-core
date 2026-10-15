/* The arithmetic of vdw/rl2012.py (Rabung & Lotts's cyclic zipper lower bounds for van der Waerden numbers).

   Imago's laboratory (https://ecdysis.me/a/Imago). Four modes:

   crit k l p z g
       The power classes mod the prime p from its primitive root g: x = g^e (mod p) has class e mod k, for e = 0 to
       p - 2; every nonzero residue must be reached exactly once (else "cover 0"). For z = 0 the colouring of Z_p is
       the classes; for z = 1 the zipped colouring of Z_2p is kappa(y) = class(y mod p) + (k/2)[y even] (mod k), y not
       a multiple of p. Prints one line of nine integers:
           cover  n2_run  n2_at  n3_bad  n3_first  z3a_run  z3a_at  z3b_bad  z3b_first
       n2_run: the longest run of consecutive residues in [1, p - 1] in one class, n2_at the start of the first run of
       length >= l (0 if none). n3_bad: the number of positions i0 in [0, l - 1] at which the l-string of residues
       with 0 in place i0 (-i0, ..., -1, 0, 1, ..., l - 1 - i0, mod p) has its l - 1 nonzero members in one class;
       n3_first the first such i0 (-1 if none). For z = 1, z3a_run and z3a_at likewise for the runs of kappa inside
       [1, p - 1] and [p + 1, 2p - 1], and z3b_bad and z3b_first for the l-strings of Z_2p with 0 or p in place i0
       (z3b_first is i0, or l + i0 for the strings through p); for z = 0 these four are -1.
   kappa k p g z FILE
       Writes the colouring of the numbers 1 to 2^z p (number y is the residue y - 1) as bytes: the class (as above)
       of y - 1, or 255 where y - 1 is a multiple of p.
   scan FILE l
       Every progression x, x + d, ..., x + (l - 1)d with 1 <= x, x + (l - 1)d <= n, d >= 1 is examined, n the file's
       length, byte y - 1 the class of number y (255 free). Prints "count pairs first_x first_d": those whose l
       numbers are all fixed and in one class, the number examined, and the first in one class (by d, then x), or
       0 0. Two threads take the differences in turn.
   forbid FILE l
       As vdw/hhlm.c's forbid, for l from 3 to 16: for each free number y, class c is forbidden if some progression
       through y has its other l - 1 numbers fixed and in class c; prints "y mask" and, for c = 0 to 7, the first
       such progression "x d" (0 0 if none), then "multi m", the progressions holding two free numbers and a fixed
       one. */

#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FREE 255
#define LMAX 16

static unsigned char *col;
static long n;
static int L;

static unsigned char *classes(long k, long p, long g, int *cover) {
    unsigned char *cls = malloc((size_t)p);
    if (!cls) { fprintf(stderr, "out of memory\n"); exit(2); }
    memset(cls, FREE, (size_t)p);
    uint64_t x = 1;
    *cover = 1;
    for (long e = 0; e < p - 1; e++) {
        if (x == 0 || cls[x] != FREE) { *cover = 0; break; }
        cls[x] = (unsigned char)(e % k);
        x = x * (uint64_t)g % (uint64_t)p;
    }
    if (*cover && x != 1) *cover = 0;
    for (long y = 1; *cover && y < p; y++) if (cls[y] == FREE) *cover = 0;
    return cls;
}

/* The longest run of one colour among c[a..b] (inclusive), and the start of the first run of length >= l. */
static void runs(const unsigned char *c, long a, long b, int l, long *best, long *first) {
    long run = 0;
    for (long y = a; y <= b; y++) {
        run = (y > a && c[y] == c[y - 1]) ? run + 1 : 1;
        if (run > *best) *best = run;
        if (run >= l && !*first) *first = y - l + 1;
    }
}

static void crit(long k, int l, long p, int z, long g) {
    int cover;
    unsigned char *cls = classes(k, p, g, &cover);
    long n2_run = 0, n2_at = 0, n3_bad = 0, n3_first = -1;
    long z3a_run = -1, z3a_at = -1, z3b_bad = -1, z3b_first = -1;
    if (cover) {
        runs(cls, 1, p - 1, l, &n2_run, &n2_at);
        for (int i0 = 0; i0 < l; i0++) {
            int c = -1, same = 1;
            for (int i = 0; i < l; i++) {
                if (i == i0) continue;
                long y = ((long)(i - i0) % p + p) % p;
                if (c < 0) c = cls[y];
                else if (cls[y] != c) same = 0;
            }
            if (same) { n3_bad++; if (n3_first < 0) n3_first = i0; }
        }
        if (z == 1) {
            long m = 2 * p, h = k / 2;
            unsigned char *kap = malloc((size_t)m);
            if (!kap) { fprintf(stderr, "out of memory\n"); exit(2); }
            for (long y = 0; y < m; y++)
                kap[y] = (y % p == 0) ? FREE : (unsigned char)((cls[y % p] + ((y % 2 == 0) ? h : 0)) % k);
            z3a_run = 0; z3a_at = 0;
            runs(kap, 1, p - 1, l, &z3a_run, &z3a_at);
            long at2 = 0;
            runs(kap, p + 1, m - 1, l, &z3a_run, &at2);
            if (!z3a_at) z3a_at = at2;
            z3b_bad = 0;
            for (int base = 0; base < 2; base++) {
                long centre = base ? p : 0;
                for (int i0 = 0; i0 < l; i0++) {
                    int c = -1, same = 1;
                    for (int i = 0; i < l; i++) {
                        if (i == i0) continue;
                        long y = ((centre + i - i0) % m + m) % m;
                        if (c < 0) c = kap[y];
                        else if (kap[y] != c) same = 0;
                    }
                    if (same) { z3b_bad++; if (z3b_first < 0) z3b_first = base * l + i0; }
                }
            }
            free(kap);
        }
    }
    printf("%d %ld %ld %ld %ld %ld %ld %ld %ld\n", cover, n2_run, n2_at, n3_bad, n3_first, z3a_run, z3a_at, z3b_bad,
           z3b_first);
    free(cls);
}

static void kappa(long k, long p, long g, int z, const char *path) {
    int cover;
    unsigned char *cls = classes(k, p, g, &cover);
    if (!cover) { fprintf(stderr, "%ld is not a primitive root of %ld\n", g, p); exit(2); }
    long m = z ? 2 * p : p, h = k / 2;
    FILE *f = fopen(path, "wb");
    if (!f) { perror(path); exit(2); }
    for (long y = 0; y < m; y++) {
        unsigned char v = (y % p == 0) ? FREE
                          : (unsigned char)((cls[y % p] + ((z && y % 2 == 0) ? h : 0)) % k);
        fputc(v, f);
    }
    fclose(f);
    free(cls);
}

static void load(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    col = malloc(n > 0 ? (size_t)n : 1);
    if (!col || fread(col, 1, (size_t)n, f) != (size_t)n) { fprintf(stderr, "read %s failed\n", path); exit(2); }
    fclose(f);
}

static int mono_at(long x, long d) {
    unsigned char a = col[x];
    if (a == FREE) return 0;
    for (int t = 1; t < L; t++)
        if (col[x + t * d] != a) return 0;
    return 1;
}

struct part { int id, threads; uint64_t count, pairs; long fx, fd; };

static void *scan_part(void *arg) {
    struct part *P = arg;
    unsigned char *acc = malloc(n > 0 ? (size_t)n : 1);
    if (!acc) { fprintf(stderr, "out of memory\n"); exit(2); }
    for (long d = 1 + P->id; (long)(L - 1) * d <= n - 1; d += P->threads) {
        long lim = n - (long)(L - 1) * d;
        P->pairs += (uint64_t)lim;
        for (long x = 0; x < lim; x++) acc[x] = (unsigned char)(col[x] != FREE);
        for (int t = 1; t < L; t++) {
            const unsigned char *c = col + t * d;
            for (long x = 0; x < lim; x++) acc[x] &= (unsigned char)(col[x] == c[x]);
        }
        unsigned char any = 0;
        for (long x = 0; x < lim; x++) any |= acc[x];
        if (!any) continue;
        for (long x = 0; x < lim; x++) {
            if (mono_at(x, d)) {
                if (!P->count || d < P->fd || (d == P->fd && x + 1 < P->fx)) { P->fx = x + 1; P->fd = d; }
                P->count++;
            }
        }
    }
    free(acc);
    return NULL;
}

static void scan(void) {
    enum { T = 2 };
    pthread_t th[T];
    struct part parts[T];
    for (int i = 0; i < T; i++) {
        parts[i] = (struct part){i, T, 0, 0, 0, 0};
        pthread_create(&th[i], NULL, scan_part, &parts[i]);
    }
    uint64_t count = 0, pairs = 0;
    long fx = 0, fd = 0;
    for (int i = 0; i < T; i++) {
        pthread_join(th[i], NULL);
        count += parts[i].count;
        pairs += parts[i].pairs;
        if (parts[i].count && (!fd || parts[i].fd < fd || (parts[i].fd == fd && parts[i].fx < fx))) {
            fx = parts[i].fx;
            fd = parts[i].fd;
        }
    }
    printf("%llu %llu %ld %ld\n", (unsigned long long)count, (unsigned long long)pairs, fx, fd);
}

static void forbid(void) {
    uint64_t multi = 0;
    for (long y = 0; y < n; y++) {
        if (col[y] != FREE) continue;
        unsigned mask = 0;
        long wx[8], wd[8];
        memset(wx, 0, sizeof wx);
        memset(wd, 0, sizeof wd);
        for (long d = 1; (long)(L - 1) * d <= n - 1; d++) {
            for (int t = 0; t < L; t++) {
                long x = y - (long)t * d;
                if (x < 0 || x + (long)(L - 1) * d > n - 1) continue;
                int frees = 0, fixed = 0, same = 1;
                unsigned char a = FREE;
                for (int s = 0; s < L; s++) {
                    if (s == t) continue;
                    unsigned char v = col[x + s * d];
                    if (v == FREE) { frees++; continue; }
                    if (a == FREE) a = v;
                    else if (v != a) same = 0;
                    fixed++;
                }
                if (frees && fixed) { multi++; continue; }
                if (frees || !same || a >= 8) continue;
                if (!(mask & (1u << a))) { wx[a] = x + 1; wd[a] = d; }
                mask |= 1u << a;
            }
        }
        printf("%ld %u", y + 1, mask);
        for (int c = 0; c < 8; c++) printf(" %ld %ld", wx[c], wd[c]);
        printf("\n");
    }
    printf("multi %llu\n", (unsigned long long)multi);
}

int main(int argc, char **argv) {
    if (argc == 7 && !strcmp(argv[1], "crit")) {
        long k = atol(argv[2]), p = atol(argv[4]), g = atol(argv[6]);
        int l = atoi(argv[3]), z = atoi(argv[5]);
        if (k < 2 || k > 8 || l < 3 || l > LMAX || p < 3 || l >= p || (z != 0 && z != 1) || (z && k % 2)) {
            fprintf(stderr, "crit: arguments out of range\n");
            return 2;
        }
        crit(k, l, p, z, g);
        return 0;
    }
    if (argc == 7 && !strcmp(argv[1], "kappa")) {
        long k = atol(argv[2]), p = atol(argv[3]), g = atol(argv[4]);
        int z = atoi(argv[5]);
        if (k < 2 || k > 8 || p < 3 || (z != 0 && z != 1) || (z && k % 2)) {
            fprintf(stderr, "kappa: arguments out of range\n");
            return 2;
        }
        kappa(k, p, g, z, argv[6]);
        return 0;
    }
    if (argc == 4 && (!strcmp(argv[1], "scan") || !strcmp(argv[1], "forbid"))) {
        L = atoi(argv[3]);
        if (L < 3 || L > LMAX) { fprintf(stderr, "l = %d: only 3 to %d\n", L, LMAX); return 2; }
        load(argv[2]);
        if (!strcmp(argv[1], "scan")) scan();
        else forbid();
        return 0;
    }
    fprintf(stderr, "usage: rl2012 crit k l p z g | kappa k p g z FILE | scan FILE l | forbid FILE l\n");
    return 2;
}
