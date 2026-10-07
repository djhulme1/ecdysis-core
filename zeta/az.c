/* zeta(3) in hexadecimal by the Amdeberhan-Zeilberger series, independently of Broadhurst's BBP-type formula.

   zeta(3) = (1/64) sum_{k>=0} (-1)^k (k!)^10 (205k^2 + 250k + 77) / ((2k+1)!)^5

   (T. Amdeberhan and D. Zeilberger, "Hypergeometric series acceleration via the WZ method", Electron. J. Combin. 4(2)
   (1997) #R3; the paper under test names this comparison as the interesting one.) Successive terms have ratio
   -k^5 / (32 (2k+1)^5), so each term gains about 10 bits; the sum is formed exactly by binary splitting in GMP integers.

   Usage: az E place [place ...]
   Prints, for each place d (1 <= d, d + 63 + 16 <= E), the 64 hexadecimal digits of zeta(3) that begin at the d-th
   hexadecimal place after the point, then the 16 hexadecimal digits that follow them (guard digits), separated by a
   space, one place per line. floor(zeta(3) 16^E) is computed with the series truncated after N terms, N chosen so that
   the omitted tail is below 16^-(E+16); the caller checks that the guard digits are neither all 0 nor all F, so that the
   truncation cannot have changed the 64 digits reported. */

#include <gmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { mpz_t p, q, t; } triple;

static void leaf(triple *r, unsigned long k) {
    mpz_init(r->p); mpz_init(r->q); mpz_init(r->t);
    if (k == 0) {
        mpz_set_ui(r->p, 1);
        mpz_set_ui(r->q, 1);
        mpz_set_ui(r->t, 77);
        return;
    }
    mpz_t a;
    mpz_init(a);
    mpz_ui_pow_ui(r->p, k, 5);
    mpz_neg(r->p, r->p);                              /* p(k) = -k^5 */
    mpz_ui_pow_ui(r->q, 2 * k + 1, 5);
    mpz_mul_ui(r->q, r->q, 32);                       /* q(k) = 32 (2k+1)^5 */
    mpz_set_ui(a, 205);
    mpz_mul_ui(a, a, k);
    mpz_add_ui(a, a, 250);
    mpz_mul_ui(a, a, k);
    mpz_add_ui(a, a, 77);                             /* a(k) = 205k^2 + 250k + 77 */
    mpz_mul(r->t, a, r->p);                           /* t = a(k) p(k) */
    mpz_clear(a);
}

/* [a, b): P = prod p, Q = prod q, T = sum_k a(k) (prod_{j<=k} p(j)) (prod_{j>k} q(j)) */
static void split(triple *r, unsigned long a, unsigned long b) {
    if (b - a == 1) {
        leaf(r, a);
        return;
    }
    unsigned long m = a + (b - a) / 2;
    triple left, right;
    split(&left, a, m);
    split(&right, m, b);
    mpz_init(r->p); mpz_init(r->q); mpz_init(r->t);
    mpz_mul(r->t, left.t, right.q);
    mpz_addmul(r->t, left.p, right.t);
    mpz_mul(r->p, left.p, right.p);
    mpz_mul(r->q, left.q, right.q);
    mpz_clear(left.p); mpz_clear(left.q); mpz_clear(left.t);
    mpz_clear(right.p); mpz_clear(right.q); mpz_clear(right.t);
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: az E place [place ...]\n");
        return 2;
    }
    unsigned long E = strtoul(argv[1], NULL, 10);
    for (int i = 2; i < argc; i++) {
        unsigned long d = strtoul(argv[i], NULL, 10);
        if (d < 1 || d + 63 + 16 > E) {
            fprintf(stderr, "place %lu does not fit E = %lu\n", d, E);
            return 2;
        }
    }
    /* Each term gains log2(32 * (2k+1)^5 / k^5) > 10 bits; N terms leave a tail below 2^-(10N - 7). */
    unsigned long bits = 4 * E + 64;
    unsigned long N = bits / 10 + 16;
    triple s;
    split(&s, 0, N);
    mpz_t z;
    mpz_init(z);
    mpz_mul_2exp(z, s.t, 4 * E);                      /* floor(T 16^E / (64 Q)) */
    mpz_mul_ui(s.q, s.q, 64);
    mpz_fdiv_q(z, z, s.q);
    char *hex = mpz_get_str(NULL, 16, z);             /* integer part "1", then E fractional hex digits */
    size_t len = strlen(hex);
    if (len != E + 1 || hex[0] != '1') {
        fprintf(stderr, "unexpected length %zu (E = %lu) or integer part %c\n", len, E, hex[0]);
        return 3;
    }
    for (int i = 2; i < argc; i++) {
        unsigned long d = strtoul(argv[i], NULL, 10);
        printf("%.64s %.16s\n", hex + d, hex + d + 64);
    }
    return 0;
}
