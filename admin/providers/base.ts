import { AIProvider, ChatMessage, ChatResponse, StreamCallback } from './types';

export abstract class BaseAIProvider {
  protected apiKey: string;
  protected baseUrl: string;
  protected model: string;
  protected provider: AIProvider;

  constructor(config: {
    apiKey: string;
    baseUrl?: string;
    model?: string;
    provider: AIProvider;
  }) {
    this.apiKey = config.apiKey;
    this.baseUrl = config.baseUrl || '';
    this.model = config.model || 'gpt-4';
    this.provider = config.provider;
  }

  abstract chat(messages: ChatMessage[], options?: {
    temperature?: number;
    maxTokens?: number;
    stream?: boolean;
    onStream?: StreamCallback;
  }): Promise<ChatResponse>;

  abstract generateContent(prompt: string, options?: {
    temperature?: number;
    maxTokens?: number;
  }): Promise<string>;

  getProviderName(): string {
    return this.provider;
  }

  getModel(): string {
    return this.model;
  }

  protected buildMessages(systemPrompt: string, userPrompt: string): ChatMessage[] {
    return [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ];
  }

  protected handleError(error: any): Error {
    if (error.response?.status === 429) {
      return new Error('Rate limit exceeded. Please try again later.');
    }
    if (error.response?.status === 401) {
      return new Error('Invalid API key. Please check your configuration.');
    }
    return new Error(error.message || 'Unknown error from AI provider');
  }
}

export default BaseAIProvider;