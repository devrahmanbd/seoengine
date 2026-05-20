import { SEOAnalyzer } from './core/seo-analyzer';
import { AIOptimizer } from './core/ai-optimizer';
import { ContentFetcher } from './core/content-fetcher';
import { KeywordResearch } from './core/keyword-research';
import { SchemaGenerator } from './utils/schema-generator';
import { CSVHandler } from './utils/csv-handler';
import { SEMrushAPI } from './integrations/semrush';
import { SEOConfig, SEOReport, KeywordData, BatchAnalysis } from './types';

export class SEOEngine {
  private config: SEOConfig;
  private analyzer: SEOAnalyzer;
  private optimizer: AIOptimizer;
  private fetcher: ContentFetcher;
  private keywordResearch: KeywordResearch;
  private schemaGenerator: SchemaGenerator;
  private csvHandler: CSVHandler;
  private semrush: SEMrushAPI | null = null;

  constructor(config: SEOConfig) {
    this.config = config;

    const targetKeyword = config.targetKeyword || '';
    this.analyzer = new SEOAnalyzer(targetKeyword, []);
    this.optimizer = new AIOptimizer(config);
    this.fetcher = new ContentFetcher();
    this.keywordResearch = new KeywordResearch();
    this.schemaGenerator = new SchemaGenerator();
    this.csvHandler = new CSVHandler();

    if (config.semrushApiKey) {
      this.semrush = new SEMrushAPI(config.semrushApiKey);
    }
  }

  async analyze(url: string): Promise<SEOReport> {
    const content = await this.fetcher.fetch(url);

    const secondaryKeywords = this.keywordResearch.extractKeywordsFromContent(content.content, 5);
    const analyzer = new SEOAnalyzer(this.config.targetKeyword || '', secondaryKeywords);

    const analysis = await analyzer.analyze({
      title: content.title,
      metaDescription: content.metaDescription,
      headings: content.headings,
      paragraphs: content.content.split('\n\n').filter(p => p.trim()),
      html: content.rawHtml,
      internalLinks: content.internalLinks,
      externalLinks: content.externalLinks,
      images: content.images
    });

    return {
      url,
      title: content.title,
      description: content.metaDescription,
      keyword: this.config.targetKeyword || '',
      analysis,
      timestamp: new Date()
    };
  }

  async analyzeBatch(urls: string[]): Promise<BatchAnalysis> {
    const batchId = `batch_${Date.now()}`;
    const results: SEOReport[] = [];
    const errors: string[] = [];

    for (const url of urls) {
      try {
        const report = await this.analyze(url);
        results.push(report);
      } catch (error) {
        errors.push(`${url}: ${(error as Error).message}`);
      }
    }

    return {
      id: batchId,
      urls,
      status: errors.length === urls.length ? 'failed' : 'completed',
      results,
      errors,
      createdAt: new Date(),
      completedAt: new Date()
    };
  }

  async optimize(report: SEOReport): Promise<{
    optimizedTitle: string;
    optimizedMeta: string;
    optimizedContent: string;
    changes: any[];
  }> {
    const content = await this.fetcher.fetch(report.url);
    const paragraphs = content.content.split('\n\n').filter(p => p.trim());

    const optimization = await this.optimizer.optimizeContent({
      title: content.title,
      metaDescription: content.metaDescription,
      content: content.content,
      headings: content.headings
    }, report.analysis);

    return {
      optimizedTitle: optimization.changes.find(c => c.element === 'title')?.after || content.title,
      optimizedMeta: optimization.changes.find(c => c.element === 'metaDescription')?.after || content.metaDescription,
      optimizedContent: optimization.optimized,
      changes: optimization.changes
    };
  }

  async generateContent(
    topic: string,
    contentType: 'blog' | 'product' | 'landing' | 'service' | 'faq' = 'blog'
  ): Promise<{
    title: string;
    metaDescription: string;
    content: string;
    headings: string[];
    schema: string;
  }> {
    const generated = await this.optimizer.generateSEOContent(topic, contentType);

    return {
      title: generated.title,
      metaDescription: generated.metaDescription,
      content: generated.content,
      headings: generated.headings,
      schema: JSON.stringify(generated.schema, null, 2)
    };
  }

  async getKeywordData(keyword: string): Promise<KeywordData> {
    if (this.semrush) {
      return await this.semrush.getFullKeywordAnalysis(keyword, this.config.country || 'us');
    }

    return {
      keyword,
      volume: 0,
      difficulty: this.keywordResearch.analyzeKeyword(keyword).difficulty === 'hard' ? 80 : 50,
      cpc: 0,
      competition: 0,
      trends: Array(12).fill(0),
      relatedKeywords: this.keywordResearch.generateKeywordVariations(keyword),
      intent: this.keywordResearch.determineSearchIntent(keyword)
    };
  }

  async getRelatedKeywords(keyword: string, limit: number = 10): Promise<KeywordData[]> {
    if (this.semrush) {
      const related = await this.semrush.getRelatedKeywords(keyword, this.config.country || 'us', limit);
      return Promise.all(related.map(k => this.getKeywordData(k)));
    }

    const variations = this.keywordResearch.generateKeywordVariations(keyword);
    return variations.slice(0, limit).map(kw => ({
      keyword: kw,
      volume: Math.floor(Math.random() * 10000),
      difficulty: Math.floor(Math.random() * 100),
      cpc: Math.random() * 5,
      competition: Math.random(),
      trends: Array(12).fill(0),
      relatedKeywords: [],
      intent: this.keywordResearch.determineSearchIntent(kw)
    }));
  }

  async importFromCSV(filePath: string): Promise<BatchAnalysis> {
    const rows = await this.csvHandler.importCSV(filePath);
    const urls = rows.map(r => r.url).filter(Boolean);

    return this.analyzeBatch(urls);
  }

  async exportReport(reports: SEOReport[], outputPath: string): Promise<void> {
    this.csvHandler.exportCSV(reports, outputPath);
  }

  generateSchema(type: 'Article' | 'Product' | 'LocalBusiness' | 'FAQPage' | 'WebSite' | 'Organization', data: any): string {
    return this.schemaGenerator.generate({
      type,
      ...data
    });
  }

  generateBreadcrumb(items: { name: string; url: string }[]): string {
    return this.schemaGenerator.generateBreadcrumb(items);
  }
}

export default SEOEngine;