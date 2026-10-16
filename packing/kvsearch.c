/* Backtracking over packing k-colourings, for packing/kv2014.py. Built at run time with gcc; called through ctypes.
 *
 * A packing k-colouring gives every vertex a colour in 1..k so that two vertices of colour c are more than c apart.
 * The graph comes as its conflicts: for vertex v and colour c, the vertices u > v with d(u, v) <= c, in CSR form
 * (off[(v * k + c - 1)] .. off[(v * k + c - 1) + 1] index into idx). Vertices are coloured in index order 0..n-1,
 * colours tried in order 1..k; assigning c to v forbids c at every later conflicting vertex (forward checking), and a
 * later vertex left with no colour stops the branch at once.
 *
 * search(n, k, off, idx, cap, budget, out, out_cap, res): enumerates packing colourings until cap of them are found
 * (cap 0: no limit) or budget nodes (assignments) are spent; the first out_cap solutions are written to out (n bytes
 * each). res[0] = solutions found, res[1] = nodes spent. Returns 0 if the search was exhausted, 1 if it stopped at
 * cap, 2 if it stopped at the budget.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static int N, K;
static const int *OFF, *IDX;
static int *cnt;          /* cnt[v * K + c - 1]: earlier assignments forbidding colour c at v */
static unsigned char *col;
static int64_t found, nodes, cap, budget;
static unsigned char *out;
static int64_t out_cap;
static int stop;          /* 1 cap, 2 budget */

static int wiped(int u) {
    for (int c = 1; c <= K; c++) if (cnt[u * K + c - 1] == 0) return 0;
    return 1;
}

static void rec(int v) {
    if (stop) return;
    if (v == N) {
        if (found < out_cap) memcpy(out + found * N, col, N);
        found++;
        if (cap && found >= cap) stop = 1;
        return;
    }
    for (int c = 1; c <= K && !stop; c++) {
        if (cnt[v * K + c - 1]) continue;
        if (budget && nodes >= budget) { stop = 2; return; }
        nodes++;
        col[v] = (unsigned char)c;
        int a = OFF[v * K + c - 1], b = OFF[v * K + c];
        int dead = 0;
        for (int t = a; t < b; t++) {
            int u = IDX[t];
            cnt[u * K + c - 1]++;
            if (!dead && wiped(u)) dead = 1;
        }
        if (!dead) rec(v + 1);
        for (int t = a; t < b; t++) cnt[IDX[t] * K + c - 1]--;
        col[v] = 0;
    }
}

int search(int n, int k, const int *off, const int *idx, int64_t cap_, int64_t budget_, unsigned char *out_,
           int64_t out_cap_, int64_t *res) {
    N = n; K = k; OFF = off; IDX = idx;
    cnt = calloc((size_t)n * k, sizeof(int));
    col = calloc((size_t)n, 1);
    if (!cnt || !col) return -1;
    found = 0; nodes = 0; cap = cap_; budget = budget_; out = out_; out_cap = out_cap_; stop = 0;
    rec(0);
    res[0] = found; res[1] = nodes;
    free(cnt); free(col);
    return stop;
}
