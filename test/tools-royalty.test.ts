/**
 * standing/0.3 — the virtuous circle. Arc one: a reviewed build pays the
 * papers whose claims it depends on. Arc two: an accepted paper citing a
 * build's cid as method pays the toolwright. Same-operator pairs pay
 * nothing, so the reward only flows when the commons is shared.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { computeStanding, type OperatorRegistry } from "../src/core/scoring.js";
import type { Json } from "../src/core/canonical.js";

const reg: OperatorRegistry = {
  operatorOf: (h) => (h.startsWith("Sib") ? "op-shared" : `op-${h}`),
  vouchLinked: () => false,
};

let seq = 0;
const accept = (handle: string, id: string, builds_on: Array<{ id: string; rel: string }>) => ({
  seq: seq++, type: "paper.accept" as const,
  payload: { id, handle: id.replace("cid:", "26xx."), agent: { handle }, builds_on, field: "ml" } as unknown as Json,
});
const register = (handle: string, cid: string, depends_on: string[]) => ({
  seq: seq++, type: "build.register" as const,
  payload: { cid, slug: "s-" + seq, agent: { handle }, depends_on } as unknown as Json,
});

describe("the virtuous circle (standing/0.3)", () => {
  it("a reviewed build pays the papers it depends on — once per pair, never your own", () => {
    seq = 0;
    const rows = computeStanding(
      [
        accept("Author-1", "ecd:cid:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", []),
        // Toolwright's build cites THREE claims of the same paper: pays once.
        register("Wright-1", "ecd:cid:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", [
          "ecd:cid:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa#C1",
          "ecd:cid:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa#C2",
          "ecd:cid:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa#C3",
        ]),
        // The author's OWN app citing their own paper pays nothing.
        register("Author-1", "ecd:cid:cccccccccccccccccccccccccccccccc", [
          "ecd:cid:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa#C1",
        ]),
      ],
      reg,
    );
    assert.equal(rows.get("Author-1")!.score, 2000 + 2000, "accept + ONE buildCites despite three dep claims");
    assert.equal(rows.get("Wright-1")?.score ?? 0, 0, "registering a build earns the wright nothing by itself");
  });

  it("a paper citing a build's cid as method pays the toolwright — never for self-use", () => {
    seq = 0;
    const rows = computeStanding(
      [
        accept("Author-1", "ecd:cid:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", []),
        register("Wright-1", "ecd:cid:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", [
          "ecd:cid:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa#C1",
        ]),
        // A NEW researcher uses the tool and cites it as method:
        accept("User-1", "ecd:cid:dddddddddddddddddddddddddddddddd", [
          { id: "ecd:cid:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", rel: "method" },
          { id: "ecd:cid:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", rel: "method" }, // duplicate: pays once
        ]),
        // The wright using their OWN tool earns nothing extra:
        accept("Wright-1", "ecd:cid:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", [
          { id: "ecd:cid:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", rel: "method" },
        ]),
      ],
      reg,
    );
    assert.equal(rows.get("Wright-1")!.score, 2000 + 2000, "own paper accept + ONE toolUsed royalty");
    assert.equal(rows.get("User-1")!.score, 2000, "using a tool costs nothing and pays its wright");
  });

  it("same-operator tool use pays nothing — the commons must actually be shared", () => {
    seq = 0;
    const rows = computeStanding(
      [
        register("Sib-Wright", "ecd:cid:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", []),
        accept("Sib-User", "ecd:cid:ffffffffffffffffffffffffffffffff", [
          { id: "ecd:cid:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", rel: "method" },
        ]),
      ],
      reg,
    );
    assert.equal(rows.get("Sib-Wright")?.score ?? 0, 0, "same operator: zero royalty");
  });
});
