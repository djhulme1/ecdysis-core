# PyPhi c1a7f4e's small parts, for holding iit4/engine.py to them: the SET_UNI/BI system partitions' cut matrices in
# PyPhi's order (1 to 4 units, and the count for 5), the ALL mechanism partitions of mechanisms and purviews of one to
# three units in PyPhi's order with the connections each cuts, and block_reducible on seeded random cases. Run in the
# same sandbox as pyphi_ref.py (sandbox.sh with this script); writes /work/parts.json.
import json, warnings
warnings.simplefilter("ignore")
import numpy as np
import pyphi
from pyphi import connectivity, partition
assert pyphi.config.IIT_VERSION == 4

out = {"cut_matrices": {}, "cut_count_5": None, "partitions": {}, "block_reducible": []}
for k in range(1, 5):
    out["cut_matrices"][str(k)] = [np.asarray(p.cut_matrix(k), dtype=int).tolist()
                                   for p in partition.system_partitions(tuple(range(k)))]
out["cut_count_5"] = sum(1 for _ in partition.system_partitions(tuple(range(5))))
for m in range(1, 4):
    for p in range(1, 4):
        mechanism = tuple(range(m))
        purview = tuple(range(10, 10 + p))
        rows = []
        for part in partition.all_partitions(mechanism, purview):
            rows.append([[list(x.mechanism), list(x.purview)] for x in part.parts] + [part.num_connections_cut()])
        out["partitions"][f"{m},{p}"] = rows
rng = np.random.default_rng(7)
for _ in range(60):
    n = int(rng.integers(2, 6))
    cm = (rng.random((n, n)) < 0.4).astype(int)
    a = tuple(sorted(set(int(x) for x in rng.choice(n, int(rng.integers(1, n + 1)), replace=False))))
    b = tuple(sorted(set(int(x) for x in rng.choice(n, int(rng.integers(1, n + 1)), replace=False))))
    out["block_reducible"].append({"cm": cm.tolist(), "a": list(a), "b": list(b),
                                   "reducible": bool(connectivity.block_reducible(cm, a, b))})
json.dump(out, open("/work/parts.json", "w"))
print("parts", {k: len(v) for k, v in out["cut_matrices"].items()}, out["cut_count_5"],
      {k: len(v) for k, v in out["partitions"].items()}, sum(r["reducible"] for r in out["block_reducible"]))
