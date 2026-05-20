import axios from 'axios';
import { BaseAIProvider } from './base';
import { ChatMessage, ChatResponse, StreamCallback } from './types';
import { AnthropicMessage, AnthropicResponse } from './types';

export class AnthropicProvider extends BaseAIProvider {
  constructor(apiKey: string, model: string = 'claude-3-opus-20240229') {
    super({
      apiKey,
      provider: 'anthropic',
      model,
      baseUrl: 'https://api.anthropic.com/v1'
    });
  }

  async chat(messages: ChatMessage[], options?: {
    temperature?: number;
    maxTokens?: number;
    stream?: boolean;
    onStream?: StreamCallback;
  }): Promise<ChatResponse> {
    try {
      const anthropicMessages: AnthropicMessage[] = messages.map(m => ({
        role: m.role === 'system' ? 'user' : m.role,
        content: m.content
      }));

      const maxTokens = options?.maxTokens ?? 2000;

      const response = await axios.post<AnthropicResponse>(
        `${this.baseUrl}/messages`,
        {
          model: this.model,
          messages: anthropicMessages,
          max_tokens: maxTokens,
          temperature: options?.temperature ?? 0.7,
          stream: options?.stream ?? false
        },
        {
          headers: {
            'x-api-key': this.apiKey,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
          }
        }
      );

      const content = response.data.content
        .filter(c => c.type === 'text')
        .map(c => c.text)
        .join('');

      return {
        content,
        model: response.data.model,
        usage: {
          inputTokens: response.data.usage.input_tokens,
          outputTokens: response.data.usage.output_tokens,
          totalTokens: response.data.usage.input_tokens + response.data.usage.output_tokens
        },
        finishReason: response.data.stop_reason
      };
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  async generateContent(prompt: string, options?: {
    temperature?: number;
    maxTokens?: number;
  }): Promise<string> {
    const messages = this.buildMessages(
      'You are ZenSEO, an expert SEO strategist with deep knowledge of modern SEO, content marketing, and AI. Provide comprehensive, actionable advice.',
      prompt
    );
    const response = await this.chat(messages, options);
    return response.content;
  }

  static getAvailableModels(): { id: string; name: string; contextWindow: number }[] {
    return [
      { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', contextWindow: 200000 },
      { id: 'claude-3-sonnet-20240229', name: 'Claude 3 Sonnet', contextWindow: 200000 },
      { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', contextWindow: 200000 },
      { id: 'claude-2.1', name: 'Claude 2.1', contextWindow: 200000 },
      { id: 'claude-instant-1.2', name: 'Claude Instant', contextWindow: 100000 }
    ];
  }
}

export default AnthropicProvider;