import { BaseAIProvider } from './base';
import { OpenCodeProvider } from './opencode';
import { OpenRouterProvider } from './openrouter';
import { AnthropicProvider } from './anthropic';
import { CustomProvider } from './custom';
import { AIProvider } from './types';

export interface ProviderFactoryConfig {
  provider: AIProvider;
  apiKey: string;
  baseUrl?: string;
  model?: string;
}

export function createAIProvider(config: ProviderFactoryConfig): BaseAIProvider {
  switch (config.provider) {
    case 'opencode':
      return new OpenCodeProvider(config.apiKey, config.model);
    
    case 'openrouter':
      return new OpenRouterProvider(config.apiKey, config.model);
    
    case 'anthropic':
    case 'claude':
      return new AnthropicProvider(config.apiKey, config.model);
    
    case 'custom':
      if (!config.baseUrl) {
        throw new Error('baseUrl is required for custom provider');
      }
      return new CustomProvider({
        apiKey: config.apiKey,
        baseUrl: config.baseUrl,
        model: config.model
      });
    
    case 'openai':
      return new CustomProvider({
        apiKey: config.apiKey,
        baseUrl: config.baseUrl || 'https://api.openai.com/v1',
        model: config.model || 'gpt-4'
      });
    
    default:
      throw new Error(`Unknown provider: ${config.provider}`);
  }
}

export { BaseAIProvider } from './base';
export { OpenCodeProvider } from './opencode';
export { OpenRouterProvider } from './openrouter';
export { AnthropicProvider } from './anthropic';
export { CustomProvider } from './custom';
export * from './types';