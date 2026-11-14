import { IInferenceEngine, InferencePrompt, InferenceOutput } from '../../application/ports/IInferenceEngine.js';
import { Result } from '../../shared/types/Result.js';
import { InfrastructureError } from '../../shared/errors/DomainError.js';

export interface LlamaServerConfig {
  readonly baseUrl?: string;
  readonly modelName?: string;
  readonly timeoutMs?: number;
}

export class LlamaServerAdapter implements IInferenceEngine {
  /**
   * Measured on a CPU-only i5-10310U (~10-12.6 tok/s): typical replies of
   * 1100-1300 tokens took 86-130 s; a reply that ran to the full 2048-token
   * budget took 208 s. 300 s covers both with headroom.
   */
  public static readonly DEFAULT_TIMEOUT_MS = 300_000;

  public readonly endpoint: string;
  private readonly modelName: string;
  private readonly timeoutMs: number;

  constructor(config?: LlamaServerConfig) {
    const rawUrl = (config?.baseUrl || process.env.LLAMA_SERVER_URL || 'http://127.0.0.1:8080').trim().replace(/\/+$/, '');
    this.endpoint = this.normalizeEndpoint(rawUrl);
    this.modelName = config?.modelName || process.env.LLAMA_MODEL_NAME || 'edge-clean-copilot-q4_k_m';
    this.timeoutMs = config?.timeoutMs || LlamaServerAdapter.DEFAULT_TIMEOUT_MS;
  }

  private normalizeEndpoint(rawUrl: string): string {
    if (rawUrl.endsWith('/v1/chat/completions')) {
      return rawUrl;
    }
    if (rawUrl.endsWith('/v1')) {
      return `${rawUrl}/chat/completions`;
    }
    return `${rawUrl}/v1/chat/completions`;
  }

  public async complete(
    prompt: InferencePrompt
  ): Promise<Result<InferenceOutput, InfrastructureError>> {
    const startTime = Date.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    try {

      const response = await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: this.modelName,
          temperature: prompt.temperature ?? 0.1,
          max_tokens: prompt.maxTokens ?? 2048,
          messages: [
            { role: 'system', content: prompt.systemPrompt },
            { role: 'user', content: prompt.userPrompt }
          ]
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        const errorText = (await response.text().catch(() => 'Unknown error body')).slice(0, 500);
        return Result.fail(
          new InfrastructureError(
            `llama-server HTTP ${response.status}: ${errorText}`,
            'LLAMA_SERVER_HTTP_ERROR'
          )
        );
      }

      interface ChatCompletionResponse {
        choices?: Array<{
          message?: {
            content?: unknown;
          };
          finish_reason?: string;
        }>;
        model?: string;
      }

      let json: ChatCompletionResponse;
      try {
        json = (await response.json()) as ChatCompletionResponse;
      } catch (parseError) {
        if (controller.signal.aborted) {
          throw parseError;
        }
        return Result.fail(
          new InfrastructureError('llama-server returned a non-JSON response body', 'INVALID_RESPONSE_ERROR', parseError)
        );
      }
      const choice = json.choices?.[0];
      const text = typeof choice?.message?.content === 'string' ? choice.message.content : undefined;

      if (choice?.finish_reason === 'length') {
        return Result.fail(
          new InfrastructureError(
            'llama-server output was truncated (finish_reason=length). Increase --max-tokens or reduce the input size.',
            'TRUNCATED_COMPLETION_ERROR'
          )
        );
      }

      if (!text) {
        return Result.fail(
          new InfrastructureError('llama-server returned an empty completion choice', 'EMPTY_COMPLETION_ERROR')
        );
      }

      return Result.ok({
        text,
        modelName: json.model || this.modelName,
        durationMs: Date.now() - startTime
      });
    } catch (error) {
      if (controller.signal.aborted) {
        return Result.fail(
          new InfrastructureError(
            `llama-server at ${this.endpoint} did not respond within ${this.timeoutMs}ms.`,
            'LLAMA_TIMEOUT_ERROR',
            error
          )
        );
      }
      return Result.fail(
        new InfrastructureError(
          `Failed to connect to llama-server at ${this.endpoint}. Ensure llama-server is running.`,
          'LLAMA_CONNECTION_ERROR',
          error
        )
      );
    } finally {
      clearTimeout(timer);
    }
  }
}
