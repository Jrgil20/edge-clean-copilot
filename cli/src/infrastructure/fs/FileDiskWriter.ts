import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { Result } from '../../shared/types/Result.js';
import { InfrastructureError } from '../../shared/errors/DomainError.js';

export class FileDiskWriter {
  public async write(filePath: string, content: string): Promise<Result<void, InfrastructureError>> {
    try {
      const resolvedPath = path.resolve(process.cwd(), filePath);
      const parentDir = path.dirname(resolvedPath);
      await fs.mkdir(parentDir, { recursive: true });
      await fs.writeFile(resolvedPath, content, 'utf-8');
      return Result.ok(undefined);
    } catch (error) {
      return Result.fail(
        new InfrastructureError(
          `Unable to write file at "${filePath}": ${(error as Error).message}`,
          'FILE_WRITE_ERROR',
          error
        )
      );
    }
  }
}
