// Types for the reference runner's input stage (inputs.mjs), so the tests can import it under strict TypeScript.
export interface RunnerInput { name: string; url: string; sha256: string; bytes: number; access: "open" | "registered" | "restricted"; licence?: string }
export interface PrepareOptions {
  cacheDir?: string;
  supplied?: Map<string, string>;
  totalCap?: number;
  allowInsecure?: boolean;
  fetchImpl?: typeof fetch;
  lookup?: (host: string) => Promise<string[]>;
  timeoutMs?: number;
  log?: (line: string) => void;
}
export const MAX_INPUTS: number;
export const ACCESS: readonly string[];
export const DEFAULT_TOTAL_CAP: number;
export const MAX_REDIRECTS: number;
export const USER_AGENT: string;
export function inputProblems(inputs: unknown, allowInsecure?: boolean): string[];
export function isPublicAddress(addr: string): boolean;
export function urlProblem(url: string, addresses: string[], origin?: string | null, allowInsecure?: boolean): string | null;
export function hashFile(path: string): Promise<{ sha256: string; bytes: number }>;
export function fileProblem(path: string, input: RunnerInput): Promise<string | null>;
export function fetchInput(input: RunnerInput, dest: string, o?: PrepareOptions): Promise<string | null>;
export function prepareInputs(inputs: RunnerInput[] | undefined, o?: PrepareOptions): Promise<{ paths: Map<string, string>; problems?: undefined } | { problems: string[]; paths?: undefined }>;
export function parseSupplied(argv: string[]): Map<string, string>;
