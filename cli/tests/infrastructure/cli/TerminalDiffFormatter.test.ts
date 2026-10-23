import { describe, it, expect } from 'vitest';
import { TerminalDiffFormatter } from '../../../src/infrastructure/cli/TerminalDiffFormatter.js';

describe('TerminalDiffFormatter', () => {
  const formatter = new TerminalDiffFormatter();

  it('should detect when there are zero changes between files', () => {
    const original = 'const a = 1;\nconst b = 2;';
    const refactored = 'const a = 1;\nconst b = 2;';

    const result = formatter.format(original, refactored, 'test.ts');
    expect(result.hasChanges).toBe(false);
    expect(result.addedCount).toBe(0);
    expect(result.removedCount).toBe(0);
    expect(result.formattedTerminalOutput).toContain('No architectural changes needed');
  });

  it('should format line additions with green prefix (+)', () => {
    const original = 'const a = 1;';
    const refactored = 'const a = 1;\nconst b = 2;';

    const result = formatter.format(original, refactored, 'test.ts');
    expect(result.hasChanges).toBe(true);
    expect(result.addedCount).toBe(1);
    expect(result.removedCount).toBe(0);
    expect(result.lines).toEqual([
      { type: 'unchanged', content: 'const a = 1;' },
      { type: 'added', content: 'const b = 2;' }
    ]);
    expect(result.formattedTerminalOutput).toContain('+ const b = 2;');
  });

  it('should format line removals with red prefix (-)', () => {
    const original = 'import express from "express";\nexport class Service {}';
    const refactored = 'export class Service {}';

    const result = formatter.format(original, refactored, 'test.ts');
    expect(result.hasChanges).toBe(true);
    expect(result.addedCount).toBe(0);
    expect(result.removedCount).toBe(1);
    expect(result.lines).toEqual([
      { type: 'removed', content: 'import express from "express";' },
      { type: 'unchanged', content: 'export class Service {}' }
    ]);
    expect(result.formattedTerminalOutput).toContain('- import express from "express";');
  });

  it('should handle modifications as removal + addition and render header', () => {
    const original = 'const value: any = 42;';
    const refactored = 'const value: number = 42;';

    const result = formatter.format(original, refactored, 'test.ts');
    expect(result.hasChanges).toBe(true);
    expect(result.addedCount).toBe(1);
    expect(result.removedCount).toBe(1);
    expect(result.formattedTerminalOutput).toContain('--- test.ts (original)');
    expect(result.formattedTerminalOutput).toContain('+++ test.ts (clean-refactored)');
    expect(result.formattedTerminalOutput).toContain('- const value: any = 42;');
    expect(result.formattedTerminalOutput).toContain('+ const value: number = 42;');
  });
});
