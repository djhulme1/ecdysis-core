#!/bin/sh
# Cross-checks against cubff, in the pinned image with --network none, after
# xcheck/build_cubff.sh has built xcheck/bin/:
#  1. the interpreter: 400k tapes through cubff's own Bff::Evaluate, this
#     program's fast interpreter and its reference interpreter, both
#     variants, step limits 8192, 1000 and 100; outputs must be identical;
#  2. the measure: soups with no instruction bytes (so a cubff epoch leaves
#     them unchanged) measured by cubff's main (--load, --mutation_prob 0)
#     and by this program; log lines must be identical;
#  3. end to end from evolved soups: compare_runs.sh with --load.
set -eu
T=/tmp/xc
rm -rf $T && mkdir -p $T
gcc -O2 -pthread /work/test_bff_soup.c -lbrotlienc -lm -o $T/t 2>/dev/null
$T/t gen-tapes >$T/tapes.bin
echo "1. interpreter: $(($(stat -c %s $T/tapes.bin) / 128)) tapes"
for L in bff bff_noheads; do
  for LIM in 8192 1000 100; do
    $T/t eval-tapes $L $LIM <$T/tapes.bin >$T/fast.out
    $T/t eval-tapes $L $LIM ref <$T/tapes.bin >$T/ref.out
    /work/xcheck/bin/cubff_eval_$L $LIM <$T/tapes.bin >$T/cubff.out
    if cmp -s $T/fast.out $T/cubff.out && cmp -s $T/ref.out $T/cubff.out; then
      echo "   $L limit $LIM: identical final tapes and op counts (fast, reference, cubff)"
    else
      echo "   $L limit $LIM: DIFFERENT"; exit 1
    fi
  done
done
echo "2. measure on inert soups"
for K in inert-random inert-structured inert-mixed; do
  $T/t gen-soup $K $T/$K.dat
  /work/xcheck/bin/cubff_main --lang bff --load $T/$K.dat --mutation_prob 0 --max_epochs 0 \
    --disable_output --log $T/$K.cubff.log >/dev/null
  ours=$($T/t measure-file $T/$K.dat)
  theirs=$(tail -1 $T/$K.cubff.log)
  [ "$ours" = "$theirs" ] && echo "   $K: identical ($ours)" || { echo "   $K: DIFFERENT ours=$ours cubff=$theirs"; exit 1; }
done
echo "3. end to end from evolved soups"
for S in ${EVOLVED:-evolved-bff-2000 evolved-bff_noheads-2000}; do
  L=$(echo $S | sed 's/^evolved-//; s/-[0-9]*$//')
  $T/t gen-soup $S $T/$S.dat
  sh /work/xcheck/compare_runs.sh $L 777 192 $T/$S.dat | sed 's/^/   /'
done
