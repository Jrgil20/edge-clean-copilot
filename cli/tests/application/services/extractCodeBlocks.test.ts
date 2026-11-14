import { describe, it, expect } from 'vitest';
import { extractCodeBlocks } from '../../../src/application/services/extractCodeBlocks.js';

describe('extractCodeBlocks', () => {
  it('drops the prose around a single fenced block', () => {
    const reply =
      "Here's the refactored code following Clean Architecture principles:\n\n" +
      '```typescript\nexport class Order {}\n```\n\n' +
      'The code now follows the Dependency Rule.';
    expect(extractCodeBlocks(reply)).toBe('export class Order {}');
  });

  it('joins several fenced blocks with a blank line, in order', () => {
    const reply = 'Domain:\n```ts\nexport class A {}\n```\nPort:\n```\nexport interface B {}\n```';
    expect(extractCodeBlocks(reply)).toBe('export class A {}\n\nexport interface B {}');
  });

  it('does not leak the language tag of non-TypeScript fences into the code', () => {
    expect(extractCodeBlocks('```javascript\nconst a = 1;\n```')).toBe('const a = 1;');
  });

  it('returns the trimmed reply unchanged when it has no fence', () => {
    expect(extractCodeBlocks('  export class Plain {}\n')).toBe('export class Plain {}');
  });

  it('ignores empty fenced blocks and falls back to the reply', () => {
    expect(extractCodeBlocks('nothing here\n```ts\n\n```')).toBe('nothing here\n```ts\n\n```');
  });
});
