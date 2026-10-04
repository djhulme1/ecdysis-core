/**
 * The form fields that declare what a claim from human literature covers
 * (scope/0.1): its scope (the paper's, not the registrant's) and the test's
 * fidelity to the paper's reported method. Shared by the person's and the
 * steward's forms; the handlers read them with scopeFromForm and
 * fidelityFromForm (core/v2/kinds.ts), and the service checks them as it
 * checks an agent's signed registration.
 */

import { esc } from "../design.js";

/** The scope and fidelity fields, as one fieldset. `optional`: the claim may be conceptual, which declares neither. */
export function scopeFields(id: string, optional = true): string {
  const i = esc(id);
  const none = optional ? `<option value="">none: a conceptual claim</option>` : `<option value="">choose</option>`;
  return `<fieldset><legend>${optional ? "For an empirical claim: what" : "What"} the paper covers</legend>
<p class="small">The paper's scope, not yours. Only data covering its population and period can confirm or refute the claim; a test on other data, or with a changed method, is a robustness test, shown beside it and never counted for or against it.</p>
<label for="${i}-scope">Scope</label> <select id="${i}-scope" name="scope">${none}<option value="period">a period: the span of the paper's data</option><option value="construction">general by construction: a theorem, a simulation's ensemble, a named benchmark or model</option><option value="asserted">general, asserted: the quote itself asserts the finding beyond the paper's data</option></select>
<label for="${i}-from">From (for a period)</label> <input type="month" id="${i}-from" name="scope_from" placeholder="YYYY-MM">
<label for="${i}-to">To (for a period)</label> <input type="month" id="${i}-to" name="scope_to" placeholder="YYYY-MM">
<label for="${i}-basis">Basis: the paper's words that state its data's period; or what defines the object; or, for asserted, the exact words of the quote that assert it</label> <textarea id="${i}-basis" name="scope_basis" rows="2" maxlength="400"></textarea>
<label for="${i}-fidelity">Does the test state the paper's method?</label> <select id="${i}-fidelity" name="fidelity">${optional ? `<option value="">none: a conceptual claim</option>` : `<option value="">choose</option>`}<option value="reported">reported: the test states the method the paper reports</option><option value="adapted">adapted: another data source, other sample rules, another statistic or other thresholds</option></select>
<label for="${i}-fidelity-basis">How the test follows the paper, or what it changes</label> <textarea id="${i}-fidelity-basis" name="fidelity_basis" rows="2" maxlength="400"></textarea>
</fieldset>`;
}

/** The fields' values, as the handlers pass them on (core/v2/kinds.ts reads them). */
export function scopeFormValues(get: (name: string) => string | null): { scope: { scope: string; from: string; to: string; basis: string }; fidelity: { as: string; basis: string } } {
  return {
    scope: { scope: get("scope") ?? "", from: get("scope_from") ?? "", to: get("scope_to") ?? "", basis: get("scope_basis") ?? "" },
    fidelity: { as: get("fidelity") ?? "", basis: get("fidelity_basis") ?? "" },
  };
}
