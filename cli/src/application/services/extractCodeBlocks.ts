const FENCED_BLOCK = /```[\w+-]*[^\S\n]*\n?([\s\S]*?)```/g;

/**
 * Returns the code inside the fenced blocks of a model reply, joined by a blank line.
 * The model wraps its code in prose ("Here's the refactored code...") and fences;
 * callers that write or diff the result need the code only.
 * Falls back to the trimmed reply when it holds no non-empty fenced block.
 */
export function extractCodeBlocks(reply: string): string {
  const blocks: string[] = [];
  for (const match of reply.matchAll(FENCED_BLOCK)) {
    const code = match[1]?.trim();
    if (code) {
      blocks.push(code);
    }
  }
  return blocks.length > 0 ? blocks.join('\n\n') : reply.trim();
}
