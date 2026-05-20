import axios from 'axios';
import { BaseAIProvider } from './base';
import { ChatMessage, ChatResponse, StreamCallback } from './types';

export class CustomProvider extends BaseAIProvider {
  constructor(config: {
    apiKey: string;
    baseUrl: string;
    model?: string;
  }) {
    super({
      apiKey: config.apiKey,
      provider: 'custom',
      baseUrl: config.baseUrl,
      model: config.model || 'gpt-4'
    });
  }

  async chat(messages: ChatMessage[], options?: {
    temperature?: number;
    maxTokens?: number;
    stream?: boolean;
    onStream?: StreamCallback;
  }): Promise<ChatResponse> {
    try {
      const response = await axios.post(
        `${this.baseUrl}/chat/completions`,
        {
          model: this.model,
          messages,
          temperature: options?.temperature ?? 0.7,
          max_tokens: options?.maxTokens ?? 2000,
          stream: options?.stream ?? false
        },
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          },
          timeout: 60000
        }
      );

      return {
        content: response.data.choices[0]?.message?.content || '',
        model: response.data.model || this.model,
        usage: response.data.usage,
        finishReason: response.data.choices[0]?.finish_reason
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
      'You are ZenSEO, an expert SEO strategist. Provide concise, actionable advice.',
      prompt
    );
    const response = await this.chat(messages, options);
    return response.content;
  }

  async testConnection(): Promise<{ success: boolean; latency: number; model: string }> {
    const start = Date.now();
    try {
      await this.chat(
        [{ role: 'user', content: 'Hello' }],
        { maxTokens: 10 }
      );
      return {
        success: true,
        latency: Date.now() - start,
        model: this.model
      };
    } catch (error) {
      return {
        success: false,
        latency: Date.now() - start,
        model: this.model
      };
    }
  }
}

export default CustomProvider;