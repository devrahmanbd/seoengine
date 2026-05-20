import axios from 'axios';
import * as cheerio from 'cheerio';
import TurndownService from 'turndown';

export interface FetchedContent {
  title: string;
  metaDescription: string;
  content: string;
  rawHtml: string;
  headings: { level: number; text: string }[];
  internalLinks: { url: string; text: string; isFollow: boolean }[];
  externalLinks: { url: string; text: string; isFollow: boolean }[];
  images: { src: string; alt: string }[];
  author: string;
  publishedDate: string;
  language: string;
  canonicalUrl: string;
  ogTags: Record<string, string>;
}

export class ContentFetcher {
  private turndown: TurndownService;

  constructor() {
    this.turndown = new TurndownService({
      headingStyle: 'atx',
      codeBlockStyle: 'fenced'
    });
    (this.turndown as any).addRule('img', {
      replacement: (_content: string, node: any) => {
        const alt = node.alt || '';
        const src = node.src || '';
        return `![${alt}](${src})`;
      }
    });
  }

  async fetch(url: string): Promise<FetchedContent> {
    try {
      const response = await axios.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; SEOEngine/1.0)',
          'Accept': 'text/html,application/xhtml+xml'
        },
        timeout: 30000,
        maxRedirects: 5
      });

      return this.parseHTML(response.data, url);
    } catch (error) {
      console.error(`Failed to fetch ${url}:`, (error as Error).message);
      throw new Error(`Failed to fetch URL: ${(error as Error).message}`);
    }
  }

  private parseHTML(html: string, baseUrl: string): FetchedContent {
    const $ = cheerio.load(html);

    const title = $('title').text().trim() ||
      $('meta[property="og:title"]').attr('content')?.trim() || '';

    const metaDescription = $('meta[name="description"]').attr('content')?.trim() ||
      $('meta[property="og:description"]').attr('content')?.trim() || '';

    const canonicalUrl = $('link[rel="canonical"]').attr('href') || baseUrl;

    const headings: { level: number; text: string }[] = [];
    $('h1, h2, h3, h4, h5, h6').each((_i, el) => {
      const element = el as unknown as { tagName: string };
      const level = parseInt(element.tagName.replace('h', ''), 10);
      const text = $(el).text().trim();
      if (text) {
        headings.push({ level, text });
      }
    });

    const internalLinks: { url: string; text: string; isFollow: boolean }[] = [];
    const externalLinks: { url: string; text: string; isFollow: boolean }[] = [];

    $('a[href]').each((_i, el) => {
      const href = $(el).attr('href');
      const text = $(el).text().trim();
      const isFollow = $(el).attr('rel') !== 'nofollow';

      if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
        const isInternal = href.startsWith('/') || href.startsWith(baseUrl) || !href.includes('://');

        if (isInternal) {
          const fullUrl = href.startsWith('/') ? new URL(href, baseUrl).href : href;
          internalLinks.push({ url: fullUrl, text, isFollow });
        } else {
          externalLinks.push({ url: href, text, isFollow });
        }
      }
    });

    const images: { src: string; alt: string }[] = [];
    $('img').each((_i, el) => {
      const src = $(el).attr('src') || $(el).attr('data-src') || '';
      const alt = $(el).attr('alt') || '';
      if (src) {
        images.push({ src, alt });
      }
    });

    const ogTags: Record<string, string> = {};
    $('meta[property^="og:"]').each((_i, el) => {
      const property = $(el).attr('property') || '';
      const content = $(el).attr('content') || '';
      if (property && content) {
        ogTags[property.replace('og:', '')] = content;
      }
    });

    const contentHtml = $('article').html() || $('main').html() || $('body').html() || '';
    const content = this.turndown.turndown(contentHtml);

    return {
      title,
      metaDescription,
      content,
      rawHtml: html,
      headings,
      internalLinks: internalLinks.slice(0, 50),
      externalLinks: externalLinks.slice(0, 50),
      images: images.slice(0, 30),
      author: $('meta[name="author"]').attr('content') || '',
      publishedDate: $('meta[property="article:published_time"]').attr('content') ||
        $('time[datetime]').attr('datetime') || '',
      language: $('html').attr('lang') || 'en',
      canonicalUrl,
      ogTags
    };
  }

  async fetchMultiple(urls: string[]): Promise<{ url: string; content: FetchedContent | null; error?: string }[]> {
    const results = await Promise.allSettled(urls.map(url => this.fetch(url)));

    return results.map((result, index) => ({
      url: urls[index],
      content: result.status === 'fulfilled' ? result.value : null,
      error: result.status === 'rejected' ? result.reason.message : undefined
    }));
  }
}

export default ContentFetcher;