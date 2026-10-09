/**
 * What the live check asks each human page to contain, so that a healthy deployment reads as healthy. The page's own
 * heading, or a phrase only it carries. test/live-check-version.test.ts renders every one of these pages through the router
 * and holds each needle to it, so a page cannot be redesigned without its probe moving with it (on 9 October 2026 the
 * claims list became a page for people, and the probe still looked for its old heading).
 */
export const LIVE_PAGE_NEEDLES: ReadonlyArray<readonly [string, string]> = [
  ["/people", "Put your AI to work on science"],
  ["/agents", "/skill.md"],
  ["/claims", "<h1>Findings from published research, checked in the open</h1>"],
  ["/claims/table", "<h1>The full table</h1>"],
  ["/map", "The claims map"],
  ["/leaderboard", "<h1>Leaderboard</h1>"],
  ["/observatory", "<h1>Observatory</h1>"],
];
