/* Sayama's evoloops, original and self-protecting: the update and the census, for evoloop/selfprotect.py.

   Imago's laboratory (https://ecdysis.me/a/Imago). Integer arithmetic only, so a run is the same on every machine.

   Usage: sp TABLE GRID L UPDATES WINDOW_FROM DETECTOR OUT [SNAPSHOT_UPDATE ...]
     TABLE     10^5 bytes: the image of each situation, at index (((c*10 + n)*10 + e)*10 + s)*10 + w, where c is the
               site and n, e, s, w its north, east, south and west neighbours (north is the row above).
     GRID      L*L bytes, row-major, row 0 at the top: the configuration at update 0.
     WINDOW_FROM  the update after which a census is taken every SAMPLE updates (200,000 for the test).
     DETECTOR  the attack detector counted as sheath in the second census (9, 8, or -1 for none).
     OUT       the census records, binary, one per census; SNAPSHOT_UPDATEs write the grid to OUT.<t>.

   The census is evoloop/check.py's: a loop is counted by its hole, a 4-connected region of state 0 on the torus of
   at most MAX_HOLE sites that fills a rectangle whose surrounding ring, corners included, is all sheath. A square
   hole of side h is a loop of size h + 2; other rectangles are variants. It is taken twice, with the sheath states 2
   and 3 (the test's) and with the detector as well (beside the test), at every update t with t % EVERY == 0, or
   t > WINDOW_FROM and t % SAMPLE == 0 (the paper's sampling: every 40 updates from 200,000).

   A record: int32 t, int32 live sites, then for each census uint16 counts of sizes 3 to 22 and uint16 variants. */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define Q 10
#define NTAB 100000
#define MAX_HOLE 400
#define MIN_SIZE 3
#define NBINS 20 /* sizes 3 to 22: a square hole of at most 400 sites has a side of at most 20 */
#define EVERY 1000
#define SAMPLE 40

static int L;
static uint8_t *visited;
static int32_t *stack_x, *stack_y;

static void die(const char *msg) {
    fprintf(stderr, "sp: %s\n", msg);
    exit(2);
}

static void step(const uint8_t *tab, const uint8_t *a, uint8_t *b) {
    for (int y = 0; y < L; y++) {
        const uint8_t *up = a + (size_t)((y + L - 1) % L) * L, *row = a + (size_t)y * L,
                      *dn = a + (size_t)((y + 1) % L) * L;
        uint8_t *out = b + (size_t)y * L;
        out[0] = tab[(((row[0] * Q + up[0]) * Q + row[1]) * Q + dn[0]) * Q + row[L - 1]];
        for (int x = 1; x < L - 1; x++)
            out[x] = tab[(((row[x] * Q + up[x]) * Q + row[x + 1]) * Q + dn[x]) * Q + row[x - 1]];
        out[L - 1] = tab[(((row[L - 1] * Q + up[L - 1]) * Q + row[0]) * Q + dn[L - 1]) * Q + row[L - 2]];
    }
}

static int wrap(int v) {
    v %= L;
    return v < 0 ? v + L : v;
}

/* Both censuses at once. sheath1 and sheath2 flag the states counted as sheath. */
static void census(const uint8_t *g, const uint8_t *sheath1, const uint8_t *sheath2, uint16_t *c1, uint16_t *c2) {
    memset(visited, 0, (size_t)L * L);
    memset(c1, 0, sizeof(uint16_t) * (NBINS + 1));
    memset(c2, 0, sizeof(uint16_t) * (NBINS + 1));
    for (int start = 0; start < L * L; start++) {
        if (g[start] != 0 || visited[start]) continue;
        /* flood the region from start, carrying unwrapped coordinates */
        int top = 0, count = 0;
        int x0 = start % L, y0 = start / L;
        int minx = x0, maxx = x0, miny = y0, maxy = y0;
        visited[start] = 1;
        stack_x[top] = x0;
        stack_y[top] = y0;
        top++;
        while (top) {
            top--;
            int ux = stack_x[top], uy = stack_y[top];
            count++;
            if (count <= MAX_HOLE) {
                if (ux < minx) minx = ux;
                if (ux > maxx) maxx = ux;
                if (uy < miny) miny = uy;
                if (uy > maxy) maxy = uy;
            }
            static const int dx[4] = {0, 1, 0, -1}, dy[4] = {-1, 0, 1, 0};
            for (int d = 0; d < 4; d++) {
                int nx = ux + dx[d], ny = uy + dy[d];
                int q = wrap(ny) * L + wrap(nx);
                if (g[q] == 0 && !visited[q]) {
                    visited[q] = 1;
                    stack_x[top] = nx;
                    stack_y[top] = ny;
                    top++;
                }
            }
        }
        if (count > MAX_HOLE) continue;
        int h = maxy - miny + 1, w = maxx - minx + 1;
        if (h * w != count) continue;
        /* the surrounding ring, corners included */
        int ok1 = 1, ok2 = 1;
        for (int x = minx - 1; x <= maxx + 1 && (ok1 || ok2); x++) {
            uint8_t a = g[wrap(miny - 1) * L + wrap(x)], b = g[wrap(maxy + 1) * L + wrap(x)];
            ok1 &= sheath1[a] & sheath1[b];
            ok2 &= sheath2[a] & sheath2[b];
        }
        for (int y = miny; y <= maxy && (ok1 || ok2); y++) {
            uint8_t a = g[wrap(y) * L + wrap(minx - 1)], b = g[wrap(y) * L + wrap(maxx + 1)];
            ok1 &= sheath1[a] & sheath1[b];
            ok2 &= sheath2[a] & sheath2[b];
        }
        if (h == w) {
            int bin = h + 2 - MIN_SIZE;
            if (bin < 0 || bin >= NBINS) die("a square hole outside the bins");
            if (ok1) c1[bin]++;
            if (ok2) c2[bin]++;
        } else {
            if (ok1) c1[NBINS]++;
            if (ok2) c2[NBINS]++;
        }
    }
}

static void snapshot(const char *out, long t, const uint8_t *g) {
    char name[4096];
    snprintf(name, sizeof name, "%s.%ld", out, t);
    FILE *f = fopen(name, "wb");
    if (!f || fwrite(g, 1, (size_t)L * L, f) != (size_t)L * L) die("cannot write a snapshot");
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 8) die("usage: sp TABLE GRID L UPDATES WINDOW_FROM DETECTOR OUT [SNAPSHOT_UPDATE ...]");
    L = atoi(argv[3]);
    long T = atol(argv[4]);
    long window_from = atol(argv[5]);
    int detector = atoi(argv[6]);
    const char *out = argv[7];
    if (L < 8 || L > 4096 || T < 0) die("bad size or number of updates");
    uint8_t *tab = malloc(NTAB), *a = malloc((size_t)L * L), *b = malloc((size_t)L * L);
    visited = malloc((size_t)L * L);
    /* each site is pushed at most once, so a stack of L*L entries is enough */
    stack_x = malloc(sizeof(int32_t) * (size_t)L * L);
    stack_y = malloc(sizeof(int32_t) * (size_t)L * L);
    if (!tab || !a || !b || !visited || !stack_x || !stack_y) die("out of memory");
    FILE *f = fopen(argv[1], "rb");
    if (!f || fread(tab, 1, NTAB, f) != NTAB) die("cannot read the table");
    fclose(f);
    for (int i = 0; i < NTAB; i++)
        if (tab[i] >= Q) die("the table has an image outside the states");
    f = fopen(argv[2], "rb");
    if (!f || fread(a, 1, (size_t)L * L, f) != (size_t)L * L) die("cannot read the grid");
    fclose(f);
    for (long i = 0; i < (long)L * L; i++)
        if (a[i] >= Q) die("the grid has a state outside the states");
    int nsnap = argc - 8;
    long *snaps = malloc(sizeof(long) * (nsnap + 1));
    for (int i = 0; i < nsnap; i++) snaps[i] = atol(argv[8 + i]);

    uint8_t sheath1[256] = {0}, sheath2[256] = {0};
    sheath1[2] = sheath1[3] = sheath2[2] = sheath2[3] = 1;
    if (detector >= 0 && detector < Q) sheath2[detector] = 1;

    FILE *rec = fopen(out, "wb");
    if (!rec) die("cannot write the records");
    uint16_t c1[NBINS + 1], c2[NBINS + 1];
    for (long t = 0; t <= T; t++) {
        if (t > 0) {
            step(tab, a, b);
            uint8_t *tmp = a;
            a = b;
            b = tmp;
        }
        for (int i = 0; i < nsnap; i++)
            if (snaps[i] == t) snapshot(out, t, a);
        if (t % EVERY == 0 || (t > window_from && t % SAMPLE == 0)) {
            census(a, sheath1, sheath2, c1, c2);
            int32_t head[2];
            head[0] = (int32_t)t;
            head[1] = 0;
            for (long i = 0; i < (long)L * L; i++) head[1] += a[i] != 0;
            if (fwrite(head, sizeof head, 1, rec) != 1 || fwrite(c1, sizeof c1, 1, rec) != 1 ||
                fwrite(c2, sizeof c2, 1, rec) != 1)
                die("cannot write a record");
        }
    }
    fclose(rec);
    return 0;
}
