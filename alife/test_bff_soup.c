/*
 * test_bff_soup.c: tests for bff_soup.c, and the tools used to cross-check it
 * against the authors' cubff.
 *
 * Build: gcc -O2 -pthread test_bff_soup.c -lbrotlienc -lm -o test_bff_soup
 *
 *   test_bff_soup unit
 *       Unit tests: SHA-256 and xoshiro256** vectors, the seed derivation,
 *       the interpreter on hand-written tapes (each instruction, loops,
 *       unmatched brackets, head wrap-around, the step limit,
 *       self-modification), fast against reference interpreter on random
 *       tapes, the mutation shortcut, mutation rate and replacement
 *       uniformity, the pairing, determinism across threads, the measure.
 *
 *   test_bff_soup cubff-log LANG SEED MAX_EPOCHS [SOUP_FILE [MUTATION_PROB]]
 *       Drives this file's epoch code (soup_epoch, bff_eval, soup_measure)
 *       with cubff's own generator, restated from common_language.h, and
 *       prints the log cubff's `bin/main --lang LANG --seed SEED
 *       --max_epochs MAX_EPOCHS --log FILE` writes. With SOUP_FILE (cubff's
 *       checkpoint format) it starts from that soup, as `--load` does, and
 *       MUTATION_PROB (out of 2^30, default 2^18) mirrors --mutation_prob.
 *       Validation only: the program never uses cubff's generator.
 *
 *   test_bff_soup gen-tapes          random 128-byte tapes to stdout
 *   test_bff_soup eval-tapes LANG [LIMIT] [ref]
 *       Runs tapes from stdin through bff_eval (or bff_eval_ref), writing
 *       each final tape and its op count (u32 LE), as xcheck/cubff_eval.cc
 *       does with cubff's interpreter.
 *   test_bff_soup gen-soup KIND FILE  a soup in cubff's checkpoint format:
 *       KIND inert-random, inert-structured, inert-mixed (no instruction
 *       bytes, so a cubff epoch leaves it unchanged), or evolved-LANG-EPOCHS
 *       (this program's soup after EPOCHS epochs from a fixed seed).
 *   test_bff_soup measure-file FILE   the measure of a checkpoint's soup, as
 *       a cubff log line.
 */
#define BFF_SOUP_NO_MAIN
#include "bff_soup.c"

static int failures;
static int checks;

#define CHECK(cond, ...)                                                       \
    do {                                                                       \
        checks++;                                                              \
        if (!(cond)) {                                                         \
            failures++;                                                        \
            fprintf(stderr, "FAIL %s:%d: ", __FILE__, __LINE__);               \
            fprintf(stderr, __VA_ARGS__);                                      \
            fputc('\n', stderr);                                               \
        }                                                                      \
    } while (0)

/* ------------------------------------------------------------------------
 * cubff's generator, restated for validation (common_language.h)
 * ---------------------------------------------------------------------- */

/* common_language.h:131-136 */
static uint64_t splitmix64(uint64_t x)
{
    uint64_t z = x + 0x9e3779b97f4a7c15ULL;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

typedef struct {
    noise base;
    uint64_t seed;
    uint32_t mutation_prob; /* out of 2^30 */
} cubff_noise;

/* common_language.h:367-369 */
static uint64_t cubff_seed(const cubff_noise *c, uint64_t s2)
{
    return splitmix64(splitmix64(c->seed) ^ splitmix64(s2));
}

/* common_language.h:418-424 and 464-476 */
static void cubff_order(noise *self, uint32_t *perm, uint32_t n, uint64_t epoch)
{
    const cubff_noise *c = (const cubff_noise *)self;
    for (uint32_t i = 0; i < n; i++)
        perm[i] = i;
    for (uint64_t i = n; i-- > 0;) {
        uint64_t j = splitmix64(cubff_seed(c, epoch * n + i)) % (i + 1);
        uint32_t tmp = perm[i];
        perm[i] = perm[j];
        perm[j] = tmp;
    }
}

/* common_language.h:172-180, with seed = seed(epoch) (common_language.h:491-492) */
static void cubff_mutate(noise *self, uint8_t *t, uint32_t n, uint64_t epoch, uint32_t pair)
{
    const cubff_noise *c = (const cubff_noise *)self;
    const uint64_t se = cubff_seed(c, epoch);
    for (uint64_t i = 0; i < PAIR_BYTES; i++) {
        uint64_t rng = splitmix64(((uint64_t)n * se + pair) * PAIR_BYTES + i);
        uint8_t repl = (uint8_t)(rng & 0xFF);
        uint64_t prob = (rng >> 8) & ((1ULL << 30) - 1);
        if (prob < c->mutation_prob)
            t[i] = repl;
    }
}

/* common_language.h:139-155 with seed(0) (common_language.h:371-373) */
static void cubff_init(soup *s, const cubff_noise *c)
{
    const uint64_t s0 = cubff_seed(c, 0);
    for (uint64_t idx = 0; idx < s->n; idx++)
        for (uint64_t i = 0; i < TAPE_BYTES; i++)
            s->bytes[idx * TAPE_BYTES + i] =
                (uint8_t)(splitmix64((uint64_t)TAPE_BYTES * s->n * s0 + TAPE_BYTES * idx + i) % 256);
}

/* cubff's checkpoint format (common_language.h:354-360,398-403,576-580):
 * reset_index, num_programs, epoch as size_t, then the soup. */
static int soup_save(const soup *s, const char *path, uint64_t epoch)
{
    FILE *f = fopen(path, "wb");
    if (!f)
        return -1;
    uint64_t hdr[3] = {1, s->n, epoch};
    int ok = fwrite(hdr, sizeof hdr, 1, f) == 1 &&
             fwrite(s->bytes, (size_t)s->n * TAPE_BYTES, 1, f) == 1;
    return (fclose(f) == 0 && ok) ? 0 : -1;
}

static int soup_load(soup *s, const char *path, uint64_t *epoch)
{
    FILE *f = fopen(path, "rb");
    uint64_t hdr[3];
    if (!f || fread(hdr, sizeof hdr, 1, f) != 1 || hdr[1] == 0 || hdr[1] > (1u << 24) ||
        soup_alloc(s, (uint32_t)hdr[1]) ||
        fread(s->bytes, (size_t)s->n * TAPE_BYTES, 1, f) != 1) {
        if (f)
            fclose(f);
        return -1;
    }
    fclose(f);
    *epoch = hdr[2];
    return 0;
}

static void hex32(const uint8_t d[32], char out[65])
{
    for (int i = 0; i < 32; i++)
        snprintf(out + 2 * i, 3, "%02x", d[i]);
}

static int parse_lang(const char *s)
{
    if (!strcmp(s, "bff"))
        return LANG_BFF;
    if (!strcmp(s, "bff_noheads"))
        return LANG_BFF_NOHEADS;
    fprintf(stderr, "unknown language %s\n", s);
    exit(2);
}

/* The log cubff's main writes (main.cc:339-341,397-398): a line after
 * epoch e whenever e % 64 == 0, until a line's epoch exceeds max_epochs
 * (main.cc:461-462). */
static int cubff_log(int lang, uint64_t seed, uint64_t max_epochs, const char *soup_file,
                     uint32_t mutation_prob)
{
    soup s;
    cubff_noise c = {{cubff_order, cubff_mutate}, seed, mutation_prob};
    uint64_t epoch = 0;
    if (soup_file) {
        if (soup_load(&s, soup_file, &epoch))
            return 1;
    } else {
        if (soup_alloc(&s, NUM_PROGRAMS))
            return 1;
        cubff_init(&s, &c);
    }
    printf("epoch,brotli_size,soup_size,higher_entropy\n");
    for (;; epoch++) {
        soup_epoch(&s, &c.base, epoch, lang);
        if (epoch % MEASURE_EVERY == 0) {
            sample m;
            if (soup_measure(&s, &m))
                return 1;
            printf("%llu,%llu,%u,%f\n", (unsigned long long)(epoch + 1),
                   (unsigned long long)m.zsize, s.n, (double)m.hoe);
            if (getenv("BFF_SOUP_HASHES")) {
                uint8_t d[32];
                char h[65];
                sha256(s.bytes, (size_t)s.n * TAPE_BYTES, d);
                hex32(d, h);
                fprintf(stderr, "soup after epoch %llu: sha256 %s\n",
                        (unsigned long long)(epoch + 1), h);
            }
            if (epoch + 1 > max_epochs)
                break;
        }
    }
    fprintf(stderr, "guard checks %llu, failures %llu\n", (unsigned long long)s.guard_checks,
            (unsigned long long)s.guard_failures);
    return s.guard_failures ? 1 : 0;
}

/* ------------------------------------------------------------------------
 * Unit tests: generators
 * ---------------------------------------------------------------------- */

static void test_sha256(void)
{
    static const struct {
        int len_a; /* message: len_a copies of 'a', or -1/-2/-3 for the named ones */
        const char *hex;
    } v[] = {
        {-1, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        {-2, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"},
        {-3, "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"},
        {55, "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318"},
        {56, "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a"},
        {63, "7d3e74a05d7db15bce4ad9ec0658ea98e3f06eeecf16b4c6fff2da457ddc2f34"},
        {64, "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb"},
        {65, "635361c48bb9eab14198e76ea8ab7f1a41685d6ad62aa9146d301d4f17eb0ae0"},
        {119, "31eba51c313a5c08226adf18d4a359cfdfd8d2e816b13f4af952f7ea6584dcfb"},
        {120, "2f3d335432c70b580af0e8e1b3674a7c020d683aa5f73aaaedfdc55af904c21c"},
        {1000, "41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3"},
    };
    static uint8_t buf[1000];
    for (size_t i = 0; i < sizeof v / sizeof v[0]; i++) {
        const uint8_t *msg = buf;
        size_t len;
        if (v[i].len_a == -1) {
            len = 0;
        } else if (v[i].len_a == -2) {
            msg = (const uint8_t *)"abc";
            len = 3;
        } else if (v[i].len_a == -3) {
            msg = (const uint8_t *)"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
            len = 56;
        } else {
            memset(buf, 'a', (size_t)v[i].len_a);
            len = (size_t)v[i].len_a;
        }
        uint8_t d[32];
        char h[65];
        sha256(msg, len, d);
        hex32(d, h);
        CHECK(!strcmp(h, v[i].hex), "sha256 vector %zu: %s", i, h);
    }
}

static void test_xoshiro(void)
{
    /* Reference values from an independent Python implementation. */
    xoshiro256 g = {{1, 2, 3, 4}};
    const uint64_t want[6] = {11520ULL, 0ULL, 1509978240ULL, 1215971899390074240ULL,
                              1216172134540287360ULL, 607988272756665600ULL};
    for (int i = 0; i < 6; i++) {
        uint64_t x = xo_next(&g);
        CHECK(x == want[i], "xoshiro output %d: %llu", i, (unsigned long long)x);
    }
    /* The derivation: SHA-256(seed || u64le(run)) -> state (Python reference). */
    uint8_t seed[32];
    CHECK(parse_seed("00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff", seed) == 0,
          "parse_seed");
    const struct {
        uint64_t run, s0, first[3];
    } d[] = {
        {0, 0x863d0e37d956483cULL, {1017363738390925913ULL, 12365621426662623219ULL, 14117908553105111034ULL}},
        {1, 0x563e3b70d3fba7b5ULL, {10764507158313542685ULL, 11888047275783186246ULL, 6379318863248880535ULL}},
        {19, 0xe643bc595fe68a2dULL, {17395028902228174044ULL, 13436548349755136245ULL, 13633358971723355751ULL}},
    };
    for (int i = 0; i < 3; i++) {
        derive_generator(&g, seed, d[i].run);
        CHECK(g.s[0] == d[i].s0, "derived state for run %llu", (unsigned long long)d[i].run);
        for (int k = 0; k < 3; k++)
            CHECK(xo_next(&g) == d[i].first[k], "derived output %d for run %llu", k,
                  (unsigned long long)d[i].run);
    }
    CHECK(parse_seed("0011", seed) != 0, "short seed rejected");
    CHECK(parse_seed("zz112233445566778899aabbccddeeff00112233445566778899aabbccddeeff", seed) != 0,
          "non-hex seed rejected");
    CHECK(parse_seed(NULL, seed) != 0, "missing seed rejected");
    /* Bounded integers stay in range and hit both ends. */
    derive_generator(&g, seed, 7);
    int seen_lo = 0, seen_hi = 0, bad = 0;
    for (int i = 0; i < 100000; i++) {
        uint32_t x = xo_below(&g, 7);
        bad += x >= 7;
        seen_lo |= x == 0;
        seen_hi |= x == 6;
    }
    CHECK(!bad && seen_lo && seen_hi, "xo_below range");
    for (int i = 0; i < 1000; i++)
        CHECK(xo_below(&g, 1) == 0, "xo_below(1)");
}

/* ------------------------------------------------------------------------
 * Unit tests: the interpreter on hand-written tapes
 * ---------------------------------------------------------------------- */

static int first_diff(const uint8_t *a, const uint8_t *b)
{
    for (int i = 0; i < PAIR_BYTES; i++)
        if (a[i] != b[i])
            return i;
    return -1;
}

/* Runs `in` through both interpreters; both must leave `want` and, if
 * want_ops >= 0, report want_ops. */
static void expect(const char *name, int lang, uint32_t limit, const uint8_t in[PAIR_BYTES],
                   const uint8_t want[PAIR_BYTES], long want_ops)
{
    uint8_t a[PAIR_BYTES], b[PAIR_BYTES];
    memcpy(a, in, PAIR_BYTES);
    memcpy(b, in, PAIR_BYTES);
    uint32_t oa = bff_eval_ref(a, lang, limit);
    uint32_t ob = bff_eval(b, lang, limit);
    int da = first_diff(a, want), db = first_diff(b, want);
    CHECK(da < 0, "%s: reference tape differs at byte %d (%d, want %d)", name, da, da < 0 ? 0 : a[da],
          da < 0 ? 0 : want[da]);
    CHECK(db < 0, "%s: fast tape differs at byte %d (%d, want %d)", name, db, db < 0 ? 0 : b[db],
          db < 0 ? 0 : want[db]);
    if (want_ops >= 0) {
        CHECK(oa == (uint32_t)want_ops, "%s: reference ops %u, want %ld", name, oa, want_ops);
        CHECK(ob == (uint32_t)want_ops, "%s: fast ops %u, want %ld", name, ob, want_ops);
    }
    CHECK(oa == ob, "%s: ops differ, reference %u fast %u", name, oa, ob);
}

#define FILL 0x09 /* a no-op byte that is not zero */

/* A fresh "bff" tape: head0 at h0, head1 at h1, code from byte 2. */
static void bff_tape(uint8_t t[PAIR_BYTES], int h0, int h1, const char *code)
{
    memset(t, FILL, PAIR_BYTES);
    t[0] = (uint8_t)h0;
    t[1] = (uint8_t)h1;
    memcpy(t + 2, code, strlen(code));
}

static void test_interpreter(void)
{
    uint8_t in[PAIR_BYTES], want[PAIR_BYTES];
    const int B = LANG_BFF, N = LANG_BFF_NOHEADS;
    const uint32_t L = STEP_LIMIT;

    /* Each instruction ("bff": heads from bytes 0 and 1, code from byte 2). */
    bff_tape(in, 100, 101, "+");
    in[100] = 5;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 6;
    expect("+ increments t[head0]", B, L, in, want, 1);

    bff_tape(in, 100, 101, "-");
    in[100] = 0;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 255;
    expect("- wraps 0 to 255", B, L, in, want, 1);

    bff_tape(in, 100, 101, "+");
    in[100] = 255;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 0;
    expect("+ wraps 255 to 0", B, L, in, want, 1);

    bff_tape(in, 100, 101, ">+");
    memcpy(want, in, PAIR_BYTES);
    want[101] = FILL + 1;
    expect("> moves head0 right", B, L, in, want, 2);

    bff_tape(in, 100, 101, "<+");
    memcpy(want, in, PAIR_BYTES);
    want[99] = FILL + 1;
    expect("< moves head0 left", B, L, in, want, 2);

    bff_tape(in, 127, 101, ">+");
    memcpy(want, in, PAIR_BYTES);
    want[0] = 128;
    expect("head0 wraps 127 -> 0", B, L, in, want, 2);

    bff_tape(in, 0, 101, "<+");
    memcpy(want, in, PAIR_BYTES);
    want[127] = FILL + 1;
    expect("head0 wraps 0 -> 127", B, L, in, want, 2);

    bff_tape(in, 200, 129, "+.");
    memcpy(want, in, PAIR_BYTES);
    want[72] = FILL + 1; /* 200 mod 128 */
    want[1] = FILL + 1;  /* head1 = 129 mod 128 = 1, and . copies t[72] there */
    expect("initial heads are bytes 0 and 1 mod 128", B, L, in, want, 2);

    bff_tape(in, 100, 110, "}.");
    in[100] = 0x41;
    memcpy(want, in, PAIR_BYTES);
    want[111] = 0x41;
    expect("} moves head1 right; . copies t[head0] to t[head1]", B, L, in, want, 2);

    bff_tape(in, 100, 110, "{.");
    in[100] = 0x41;
    memcpy(want, in, PAIR_BYTES);
    want[109] = 0x41;
    expect("{ moves head1 left", B, L, in, want, 2);

    bff_tape(in, 100, 127, "}.");
    in[100] = 0x41;
    memcpy(want, in, PAIR_BYTES);
    want[0] = 0x41;
    expect("head1 wraps 127 -> 0", B, L, in, want, 2);

    bff_tape(in, 100, 0, "{.");
    in[100] = 0x41;
    memcpy(want, in, PAIR_BYTES);
    want[127] = 0x41;
    expect("head1 wraps 0 -> 127", B, L, in, want, 2);

    bff_tape(in, 100, 110, ",");
    in[110] = 0x42;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 0x42;
    expect(", copies t[head1] to t[head0]", B, L, in, want, 1);

    /* Byte 0 is a no-op when executed and costs no op. */
    bff_tape(in, 100, 101, "\x01+");
    in[2] = 0;
    in[100] = 5;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 6;
    expect("byte 0 is a no-op", B, L, in, want, 1);

    /* Loops. */
    bff_tape(in, 100, 101, "[-]");
    in[100] = 5;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 0;
    expect("[-] counts down to zero", B, L, in, want, 1 + 5 * 2);

    bff_tape(in, 100, 101, "[+]+");
    in[100] = 0;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 1;
    expect("[ with t[head0] == 0 jumps past the matching ]", B, L, in, want, 2);

    bff_tape(in, 100, 101, "[>+++<-]");
    in[100] = 2;
    in[101] = 0;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 0;
    want[101] = 6;
    expect("[>+++<-] multiplies", B, L, in, want, 1 + 2 * 7);

    bff_tape(in, 100, 101, "[>[-]<-]");
    in[100] = 2;
    in[101] = 3;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 0;
    want[101] = 0;
    expect("nested loops match by nesting in both directions", B, L, in, want, 17);

    memset(in, FILL, PAIR_BYTES);
    in[0] = 100;
    in[1] = 101;
    in[2] = '[';
    in[70] = ']';
    in[71] = '+';
    in[100] = 0;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 1;
    expect("[ finds its ] in the second program", B, L, in, want, 2);

    /* Unmatched brackets. */
    bff_tape(in, 100, 101, "[+");
    in[100] = 0;
    memcpy(want, in, PAIR_BYTES);
    expect("unmatched [ with t[head0] == 0 stops execution", B, L, in, want, 1);

    bff_tape(in, 100, 101, "[+");
    in[100] = 7;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 8;
    expect("unmatched [ with t[head0] != 0 falls through", B, L, in, want, 2);

    bff_tape(in, 100, 101, "+]+");
    in[100] = 7;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 8;
    expect("unmatched ] with t[head0] != 0 stops execution", B, L, in, want, 2);

    bff_tape(in, 100, 101, "+]+");
    in[100] = 255;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 1;
    expect("unmatched ] with t[head0] == 0 falls through", B, L, in, want, 3);

    bff_tape(in, 100, '[', "-]");
    in[100] = 3;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 0;
    expect("] matches a [ in byte 1 (a head byte)", B, L, in, want, 6);

    memset(in, FILL, PAIR_BYTES);
    in[0] = 100;
    in[1] = 101;
    in[2] = '[';
    in[127] = ']';
    in[100] = 0;
    memcpy(want, in, PAIR_BYTES);
    expect("[ jumping to a ] in byte 127 ends execution", B, L, in, want, 1);

    memset(in, FILL, PAIR_BYTES);
    in[0] = 100;
    in[1] = 101;
    in[127] = '[';
    in[100] = 0;
    memcpy(want, in, PAIR_BYTES);
    expect("[ in byte 127 with t[head0] == 0 is unmatched", B, L, in, want, 1);

    /* Self-modification. */
    bff_tape(in, 5, 101, "+");
    in[5] = '*'; /* 0x2A, a no-op, becomes + before it is reached */
    memcpy(want, in, PAIR_BYTES);
    want[5] = ','; /* + then +: 0x2A -> 0x2B -> 0x2C */
    expect("an instruction written ahead is executed", B, L, in, want, 2);

    bff_tape(in, 50, 101, "+>[");
    in[50] = '\\'; /* 0x5C becomes ] (0x5D) */
    in[51] = 0;
    in[60] = '+';
    memcpy(want, in, PAIR_BYTES);
    want[50] = ']';
    want[51] = 1;
    expect("a ] created at run time matches", B, L, in, want, 4);

    /* bff_noheads: heads and instruction pointer start at 0, byte 0 runs. */
    memset(in, FILL, PAIR_BYTES);
    in[0] = '+';
    memcpy(want, in, PAIR_BYTES);
    want[0] = ',';
    expect("noheads: code starts at byte 0 with head0 at 0", N, L, in, want, 1);

    memset(in, FILL, PAIR_BYTES);
    in[0] = '>';
    in[1] = '+';
    memcpy(want, in, PAIR_BYTES);
    want[1] = ',';
    expect("noheads: bytes 0 and 1 are code, not head positions", N, L, in, want, 2);

    memset(in, FILL, PAIR_BYTES);
    in[0] = '+';
    in[1] = '+';
    memcpy(want, in, PAIR_BYTES);
    expect("bff: bytes 0 and 1 are never executed", B, L, in, want, 0);

    /* The step limit. */
    memset(in, FILL, PAIR_BYTES);
    in[0] = '[';
    in[1] = ']';
    memcpy(want, in, PAIR_BYTES);
    expect("noheads: [] loops until the 8192-step limit", N, L, in, want, 8192);

    bff_tape(in, 100, 101, "[]");
    memcpy(want, in, PAIR_BYTES);
    expect("bff: [] loops until the 8192-step limit", B, L, in, want, 8192);

    memset(in, FILL, PAIR_BYTES);
    in[0] = 100;
    in[1] = 101;
    in[2] = '[';
    in[53] = ']';
    memcpy(want, in, PAIR_BYTES);
    expect("a loop of 50 no-ops counts each no-op as a step", B, L, in, want, 161);

    for (uint32_t lim = 26; lim <= 40; lim++) {
        char name[64];
        bff_tape(in, 100, 101, "[}.]");
        in[100] = 1;
        memcpy(want, in, PAIR_BYTES);
        for (uint32_t w = 0; w < lim / 3; w++)
            want[102 + w] = 1;
        snprintf(name, sizeof name, "step limit %u stops mid-loop", lim);
        expect(name, B, lim, in, want, lim);
    }

    bff_tape(in, 100, 101, "+++");
    in[100] = 0;
    memcpy(want, in, PAIR_BYTES);
    want[100] = 2;
    expect("limit 2 stops after two steps", B, 2, in, want, 2);
    memcpy(want, in, PAIR_BYTES);
    expect("limit 0 executes nothing", B, 0, in, want, 0);

    memset(in, FILL, PAIR_BYTES);
    in[0] = 100;
    in[1] = 101;
    in[60] = '+';
    in[100] = 0;
    memcpy(want, in, PAIR_BYTES);
    expect("limit inside a run of no-ops stops before the instruction", B, 58, in, want, 0);
    want[100] = 1;
    expect("limit just after the instruction includes it", B, 59, in, want, 1);
}

/* Fast against reference on many random tapes of several kinds. */
static void test_interpreters_agree(long count)
{
    static const char CODE[] = "<>{}+-.,[]";
    uint8_t seed[32] = {0x5e};
    xoshiro256 g;
    derive_generator(&g, seed, 99);
    long mismatches = 0;
    for (long i = 0; i < count; i++) {
        uint8_t a[PAIR_BYTES], b[PAIR_BYTES];
        const int kind = (int)(i % 5);
        for (int j = 0; j < PAIR_BYTES; j++) {
            uint64_t x = xo_next(&g);
            switch (kind) {
            case 0: a[j] = (uint8_t)x; break;
            case 1: a[j] = (x >> 8) % 3 ? (uint8_t)CODE[x % 10] : (uint8_t)(x >> 16); break;
            case 2: a[j] = (x >> 8) % 8 ? (uint8_t)CODE[x % 10] : 0; break;
            case 3: a[j] = (x >> 8) % 16 == 0 ? (uint8_t)CODE[x % 10] : (uint8_t)(x >> 16); break;
            default: a[j] = (x >> 8) % 2 ? (uint8_t)"[]{}"[x % 4] : (uint8_t)CODE[(x >> 4) % 10]; break;
            }
        }
        const int lang = (int)((i / 5) % 2);
        const uint32_t limit = (i % 3 == 0) ? (uint32_t)(xo_next(&g) % 600) : STEP_LIMIT;
        memcpy(b, a, PAIR_BYTES);
        uint32_t of = bff_eval(a, lang, limit), orf = bff_eval_ref(b, lang, limit);
        if (of != orf || memcmp(a, b, PAIR_BYTES)) {
            if (mismatches < 3)
                fprintf(stderr, "  mismatch: tape %ld kind %d lang %d limit %u\n", i, kind, lang, limit);
            mismatches++;
        }
    }
    CHECK(mismatches == 0, "fast and reference interpreters disagree on %ld of %ld tapes", mismatches,
          count);
}

/* The mask builder against the byte tables, for every byte value. */
static void test_masks(void)
{
    uint8_t t[PAIR_BYTES];
    for (int v = 0; v < 256; v++) {
        memset(t, v, PAIR_BYTES);
        uint64_t im[2], bm[2], im2[2], bm2[2];
        build_masks(t, im, bm);
        build_masks_scalar(t, im2, bm2);
        const uint64_t all = IS_INSTR[v] ? ~0ULL : 0, br = IS_BRACKET[v] ? ~0ULL : 0;
        CHECK(im[0] == all && im[1] == all && bm[0] == br && bm[1] == br, "masks for byte %d", v);
        CHECK(im2[0] == all && im2[1] == all && bm2[0] == br && bm2[1] == br, "scalar masks %d", v);
    }
    int n_instr = 0;
    for (int v = 0; v < 256; v++)
        n_instr += IS_INSTR[v];
    CHECK(n_instr == 10, "ten instruction bytes");
    xoshiro256 g = {{9, 8, 7, 6}};
    for (int k = 0; k < 10000; k++) {
        for (int j = 0; j < PAIR_BYTES; j++)
            t[j] = (uint8_t)xo_next(&g);
        uint64_t im[2], bm[2], im2[2], bm2[2];
        build_masks(t, im, bm);
        build_masks_scalar(t, im2, bm2);
        CHECK(im[0] == im2[0] && im[1] == im2[1] && bm[0] == bm2[0] && bm[1] == bm2[1],
              "masks on random tape %d", k);
    }
}

/* ------------------------------------------------------------------------
 * Unit tests: noise
 * ---------------------------------------------------------------------- */

/* The plain loop the mutation shortcut must reproduce draw for draw. */
static uint64_t mutate_plain(xoshiro256 *g, uint8_t *t, uint32_t *hist)
{
    uint64_t events = 0;
    for (int i = 0; i < PAIR_BYTES;) {
        uint64_t w = xo_next(g);
        for (int k = 0; k < 5 && i < PAIR_BYTES; k++, i++, w >>= MUT_BITS)
            if ((w & ((1u << MUT_BITS) - 1)) == 0) {
                t[i] = (uint8_t)(xo_next(g) >> 56);
                events++;
                if (hist)
                    hist[t[i]]++;
            }
    }
    return events;
}

static void test_mutation(void)
{
    uint8_t seed[32] = {0x77};
    stream_noise nz;
    stream_noise_init(&nz, seed, 3);
    xoshiro256 plain = nz.g;
    uint8_t a[PAIR_BYTES], b[PAIR_BYTES];
    long diffs = 0;
    uint64_t events = 0;
    static uint32_t hist[256];
    const long tapes = 1L << 19; /* 2^26 bytes: 2^14 expected mutations */
    for (long i = 0; i < tapes; i++) {
        for (int j = 0; j < PAIR_BYTES; j++)
            a[j] = b[j] = (uint8_t)(i * 31 + j);
        nz.base.mutate(&nz.base, a, NUM_PROGRAMS, 0, 0);
        events += mutate_plain(&plain, b, hist);
        diffs += memcmp(a, b, PAIR_BYTES) != 0;
    }
    CHECK(diffs == 0, "mutation shortcut differs from the plain loop on %ld tapes", diffs);
    CHECK(!memcmp(&plain, &nz.g, sizeof plain), "mutation shortcut consumes different draws");
    const double expect_ev = (double)tapes * PAIR_BYTES / 4096.0, sd = sqrt(expect_ev);
    CHECK(fabs((double)events - expect_ev) < 5 * sd, "mutation events %llu, expected %.0f +- %.0f",
          (unsigned long long)events, expect_ev, sd);
    double chi2 = 0;
    for (int v = 0; v < 256; v++) {
        double e = events / 256.0;
        chi2 += (hist[v] - e) * (hist[v] - e) / e;
    }
    CHECK(chi2 < 255 + 6 * sqrt(2 * 255.0), "replacement bytes not uniform: chi2 %.1f", chi2);
    fprintf(stderr, "  mutation: %llu events in %ld bytes (rate %.3e, cubff 2^-12 = %.3e), "
                    "replacement chi2 %.1f on 255 dof\n",
            (unsigned long long)events, tapes * PAIR_BYTES, events / (double)(tapes * PAIR_BYTES),
            1.0 / 4096, chi2);
}

static void test_pairing(void)
{
    uint8_t seed[32] = {0x42};
    stream_noise nz;
    stream_noise_init(&nz, seed, 0);
    enum { N = 1000, TRIALS = 40000 };
    static uint32_t perm[N], first_pos[10], seen[N];
    for (int trial = 0; trial < TRIALS; trial++) {
        nz.base.order(&nz.base, perm, N, (uint64_t)trial);
        if (trial < 50) {
            memset(seen, 0, sizeof seen);
            int ok = 1;
            for (int i = 0; i < N; i++)
                ok &= perm[i] < N && !seen[perm[i]]++;
            CHECK(ok, "pairing order is a permutation");
        }
        for (int i = 0; i < N; i++)
            if (perm[i] == 0) {
                first_pos[i * 10 / N]++;
                break;
            }
    }
    double chi2 = 0;
    for (int b = 0; b < 10; b++)
        chi2 += (first_pos[b] - TRIALS / 10.0) * (first_pos[b] - TRIALS / 10.0) / (TRIALS / 10.0);
    CHECK(chi2 < 40, "program 0's slot is not uniform: chi2 %.1f on 9 dof", chi2);
    /* cubff-compat order is a permutation too, and matches a direct restatement. */
    cubff_noise c = {{cubff_order, cubff_mutate}, 10248, 1u << 18};
    c.base.order(&c.base, perm, N, 5);
    memset(seen, 0, sizeof seen);
    int ok = 1;
    for (int i = 0; i < N; i++)
        ok &= perm[i] < N && !seen[perm[i]]++;
    CHECK(ok, "cubff order is a permutation");
}

/* ------------------------------------------------------------------------
 * Unit tests: the soup, determinism, the measure
 * ---------------------------------------------------------------------- */

static void soup_digest(const soup *s, char out[65])
{
    uint8_t d[32];
    sha256(s->bytes, (size_t)s->n * TAPE_BYTES, d);
    hex32(d, out);
}

static void evolve(soup *s, const uint8_t seed[32], uint64_t run, uint64_t epochs, int lang)
{
    stream_noise nz;
    stream_noise_init(&nz, seed, run);
    soup_fill_random(s, &nz.g);
    for (uint64_t e = 0; e < epochs; e++)
        soup_epoch(s, &nz.base, e, lang);
}

static void test_determinism(void)
{
    uint8_t seed[32];
    parse_seed("00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff", seed);
    soup s1, s2;
    char d1[65], d2[65], d3[65];
    soup_alloc(&s1, 4096);
    soup_alloc(&s2, 4096);
    evolve(&s1, seed, 5, 200, LANG_BFF);
    evolve(&s2, seed, 5, 200, LANG_BFF);
    soup_digest(&s1, d1);
    soup_digest(&s2, d2);
    CHECK(!strcmp(d1, d2), "same seed and run, different soups");
    evolve(&s2, seed, 6, 200, LANG_BFF);
    soup_digest(&s2, d3);
    CHECK(strcmp(d1, d3), "different runs gave the same soup");
    CHECK(s1.guard_checks > 0 && s1.guard_failures == 0, "guard ran without failures");
    soup_free(&s1);
    soup_free(&s2);

    /* run_all on two threads gives what each run gives alone. */
    config cfg;
    memset(&cfg, 0, sizeof cfg);
    memcpy(cfg.seed, seed, 32);
    cfg.runs = 5;
    cfg.epochs = 130;
    cfg.lang = LANG_BFF_NOHEADS;
    cfg.n = 2048;
    cfg.quiet = 1;
    run_result *par = calloc(cfg.runs, sizeof *par), solo;
    CHECK(run_all(&cfg, par) == 0, "run_all");
    for (uint32_t i = 0; i < cfg.runs; i++) {
        memset(&solo, 0, sizeof solo);
        solo.index = i;
        run_one(&cfg, &solo);
        int same = solo.ntraj == par[i].ntraj && solo.cross_epoch == par[i].cross_epoch;
        for (uint32_t j = 0; same && j < solo.ntraj; j++)
            same = solo.traj[j].zsize == par[i].traj[j].zsize &&
                   solo.traj[j].hoe == par[i].traj[j].hoe &&
                   solo.traj[j].ops_per_pair == par[i].traj[j].ops_per_pair;
        CHECK(same, "run %u differs between threaded and solo execution", i);
        CHECK(solo.ntraj == 4, "samples after epochs 1, 65, 129 and the last (130): got %u", solo.ntraj);
        if (solo.ntraj == 4)
            CHECK(solo.traj[0].epoch == 1 && solo.traj[1].epoch == 65 && solo.traj[2].epoch == 129 &&
                      solo.traj[3].epoch == 130,
                  "sample epochs");
        free(solo.traj);
        free(par[i].traj);
    }
    free(par);
}

static void test_measure(void)
{
    soup s;
    sample m;
    soup_alloc(&s, NUM_PROGRAMS);
    memset(s.bytes, 0, (size_t)s.n * TAPE_BYTES);
    CHECK(soup_measure(&s, &m) == 0, "measure");
    CHECK(m.h0 == 0.0 && m.hoe <= 0 && m.hoe > -0.01, "all-zero soup: h0 %f hoe %f", m.h0,
          (double)m.hoe);

    xoshiro256 g = {{1, 2, 3, 4}};
    soup_fill_random(&s, &g);
    soup_measure(&s, &m);
    CHECK(m.h0 > 7.9999 && m.h0 <= 8.0, "random soup h0 %f", m.h0);
    CHECK(m.hoe < 0 && m.hoe > -0.001, "random soup hoe %f (cubff's epoch-1 value is -0.000157)",
          (double)m.hoe);
    fprintf(stderr, "  measure: random soup h0 %.6f bpb %.6f hoe %.6f\n", m.h0, m.bpb, (double)m.hoe);

    /* A soup of copies of one random program: high-order entropy close to h0. */
    uint8_t seed[32] = {0x0b};
    derive_generator(&g, seed, 0);
    for (int j = 0; j < TAPE_BYTES; j++)
        s.bytes[j] = (uint8_t)xo_next(&g);
    for (uint32_t i = 1; i < s.n; i++)
        memcpy(s.bytes + (size_t)i * TAPE_BYTES, s.bytes, TAPE_BYTES);
    soup_measure(&s, &m);
    CHECK(m.hoe > HOE_THRESHOLD, "a soup of one program's copies: hoe %f", (double)m.hoe);
    fprintf(stderr, "  measure: one program copied: h0 %.4f bpb %.6f hoe %.4f\n", m.h0, m.bpb,
            (double)m.hoe);
    soup_free(&s);
}

/* ------------------------------------------------------------------------
 * Cross-check tools
 * ---------------------------------------------------------------------- */

static int gen_tapes(void)
{
    static const char CODE[] = "<>{}+-.,[]";
    xoshiro256 g = {{0xC0FFEE, 0xBFF, 0x5EED, 0x7A9E}};
    uint8_t t[PAIR_BYTES];
    /* 400k tapes in five kinds, as test_interpreters_agree. */
    for (long i = 0; i < 400000; i++) {
        const int kind = (int)(i % 5);
        for (int j = 0; j < PAIR_BYTES; j++) {
            uint64_t x = xo_next(&g);
            switch (kind) {
            case 0: t[j] = (uint8_t)x; break;
            case 1: t[j] = (x >> 8) % 3 ? (uint8_t)CODE[x % 10] : (uint8_t)(x >> 16); break;
            case 2: t[j] = (x >> 8) % 8 ? (uint8_t)CODE[x % 10] : 0; break;
            case 3: t[j] = (x >> 8) % 16 == 0 ? (uint8_t)CODE[x % 10] : (uint8_t)(x >> 16); break;
            default: t[j] = (x >> 8) % 2 ? (uint8_t)"[]{}"[x % 4] : (uint8_t)CODE[(x >> 4) % 10]; break;
            }
        }
        if (fwrite(t, PAIR_BYTES, 1, stdout) != 1)
            return 1;
    }
    return 0;
}

static int eval_tapes(int lang, uint32_t limit, int use_ref)
{
    uint8_t t[PAIR_BYTES];
    while (fread(t, PAIR_BYTES, 1, stdin) == 1) {
        uint32_t ops = use_ref ? bff_eval_ref(t, lang, limit) : bff_eval(t, lang, limit);
        uint8_t le[4] = {(uint8_t)ops, (uint8_t)(ops >> 8), (uint8_t)(ops >> 16), (uint8_t)(ops >> 24)};
        if (fwrite(t, PAIR_BYTES, 1, stdout) != 1 || fwrite(le, 4, 1, stdout) != 1)
            return 1;
    }
    return 0;
}

/* Soups for the measure and end-to-end checks, in cubff's checkpoint format. */
static int gen_soup(const char *kind, const char *path)
{
    soup s;
    uint8_t noninstr[246];
    int k = 0;
    for (int v = 0; v < 256; v++)
        if (!IS_INSTR[v])
            noninstr[k++] = (uint8_t)v;
    if (soup_alloc(&s, NUM_PROGRAMS))
        return 1;
    xoshiro256 g = {{11, 22, 33, 44}};
    const size_t len = (size_t)s.n * TAPE_BYTES;
    if (!strncmp(kind, "inert-", 6)) {
        uint8_t templates[37][TAPE_BYTES];
        for (int i = 0; i < 37; i++)
            for (int j = 0; j < TAPE_BYTES; j++)
                templates[i][j] = noninstr[xo_below(&g, 246)];
        for (uint32_t p = 0; p < s.n; p++) {
            uint8_t *prog = s.bytes + (size_t)p * TAPE_BYTES;
            int structured = !strcmp(kind, "inert-structured") ||
                             (!strcmp(kind, "inert-mixed") && p % 2 == 0);
            for (int j = 0; j < TAPE_BYTES; j++)
                prog[j] = (structured && xo_below(&g, 100) != 0) ? templates[p % 37][j]
                                                                   : noninstr[xo_below(&g, 246)];
        }
    } else if (!strncmp(kind, "evolved-", 8)) {
        char lang_name[32];
        unsigned long long epochs;
        if (sscanf(kind + 8, "%31[a-z_]-%llu", lang_name, &epochs) != 2)
            return 2;
        uint8_t seed[32] = {0xEC, 0xD1};
        evolve(&s, seed, 0, epochs, parse_lang(lang_name));
    } else {
        fprintf(stderr, "unknown soup kind %s\n", kind);
        return 2;
    }
    (void)len;
    return soup_save(&s, path, 0) ? 1 : 0;
}

static int measure_file(const char *path)
{
    soup s;
    sample m;
    uint64_t epoch;
    if (soup_load(&s, path, &epoch) || soup_measure(&s, &m))
        return 1;
    printf("%llu,%llu,%u,%f\n", (unsigned long long)(epoch + 1), (unsigned long long)m.zsize, s.n,
           (double)m.hoe);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc >= 2 && !strcmp(argv[1], "unit")) {
        double t0 = now_seconds();
        test_sha256();
        test_xoshiro();
        test_masks();
        test_interpreter();
        test_interpreters_agree(argc >= 3 ? atol(argv[2]) : 500000);
        test_mutation();
        test_pairing();
        test_determinism();
        test_measure();
        fprintf(stderr, "%d checks, %d failures (%.1f s)\n", checks, failures, now_seconds() - t0);
        return failures ? 1 : 0;
    }
    if (argc >= 5 && !strcmp(argv[1], "cubff-log"))
        return cubff_log(parse_lang(argv[2]), strtoull(argv[3], NULL, 10), strtoull(argv[4], NULL, 10),
                         argc >= 6 ? argv[5] : NULL,
                         argc >= 7 ? (uint32_t)strtoul(argv[6], NULL, 10) : (1u << 18));
    if (argc == 2 && !strcmp(argv[1], "gen-tapes"))
        return gen_tapes();
    if (argc >= 3 && !strcmp(argv[1], "eval-tapes"))
        return eval_tapes(parse_lang(argv[2]), argc >= 4 ? (uint32_t)strtoul(argv[3], NULL, 10) : STEP_LIMIT,
                          argc >= 5 && !strcmp(argv[4], "ref"));
    if (argc == 4 && !strcmp(argv[1], "gen-soup"))
        return gen_soup(argv[2], argv[3]);
    if (argc == 3 && !strcmp(argv[1], "measure-file"))
        return measure_file(argv[2]);
    fprintf(stderr, "usage: %s unit [N] | cubff-log LANG SEED MAX_EPOCHS [SOUP [MUTATION_PROB]] | "
                    "gen-tapes | eval-tapes LANG [LIMIT] [ref] | gen-soup KIND FILE | measure-file FILE\n",
            argv[0]);
    return 2;
}
