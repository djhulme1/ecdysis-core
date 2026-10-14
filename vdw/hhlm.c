/* The progression scans of vdw/hhlm.py (Herwig, Heule, van Lambalgen & van Maaren's Cyclic Zipper certificates).

   Imago's laboratory (https://ecdysis.me/a/Imago). A colouring is a file of bytes, one a number: byte y - 1 holds the
   class of the number y (0 to r - 1), or 255 for a free number, whose class the run chooses afterwards.

   scan FILE k
       Every progression x, x + d, ..., x + (k - 1)d with 1 <= x, x + (k - 1)d <= n and d >= 1 is examined. Prints
       "count pairs first_x first_d": the number of those whose k numbers are all fixed and in one class, the number
       of progressions examined, and the first one in one class (by d, then x), or 0 0.
   forbid FILE k
       For each free number y, every progression through y is examined. If its other k - 1 numbers are all fixed and
       in one class c, class c is forbidden to y. Prints, for each free y in increasing order, "y mask" and then, for
       c = 0 to 7, the first such progression "x d" (0 0 if none). Last, "multi m": the number of progressions
       holding two or more free numbers and at least one fixed one, which the run requires to be 0. Progressions of
       free numbers only are left to the run.

   The fast path of scan ORs, for each d, the indicator of a progression in one class over all x (a loop the compiler
   vectorises); only a d with a hit is counted again one x at a time. */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FREE 255

static unsigned char *col;
static long n;

static void load(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    col = malloc(n > 0 ? n : 1);
    if (!col || fread(col, 1, n, f) != (size_t)n) { fprintf(stderr, "read %s failed\n", path); exit(2); }
    fclose(f);
}

/* Whether some x in [0, lim) starts a progression of difference d in one class, all fixed. */
static int any_d(int k, long d, long lim) {
    const unsigned char *c0 = col, *c1 = col + d, *c2 = col + 2 * d, *c3 = col + 3 * d, *c4 = col + 4 * d,
                        *c5 = col + 5 * d, *c6 = col + 6 * d, *c7 = col + 7 * d, *c8 = col + 8 * d;
    unsigned char acc = 0;
    long x;
    switch (k) {
    case 3:
        for (x = 0; x < lim; x++) {
            unsigned char a = c0[x];
            acc |= (unsigned char)((a != FREE) & (a == c1[x]) & (a == c2[x]));
        }
        break;
    case 4:
        for (x = 0; x < lim; x++) {
            unsigned char a = c0[x];
            acc |= (unsigned char)((a != FREE) & (a == c1[x]) & (a == c2[x]) & (a == c3[x]));
        }
        break;
    case 5:
        for (x = 0; x < lim; x++) {
            unsigned char a = c0[x];
            acc |= (unsigned char)((a != FREE) & (a == c1[x]) & (a == c2[x]) & (a == c3[x]) & (a == c4[x]));
        }
        break;
    case 6:
        for (x = 0; x < lim; x++) {
            unsigned char a = c0[x];
            acc |= (unsigned char)((a != FREE) & (a == c1[x]) & (a == c2[x]) & (a == c3[x]) & (a == c4[x]) &
                                   (a == c5[x]));
        }
        break;
    case 7:
        for (x = 0; x < lim; x++) {
            unsigned char a = c0[x];
            acc |= (unsigned char)((a != FREE) & (a == c1[x]) & (a == c2[x]) & (a == c3[x]) & (a == c4[x]) &
                                   (a == c5[x]) & (a == c6[x]));
        }
        break;
    case 8:
        for (x = 0; x < lim; x++) {
            unsigned char a = c0[x];
            acc |= (unsigned char)((a != FREE) & (a == c1[x]) & (a == c2[x]) & (a == c3[x]) & (a == c4[x]) &
                                   (a == c5[x]) & (a == c6[x]) & (a == c7[x]));
        }
        break;
    case 9:
        for (x = 0; x < lim; x++) {
            unsigned char a = c0[x];
            acc |= (unsigned char)((a != FREE) & (a == c1[x]) & (a == c2[x]) & (a == c3[x]) & (a == c4[x]) &
                                   (a == c5[x]) & (a == c6[x]) & (a == c7[x]) & (a == c8[x]));
        }
        break;
    default:
        fprintf(stderr, "k = %d: only 3 to 9\n", k);
        exit(2);
    }
    return acc != 0;
}

/* One x at a time: whether x starts a progression of difference d in one class, all fixed. */
static int mono_at(int k, long x, long d) {
    unsigned char a = col[x];
    if (a == FREE) return 0;
    for (int t = 1; t < k; t++)
        if (col[x + t * d] != a) return 0;
    return 1;
}

static void scan(int k) {
    uint64_t count = 0, pairs = 0;
    long fx = 0, fd = 0;
    for (long d = 1; (long)(k - 1) * d <= n - 1; d++) {
        long lim = n - (long)(k - 1) * d;
        pairs += (uint64_t)lim;
        if (!any_d(k, d, lim)) continue;
        for (long x = 0; x < lim; x++) {
            if (mono_at(k, x, d)) {
                if (!count) { fx = x + 1; fd = d; }
                count++;
            }
        }
    }
    printf("%llu %llu %ld %ld\n", (unsigned long long)count, (unsigned long long)pairs, fx, fd);
}

static void forbid(int k) {
    uint64_t multi = 0;
    for (long y = 0; y < n; y++) {
        if (col[y] != FREE) continue;
        unsigned mask = 0;
        long wx[8], wd[8];
        memset(wx, 0, sizeof wx);
        memset(wd, 0, sizeof wd);
        for (long d = 1; (long)(k - 1) * d <= n - 1; d++) {
            for (int t = 0; t < k; t++) {
                long x = y - (long)t * d;
                if (x < 0 || x + (long)(k - 1) * d > n - 1) continue;
                int frees = 0, fixed = 0, same = 1;
                unsigned char a = FREE;
                for (int s = 0; s < k; s++) {
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
    if (argc != 4) {
        fprintf(stderr, "usage: hhlm scan|forbid FILE k\n");
        return 2;
    }
    int k = atoi(argv[3]);
    if (k < 3 || k > 9) { fprintf(stderr, "k = %d: only 3 to 9\n", k); return 2; }
    load(argv[2]);
    if (!strcmp(argv[1], "scan")) scan(k);
    else if (!strcmp(argv[1], "forbid")) forbid(k);
    else { fprintf(stderr, "unknown mode %s\n", argv[1]); return 2; }
    return 0;
}
