export interface DiffLine {
  readonly type: 'added' | 'removed' | 'unchanged';
  readonly content: string;
}

export interface DiffResult {
  readonly hasChanges: boolean;
  readonly addedCount: number;
  readonly removedCount: number;
  readonly lines: readonly DiffLine[];
  readonly formattedTerminalOutput: string;
}

export class TerminalDiffFormatter {
  // ANSI terminal color codes
  private static readonly RESET = '\x1b[0m';
  private static readonly RED = '\x1b[31m';
  private static readonly GREEN = '\x1b[32m';
  private static readonly CYAN = '\x1b[36m';
  private static readonly DIM = '\x1b[90m';
  private static readonly BOLD = '\x1b[1m';

  /**
   * Compares original text with refactored text and computes a line-by-line unified diff.
   */
  public format(originalText: string, refactoredText: string, fileName = 'source'): DiffResult {
    const origLines = originalText.split('\n');
    const refLines = refactoredText.split('\n');

    if (originalText === refactoredText) {
      return {
        hasChanges: false,
        addedCount: 0,
        removedCount: 0,
        lines: origLines.map((content) => ({ type: 'unchanged', content })),
        formattedTerminalOutput: `${TerminalDiffFormatter.DIM}No architectural changes needed (code already compliant).${TerminalDiffFormatter.RESET}`
      };
    }

    const diffLines = this.computeLcsDiff(origLines, refLines);

    let addedCount = 0;
    let removedCount = 0;

    for (const line of diffLines) {
      if (line.type === 'added') addedCount++;
      if (line.type === 'removed') removedCount++;
    }

    const outputLines: string[] = [
      `${TerminalDiffFormatter.BOLD}--- ${fileName} (original)${TerminalDiffFormatter.RESET}`,
      `${TerminalDiffFormatter.BOLD}+++ ${fileName} (clean-refactored)${TerminalDiffFormatter.RESET}`,
      `${TerminalDiffFormatter.CYAN}@@ -1,${origLines.length} +1,${refLines.length} @@${TerminalDiffFormatter.RESET}`
    ];

    for (const dl of diffLines) {
      if (dl.type === 'added') {
        outputLines.push(`${TerminalDiffFormatter.GREEN}+ ${dl.content}${TerminalDiffFormatter.RESET}`);
      } else if (dl.type === 'removed') {
        outputLines.push(`${TerminalDiffFormatter.RED}- ${dl.content}${TerminalDiffFormatter.RESET}`);
      } else {
        outputLines.push(`${TerminalDiffFormatter.DIM}  ${dl.content}${TerminalDiffFormatter.RESET}`);
      }
    }

    return {
      hasChanges: true,
      addedCount,
      removedCount,
      lines: diffLines,
      formattedTerminalOutput: outputLines.join('\n')
    };
  }

  /**
   * Computes the Longest Common Subsequence (LCS) diff between two line arrays.
   */
  private computeLcsDiff(orig: readonly string[], ref: readonly string[]): DiffLine[] {
    const n = orig.length;
    const m = ref.length;

    // dp[i][j] stores the length of LCS of orig[0..i-1] and ref[0..j-1]
    const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));

    for (let i = 1; i <= n; i++) {
      for (let j = 1; j <= m; j++) {
        if (orig[i - 1] === ref[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1] + 1;
        } else {
          dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
        }
      }
    }

    // Backtrack to build the diff
    let i = n;
    let j = m;
    const result: DiffLine[] = [];

    while (i > 0 || j > 0) {
      if (i > 0 && j > 0 && orig[i - 1] === ref[j - 1]) {
        result.push({ type: 'unchanged', content: orig[i - 1] });
        i--;
        j--;
      } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
        result.push({ type: 'added', content: ref[j - 1] });
        j--;
      } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
        result.push({ type: 'removed', content: orig[i - 1] });
        i--;
      }
    }

    return result.reverse();
  }
}
