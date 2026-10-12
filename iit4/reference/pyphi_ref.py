# Reference runs of PyPhi c1a7f4e under the authors' configuration, inside a sandbox with no network: PyPhi is never run
# anywhere else. Input: /work/jobs.json = [{"name", "tpm" (state-by-node rows, little-endian), "cm" (or null), "labels",
# "states": [...], "nodes": null (condense over all subsets) or [indices] (one candidate)}], with the authors'
# pyphi_config.yml beside it. Output: /work/ref_out.json. Run, with PyPhi at c1a7f4e, graphiit at 1318d8b and the wheels
# sandbox.sh names in local directories:
#   docker run --rm --network none -v WHEELS:/wheels:ro -v PYPHI:/src/pyphi:ro -v GRAPHIIT:/src/graphiit:ro \
#     -v iit4/reference:/scripts:ro -v WORK:/work python@sha256:ddb0207a... sh /scripts/sandbox.sh
import json, time, warnings
warnings.simplefilter("ignore")
import numpy as np
import pyphi
import pyphi.new_big_phi as nbp
assert pyphi.config.IIT_VERSION == 4, pyphi.config.IIT_VERSION

def condensed(network, state):
    result, covered = [], set()
    for c in reversed(sorted(nbp.irreducible_complexes(network, state))):
        if not any(n in covered for n in c.node_indices):
            result.append(c)
            covered |= set(c.node_indices)
    return result

def describe(sub, sia):
    ps = nbp.phi_structure(sub, sia)
    ds = []
    for d in ps.distinctions:
        ds.append({"mechanism": list(d.mechanism), "phi": float(d.phi),
                   "cause": [list(d.cause.purview), list(d.cause.specified_state.state), float(d.cause.phi)],
                   "effect": [list(d.effect.purview), list(d.effect.specified_state.state), float(d.effect.phi)]})
    return {"nodes": list(sia.node_indices), "phi_s": float(sia.phi), "big_phi": float(ps.big_phi),
            "distinctions": ds, "relations": len(ps.relations),
            "cause_state": list(sia.system_state.cause.state), "effect_state": list(sia.system_state.effect.state)}

jobs = json.load(open("/work/jobs.json"))
out = []
for job in jobs:
    t = time.time()
    cm = None if job.get("cm") is None else np.array(job["cm"])
    net = pyphi.Network(np.array(job["tpm"], dtype=float), cm=cm, node_labels=job["labels"])
    for st in job["states"]:
        st = tuple(st)
        rec = {"name": job["name"], "state": list(st)}
        try:
            if job.get("nodes") is None:
                rec["complexes"] = [describe(pyphi.Subsystem(net, st, c.node_indices), c) for c in condensed(net, st)]
            else:
                sub = pyphi.Subsystem(net, st, tuple(job["nodes"]))
                sia = nbp.sia(sub)
                rec["candidate"] = describe(sub, sia) if sia.phi > 0 else {"phi_s": float(sia.phi)}
        except pyphi.exceptions.StateUnreachableError:
            rec["unreachable"] = True
        rec["secs"] = round(time.time() - t, 2)
        out.append(rec)
        summary = [("".join(job["labels"][i] for i in c["nodes"]), round(c["phi_s"], 4), round(c["big_phi"], 4),
                    len(c["distinctions"]), c["relations"]) for c in rec.get("complexes", [])]
        print(job["name"], st, summary, rec["secs"], flush=True)
        json.dump(out, open("/work/ref_out.json", "w"))
print("done", len(out))
