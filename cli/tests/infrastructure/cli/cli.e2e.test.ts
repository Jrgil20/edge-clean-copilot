import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import * as path from 'node:path';

const CLI_ROOT = path.resolve(__dirname, '../../..');
const TSX = path.join(CLI_ROOT, 'node_modules', '.bin', 'tsx');
const ENTRY = path.join(CLI_ROOT, 'src', 'infrastructure', 'cli', 'index.ts');

let scratch: string;
let input: string;

function run(args: string[], env: NodeJS.ProcessEnv = {}) {
  const clean = { ...process.env };
  delete clean.CLEAN_COPILOT_TIMEOUT_MS;
  const res = spawnSync(TSX, [ENTRY, ...args], {
    cwd: CLI_ROOT,
    env: { ...clean, ...env },
    encoding: 'utf-8',
    timeout: 30_000
  });
  return { code: res.status, stdout: res.stdout, stderr: res.stderr };
}

beforeAll(() => {
  scratch = mkdtempSync(path.join(tmpdir(), 'ecc-cli-e2e-'));
  input = path.join(scratch, 'legacy.ts');
  writeFileSync(input, 'export class Order { total = 0; }\n');
});

afterAll(() => {
  rmSync(scratch, { recursive: true, force: true });
});

describe('clean-copilot refactor (end to end, mock engine)', () => {
  it('prints only the refactored code on stdout and the banner on stderr', () => {
    const { code, stdout, stderr } = run(['refactor', input, '--mock']);
    expect(code).toBe(0);
    expect(stdout.startsWith('// [Edge Clean Copilot - Mock Engine Output]')).toBe(true);
    expect(stdout).not.toContain('Edge Clean Copilot — Clean Architecture Refactoring');
    expect(stdout).not.toContain('[Status]');
    expect(stderr).toContain('Edge Clean Copilot — Clean Architecture Refactoring');
    expect(stderr).toContain('[Status] Success');
  });

  it('writes the refactored code to --output', () => {
    const out = path.join(scratch, 'out.ts');
    const { code, stderr } = run(['refactor', input, '--mock', '-o', out]);
    expect(code).toBe(0);
    expect(readFileSync(out, 'utf-8').startsWith('// [Edge Clean Copilot - Mock Engine Output]')).toBe(true);
    expect(stderr).toContain('[Saved File]');
  });

  it('reports the default 300000 ms timeout', () => {
    const { code, stderr } = run(['refactor', input, '--mock']);
    expect(code).toBe(0);
    expect(stderr).toContain('[Timeout]      : 300000 ms');
  });

  it('takes the timeout from CLEAN_COPILOT_TIMEOUT_MS, and --timeout overrides it', () => {
    expect(run(['refactor', input, '--mock'], { CLEAN_COPILOT_TIMEOUT_MS: '120000' }).stderr).toContain(
      '[Timeout]      : 120000 ms'
    );
    expect(
      run(['refactor', input, '--mock', '--timeout', '9000'], { CLEAN_COPILOT_TIMEOUT_MS: '120000' }).stderr
    ).toContain('[Timeout]      : 9000 ms');
  });

  it('rejects a non-positive or non-integer --timeout with exit code 1', () => {
    for (const bad of ['0', '-5', 'abc', '1.5']) {
      const { code, stdout, stderr } = run(['refactor', input, '--mock', '--timeout', bad]);
      expect(code).toBe(1);
      expect(stdout).toBe('');
      expect(stderr).toContain('--timeout must be a positive integer (milliseconds).');
    }
  });

  it('still rejects an out-of-range --temperature with exit code 1', () => {
    const { code, stderr } = run(['refactor', input, '--mock', '--temperature', '5']);
    expect(code).toBe(1);
    expect(stderr).toContain('--temperature must be a number between 0 and 2.');
  });

  it('still refuses to overwrite the input file', () => {
    const { code, stderr } = run(['refactor', input, '--mock', '-o', input]);
    expect(code).toBe(1);
    expect(stderr).toContain('refusing to overwrite the original');
    expect(readFileSync(input, 'utf-8')).toBe('export class Order { total = 0; }\n');
  });

  it('exits 1 when the input file does not exist', () => {
    const { code, stderr } = run(['refactor', path.join(scratch, 'missing.ts'), '--mock']);
    expect(code).toBe(1);
    expect(stderr).toContain('[ERROR]');
  });
});
