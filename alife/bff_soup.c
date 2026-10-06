/*
 * bff_soup.c: an independent reimplementation of the BFF primordial soup of
 * Aguera y Arcas et al., "Computational Life: How Well-formed,
 * Self-replicating Programs Emerge from Simple Interaction"
 * (arXiv:2406.19108), written to count how often the soup's state transition
 * (the jump in high-order entropy that marks self-replicators taking over)
 * happens within a fixed number of epochs.
 *
 * Specification: the authors' code, cubff (Apache-2.0), commit
 * f212e849027c98fcf4b242eccfb5fed435223e23. Each rule below cites the cubff
 * file and line it follows. No cubff code is compiled into this program; the
 * few rules that define the semantics are restated here in C and cited.
 *
 * Build: gcc -O2 -pthread bff_soup.c -lbrotlienc -lm -o bff
 * Run:   ECDYSIS_SEED=<64 hex digits> ./bff [runs=20] [epochs=16384] [lang]
 *        lang is "bff" (the default: cubff's --lang bff, whose heads start
 *        where the tape's first two bytes say) or "bff_noheads" (cubff's
 *        --lang bff_noheads, heads and instruction pointer start at 0). The
 *        paper says "To run the BFF variant from Section 2, pass --lang
 *        bff_noheads", and its 40%-within-16k figure is from Section 2; see
 *        README.md.
 *
 * Randomness comes from ECDYSIS_SEED and nothing else: run r uses
 * xoshiro256** seeded with SHA-256(seed bytes || r as 8 little-endian
 * bytes). Each run is simulated by one thread from start to finish, so the
 * outputs are the same, bit for bit, however the threads are scheduled.
 *
 * Writes results/outputs.json (the summary) and results/trajectory.csv
 * (every high-order entropy sample of every run); progress goes to stderr.
 */

#define _POSIX_C_SOURCE 200809L

#include <brotli/encode.h>
#include <errno.h>
#include <math.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

/* ------------------------------------------------------------------------
 * Parameters: cubff's defaults for the soup
 * ---------------------------------------------------------------------- */

enum {
    TAPE_BYTES = 64,  /* common.h:55 kSingleTapeSize = 64 */
    PAIR_BYTES = 128, /* two tapes concatenated: common_language.h:164-171 */
};
#define NUM_PROGRAMS (1u << 17) /* common.h:59 num_programs = 128*1024; main.cc:180 */
#define STEP_LIMIT 8192u        /* common_language.h:184 Evaluate(tape, 8 * 1024, ...) */
/* Background mutation: mutation_prob = round(2^30 / (256 * 16)) = 2^18 out of
 * 2^30 (main.cc:183,226; common.h:61), i.e. exactly 2^-12 = 0.0244% per byte
 * per epoch (common_language.h:172-180). */
#define MUT_BITS 12
#define MEASURE_EVERY 64u /* main.cc:204 --print_interval 64, main.cc:324 callback_interval */
#define BROTLI_QUALITY 2  /* common_language.h:505 BrotliEncoderCompress(2, 24, ...) */
#define BROTLI_LGWIN 24   /* common_language.h:505 */
/* The transition: the first sample with high-order entropy above 3.0, the
 * rule of the authors' own scripts (python/runit.py:29,
 * python/cond_exp.py:55, python/time_to_sr.py:33,52). */
#define HOE_THRESHOLD 3.0
#define MAX_RUNS 1000u
#define NUM_THREADS 2u

enum lang { LANG_BFF = 0, LANG_BFF_NOHEADS = 1 };
static const char *const LANG_NAME[2] = {"bff", "bff_noheads"};

/* ------------------------------------------------------------------------
 * SHA-256 (FIPS 180-4), used only to derive each run's generator
 * ---------------------------------------------------------------------- */

static uint32_t ror32(uint32_t x, int k) { return (x >> k) | (x << (32 - k)); }

static void sha256_block(uint32_t h[8], const uint8_t blk[64])
{
    static const uint32_t K[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
        0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
        0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
        0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
        0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
    uint32_t w[64];
    for (int i = 0; i < 16; i++)
        w[i] = (uint32_t)blk[4 * i] << 24 | (uint32_t)blk[4 * i + 1] << 16 |
               (uint32_t)blk[4 * i + 2] << 8 | (uint32_t)blk[4 * i + 3];
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ror32(w[i - 15], 7) ^ ror32(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ror32(w[i - 2], 17) ^ ror32(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    uint32_t a = h[0], b = h[1], c = h[2], d = h[3];
    uint32_t e = h[4], f = h[5], g = h[6], k = h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t t1 = k + (ror32(e, 6) ^ ror32(e, 11) ^ ror32(e, 25)) +
                      ((e & f) ^ (~e & g)) + K[i] + w[i];
        uint32_t t2 = (ror32(a, 2) ^ ror32(a, 13) ^ ror32(a, 22)) +
                      ((a & b) ^ (a & c) ^ (b & c));
        k = g;
        g = f;
        f = e;
        e = d + t1;
        d = c;
        c = b;
        b = a;
        a = t1 + t2;
    }
    h[0] += a;
    h[1] += b;
    h[2] += c;
    h[3] += d;
    h[4] += e;
    h[5] += f;
    h[6] += g;
    h[7] += k;
}

static void sha256(const uint8_t *msg, size_t len, uint8_t out[32])
{
    uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                     0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    uint8_t blk[64];
    size_t i = 0;
    for (; len - i >= 64; i += 64)
        sha256_block(h, msg + i);
    size_t rem = len - i;
    memset(blk, 0, sizeof blk);
    if (rem)
        memcpy(blk, msg + i, rem);
    blk[rem] = 0x80;
    if (rem >= 56) {
        sha256_block(h, blk);
        memset(blk, 0, sizeof blk);
    }
    uint64_t bits = (uint64_t)len * 8;
    for (int j = 0; j < 8; j++)
        blk[63 - j] = (uint8_t)(bits >> (8 * j));
    sha256_block(h, blk);
    for (int j = 0; j < 8; j++) {
        out[4 * j] = (uint8_t)(h[j] >> 24);
        out[4 * j + 1] = (uint8_t)(h[j] >> 16);
        out[4 * j + 2] = (uint8_t)(h[j] >> 8);
        out[4 * j + 3] = (uint8_t)h[j];
    }
}

/* ------------------------------------------------------------------------
 * xoshiro256** (Blackman and Vigna, 2018) and the per-run derivation
 * ---------------------------------------------------------------------- */

typedef struct {
    uint64_t s[4];
} xoshiro256;

static inline uint64_t rotl64(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }

static inline uint64_t xo_next(xoshiro256 *g)
{
    uint64_t *s = g->s;
    const uint64_t result = rotl64(s[1] * 5, 7) * 9;
    const uint64_t t = s[1] << 17;
    s[2] ^= s[0];
    s[3] ^= s[1];
    s[1] ^= s[2];
    s[0] ^= s[3];
    s[2] ^= t;
    s[3] = rotl64(s[3], 45);
    return result;
}

/* A uniform integer in [0, n) for 1 <= n < 2^32, without bias (Lemire,
 * "Fast random integer generation in an interval", 2019). */
static inline uint32_t xo_below(xoshiro256 *g, uint32_t n)
{
    uint64_t m = (xo_next(g) >> 32) * (uint64_t)n;
    uint32_t low = (uint32_t)m;
    if (low < n) {
        uint32_t floor = (uint32_t)(-n) % n;
        while (low < floor) {
            m = (xo_next(g) >> 32) * (uint64_t)n;
            low = (uint32_t)m;
        }
    }
    return (uint32_t)(m >> 32);
}

/* Run r's generator: xoshiro256** whose four state words are the
 * little-endian 64-bit words of SHA-256(seed || r as 8 little-endian bytes). */
static void derive_generator(xoshiro256 *g, const uint8_t seed[32], uint64_t run)
{
    uint8_t msg[40], d[32];
    memcpy(msg, seed, 32);
    for (int k = 0; k < 8; k++)
        msg[32 + k] = (uint8_t)(run >> (8 * k));
    sha256(msg, sizeof msg, d);
    for (int w = 0; w < 4; w++) {
        uint64_t v = 0;
        for (int k = 7; k >= 0; k--)
            v = v << 8 | d[8 * w + k];
        g->s[w] = v;
    }
    if (!(g->s[0] | g->s[1] | g->s[2] | g->s[3]))
        g->s[0] = 1; /* the one state xoshiro cannot use; never met in practice */
}

/* ------------------------------------------------------------------------
 * The BFF interpreter
 * ---------------------------------------------------------------------- */

/*
 * One interaction: execute the 128-byte tape t (two programs concatenated)
 * in place for at most `limit` steps. Returns cubff's op count, the steps
 * that executed one of the ten instructions (bff.inc.h:358,374-375,388); it
 * is used here only for statistics.
 *
 * The instructions (bff.inc.h:58-85,289-349). Every other byte, 0 included,
 * is a no-op that still costs a step:
 *   <  head0 -= 1            >  head0 += 1
 *   {  head1 -= 1            }  head1 += 1
 *   +  t[head0] += 1         -  t[head0] -= 1          (mod 256)
 *   .  t[head1] = t[head0]   ,  t[head0] = t[head1]
 *   [  if t[head0] == 0, jump forward to the matching ]
 *   ]  if t[head0] != 0, jump back to the matching [
 * Code and data share the tape, so a program can rewrite instructions it has
 * yet to execute, and brackets are matched on the tape as it is when the
 * jump happens.
 *
 * Two interpreters follow. bff_eval_ref is the specification: it walks the
 * tape one step at a time exactly as cubff's Evaluate does. bff_eval gives
 * the same tape and the same op count, faster; the tests check the two
 * against each other and against cubff's own code, and every run re-checks
 * a sample of interactions with the reference as it goes (soup_epoch).
 */
static uint32_t bff_eval_ref(uint8_t *t, int lang, uint32_t limit)
{
    int pc, h0, h1;
    if (lang == LANG_BFF) {
        /* bff.cu:15 defines BFF_HEADS, so bff.inc.h:270-275 applies: the
         * heads start at the tape's first two bytes mod 128 (headpos,
         * bff.inc.h:50-52) and the instruction pointer at byte 2. */
        h0 = t[0] % PAIR_BYTES;
        h1 = t[1] % PAIR_BYTES;
        pc = 2;
    } else {
        /* bff_noheads.cu leaves BFF_HEADS undefined, so bff.inc.h:277-282:
         * heads at 2*64 = 128, which wraps to 0 before the first step, and
         * the instruction pointer at byte 0. */
        h0 = h1 = 0;
        pc = 0;
    }
    uint32_t step = 0, noops = 0;
    while (step < limit) {      /* bff.inc.h:367 */
        h0 &= PAIR_BYTES - 1;   /* bff.inc.h:368-369: both heads wrap mod 128 */
        h1 &= PAIR_BYTES - 1;   /* before every step */
        step++;                 /* every byte read is a step, instruction or not */
        switch (t[pc]) {
        case '<': h0--; break;
        case '>': h0++; break;
        case '{': h1--; break;
        case '}': h1++; break;
        case '+': t[h0]++; break;
        case '-': t[h0]--; break;
        case '.': t[h1] = t[h0]; break;
        case ',': t[h0] = t[h1]; break;
        case '[':
            if (t[h0] == 0) {
                /* bff.inc.h:317-330: scan forward from pc+1, counting
                 * nesting, and land on the matching ]; execution resumes
                 * after it. With no match before the end of the tape,
                 * execution stops. */
                int depth = 1, p = pc + 1;
                for (; p < PAIR_BYTES; p++) {
                    if (t[p] == ']' && --depth == 0)
                        break;
                    if (t[p] == '[')
                        depth++;
                }
                if (depth != 0)
                    goto done;
                pc = p;
            }
            break;
        case ']':
            if (t[h0] != 0) {
                /* bff.inc.h:331-344: scan back from pc-1 down to byte 0 and
                 * land on the matching [; execution resumes after it. With
                 * no match, execution stops. */
                int depth = 1, p = pc - 1;
                for (; p >= 0; p--) {
                    if (t[p] == '[' && --depth == 0)
                        break;
                    if (t[p] == ']')
                        depth++;
                }
                if (depth != 0)
                    goto done;
                pc = p;
            }
            break;
        default:
            noops++;
            break;
        }
        if (++pc >= PAIR_BYTES) /* bff.inc.h:381-385: off the end, stop */
            break;
    }
done:
    return step - noops;
}

/* Which bytes are instructions, and which are brackets (bff.inc.h:58-85). */
static const uint8_t IS_INSTR[256] = {
    ['<'] = 1, ['>'] = 1, ['{'] = 1, ['}'] = 1, ['+'] = 1,
    ['-'] = 1, ['.'] = 1, [','] = 1, ['['] = 1, [']'] = 1,
};
static const uint8_t IS_BRACKET[256] = {['['] = 1, [']'] = 1};

/* Bitmasks of the positions holding instructions (im) and brackets (bm),
 * bit p of word p/64 for position p. The portable version: */
static inline void build_masks_scalar(const uint8_t *t, uint64_t im[2], uint64_t bm[2])
{
    for (int w = 0; w < 2; w++) {
        uint64_t mi = 0, mb = 0;
        for (int i = 0; i < 64; i++) {
            mi |= (uint64_t)IS_INSTR[t[64 * w + i]] << i;
            mb |= (uint64_t)IS_BRACKET[t[64 * w + i]] << i;
        }
        im[w] = mi;
        bm[w] = mb;
    }
}

#if defined(__SSE2__)
#include <emmintrin.h>
/* The same with SSE2, 16 bytes at a time. Instruction bytes are
 * 0x2B-0x2E (+ , - .), 0x3C and 0x3E (< >, those x with x|2 == 0x3E), and
 * 0x5B 0x5D 0x7B 0x7D ([ ] { }, those x with x|0x20 == 0x7B or 0x7D). */
static inline void build_masks(const uint8_t *t, uint64_t im[2], uint64_t bm[2])
{
    const __m128i k2b = _mm_set1_epi8(0x2B), k3 = _mm_set1_epi8(3);
    const __m128i k02 = _mm_set1_epi8(0x02), k3e = _mm_set1_epi8(0x3E);
    const __m128i k20 = _mm_set1_epi8(0x20), k7b = _mm_set1_epi8(0x7B), k7d = _mm_set1_epi8(0x7D);
    const __m128i k5b = _mm_set1_epi8(0x5B), k5d = _mm_set1_epi8(0x5D);
    for (int w = 0; w < 2; w++) {
        uint64_t mi = 0, mb = 0;
        for (int c = 0; c < 4; c++) {
            const __m128i x = _mm_loadu_si128((const __m128i *)(const void *)(t + 64 * w + 16 * c));
            const __m128i d = _mm_sub_epi8(x, k2b);
            const __m128i arith = _mm_cmpeq_epi8(_mm_min_epu8(d, k3), d);
            const __m128i move0 = _mm_cmpeq_epi8(_mm_or_si128(x, k02), k3e);
            const __m128i y = _mm_or_si128(x, k20);
            const __m128i brace = _mm_or_si128(_mm_cmpeq_epi8(y, k7b), _mm_cmpeq_epi8(y, k7d));
            const __m128i brack = _mm_or_si128(_mm_cmpeq_epi8(x, k5b), _mm_cmpeq_epi8(x, k5d));
            const __m128i any = _mm_or_si128(_mm_or_si128(arith, move0), brace);
            mi |= (uint64_t)(uint16_t)_mm_movemask_epi8(any) << (16 * c);
            mb |= (uint64_t)(uint16_t)_mm_movemask_epi8(brack) << (16 * c);
        }
        im[w] = mi;
        bm[w] = mb;
    }
}
#else
#define build_masks build_masks_scalar
#endif

/* First instruction at or after position pc, from the instruction mask;
 * PAIR_BYTES if there is none. */
static inline int next_instr(const uint64_t im[2], int pc)
{
    if (pc < 64) {
        uint64_t m = im[0] >> pc;
        if (m)
            return pc + __builtin_ctzll(m);
        return im[1] ? 64 + __builtin_ctzll(im[1]) : PAIR_BYTES;
    }
    uint64_t m = im[1] >> (pc - 64);
    return m ? pc + __builtin_ctzll(m) : PAIR_BYTES;
}

/* The ] matching the [ at pc, scanning pc+1..127 over the bracket mask with
 * the reference's nesting rule; -1 if there is none. */
static inline int match_forward(const uint8_t *t, const uint64_t bm[2], int pc)
{
    int depth = 1, start = pc + 1;
    if (start >= PAIR_BYTES)
        return -1;
    for (int w = start >> 6; w < 2; w++) {
        uint64_t m = bm[w];
        if (w == start >> 6)
            m &= ~0ULL << (start & 63);
        for (; m; m &= m - 1) {
            int p = (w << 6) + __builtin_ctzll(m);
            if (t[p] == ']') {
                if (--depth == 0)
                    return p;
            } else {
                depth++;
            }
        }
    }
    return -1;
}

/* The [ matching the ] at pc, scanning pc-1 down to 0; -1 if none. */
static inline int match_backward(const uint8_t *t, const uint64_t bm[2], int pc)
{
    int depth = 1;
    if (pc <= 0)
        return -1;
    const int last = pc - 1;
    for (int w = last >> 6; w >= 0; w--) {
        uint64_t m = bm[w];
        if (w == last >> 6)
            m &= (2ULL << (last & 63)) - 1; /* bits 0..last%64 (all 64 when 63) */
        while (m) {
            int b = 63 - __builtin_clzll(m);
            int p = (w << 6) + b;
            if (t[p] == '[') {
                if (--depth == 0)
                    return p;
            } else {
                depth++;
            }
            m &= ~(1ULL << b);
        }
    }
    return -1;
}

/*
 * The fast interpreter. Same semantics as bff_eval_ref; two shortcuts, both
 * exact:
 *
 * 1. Runs of no-op bytes are skipped in one move, using a bitmask of the
 *    positions that hold instructions (kept current on every write). A run
 *    of k no-ops costs k steps, as in the reference, and if the step limit
 *    falls inside the run, execution stops there with the same tape.
 *
 * 2. Loops that provably repeat are fast-forwarded. At every backward jump
 *    the state (jump target, head0, head1, tape) is compared with a saved
 *    one (Brent's cycle detection: the saved state moves at the 1st, 2nd,
 *    4th, 8th... jump). If they are equal, the steps in between form a cycle
 *    that will repeat until the step limit, so whole cycles are skipped and
 *    the last partial cycle is executed normally, ending exactly where the
 *    reference ends. If no write happened since the saved state, the tape is
 *    unchanged and head1 is irrelevant (only the writes . and , read it), so
 *    jump target and head0 suffice.
 */
static uint32_t bff_eval(uint8_t *t, int lang, uint32_t limit)
{
    uint64_t im[2], bm[2];
    build_masks(t, im, bm);
    int pc, h0, h1;
    if (lang == LANG_BFF) {
        h0 = t[0] % PAIR_BYTES;
        h1 = t[1] % PAIR_BYTES;
        pc = 2;
    } else {
        h0 = h1 = 0;
        pc = 0;
    }
    uint32_t step = 0, noops = 0, writes = 0;

    /* Brent's cycle detection over the states seen at backward jumps. */
    int detect = 1, saved = 0, s_pc = 0, s_h0 = 0, s_h1 = 0;
    uint32_t s_step = 0, s_noops = 0, s_writes = 0, power = 1, lam = 0;
    uint8_t s_tape[PAIR_BYTES];

#define BFF_WRITE(pos, value)                                                     \
    do {                                                                          \
        const int x_ = (pos);                                                     \
        const uint8_t v_ = (uint8_t)(value);                                      \
        const uint64_t bit_ = 1ULL << (x_ & 63);                                  \
        t[x_] = v_;                                                               \
        im[x_ >> 6] = (im[x_ >> 6] & ~bit_) | ((uint64_t)IS_INSTR[v_] << (x_ & 63)); \
        bm[x_ >> 6] = (bm[x_ >> 6] & ~bit_) | ((uint64_t)IS_BRACKET[v_] << (x_ & 63)); \
        writes++;                                                                 \
    } while (0)

    for (;;) {
        const int q = next_instr(im, pc);
        if (q != pc) { /* skip the no-ops at pc..q-1, one step each */
            const uint32_t run = (uint32_t)(q - pc);
            if (run >= limit - step) {
                noops += limit - step;
                step = limit;
                break;
            }
            step += run;
            noops += run;
            if (q >= PAIR_BYTES)
                break;
            pc = q;
        }
        if (step >= limit)
            break;
        step++;
        switch (t[pc]) {
        case '<': h0 = (h0 - 1) & (PAIR_BYTES - 1); break;
        case '>': h0 = (h0 + 1) & (PAIR_BYTES - 1); break;
        case '{': h1 = (h1 - 1) & (PAIR_BYTES - 1); break;
        case '}': h1 = (h1 + 1) & (PAIR_BYTES - 1); break;
        case '+': BFF_WRITE(h0, t[h0] + 1); break;
        case '-': BFF_WRITE(h0, t[h0] - 1); break;
        case '.': BFF_WRITE(h1, t[h0]); break;
        case ',': BFF_WRITE(h0, t[h1]); break;
        case '[':
            if (t[h0] == 0) {
                const int p = match_forward(t, bm, pc);
                if (p < 0)
                    goto done;
                pc = p;
            }
            break;
        case ']':
            if (t[h0] != 0) {
                const int p = match_backward(t, bm, pc);
                if (p < 0)
                    goto done;
                pc = p;
                if (!detect)
                    break;
                if (saved && p == s_pc && h0 == s_h0 &&
                    (writes == s_writes ||
                     (h1 == s_h1 && memcmp(t, s_tape, PAIR_BYTES) == 0))) {
                    const uint32_t period = step - s_step;
                    const uint32_t cycles = (limit - step) / period;
                    step += cycles * period;
                    noops += cycles * (noops - s_noops);
                    detect = 0; /* the rest is less than one cycle */
                } else if (!saved || ++lam == power) {
                    if (saved)
                        power <<= 1;
                    saved = 1;
                    lam = 0;
                    s_pc = p;
                    s_h0 = h0;
                    s_h1 = h1;
                    s_step = step;
                    s_noops = noops;
                    s_writes = writes;
                    memcpy(s_tape, t, PAIR_BYTES);
                }
            }
            break;
        default: /* unreachable: q is an instruction */
            break;
        }
        if (++pc >= PAIR_BYTES)
            break;
    }
#undef BFF_WRITE
done:
    return step - noops;
}

/* ------------------------------------------------------------------------
 * Noise: the epoch's pairing and the background mutation
 * ---------------------------------------------------------------------- */

/* The soup takes its randomness through this interface so that the tests
 * can drive the same epoch code with cubff's own generator (see
 * test_bff_soup.c); the program itself only ever uses stream_noise. */
typedef struct noise noise;
struct noise {
    void (*order)(noise *self, uint32_t *perm, uint32_t n, uint64_t epoch);
    void (*mutate)(noise *self, uint8_t *tape, uint32_t n, uint64_t epoch, uint32_t pair);
};

typedef struct {
    noise base;
    xoshiro256 g;
} stream_noise;

/* Pairing (common_language.h:464-476 with the defaults permute_programs =
 * true and fixed_shuffle = false, main.cc:198,200): every epoch the indices
 * are reset to 0..n-1 and shuffled by a Fisher-Yates pass from the end
 * (common_language.h:418-424), a uniformly random permutation; pair k is
 * (perm[2k], perm[2k+1]), the first program taking bytes 0-63 of the
 * concatenated tape (common_language.h:166-171). Every program is in
 * exactly one pair per epoch. */
static void stream_order(noise *self, uint32_t *perm, uint32_t n, uint64_t epoch)
{
    xoshiro256 *g = &((stream_noise *)self)->g;
    (void)epoch;
    for (uint32_t i = 0; i < n; i++)
        perm[i] = i;
    for (uint32_t i = n - 1; i > 0; i--) {
        uint32_t j = xo_below(g, i + 1);
        uint32_t tmp = perm[i];
        perm[i] = perm[j];
        perm[j] = tmp;
    }
}

/* Background mutation (common_language.h:172-180): before execution, each
 * of the pair's 128 bytes is replaced, independently and with probability
 * exactly 2^-12, by a uniformly random byte (which may equal the old one).
 * cubff draws 30 random bits per byte and mutates when they are below 2^18;
 * here the same event is "12 fresh random bits are all zero": each 64-bit
 * draw decides five bytes, in order, from its low 60 bits, and each mutated
 * byte's replacement is the top byte of the next draw. The distribution is
 * the same. A word with no zero field (the usual case, tested in one go:
 * the "has a zero field" bit trick, exact for the any-zero question) changes
 * nothing; the draws consumed do not depend on the shortcut. */
#define MUT_FIELD_ONES 0x001001001001001ULL  /* the low bit of each 12-bit field */
#define MUT_FIELD_HIGHS 0x800800800800800ULL /* the high bit of each field */
static void stream_mutate(noise *self, uint8_t *t, uint32_t n, uint64_t epoch, uint32_t pair)
{
    xoshiro256 *g = &((stream_noise *)self)->g;
    (void)n;
    (void)epoch;
    (void)pair;
    for (int i = 0; i < PAIR_BYTES;) {
        uint64_t w = xo_next(g) & ((1ULL << 60) - 1);
        if (((w - MUT_FIELD_ONES) & ~w & MUT_FIELD_HIGHS) == 0) {
            i += 5;
            continue;
        }
        for (int k = 0; k < 5 && i < PAIR_BYTES; k++, i++, w >>= MUT_BITS)
            if ((w & ((1u << MUT_BITS) - 1)) == 0)
                t[i] = (uint8_t)(xo_next(g) >> 56);
    }
}

static void stream_noise_init(stream_noise *nz, const uint8_t seed[32], uint64_t run)
{
    nz->base.order = stream_order;
    nz->base.mutate = stream_mutate;
    derive_generator(&nz->g, seed, run);
}

/* ------------------------------------------------------------------------
 * The soup
 * ---------------------------------------------------------------------- */

typedef struct {
    uint32_t n;     /* programs */
    uint8_t *bytes; /* n * 64 bytes, program i at bytes[64 i] */
    uint32_t *perm;
    uint8_t *zbuf; /* brotli output */
    size_t zcap;
    uint64_t pairs_run, guard_checks, guard_failures;
} soup;

/* Every GUARD_EVERY-th interaction (counted across epochs, so a random pair
 * of the epoch's random order) is run by both interpreters and the results
 * compared; a mismatch fails the run. */
#define GUARD_EVERY 4096u

static int soup_alloc(soup *s, uint32_t n)
{
    size_t len = (size_t)n * TAPE_BYTES;
    memset(s, 0, sizeof *s);
    s->n = n;
    s->bytes = aligned_alloc(64, len);
    s->perm = malloc((size_t)n * sizeof *s->perm);
    s->zcap = BrotliEncoderMaxCompressedSize(len);
    s->zbuf = s->zcap ? malloc(s->zcap) : NULL;
    return (s->bytes && s->perm && s->zbuf) ? 0 : -1;
}

static void soup_free(soup *s)
{
    free(s->bytes);
    free(s->perm);
    free(s->zbuf);
    memset(s, 0, sizeof *s);
}

/* Initialisation (common_language.h:139-155 with zero_init = false,
 * main.cc:201): every byte uniformly random. */
static void soup_fill_random(soup *s, xoshiro256 *g)
{
    size_t len = (size_t)s->n * TAPE_BYTES;
    for (size_t i = 0; i < len; i += 8) {
        uint64_t x = xo_next(g);
        for (int k = 0; k < 8; k++)
            s->bytes[i + k] = (uint8_t)(x >> (8 * k));
    }
}

/* One epoch (common_language.h:432-494): order the programs into pairs, then
 * for each pair concatenate, mutate, execute and split back
 * (common_language.h:157-193). Pairs are disjoint, so the order in which
 * they run does not matter. Returns the epoch's op count. */
static uint64_t soup_epoch(soup *s, noise *nz, uint64_t epoch, int lang)
{
    const uint32_t pairs = s->n / 2;
    uint64_t ops = 0;
    uint8_t tape[PAIR_BYTES];
    nz->order(nz, s->perm, s->n, epoch);
    for (uint32_t k = 0; k < pairs; k++) {
        uint8_t *a = s->bytes + (size_t)s->perm[2 * k] * TAPE_BYTES;
        uint8_t *b = s->bytes + (size_t)s->perm[2 * k + 1] * TAPE_BYTES;
        if (k + 1 < pairs) {
            __builtin_prefetch(s->bytes + (size_t)s->perm[2 * k + 2] * TAPE_BYTES);
            __builtin_prefetch(s->bytes + (size_t)s->perm[2 * k + 3] * TAPE_BYTES);
        }
        memcpy(tape, a, TAPE_BYTES);
        memcpy(tape + TAPE_BYTES, b, TAPE_BYTES);
        nz->mutate(nz, tape, s->n, epoch, k);
        if (++s->pairs_run % GUARD_EVERY == 0) {
            uint8_t ref[PAIR_BYTES];
            memcpy(ref, tape, PAIR_BYTES);
            const uint32_t fast_ops = bff_eval(tape, lang, STEP_LIMIT);
            const uint32_t ref_ops = bff_eval_ref(ref, lang, STEP_LIMIT);
            s->guard_checks++;
            if (fast_ops != ref_ops || memcmp(ref, tape, PAIR_BYTES) != 0)
                s->guard_failures++;
            ops += fast_ops;
        } else {
            ops += bff_eval(tape, lang, STEP_LIMIT);
        }
        memcpy(a, tape, TAPE_BYTES);
        memcpy(b, tape + TAPE_BYTES, TAPE_BYTES);
    }
    return ops;
}

/* ------------------------------------------------------------------------
 * The measure: high-order entropy
 * ---------------------------------------------------------------------- */

typedef struct {
    uint64_t epoch;     /* epochs completed, cubff's state.epoch */
    double h0;          /* Shannon entropy of the byte histogram, bits per byte */
    double bpb;         /* brotli-compressed size, bits per byte */
    float hoe;          /* h0 - bpb, kept as a float as cubff does */
    uint64_t zsize;     /* brotli-compressed size, bytes */
    double ops_per_pair;
} sample;

/* common_language.h:504-546: brotli at quality 2, window 2^24, generic
 * mode, over the whole soup in program order; Shannon entropy of the byte
 * histogram, summed over byte values 0..255 in order; high-order entropy =
 * h0 - compressed bits per byte, stored as a float (common.h:87). */
static int soup_measure(soup *s, sample *m)
{
    const size_t len = (size_t)s->n * TAPE_BYTES;
    uint64_t counts[256] = {0};
    for (size_t i = 0; i < len; i++)
        counts[s->bytes[i]]++;
    double h0 = 0.0;
    for (int c = 0; c < 256; c++) {
        double frac = counts[c] * 1.0 / len;
        h0 -= counts[c] ? frac * log2(frac) : 0.0;
    }
    size_t zsize = s->zcap;
    if (!BrotliEncoderCompress(BROTLI_QUALITY, BROTLI_LGWIN, BROTLI_MODE_GENERIC, len,
                               s->bytes, &zsize, s->zbuf))
        return -1;
    double bpb = zsize * 8.0 / len;
    m->h0 = h0;
    m->bpb = bpb;
    m->zsize = zsize;
    m->hoe = (float)(h0 - bpb);
    return 0;
}

/* ------------------------------------------------------------------------
 * Runs
 * ---------------------------------------------------------------------- */

typedef struct {
    uint8_t seed[32];
    uint32_t runs;
    uint64_t epochs;
    int lang;
    uint32_t n;
    int quiet;
} config;

typedef struct {
    uint32_t index;
    int64_t cross_epoch; /* epochs completed at the first sample above the threshold, or -1 */
    uint64_t epochs_run;
    sample *traj;
    uint32_t ntraj;
    double seconds; /* wall time, for progress only: never written to results */
    uint64_t guard_checks;
    int failed;
} run_result;

static double now_seconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* One run: a fresh random soup, then epochs until the transition or the
 * epoch budget. High-order entropy is sampled after epoch 1 and every 64
 * epochs after that (epochs completed = 1, 65, 129, ...: cubff calls back
 * when epoch % 64 == 0 and reports epoch + 1, common_language.h:496,540),
 * and once more after the last epoch, so that "within E epochs" includes
 * epoch E. The run stops at its first sample above the threshold. */
static void run_one(const config *cfg, run_result *r)
{
    soup s;
    stream_noise nz;
    r->cross_epoch = -1;
    r->traj = calloc(cfg->epochs / MEASURE_EVERY + 2, sizeof *r->traj);
    if (!r->traj || soup_alloc(&s, cfg->n)) {
        r->failed = 1;
        return;
    }
    stream_noise_init(&nz, cfg->seed, r->index);
    soup_fill_random(&s, &nz.g);

    const double t0 = now_seconds();
    double t_last = t0;
    uint64_t e_last = 0, ops = 0, pairs = 0;
    for (uint64_t e = 0; e < cfg->epochs; e++) {
        ops += soup_epoch(&s, &nz.base, e, cfg->lang);
        pairs += s.n / 2;
        r->epochs_run = e + 1;
        if (s.guard_failures) {
            fprintf(stderr, "run %u: interpreter guard mismatch at epoch %llu; run failed\n",
                    r->index, (unsigned long long)(e + 1));
            r->failed = 1;
            break;
        }
        if (e % MEASURE_EVERY != 0 && e + 1 != cfg->epochs)
            continue;
        sample *m = &r->traj[r->ntraj++];
        if (soup_measure(&s, m)) {
            r->failed = 1;
            break;
        }
        m->epoch = e + 1;
        m->ops_per_pair = (double)ops / (double)pairs;
        ops = pairs = 0;
        const int crossed = (double)m->hoe > HOE_THRESHOLD;
        if (crossed)
            r->cross_epoch = (int64_t)m->epoch;
        if (!cfg->quiet && (e % 256 == 0 || crossed || e + 1 == cfg->epochs)) {
            double t = now_seconds();
            fprintf(stderr,
                    "run %2u  epoch %6llu  hoe %8.5f  h0 %.4f  bpb %.4f  ops/pair %8.1f"
                    "  %6.1f epochs/s%s\n",
                    r->index, (unsigned long long)m->epoch, (double)m->hoe, m->h0, m->bpb,
                    m->ops_per_pair, (t > t_last) ? (m->epoch - e_last) / (t - t_last) : 0.0,
                    crossed ? "  TRANSITION" : "");
            t_last = t;
            e_last = m->epoch;
        }
        if (crossed)
            break;
    }
    r->seconds = now_seconds() - t0;
    r->guard_checks = s.guard_checks;
    soup_free(&s);
}

static const config *g_cfg;
static run_result *g_runs;
static uint32_t g_next;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;

static void *worker(void *arg)
{
    (void)arg;
    for (;;) {
        pthread_mutex_lock(&g_lock);
        uint32_t i = g_next++;
        pthread_mutex_unlock(&g_lock);
        if (i >= g_cfg->runs)
            return NULL;
        run_one(g_cfg, &g_runs[i]);
    }
}

/* Runs every run, NUM_THREADS at a time. Each run is simulated by one
 * thread from start to finish with its own generator, so results do not
 * depend on scheduling. Returns 0 if every run completed. */
static int run_all(const config *cfg, run_result *runs)
{
    pthread_t th[NUM_THREADS];
    uint32_t nth = cfg->runs < NUM_THREADS ? cfg->runs : NUM_THREADS;
    for (uint32_t i = 0; i < cfg->runs; i++) {
        memset(&runs[i], 0, sizeof runs[i]);
        runs[i].index = i;
    }
    g_cfg = cfg;
    g_runs = runs;
    g_next = 0;
    for (uint32_t i = 0; i < nth; i++)
        if (pthread_create(&th[i], NULL, worker, NULL) != 0)
            return -1;
    for (uint32_t i = 0; i < nth; i++)
        pthread_join(th[i], NULL);
    for (uint32_t i = 0; i < cfg->runs; i++)
        if (runs[i].failed)
            return -1;
    return 0;
}

static int parse_seed(const char *hex, uint8_t seed[32])
{
    if (!hex || strlen(hex) != 64)
        return -1;
    for (int i = 0; i < 64; i++) {
        char c = hex[i];
        int v = (c >= '0' && c <= '9')   ? c - '0'
                : (c >= 'a' && c <= 'f') ? c - 'a' + 10
                : (c >= 'A' && c <= 'F') ? c - 'A' + 10
                                         : -1;
        if (v < 0)
            return -1;
        if (i % 2 == 0)
            seed[i / 2] = (uint8_t)(v << 4);
        else
            seed[i / 2] |= (uint8_t)v;
    }
    return 0;
}

#ifndef BFF_SOUP_NO_MAIN

/* ------------------------------------------------------------------------
 * Output and main
 * ---------------------------------------------------------------------- */

static int cmp_i64(const void *a, const void *b)
{
    int64_t x = *(const int64_t *)a, y = *(const int64_t *)b;
    return (x > y) - (x < y);
}

static int write_outputs(const char *dir, const config *cfg, const run_result *runs)
{
    char path[512];
    uint32_t transitions = 0, failed = 0;
    int64_t crossed[MAX_RUNS];
    float max_hoe_untransitioned = -INFINITY;
    char epochs_str[16 * MAX_RUNS] = "", final_str[16 * MAX_RUNS] = "";
    size_t ep = 0, fp = 0;

    uint64_t guard_checks = 0;
    for (uint32_t i = 0; i < cfg->runs; i++) {
        const run_result *r = &runs[i];
        failed += r->failed != 0;
        guard_checks += r->guard_checks;
        if (r->cross_epoch >= 0)
            crossed[transitions++] = r->cross_epoch;
        for (uint32_t j = 0; j < r->ntraj && r->cross_epoch < 0; j++)
            if (r->traj[j].hoe > max_hoe_untransitioned)
                max_hoe_untransitioned = r->traj[j].hoe;
        /* a run's first epoch above the threshold, -1 if none, -2 if it failed */
        ep += snprintf(epochs_str + ep, sizeof epochs_str - ep, "%s%lld", i ? "," : "",
                       r->failed ? -2LL : (long long)r->cross_epoch);
        fp += snprintf(final_str + fp, sizeof final_str - fp, "%s%.3f", i ? "," : "",
                       r->ntraj ? (double)r->traj[r->ntraj - 1].hoe : 0.0);
    }
    char median[32] = "-1";
    if (transitions) {
        qsort(crossed, transitions, sizeof crossed[0], cmp_i64);
        int64_t lo = crossed[(transitions - 1) / 2], hi = crossed[transitions / 2];
        if ((lo + hi) % 2 == 0)
            snprintf(median, sizeof median, "%lld", (long long)((lo + hi) / 2));
        else
            snprintf(median, sizeof median, "%lld.5", (long long)((lo + hi) / 2));
    }

    snprintf(path, sizeof path, "%s/outputs.json", dir);
    FILE *f = fopen(path, "w");
    if (!f)
        return -1;
    fprintf(f, "{\n");
    fprintf(f, "  \"runs\": %u,\n", cfg->runs);
    fprintf(f, "  \"epochs_max\": %llu,\n", (unsigned long long)cfg->epochs);
    fprintf(f, "  \"transitions\": %u,\n", transitions);
    fprintf(f, "  \"fraction\": %.4f,\n", (double)transitions / cfg->runs);
    fprintf(f, "  \"median_epoch\": %s,\n", median);
    fprintf(f, "  \"epochs\": \"%s\",\n", epochs_str);
    fprintf(f, "  \"threshold\": %.1f,\n", HOE_THRESHOLD);
    fprintf(f, "  \"mutation_rate\": %.12f,\n", 1.0 / (1u << MUT_BITS));
    fprintf(f, "  \"step_limit\": %u,\n", STEP_LIMIT);
    fprintf(f, "  \"num_programs\": %u,\n", cfg->n);
    fprintf(f, "  \"tape_bytes\": %d,\n", TAPE_BYTES);
    fprintf(f, "  \"language\": \"%s\",\n", LANG_NAME[cfg->lang]);
    fprintf(f, "  \"measure_every\": %u,\n", MEASURE_EVERY);
    {
        uint32_t v = BrotliEncoderVersion();
        fprintf(f, "  \"brotli\": \"%u.%u.%u q%d lgwin%d\",\n", v >> 24, (v >> 12) & 0xfff,
                v & 0xfff, BROTLI_QUALITY, BROTLI_LGWIN);
    }
    fprintf(f, "  \"rng\": \"xoshiro256** from sha256(seed||u64le(run))\",\n");
    if (transitions < cfg->runs)
        fprintf(f, "  \"max_hoe_no_transition\": %.4f,\n", (double)max_hoe_untransitioned);
    else
        fprintf(f, "  \"max_hoe_no_transition\": -1,\n");
    fprintf(f, "  \"final_hoe\": \"%s\",\n", final_str);
    fprintf(f, "  \"guard_checks\": %llu,\n", (unsigned long long)guard_checks);
    fprintf(f, "  \"failed_runs\": %u\n", failed);
    fprintf(f, "}\n");
    if (fclose(f))
        return -1;

    snprintf(path, sizeof path, "%s/trajectory.csv", dir);
    f = fopen(path, "w");
    if (!f)
        return -1;
    fprintf(f, "run,epoch,hoe,h0,bpb,brotli_size,ops_per_pair\n");
    for (uint32_t i = 0; i < cfg->runs; i++)
        for (uint32_t j = 0; j < runs[i].ntraj; j++) {
            const sample *m = &runs[i].traj[j];
            fprintf(f, "%u,%llu,%.6f,%.6f,%.6f,%llu,%.3f\n", i, (unsigned long long)m->epoch,
                    (double)m->hoe, m->h0, m->bpb, (unsigned long long)m->zsize, m->ops_per_pair);
        }
    return fclose(f) ? -1 : 0;
}

static int parse_u64(const char *s, uint64_t lo, uint64_t hi, uint64_t *out)
{
    char *end;
    errno = 0;
    unsigned long long v = strtoull(s, &end, 10);
    if (errno || end == s || *end || s[0] == '-' || v < lo || v > hi)
        return -1;
    *out = v;
    return 0;
}

int main(int argc, char **argv)
{
    static config cfg;
    uint64_t v;
    cfg.runs = 20;
    cfg.epochs = 16384;
    cfg.lang = LANG_BFF;
    cfg.n = NUM_PROGRAMS;
    if (parse_seed(getenv("ECDYSIS_SEED"), cfg.seed)) {
        fprintf(stderr, "ECDYSIS_SEED must be 64 hexadecimal digits\n");
        return 2;
    }
    if (argc > 1) {
        if (parse_u64(argv[1], 1, MAX_RUNS, &v)) {
            fprintf(stderr, "runs (argv[1]) must be 1..%u\n", MAX_RUNS);
            return 2;
        }
        cfg.runs = (uint32_t)v;
    }
    if (argc > 2) {
        if (parse_u64(argv[2], 1, 1u << 22, &v)) {
            fprintf(stderr, "epochs (argv[2]) must be 1..2^22\n");
            return 2;
        }
        cfg.epochs = v;
    }
    if (argc > 3) {
        if (!strcmp(argv[3], "bff"))
            cfg.lang = LANG_BFF;
        else if (!strcmp(argv[3], "bff_noheads"))
            cfg.lang = LANG_BFF_NOHEADS;
        else {
            fprintf(stderr, "lang (argv[3]) must be bff or bff_noheads\n");
            return 2;
        }
    }
    if (argc > 4) {
        fprintf(stderr, "usage: ECDYSIS_SEED=<64 hex> %s [runs] [epochs] [bff|bff_noheads]\n",
                argv[0]);
        return 2;
    }
    if (mkdir("results", 0755) != 0 && errno != EEXIST) {
        perror("results");
        return 1;
    }
    run_result *runs = calloc(cfg.runs, sizeof *runs);
    if (!runs)
        return 1;
    fprintf(stderr, "bff_soup: %u runs x %llu epochs, lang %s, %u programs of %d bytes, %u threads\n",
            cfg.runs, (unsigned long long)cfg.epochs, LANG_NAME[cfg.lang], cfg.n, TAPE_BYTES,
            cfg.runs < NUM_THREADS ? cfg.runs : NUM_THREADS);
    const double t0 = now_seconds();
    const int rc = run_all(&cfg, runs);
    const double wall = now_seconds() - t0;
    if (write_outputs("results", &cfg, runs)) {
        perror("results/outputs.json");
        return 1;
    }
    uint64_t total_epochs = 0;
    double total_run_seconds = 0;
    for (uint32_t i = 0; i < cfg.runs; i++) {
        total_epochs += runs[i].epochs_run;
        total_run_seconds += runs[i].seconds;
        fprintf(stderr, "run %2u: %s at epoch %lld after %llu epochs, %.1f s (%.2f epochs/s)\n", i,
                runs[i].cross_epoch >= 0 ? "transition" : "no transition",
                (long long)runs[i].cross_epoch, (unsigned long long)runs[i].epochs_run,
                runs[i].seconds, runs[i].seconds > 0 ? runs[i].epochs_run / runs[i].seconds : 0.0);
    }
    fprintf(stderr, "wall %.1f s; %llu epochs in %.1f run-seconds (%.2f epochs/s per run)\n", wall,
            (unsigned long long)total_epochs, total_run_seconds,
            total_run_seconds > 0 ? total_epochs / total_run_seconds : 0.0);
    return rc ? 1 : 0;
}
#endif
