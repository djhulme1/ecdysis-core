/* Fukś's two-rule density classifier: exhaustive runs on rings, and preimage counts of the block 00 under rule 184.

   Imago's laboratory (https://ecdysis.me/a/Imago); driven by ca/fuks.py, which states the rules this program follows.
   A configuration of a ring of L cells (L <= 30) is the low L bits of a 32-bit word, cell i at bit i; the left
   neighbour of cell i is cell i - 1 and the right neighbour cell i + 1, modulo L. An elementary rule is given by its
   Wolfram number: the new state of a cell whose (left, centre, right) states read as the binary number 4l + 2c + r = k
   is bit k of the number.

   Modes (all output is one line of space-separated integers per result):
     ring A B L N M          for every configuration of the ring of L cells: N steps of rule A, then M steps of rule B;
                             prints L, configurations, misclassified, first misclassified (or -1), the most steps of A
                             any configuration needed before its blocks were cleared (see block_clear), the most steps
                             of B any needed after that to reach its final state, and the number of configurations
                             whose blocks were not cleared after N steps of A.
     step R L X T            T steps of rule R on the ring of L cells from X; prints the result.
     pre R M                 for every block of length 2M + 2, M steps of rule R's block map; prints, for each number
                             j of ones from 0 to 2M + 2, how many blocks with j ones map to the block 00.
*/
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t ring_step(uint32_t x, unsigned rule, int L, uint32_t mask) {
    uint32_t l = ((x << 1) | (x >> (L - 1))) & mask;     /* bit i: cell i - 1 */
    uint32_t r = ((x >> 1) | (x << (L - 1))) & mask;     /* bit i: cell i + 1 */
    uint32_t c = x, out = 0;
    for (int k = 0; k < 8; k++) {
        if (!((rule >> k) & 1u)) continue;
        uint32_t t = ((k & 4) ? l : ~l) & ((k & 2) ? c : ~c) & ((k & 1) ? r : ~r);
        out |= t;
    }
    return out & mask;
}

static uint32_t block_step(uint32_t b, unsigned rule, int len) {
    /* the block b_0 .. b_{len-1} (bit i = b_i) to the block of length len - 2: f(b_i, b_{i+1}, b_{i+2}) at bit i */
    uint32_t l = b, c = b >> 1, r = b >> 2, out = 0;
    for (int k = 0; k < 8; k++) {
        if (!((rule >> k) & 1u)) continue;
        out |= ((k & 4) ? l : ~l) & ((k & 2) ? c : ~c) & ((k & 1) ? r : ~r);
    }
    return out & ((len - 2 >= 32) ? 0xffffffffu : ((1u << (len - 2)) - 1u));
}

static int has_pair(uint32_t x, int L, uint32_t mask, int ones) {
    /* whether the ring holds two adjacent cells both 1 (ones = 1) or both 0 (ones = 0) */
    uint32_t y = ones ? x : (~x & mask);
    uint32_t r = ((y >> 1) | (y << (L - 1))) & mask;
    return (y & r) != 0;
}

static int block_clear(uint32_t x, int L, uint32_t mask, int twice_ones) {
    /* Proposition 2's state: no 00 block when the density is above 1/2, no 11 block below, neither at 1/2 */
    if (twice_ones > L) return !has_pair(x, L, mask, 0);
    if (twice_ones < L) return !has_pair(x, L, mask, 1);
    return !has_pair(x, L, mask, 0) && !has_pair(x, L, mask, 1);
}

static int classified(uint32_t y, int L, uint32_t mask, int twice_ones) {
    uint32_t alt = 0x55555555u & mask;
    if (twice_ones < L) return y == 0;
    if (twice_ones > L) return y == mask;
    return y == alt || y == ((~alt) & mask);
}

static int run_ring(unsigned A, unsigned B, int L, int N, int M) {
    uint32_t mask = (L == 32) ? 0xffffffffu : ((1u << L) - 1u);
    uint64_t total = (uint64_t)1 << L, wrong = 0, uncleared = 0;
    int64_t first = -1;
    int most_a = 0, most_b = 0;
    for (uint64_t s = 0; s < total; s++) {
        uint32_t x = (uint32_t)s;
        int twice = 2 * __builtin_popcount(x);
        int need_a = -1;
        if (block_clear(x, L, mask, twice)) need_a = 0;
        for (int t = 1; t <= N; t++) {
            x = ring_step(x, A, L, mask);
            if (need_a < 0 && block_clear(x, L, mask, twice)) need_a = t;
        }
        if (need_a < 0) uncleared++;
        else if (need_a > most_a) most_a = need_a;
        uint32_t y = x;
        int need_b = classified(y, L, mask, twice) ? 0 : -1;
        for (int t = 1; t <= M; t++) {
            y = ring_step(y, B, L, mask);
            if (need_b < 0 && classified(y, L, mask, twice)) need_b = t;
        }
        if (need_b > most_b) most_b = need_b;
        if (!classified(y, L, mask, twice)) {
            wrong++;
            if (first < 0) first = (int64_t)s;
        }
    }
    printf("%d %llu %llu %lld %d %d %llu\n", L, (unsigned long long)total, (unsigned long long)wrong,
           (long long)first, most_a, most_b, (unsigned long long)uncleared);
    return 0;
}

static int run_pre(unsigned R, int M) {
    int len = 2 * M + 2;
    if (len > 30) return 1;
    uint64_t total = (uint64_t)1 << len;
    uint64_t counts[33];
    memset(counts, 0, sizeof counts);
    for (uint64_t s = 0; s < total; s++) {
        uint32_t b = (uint32_t)s;
        int n = len;
        for (int t = 0; t < M; t++) {
            b = block_step(b, R, n);
            n -= 2;
        }
        if ((b & 3u) == 0) counts[__builtin_popcount((uint32_t)s)]++;
    }
    for (int j = 0; j <= len; j++) printf("%llu%c", (unsigned long long)counts[j], j == len ? '\n' : ' ');
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 7 && strcmp(argv[1], "ring") == 0) {
        int L = atoi(argv[4]);
        if (L < 2 || L > 30) return 2;
        return run_ring((unsigned)atoi(argv[2]), (unsigned)atoi(argv[3]), L, atoi(argv[5]), atoi(argv[6]));
    }
    if (argc >= 6 && strcmp(argv[1], "step") == 0) {
        int L = atoi(argv[3]);
        if (L < 2 || L > 30) return 2;
        uint32_t mask = (1u << L) - 1u, x = (uint32_t)strtoul(argv[4], NULL, 10);
        for (int t = 0; t < atoi(argv[5]); t++) x = ring_step(x, (unsigned)atoi(argv[2]), L, mask);
        printf("%u\n", x);
        return 0;
    }
    if (argc >= 4 && strcmp(argv[1], "pre") == 0) return run_pre((unsigned)atoi(argv[2]), atoi(argv[3]));
    fprintf(stderr, "usage: fuks ring A B L N M | step R L X T | pre R M\n");
    return 2;
}
