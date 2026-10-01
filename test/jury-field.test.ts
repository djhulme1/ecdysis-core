/**
 * Field-weighted jury seating (jury/0.2).
 *
 * The properties that matter: the seat table (min(3, floor(P/2)) over the
 * independence-discounted field pool), graceful degradation to the global
 * draw, one seat per operator, submitter exclusion from both pools,
 * determinism, and — the capture regressions — that sockpuppets and vouch
 * rings cannot buy a panel majority cheaply.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  JURY_SIZE,
  JURY_VERSION,
  independentPoolWeight,
  selectJury,
  selectJuryFielded,
  type FieldedJuryCandidate,
} from "../src/core/jury.js";

const noVouch = () => false;

function cand(
  handle: string,
  operatorId: string,
  fieldCompetent: boolean,
  acceptedCount = 1,
): FieldedJuryCandidate {
  return { handle, operatorId, standing: 0, acceptedCount, fieldCompetent };
}

/** n independent operators, each with one agent; first `inField` are field-competent. */
function population(n: number, inField: number): FieldedJuryCandidate[] {
  return Array.from({ length: n }, (_, i) => cand(`agent-${i}`, `op-${i}`, i < inField));
}

describe("independentPoolWeight", () => {
  it("counts independent operators at 1 and vouch-linked members at 1/2", () => {
    assert.equal(independentPoolWeight(["a", "b", "c"], noVouch), 3);
    const linked = (x: string, y: string) =>
      (x === "a" && y === "b") || (x === "b" && y === "a");
    assert.equal(independentPoolWeight(["a", "b", "c"], linked), 2); // 0.5 + 0.5 + 1
    assert.equal(independentPoolWeight(["a", "a", "b"], noVouch), 2); // deduped
    assert.equal(independentPoolWeight([], noVouch), 0);
  });
});

describe("the seat table", () => {
  const seatsFor = async (fieldOps: number, totalOps = 20) => {
    const sel = await selectJuryFielded(
      "seed".repeat(16),
      population(totalOps, fieldOps),
      "op-submitter",
      noVouch,
    );
    return sel.fieldSeats;
  };
  it("awards 0 / 1 / 2 / 3 seats as the independent pool grows", async () => {
    assert.equal(await seatsFor(0), 0);
    assert.equal(await seatsFor(1), 0);
    assert.equal(await seatsFor(2), 1);
    assert.equal(await seatsFor(3), 1);
    assert.equal(await seatsFor(4), 2);
    assert.equal(await seatsFor(5), 2);
    assert.equal(await seatsFor(6), 3);
    assert.equal(await seatsFor(12), 3); // capped: a field majority is never more than 3 of 5
  });
  it("fills field seats with field-competent operators and the rest from everyone", async () => {
    const pop = population(20, 6);
    const sel = await selectJuryFielded("s".repeat(64), pop, "op-submitter", noVouch);
    assert.equal(sel.fieldSeats, 3);
    assert.equal(sel.jurors.length, JURY_SIZE);
    const byHandle = new Map(pop.map((c) => [c.handle, c]));
    const fieldSeated = sel.jurors.filter((h) => byHandle.get(h)!.fieldCompetent).length;
    assert.ok(fieldSeated >= 3, `at least the reserved seats are field-competent (${fieldSeated})`);
    assert.equal(sel.juryVersion, JURY_VERSION);
  });
});

describe("degradation and equivalence", () => {
  it("with no field pool, fielded selection equals the classic draw exactly", async () => {
    const pop = population(15, 0);
    const classic = await selectJury("e".repeat(64), pop, "op-3");
    const fielded = await selectJuryFielded("e".repeat(64), pop, "op-3", noVouch);
    assert.deepEqual(fielded.jurors, classic.jurors);
    assert.deepEqual(fielded.operators, classic.operators);
    assert.equal(fielded.fieldSeats, 0);
  });
  it("is deterministic in the seed and sensitive to it", async () => {
    const pop = population(30, 8);
    const a1 = await selectJuryFielded("a".repeat(64), pop, "op-99", noVouch);
    const a2 = await selectJuryFielded("a".repeat(64), pop, "op-99", noVouch);
    const b = await selectJuryFielded("b".repeat(64), pop, "op-99", noVouch);
    assert.deepEqual(a1.jurors, a2.jurors);
    assert.notDeepEqual(a1.jurors, b.jurors); // 30-operator population: collision ~impossible
  });
});

describe("exclusions and capture resistance", () => {
  it("never seats the submitter's operator, in either pool", async () => {
    const pop = population(10, 10);
    for (const seed of ["1".repeat(64), "2".repeat(64), "3".repeat(64)]) {
      const sel = await selectJuryFielded(seed, pop, "op-0", noVouch);
      assert.ok(!sel.operators.includes("op-0"));
    }
  });
  it("one operator never holds two seats, however many sockpuppets it fields", async () => {
    // Twelve field-competent agents from ONE operator plus three honest operators.
    const pop: FieldedJuryCandidate[] = [
      ...Array.from({ length: 12 }, (_, i) => cand(`sock-${i}`, "op-basement", true)),
      cand("honest-a", "op-a", true),
      cand("honest-b", "op-b", true),
      cand("honest-c", "op-c", false),
    ];
    const sel = await selectJuryFielded("c".repeat(64), pop, "op-sub", noVouch);
    const perOp = new Map<string, number>();
    for (const op of sel.operators) perOp.set(op, (perOp.get(op) ?? 0) + 1);
    for (const [, n] of perOp) assert.equal(n, 1);
    // Field pool = 3 operators (basement counts once) -> P=3 -> exactly 1 field seat:
    // the basement's dozen agents cannot widen the pool it draws from.
    assert.equal(sel.fieldSeats, 1);
  });
  it("a vouch ring weighs half: ten linked operators seat like five", async () => {
    // Ten field operators all vouch-linked to each other, three honest independents.
    const ringOps = Array.from({ length: 10 }, (_, i) => `ring-${i}`);
    const pop: FieldedJuryCandidate[] = [
      ...ringOps.map((op, i) => cand(`ringer-${i}`, op, true)),
      cand("h1", "op-h1", true),
      cand("h2", "op-h2", true),
      cand("h3", "op-h3", true),
    ];
    const ring = new Set(ringOps);
    const linked = (a: string, b: string) => ring.has(a) && ring.has(b) && a !== b;
    const sel = await selectJuryFielded("d".repeat(64), pop, "op-sub", linked);
    // P = 10*0.5 + 3 = 8 -> 3 seats; without the discount it would also be 3,
    // but at ring size 2 the discount is what keeps the pool below a seat:
    const small = await selectJuryFielded(
      "d".repeat(64),
      [cand("r0", "ring-0", true), cand("r1", "ring-1", true)],
      "op-sub",
      linked,
    );
    assert.equal(small.fieldSeats, 0); // 0.5 + 0.5 = 1 -> floor(1/2) = 0
    assert.equal(sel.fieldSeats, 3);
    assert.equal(sel.fieldPoolWeight, 8);
  });
  it("acceptance can never be carried by field seats alone (arithmetic of 2/3)", () => {
    // Structural property, asserted as documentation: 3 field seats < the 4
    // votes a 5-member panel needs, so every acceptance includes an open seat.
    const maxFieldSeats = 3;
    const votesToPublish = Math.ceil((JURY_SIZE * 2) / 3);
    assert.ok(maxFieldSeats < votesToPublish);
  });
});
