// Cross-check harness: runs cubff's own interpreter, Bff::Evaluate from
// bff.inc.h as compiled from the cubff checkout (CUBFF_VARIANT is "bff.cu" or
// "bff_noheads.cu"), on 128-byte tapes read from stdin, and writes each final
// tape followed by the op count (u32, little-endian) to stdout: the format of
// `test_bff_soup eval-tapes`. Optional argv[1]: the step limit (default 8192,
// as MutateAndRunPrograms uses, common_language.h:184).
#include CUBFF_VARIANT

#include <cstdio>
#include <cstdlib>

int main(int argc, char **argv) {
  size_t limit = argc > 1 ? strtoul(argv[1], nullptr, 10) : 8 * 1024;
  uint8_t tape[2 * kSingleTapeSize];
  while (fread(tape, sizeof tape, 1, stdin) == 1) {
    uint32_t ops = (uint32_t)Bff::Evaluate(tape, limit, false);
    uint8_t le[4] = {(uint8_t)ops, (uint8_t)(ops >> 8), (uint8_t)(ops >> 16),
                     (uint8_t)(ops >> 24)};
    if (fwrite(tape, sizeof tape, 1, stdout) != 1 ||
        fwrite(le, 4, 1, stdout) != 1)
      return 1;
  }
  return 0;
}
