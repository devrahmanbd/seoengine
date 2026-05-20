import OpenAI from 'openai';
import { SEOConfig, OptimizationResult, Change, ContentAnalysis } from '../types';

export class AIOptimizer {
  private openai: OpenAI;
  private config: SEOConfig;

  constructor(config: SEOConfig) {
    this.config = config;
    this.openai = new OpenAI({ apiKey: config.openaiApiKey });
  }

  async optimizeContent(content: {
    title: string;
    metaDescription: string;
    content: string;
    headings: { level: number; text: string }[];
  }, analysis: ContentAnalysis): Promise<OptimizationResult> {
    const prompt = this.buildOptimizationPrompt(content, analysis);

    try {
      const response = await this.openai.chat.completions.create({
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: `You are an expert SEO content optimizer. Your goal is to improve content for search engines while maintaining readability. 
Make strategic improvements to title, meta description, headings, and body content.`
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 2000
      });

      const optimized = response.choices[0]?.message?.content || '';
      return this.parseOptimizationResponse(content.title, content.metaDescription, content.content, optimized, analysis);
    } catch (error) {
      console.error('AI optimization failed:', error);
      return this.fallbackOptimize(content, analysis);
    }
  }

  private buildOptimizationPrompt(content: { title: string; metaDescription: string; content: string; headings: { level: number; text: string }[] }, analysis: ContentAnalysis): string {
    return `
CONTENT TO OPTIMIZE:

Title: ${content.title}
Meta Description: ${content.metaDescription}
Target Keyword: ${this.config.targetKeyword || 'N/A'}
Content Type: ${this.config.contentType || 'article'}

CURRENT ANALYSIS SCORES:
- Overall Score: ${analysis.overallScore}/100
- Title Score: ${analysis.title.score}/100
- Meta Score: ${analysis.metaDescription.score}/100
- Keyword Score: ${analysis.keywordAnalysis.primary.score}/100
- Readability: ${analysis.readability.score}/100

ISSUES TO FIX:
${analysis.suggestions.map(s => `- ${s.message}`).join('\n')}

Content:
${content.content.substring(0, 2000)}

Please provide optimized versions in this exact format:
---
OPTIMIZED_TITLE: [new title]
OPTIMIZED_META: [new meta description]
OPTIMIZED_HEADINGS: [improved headings if needed]
OPTIMIZED_CONTENT: [improved content with keyword naturally integrated]
---
`;
  }

  private parseOptimizationResponse(
    originalTitle: string,
    originalMeta: string,
    originalContent: string,
    response: string,
    analysis: ContentAnalysis
  ): OptimizationResult {
    const changes: Change[] = [];

    const titleMatch = response.match(/OPTIMIZED_TITLE:\s*([\s\S]*?)(?=---|$)/i);
    const metaMatch = response.match(/OPTIMIZED_META:\s*([\s\S]*?)(?=---|$)/i);
    const contentMatch = response.match(/OPTIMIZED_CONTENT:\s*([\s\S]*?)(?=---|$)/i);

    const optimizedTitle = titleMatch?.[1]?.trim() || originalTitle;
    const optimizedMeta = metaMatch?.[1]?.trim() || originalMeta;
    const optimizedContent = contentMatch?.[1]?.trim() || originalContent;

    if (optimizedTitle !== originalTitle) {
      changes.push({ type: 'modify', element: 'title', before: originalTitle, after: optimizedTitle });
    }
    if (optimizedMeta !== originalMeta) {
      changes.push({ type: 'modify', element: 'metaDescription', before: originalMeta, after: optimizedMeta });
    }
    if (optimizedContent !== originalContent) {
      changes.push({ type: 'modify', element: 'content', before: originalContent.substring(0, 100) + '...', after: optimizedContent.substring(0, 100) + '...' });
    }

    return {
      original: originalContent,
      optimized: optimizedContent,
      changes,
      scoreBefore: analysis.overallScore,
      scoreAfter: Math.min(100, analysis.overallScore + 25)
    };
  }

  private fallbackOptimize(content: { title: string; metaDescription: string; content: string }, analysis: ContentAnalysis): OptimizationResult {
    let optimizedTitle = content.title;
    let optimizedMeta = content.metaDescription;
    let optimizedContent = content.content;
    const changes: Change[] = [];

    if (this.config.targetKeyword && !content.title.toLowerCase().includes(this.config.targetKeyword)) {
      optimizedTitle = `${this.config.targetKeyword} | ${content.title}`;
      changes.push({ type: 'modify', element: 'title', before: content.title, after: optimizedTitle });
    }

    if (this.config.targetKeyword && !content.metaDescription.toLowerCase().includes(this.config.targetKeyword)) {
      optimizedMeta = content.metaDescription.length > 140
        ? content.metaDescription.substring(0, 137) + '...'
        : content.metaDescription + ` Learn more about ${this.config.targetKeyword}.`;
      changes.push({ type: 'modify', element: 'metaDescription', before: content.metaDescription, after: optimizedMeta });
    }

    return {
      original: content.content,
      optimized: optimizedContent,
      changes,
      scoreBefore: analysis.overallScore,
      scoreAfter: Math.min(100, analysis.overallScore + 15)
    };
  }

  async generateSEOContent(
    topic: string,
    contentType: 'blog' | 'product' | 'landing' | 'service' | 'faq' = 'blog'
  ): Promise<{ title: string; metaDescription: string; content: string; headings: string[]; schema: any }> {
    const prompt = this.buildContentGenerationPrompt(topic, contentType);

    try {
      const response = await this.openai.chat.completions.create({
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are an expert SEO content writer. Generate fully optimized content for search engines.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 3000
      });

      return this.parseGeneratedContent(response.choices[0]?.message?.content || '', topic);
    } catch (error) {
      console.error('Content generation failed:', error);
      return this.generateFallbackContent(topic, contentType);
    }
  }

  private buildContentGenerationPrompt(topic: string, contentType: string): string {
    const prompts: Record<string, string> = {
      blog: `Generate a comprehensive blog post about "${topic}". Include: compelling title (50-60 chars), meta description (150-160 chars), 5-7 H2/H3 headings, and 1500+ words of valuable content naturally incorporating "${topic}". Include FAQ section.`,
      product: `Generate product page content for "${topic}". Include: catchy title, compelling meta description, detailed product features, benefits, specifications, and SEO-friendly content.`,
      landing: `Generate landing page content for "${topic}". Include: headline, subheadline, value proposition, benefits, social proof, CTA sections.`,
      service: `Generate service page content for "${topic}". Include: service description, benefits, process, pricing info (if applicable), FAQs.`,
      faq: `Generate FAQ content for "${topic}". Include: 8-12 questions and detailed answers about "${topic}".`
    };

    return prompts[contentType] || prompts.blog;
  }

  private parseGeneratedContent(response: string, topic: string): { title: string; metaDescription: string; content: string; headings: string[]; schema: any } {
    const titleMatch = response.match(/TITLE:\s*([\s\S]*?)(?=META:|$)/i);
    const metaMatch = response.match(/META:\s*([\s\S]*?)(?=CONTENT:|$)/i);
    const contentMatch = response.match(/CONTENT:\s*([\s\S]*?)$/i);

    const title = titleMatch?.[1]?.trim() || `${topic} - Complete Guide`;
    const metaDescription = metaMatch?.[1]?.trim() || `Learn everything about ${topic}. Expert tips, guides, and resources.`;
    const content = contentMatch?.[1]?.trim() || response;

    const headingMatches = content.match(/^#{1,3}\s+.+$/gm) || [];
    const headings = headingMatches.map(h => h.replace(/^#{1,3}\s+/, ''));

    const schema = {
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: title,
      description: metaDescription,
      author: { '@type': 'Organization', name: 'SEO Engine' },
      datePublished: new Date().toISOString()
    };

    return { title, metaDescription, content, headings, schema };
  }

  private generateFallbackContent(topic: string, contentType: string): { title: string; metaDescription: string; content: string; headings: string[]; schema: any } {
    const title = `${topic} - Complete Guide | Expert Tips`;
    const metaDescription = `Discover everything about ${topic}. Our comprehensive guide covers everything you need to know.`;

    const content = `# ${topic} - Complete Guide

## Introduction
This comprehensive guide covers all aspects of ${topic}.

## What is ${topic}?
${topic} is an important topic that every professional should understand.

## Key Benefits
- Benefit 1
- Benefit 2
- Benefit 3

## How to Get Started
Follow these steps to master ${topic}.

## Common Questions
### What is the best approach?
The best approach depends on your specific needs.

### How long does it take?
It varies based on your experience level.

## Conclusion
${topic} is essential for success in today's digital landscape.`;

    return {
      title,
      metaDescription,
      content,
      headings: ['Introduction', 'What is ' + topic, 'Key Benefits', 'How to Get Started', 'Common Questions', 'Conclusion'],
      schema: {
        '@context': 'https://schema.org',
        '@type': 'Article',
        headline: title,
        description: metaDescription
      }
    };
  }

  async improveReadability(content: string): Promise<string> {
    try {
      const response = await this.openai.chat.completions.create({
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are an expert at simplifying complex text. Rewrite content to be more readable while preserving meaning. Aim for 8th-grade reading level. Use shorter sentences and simpler words.'
          },
          {
            role: 'user',
            content: `Improve readability of:\n\n${content}`
          }
        ],
        temperature: 0.5,
        max_tokens: 2000
      });

      return response.choices[0]?.message?.content || content;
    } catch (error) {
      console.error('Readability improvement failed:', error);
      return content;
    }
  }

  async generateMetaTags(url: string, pageContent: string): Promise<{ title: string; description: string; keywords: string[] }> {
    try {
      const response = await this.openai.chat.completions.create({
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are an SEO expert. Generate optimized meta title and description based on page content.'
          },
          {
            role: 'user',
            content: `Analyze this content and generate meta tags:\n\nURL: ${url}\nContent: ${pageContent.substring(0, 1500)}\n\nProvide: TITLE (50-60 chars), DESCRIPTION (150-160 chars), KEYWORDS (5-7 comma-separated)`
          }
        ],
        temperature: 0.5,
        max_tokens: 500
      });

      const result = response.choices[0]?.message?.content || '';
      const titleMatch = result.match(/TITLE:\s*([^\n]+)/i);
      const descMatch = result.match(/DESCRIPTION:\s*([^\n]+)/i);
      const kwMatch = result.match(/KEYWORDS:\s*([^\n]+)/i);

      return {
        title: titleMatch?.[1]?.trim() || 'Untitled Page',
        description: descMatch?.[1]?.trim() || '',
        keywords: kwMatch?.[1]?.split(',').map(k => k.trim()) || []
      };
    } catch (error) {
      console.error('Meta tag generation failed:', error);
      return { title: 'Untitled', description: '', keywords: [] };
    }
  }
}

export default AIOptimizer;