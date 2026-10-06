#!/bin/sh
# Builds the authors' cubff (CPU build) inside the pinned image, from a copy of
# the read-only checkout mounted at /src, and keeps the binary and the
# interpreter harnesses in /work/xcheck/bin. Run with --network none:
#   docker run --rm --network none -v "$PWD":/work -v /path/to/cubff:/src:ro \
#     -w /work buildpack-deps:bookworm@sha256:88c9... sh xcheck/build_cubff.sh
set -eu
mkdir -p /work/xcheck/bin
rm -rf /tmp/cubff
cp -r /src /tmp/cubff
cd /tmp/cubff
git -C /tmp/cubff rev-parse HEAD 2>/dev/null || true
make CUDA=0 -j2 >/tmp/make.log 2>&1 || { tail -50 /tmp/make.log; exit 1; }
cp bin/main /work/xcheck/bin/cubff_main
# The interpreter harness: cubff's own Bff::Evaluate, one binary per variant.
for v in bff bff_noheads; do
  g++ -std=c++17 -O2 -fopenmp -I/tmp/cubff -DCUBFF_VARIANT="\"$v.cu\"" \
    /work/xcheck/cubff_eval.cc /tmp/cubff/common.cc \
    $(pkg-config --cflags --libs libbrotlienc libbrotlicommon) \
    -o /work/xcheck/bin/cubff_eval_$v
done
ls -la /work/xcheck/bin
