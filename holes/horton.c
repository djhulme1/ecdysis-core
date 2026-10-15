/* holes/horton.c: empty convex polygons in a planar point set, counted exactly.
 *
 * Imago's laboratory; the engine of holes/horton.py (Horton 1983, ext:43277d513fc8f74d). Reads a point set from a
 * file (n, then n lines "x y" in decimal) and works in signed 128-bit integers; it refuses a set whose coordinates
 * could make an orientation overflow (bits of 2 max|x| plus bits of 2 max|y| above 125).
 *
 *   horton count FILE   prints "collinear C", "counts c3 c4 c5 c6 c7" and "work W": C counts pairs of points
 *                       adjacent in angle around a lower point and collinear with it (positive exactly when three are
 *                       collinear); c3..c6 the empty convex triangles to hexagons; c7 the empty convex polygons of 7 or
 *                       more vertices; W the orientation tests made.
 *   horton above FILE   for the paper's observation (g), with the points in index order (B the even indices, T the
 *                       odd): prints "above V1 V2", V1 the triples (b1, b2, t) with t not strictly above the line
 *                       through b1 and b2, V2 the triples (t1, t2, b) with b not strictly below the line through
 *                       t1 and t2.
 *
 * Counting (the module's rule 2): each empty convex polygon is counted once, by its lowest vertex p (least y, then
 * least x). Around p, the points above it are sorted counterclockwise; the fan triangle (p, q_i, q_j), i < j, is
 * empty exactly when q_j is counterclockwise of every q_l, i < l < j, as seen from q_i (they all lie in the open
 * half-plane left of p -> q_i, where that order is total). A polygon p, v_1, ..., v_m is a chain of empty fan
 * triangles turning left at every v_t; the turns at v_1 and v_m are left by the angular order.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef __int128 i128;
typedef struct { i128 x, y; } P;

static P *pts;
static int n;
static const P *apex;
static long long work;

static i128 orient(const P *a, const P *b, const P *c) {
    work++;
    return (b->x - a->x) * (c->y - a->y) - (b->y - a->y) * (c->x - a->x);
}

static int above(const P *p, const P *q) {
    return q->y > p->y || (q->y == p->y && q->x > p->x);
}

static int by_angle(const void *u, const void *v) {
    const P *a = &pts[*(const int *)u], *b = &pts[*(const int *)v];
    i128 o = (b->x - apex->x) * (a->y - apex->y) - (b->y - apex->y) * (a->x - apex->x);
    /* o < 0 when a comes before b counterclockwise (orient(apex, a, b) > 0) */
    return o < 0 ? -1 : (o > 0 ? 1 : 0);
}

static int parse(const char *s, i128 *out) {
    int neg = 0;
    i128 v = 0, cap = ((i128)1) << 120;
    if (*s == '-') { neg = 1; s++; }
    if (!*s) return 0;
    for (; *s; s++) {
        if (*s < '0' || *s > '9') return 0;
        if (v > cap) return 0;
        v = v * 10 + (*s - '0');
    }
    *out = neg ? -v : v;
    return 1;
}

static int bits(i128 v) {
    int b = 0;
    if (v < 0) v = -v;
    while (v) { b++; v >>= 1; }
    return b;
}

static void read_points(const char *path) {
    FILE *f = fopen(path, "r");
    char xs[64], ys[64];
    if (!f || fscanf(f, "%d", &n) != 1 || n < 0 || n > 100000) { fprintf(stderr, "bad input\n"); exit(2); }
    pts = malloc(sizeof(P) * (n > 0 ? n : 1));
    i128 mx = 0, my = 0;
    for (int i = 0; i < n; i++) {
        if (fscanf(f, "%63s %63s", xs, ys) != 2 || !parse(xs, &pts[i].x) || !parse(ys, &pts[i].y)) {
            fprintf(stderr, "bad point %d\n", i);
            exit(2);
        }
        i128 ax = pts[i].x < 0 ? -pts[i].x : pts[i].x, ay = pts[i].y < 0 ? -pts[i].y : pts[i].y;
        if (ax > mx) mx = ax;
        if (ay > my) my = ay;
    }
    fclose(f);
    if (bits(2 * mx) + bits(2 * my) > 125) {
        fprintf(stderr, "coordinates too large for 128-bit orientations\n");
        exit(3);
    }
}

typedef struct { int i, j; long long c[5]; } Edge;

static void count(void) {
    int *idx = malloc(sizeof(int) * (n > 0 ? n : 1));
    int *out_off = malloc(sizeof(int) * (n + 1)), *in_off = malloc(sizeof(int) * (n + 1));
    int *in_fill = malloc(sizeof(int) * (n + 1));
    int cap = 1024, ne;
    Edge *e = malloc(sizeof(Edge) * cap);
    int *in_list = malloc(sizeof(int) * cap);
    long long collinear = 0, total[5] = {0, 0, 0, 0, 0};
    for (int pi = 0; pi < n; pi++) {
        int m = 0;
        for (int q = 0; q < n; q++)
            if (q != pi && above(&pts[pi], &pts[q])) idx[m++] = q;
        apex = &pts[pi];
        qsort(idx, m, sizeof(int), by_angle);
        for (int t = 0; t + 1 < m; t++)
            if (orient(apex, &pts[idx[t]], &pts[idx[t + 1]]) == 0) collinear++;
        ne = 0;
        for (int i = 0; i < m; i++) {
            out_off[i] = ne;
            int best = -1;
            for (int j = i + 1; j < m; j++) {
                if (best >= 0 && orient(&pts[idx[i]], &pts[idx[best]], &pts[idx[j]]) <= 0) continue;
                if (ne == cap) {
                    cap *= 2;
                    e = realloc(e, sizeof(Edge) * cap);
                    in_list = realloc(in_list, sizeof(int) * cap);
                }
                e[ne].i = i;
                e[ne].j = j;
                ne++;
                best = j;
            }
        }
        out_off[m] = ne;
        for (int t = 0; t <= m; t++) in_off[t] = 0;
        for (int t = 0; t < ne; t++) in_off[e[t].j + 1]++;
        for (int t = 0; t < m; t++) in_off[t + 1] += in_off[t];
        for (int t = 0; t <= m; t++) in_fill[t] = in_off[t];
        for (int t = 0; t < ne; t++) in_list[in_fill[e[t].j]++] = t;
        for (int i = 0; i < m; i++) {
            for (int t = out_off[i]; t < out_off[i + 1]; t++) {
                long long c[5] = {1, 0, 0, 0, 0};
                const P *qi = &pts[idx[i]], *qj = &pts[idx[e[t].j]];
                for (int s = in_off[i]; s < in_off[i + 1]; s++) {
                    const Edge *f = &e[in_list[s]];
                    if (orient(&pts[idx[f->i]], qi, qj) > 0) {
                        c[1] += f->c[0];
                        c[2] += f->c[1];
                        c[3] += f->c[2];
                        c[4] += f->c[3] + f->c[4];
                    }
                }
                memcpy(e[t].c, c, sizeof c);
                for (int L = 0; L < 5; L++) total[L] += c[L];
            }
        }
    }
    printf("collinear %lld\ncounts %lld %lld %lld %lld %lld\nwork %lld\n", collinear, total[0], total[1], total[2],
           total[3], total[4], work);
}

static void above_check(void) {
    long long v1 = 0, v2 = 0;
    for (int a = 0; a < n; a += 2)
        for (int b = a + 2; b < n; b += 2)
            for (int t = 1; t < n; t += 2)
                if (orient(&pts[a], &pts[b], &pts[t]) <= 0) v1++;
    for (int a = 1; a < n; a += 2)
        for (int b = a + 2; b < n; b += 2)
            for (int t = 0; t < n; t += 2)
                if (orient(&pts[a], &pts[b], &pts[t]) >= 0) v2++;
    printf("above %lld %lld\nwork %lld\n", v1, v2, work);
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: horton count|above FILE\n"); return 2; }
    read_points(argv[2]);
    if (!strcmp(argv[1], "count")) count();
    else if (!strcmp(argv[1], "above")) above_check();
    else { fprintf(stderr, "unknown mode\n"); return 2; }
    return 0;
}
