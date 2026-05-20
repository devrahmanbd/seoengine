import axios from 'axios';
import { BaseAIProvider } from './base';
import { ChatMessage, ChatResponse, StreamCallback } from './types';

export class OpenCodeProvider extends BaseAIProvider {
  constructor(apiKey: string, model: string = 'opencode/zen') {
    super({
      apiKey,
      provider: 'opencode',
      model,
      baseUrl: 'https://api.opencode.ai/v1'
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
          }
        }
      );

      if (options?.stream && options?.onStream) {
        return { content: '', model: this.model };
      }

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
}

export default OpenCodeProvider;