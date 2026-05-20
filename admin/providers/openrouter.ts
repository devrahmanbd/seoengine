import axios from 'axios';
import { BaseAIProvider } from './base';
import { ChatMessage, ChatResponse, StreamCallback } from './types';

export class OpenRouterProvider extends BaseAIProvider {
  constructor(apiKey: string, model: string = 'openai/gpt-4-turbo') {
    super({
      apiKey,
      provider: 'openrouter',
      model,
      baseUrl: 'https://openrouter.ai/api/v1'
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
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://seoengine.ai',
            'X-Title': 'ZenSEO Engine'
          }
        }
      );

      return {
        content: response.data.choices[0]?.message?.content || '',
        model: response.data.model || this.model,
        usage: {
          inputTokens: response.data.usage?.prompt_tokens || 0,
          outputTokens: response.data.usage?.completion_tokens || 0,
          totalTokens: response.data.usage?.total_tokens || 0
        },
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

  async listModels(): Promise<{ id: string; name: string; provider: string }[]> {
    try {
      const response = await axios.get(`${this.baseUrl}/models`, {
        headers: { 'Authorization': `Bearer ${this.apiKey}` }
      });
      return response.data.data.map((m: any) => ({
        id: m.id,
        name: m.name,
        provider: m.id.split('/')[0]
      }));
    } catch (error: any) {
      return [];
    }
  }

  static getRecommendedModels(): { id: string; name: string; useCase: string }[] {
    return [
      { id: 'openai/gpt-4-turbo', name: 'GPT-4 Turbo', useCase: 'Best overall' },
      { id: 'anthropic/claude-3-opus', name: 'Claude 3 Opus', useCase: 'Complex analysis' },
      { id: 'anthropic/claude-3-sonnet', name: 'Claude 3 Sonnet', useCase: 'Balanced' },
      { id: 'google/gemini-pro-1.5', name: 'Gemini Pro 1.5', useCase: 'Long context' },
      { id: 'meta-llama/llama-3-70b-instruct', name: 'Llama 3 70B', useCase: 'Fast, cheap' }
    ];
  }
}

export default OpenRouterProvider;