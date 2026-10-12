/* pi to N decimals by two independent methods, in GMP integers, for pi/bailey88.py.

   Usage: bailey88 chud|agm N outfile
   Writes floor(pi 10^N) in decimal ("3" followed by N digits) to outfile.

   chud: the Chudnovskys' series, pi = 426880 sqrt(10005) / sum_k (-1)^k (6k)! (13591409 + 545140134 k) /
         ((3k)! (k!)^3 640320^(3k)), summed exactly by binary splitting (P, Q, T as in the GMP project's example);
         about 14.18 digits a term. floor(pi 10^N) = floor(426880 Q isqrt(10005 10^(2N)) / T), up to the last digit or
         two, which the caller does not use.
   agm:  the Gauss-Legendre (Brent-Salamin) iteration in binary fixed point with K = ceil(N log2 10) + 256 bits:
         a = 1, b = 1/sqrt(2), t = 1/4, p = 1; repeatedly a' = (a + b)/2, b' = sqrt(a b), t' = t - p (a - a')^2,
         p' = 2p, until p (a - a')^2 is below one unit in the last place; then pi = (a + b)^2 / (4 t). Truncations lose a
         few units in the last place an iteration, far inside the 256 spare bits.

   The two share nothing but GMP's integer arithmetic and the final conversion to decimal. */

#include <gmp.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const unsigned long A = 13591409UL, B = 545140134UL;

/* C^3 / 24 with C = 640320 */
static void c3_over_24(mpz_t r) {
    mpz_set_ui(r, 640320UL);
    mpz_pow_ui(r, r, 3);
    mpz_divexact_ui(r, r, 24);
}

static mpz_t C3_24;

static void bs(unsigned long a, unsigned long b, mpz_t P, mpz_t Q, mpz_t T) {
    if (b - a == 1) {
        if (a == 0) {
            mpz_set_ui(P, 1);
            mpz_set_ui(Q, 1);
        } else {
            mpz_set_ui(P, 6 * a - 5);
            mpz_mul_ui(P, P, 2 * a - 1);
            mpz_mul_ui(P, P, 6 * a - 1);
            mpz_set_ui(Q, a);
            mpz_mul_ui(Q, Q, a);
            mpz_mul_ui(Q, Q, a);
            mpz_mul(Q, Q, C3_24);
        }
        mpz_set_ui(T, B);
        mpz_mul_ui(T, T, a);
        mpz_add_ui(T, T, A);
        mpz_mul(T, T, P);
        if (a & 1) mpz_neg(T, T);
        return;
    }
    unsigned long m = a + (b - a) / 2;
    mpz_t P2, Q2, T2;
    mpz_inits(P2, Q2, T2, NULL);
    bs(a, m, P, Q, T);
    bs(m, b, P2, Q2, T2);
    /* T = Q2 T + P T2; P = P P2; Q = Q Q2 */
    mpz_mul(T, T, Q2);
    mpz_mul(T2, T2, P);
    mpz_add(T, T, T2);
    mpz_mul(P, P, P2);
    mpz_mul(Q, Q, Q2);
    mpz_clears(P2, Q2, T2, NULL);
}

static void chud(mpz_t out, unsigned long n) {
    unsigned long terms = (unsigned long)(n / 14.181647462725477) + 2;
    mpz_t P, Q, T, s;
    mpz_inits(P, Q, T, s, NULL);
    mpz_init(C3_24);
    c3_over_24(C3_24);
    bs(0, terms, P, Q, T);
    mpz_ui_pow_ui(s, 10, 2 * n);
    mpz_mul_ui(s, s, 10005);
    mpz_sqrt(s, s);                        /* floor(sqrt(10005) 10^n) */
    mpz_mul(out, Q, s);
    mpz_mul_ui(out, out, 426880);
    mpz_tdiv_q(out, out, T);
    mpz_clears(P, Q, T, s, C3_24, NULL);
}

static void agm(mpz_t out, unsigned long n) {
    unsigned long K = (unsigned long)ceil(n * 3.3219280948873623) + 256;
    mpz_t one, a, b, t, an, d, x;
    mpz_inits(one, a, b, t, an, d, x, NULL);
    mpz_setbit(one, K);
    mpz_set(a, one);
    mpz_set_ui(b, 0);
    mpz_setbit(b, 2 * K - 1);
    mpz_sqrt(b, b);                        /* 2^K / sqrt(2) */
    mpz_set_ui(t, 0);
    mpz_setbit(t, K - 2);                  /* 1/4 */
    unsigned long j = 0;                   /* p = 2^j */
    for (;;) {
        mpz_add(an, a, b);
        mpz_fdiv_q_2exp(an, an, 1);
        mpz_mul(b, a, b);
        mpz_sqrt(b, b);
        mpz_sub(d, a, an);
        mpz_mul(x, d, d);
        mpz_fdiv_q_2exp(x, x, K);
        mpz_mul_2exp(x, x, j);
        mpz_sub(t, t, x);
        mpz_set(a, an);
        j++;
        if (mpz_sgn(x) == 0) break;
        if (j > 64) { fprintf(stderr, "agm: no convergence\n"); exit(2); }
    }
    mpz_add(x, a, b);
    mpz_mul(x, x, x);
    mpz_mul_2exp(t, t, 2);
    mpz_tdiv_q(x, x, t);                   /* pi 2^K */
    mpz_ui_pow_ui(d, 10, n);
    mpz_mul(x, x, d);
    mpz_fdiv_q_2exp(out, x, K);            /* floor(pi 10^n) */
    fprintf(stderr, "agm: %lu iterations\n", j);
    mpz_clears(one, a, b, t, an, d, x, NULL);
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: bailey88 chud|agm N outfile\n");
        return 1;
    }
    unsigned long n = strtoul(argv[2], NULL, 10);
    mpz_t r;
    mpz_init(r);
    if (strcmp(argv[1], "chud") == 0) chud(r, n);
    else if (strcmp(argv[1], "agm") == 0) agm(r, n);
    else { fprintf(stderr, "unknown method\n"); return 1; }
    FILE *f = fopen(argv[3], "w");
    if (!f) { perror("fopen"); return 1; }
    mpz_out_str(f, 10, r);
    fclose(f);
    mpz_clear(r);
    return 0;
}
