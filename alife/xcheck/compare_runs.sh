#!/bin/sh
# End-to-end comparison with cubff, in the pinned image with --network none:
# cubff's own binary and this repository's epoch code driven by cubff's
# generator (test_bff_soup cubff-log) run the same seed; their logs and the
# SHA-256 of the soup after each logged epoch must be identical.
#   sh xcheck/compare_runs.sh LANG SEED MAX_EPOCHS [SOUP_FILE [MUTATION_PROB_FLOAT MUTATION_PROB_INT]]
set -eu
LANG_=$1 SEED=$2 MAX=$3 SOUP=${4:-} MPF=${5:-} MPI=${6:-}
W=/tmp/cmp_${LANG_}_${SEED}
rm -rf "$W" && mkdir -p "$W/ck"
gcc -O2 -pthread /work/test_bff_soup.c -lbrotlienc -lm -o "$W/t" 2>/dev/null
set -- --lang "$LANG_" --seed "$SEED" --max_epochs "$MAX" --disable_output \
  --log "$W/cubff.log" --checkpoint_dir "$W/ck" --save_interval 64
[ -n "$SOUP" ] && set -- "$@" --load "$SOUP"
[ -n "$MPF" ] && set -- "$@" --mutation_prob "$MPF"
OMP_NUM_THREADS=2 /work/xcheck/bin/cubff_main "$@" >/dev/null
for f in "$W"/ck/*.dat; do
  e=$(basename "$f" .dat | sed 's/^0*//')
  echo "soup after epoch $(( ${e:-0} + 1 )): sha256 $(tail -c +25 "$f" | sha256sum | cut -d' ' -f1)"
done >"$W/cubff.hashes"
if [ -n "$SOUP" ]; then
  BFF_SOUP_HASHES=1 "$W/t" cubff-log "$LANG_" "$SEED" "$MAX" "$SOUP" "${MPI:-262144}" >"$W/ours.log" 2>"$W/ours.err"
else
  BFF_SOUP_HASHES=1 "$W/t" cubff-log "$LANG_" "$SEED" "$MAX" >"$W/ours.log" 2>"$W/ours.err"
fi
grep '^soup after' "$W/ours.err" >"$W/ours.hashes" || true
echo "== cubff log (built here)"; cat "$W/cubff.log"
if cmp -s "$W/cubff.log" "$W/ours.log" && cmp -s "$W/cubff.hashes" "$W/ours.hashes"; then
  echo "IDENTICAL: logs and $(wc -l <"$W/ours.hashes") soup hashes match ($LANG_, seed $SEED)"
else
  echo "DIFFERENT"; diff "$W/cubff.log" "$W/ours.log" || true; diff "$W/cubff.hashes" "$W/ours.hashes" || true
  exit 1
fi
