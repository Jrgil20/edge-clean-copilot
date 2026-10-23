import { describe, it, expect, afterEach } from 'vitest';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as os from 'node:os';
import { FileDiskWriter } from '../../../src/infrastructure/fs/FileDiskWriter.js';
import { FileDiskReader } from '../../../src/infrastructure/fs/FileDiskReader.js';

describe('FileDiskWriter', () => {
  const tempDir = path.join(os.tmpdir(), `ecc-writer-test-${Date.now()}`);

  afterEach(async () => {
    await fs.rm(tempDir, { recursive: true, force: true }).catch(() => {});
  });

  it('should successfully write content and create parent directory recursively', async () => {
    const writer = new FileDiskWriter();
    const reader = new FileDiskReader();
    const targetFile = path.join(tempDir, 'nested', 'output.ts');
    const content = 'export class CleanService {}';

    const writeResult = await writer.write(targetFile, content);
    expect(writeResult.success).toBe(true);

    const readResult = await reader.read(targetFile);
    expect(readResult.success).toBe(true);
    if (readResult.success) {
      expect(readResult.data).toBe(content);
    }
  });

  it('should fail gracefully with InfrastructureError when writing to invalid path', async () => {
    const writer = new FileDiskWriter();
    // Writing to a directory path as if it were a file
    const invalidPath = path.join(tempDir, 'dir_as_file');
    await fs.mkdir(invalidPath, { recursive: true });

    const result = await writer.write(invalidPath, 'content');
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.code).toBe('FILE_WRITE_ERROR');
      expect(result.error.name).toBe('InfrastructureError');
    }
  });
});
