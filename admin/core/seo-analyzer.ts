import {
  ContentAnalysis,
  ContentScore,
  HeadingAnalysis,
  KeywordAnalysis,
  KeywordPlacement,
  KeywordScore,
  ReadabilityScore,
  LinkAnalysis,
  Link,
  ImageAnalysis,
  SchemaAnalysis,
  Suggestion
} from '../types';

export class SEOAnalyzer {
  private targetKeyword: string;
  private secondaryKeywords: string[];

  constructor(targetKeyword: string, secondaryKeywords: string[] = []) {
    this.targetKeyword = targetKeyword.toLowerCase();
    this.secondaryKeywords = secondaryKeywords.map(k => k.toLowerCase());
  }

  async analyze(content: {
    title: string;
    metaDescription: string;
    headings: { level: number; text: string }[];
    paragraphs: string[];
    html: string;
    internalLinks: { url: string; text: string; isFollow: boolean }[];
    externalLinks: { url: string; text: string; isFollow: boolean }[];
    images: { src: string; alt: string }[];
  }): Promise<ContentAnalysis> {
    const [
      titleAnalysis,
      metaAnalysis,
      headingAnalysis,
      keywordAnalysis,
      readability,
      internalLinkAnalysis,
      externalLinkAnalysis,
      imageAnalysis,
      schemaAnalysis,
      suggestions
    ] = await Promise.all([
      this.analyzeTitle(content.title),
      this.analyzeMetaDescription(content.metaDescription),
      this.analyzeHeadings(content.headings),
      this.analyzeKeywords(content.title, content.headings, content.paragraphs),
      this.analyzeReadability(content.paragraphs),
      this.analyzeLinks(content.internalLinks, true),
      this.analyzeLinks(content.externalLinks, false),
      this.analyzeImages(content.images),
      this.detectSchema(content.html),
      this.generateSuggestions(
        content.title,
        content.metaDescription,
        content.headings,
        content.paragraphs,
        content.images
      )
    ]);

    const contentScore = this.calculateContentScore({
      title: titleAnalysis,
      meta: metaAnalysis,
      headings: headingAnalysis,
      keyword: keywordAnalysis,
      readability,
      internalLinks: internalLinkAnalysis,
      externalLinks: externalLinkAnalysis,
      images: imageAnalysis,
      schema: schemaAnalysis
    });

    return {
      title: titleAnalysis,
      metaDescription: metaAnalysis,
      headings: headingAnalysis,
      keywordAnalysis,
      contentScore,
      readability,
      internalLinks: internalLinkAnalysis,
      outboundLinks: externalLinkAnalysis,
      images: imageAnalysis,
      schema: schemaAnalysis,
      suggestions,
      overallScore: contentScore.total
    };
  }

  private async analyzeTitle(title: string): Promise<ContentScore> {
    const issues: string[] = [];
    const suggestions: string[] = [];
    let score = 50;

    if (!title) {
      issues.push('Missing title tag');
      score -= 30;
    } else {
      if (title.length < 30) {
        issues.push('Title too short (under 30 characters)');
        score -= 10;
      } else if (title.length > 60) {
        issues.push('Title too long (over 60 characters)');
        score -= 10;
      }

      if (title.toLowerCase().includes(this.targetKeyword)) {
        score += 20;
        suggestions.push('Great: Primary keyword in title');
      } else {
        issues.push('Primary keyword not found in title');
        score -= 15;
      }

      const titleWords = title.split(/\s+/).length;
      if (titleWords < 3) {
        suggestions.push('Consider making title more descriptive');
      }
    }

    return {
      score: Math.max(0, Math.min(100, score)),
      raw: title || '',
      optimized: title ? this.optimizeTitle(title) : '',
      issues,
      suggestions
    };
  }

  private async analyzeMetaDescription(meta: string): Promise<ContentScore> {
    const issues: string[] = [];
    const suggestions: string[] = [];
    let score = 50;

    if (!meta) {
      issues.push('Missing meta description');
      score -= 25;
    } else {
      if (meta.length < 120) {
        issues.push('Meta description too short (under 120 characters)');
        score -= 10;
      } else if (meta.length > 160) {
        issues.push('Meta description too long (over 160 characters)');
        score -= 10;
      }

      if (meta.toLowerCase().includes(this.targetKeyword)) {
        score += 20;
        suggestions.push('Good: Primary keyword in meta description');
      } else {
        suggestions.push('Consider including primary keyword in meta description');
      }

      if (meta.includes('...') || meta.endsWith('.')) {
        score += 5;
      }
    }

    return {
      score: Math.max(0, Math.min(100, score)),
      raw: meta || '',
      optimized: meta ? this.optimizeMetaDescription(meta) : '',
      issues,
      suggestions
    };
  }

  private async analyzeHeadings(headings: { level: number; text: string }[]): Promise<HeadingAnalysis[]> {
    const hasH1 = headings.some(h => h.level === 1);
    const keywordInH1 = headings.find(h => h.level === 1)?.text.toLowerCase().includes(this.targetKeyword);

    return headings.map(h => ({
      level: h.level,
      text: h.text,
      containsKeyword: h.text.toLowerCase().includes(this.targetKeyword),
      keyword: this.targetKeyword
    }));
  }

  private async analyzeKeywords(
    title: string,
    headings: { level: number; text: string }[],
    paragraphs: string[]
  ): Promise<KeywordAnalysis> {
    const allText = `${title} ${headings.map(h => h.text).join(' ')} ${paragraphs.join(' ')}`.toLowerCase();
    const words = allText.split(/\s+/).filter(w => w.length > 2);
    const totalWords = words.length;

    const primaryCount = (allText.match(new RegExp(this.escapeRegex(this.targetKeyword), 'gi')) || []).length;
    const primaryDensity = totalWords > 0 ? (primaryCount / totalWords) * 100 : 0;

    const secondaryCounts: { keyword: string; count: number }[] = [];
    for (const kw of this.secondaryKeywords) {
      const count = (allText.match(new RegExp(this.escapeRegex(kw), 'gi')) || []).length;
      if (count > 0) {
        secondaryCounts.push({ keyword: kw, count });
      }
    }

    const placement: KeywordPlacement = {
      title: title.toLowerCase().includes(this.targetKeyword),
      firstParagraph: paragraphs[0]?.toLowerCase().includes(this.targetKeyword) || false,
      headings: headings.some(h => h.text.toLowerCase().includes(this.targetKeyword)),
      lastParagraph: paragraphs[paragraphs.length - 1]?.toLowerCase().includes(this.targetKeyword) || false,
      altText: false
    };

    const primaryScore = this.calculateKeywordScore(primaryDensity, placement, primaryCount);
    const secondary: KeywordScore[] = secondaryCounts.map(s => ({
      keyword: s.keyword,
      count: s.count,
      density: totalWords > 0 ? (s.count / totalWords) * 100 : 0,
      score: this.calculateKeywordScore(
        totalWords > 0 ? (s.count / totalWords) * 100 : 0,
        placement,
        s.count
      )
    }));

    return {
      primary: {
        keyword: this.targetKeyword,
        count: primaryCount,
        density: Math.round(primaryDensity * 100) / 100,
        score: primaryScore
      },
      secondary,
      density: Math.round(primaryDensity * 100) / 100,
      placement,
      variations: this.generateKeywordVariations(this.targetKeyword)
    };
  }

  private calculateKeywordScore(density: number, placement: KeywordPlacement, count: number): number {
    let score = 50;

    if (density >= 1 && density <= 2.5) {
      score += 20;
    } else if (density > 2.5) {
      score -= 10;
      if (density > 5) score -= 15;
    } else if (density > 0 && density < 1) {
      score += 10;
    }

    const placementPoints = (placement.title ? 15 : 0) +
      (placement.firstParagraph ? 10 : 0) +
      (placement.headings ? 10 : 0) +
      (placement.lastParagraph ? 5 : 0);
    score += placementPoints;

    if (count >= 3) score += 10;

    return Math.max(0, Math.min(100, score));
  }

  private async analyzeReadability(paragraphs: string[]): Promise<ReadabilityScore> {
    const text = paragraphs.join(' ');
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const words = text.split(/\s+/).filter(w => w.length > 0);
    const totalSentences = sentences.length || 1;
    const totalWords = words.length || 1;

    const syllables = this.countSyllablesInText(text);
    const avgSentenceLength = totalWords / totalSentences;
    const avgWordLength = text.length / totalWords;

    const fleschReading = 206.835 - 1.015 * avgSentenceLength - 84.6 * (syllables / totalWords);
    const fleschKincaid = 0.39 * avgSentenceLength + 11.8 * (syllables / totalWords) - 15.59;
    const gunningFog = 0.4 * (avgSentenceLength + 100 * (this.countComplexWords(words) / totalWords));
    const colemanLiau = 0.0588 * (text.length * 100 / totalWords) - 0.296 * (totalSentences * 100 / totalWords) - 15.8;
    const autoReadability = 4.71 * (text.length / totalWords) + 0.5 * (totalWords / totalSentences) - 21.43;

    let readabilityScore = 50;
    if (fleschReading >= 60) readabilityScore += 20;
    else if (fleschReading >= 30) readabilityScore += 10;
    else readabilityScore -= 10;

    let grade = 'College Graduate';
    if (fleschKincaid <= 6) grade = '6th Grade';
    else if (fleschKincaid <= 8) grade = '8th Grade';
    else if (fleschKincaid <= 10) grade = '10th Grade';
    else if (fleschKincaid <= 12) grade = '12th Grade';
    else if (fleschKincaid <= 14) grade = 'College';

    return {
      fleschKincaid: Math.round(fleschKincaid * 10) / 10,
      fleschKincaidGrade: Math.round(fleschKincaid),
      GunningFog: Math.round(gunningFog * 10) / 10,
      ColemanLiau: Math.round(colemanLiau * 10) / 10,
      automatedReadability: Math.round(autoReadability * 10) / 10,
      avgSentenceLength: Math.round(avgSentenceLength * 10) / 10,
      avgWordLength: Math.round(avgWordLength * 10) / 10,
      totalSentences,
      totalWords,
      totalSyllables: syllables,
      score: Math.max(0, Math.min(100, readabilityScore)),
      grade
    };
  }

  private countSyllablesInText(text: string): number {
    const words = text.toLowerCase().replace(/[^a-z\s]/g, '').split(/\s+/);
    return words.reduce((sum, word) => sum + this.countSyllables(word), 0);
  }

  private countSyllables(word: string): number {
    word = word.toLowerCase();
    if (word.length <= 3) return 1;
    word = word.replace(/(?:[^laeiouy]es|ed|[^laeiouy]e)$/, '');
    word = word.replace(/^y/, '');
    const matches = word.match(/[aeiouy]{1,2}/g);
    return matches ? matches.length : 1;
  }

  private countComplexWords(words: string[]): number {
    return words.filter(w => this.countSyllables(w) >= 3).length;
  }

  private async analyzeLinks(links: { url: string; text: string; isFollow: boolean }[], isInternal: boolean): Promise<LinkAnalysis> {
    const processedLinks: Link[] = links.map(l => ({
      url: l.url,
      text: l.text,
      isFollow: l.isFollow,
      isExternal: !isInternal
    }));

    let score = 60;
    const issues: string[] = [];

    if (isInternal) {
      if (links.length < 2) {
        issues.push('Consider adding more internal links');
        score -= 10;
      } else {
        score += 15;
      }
    } else {
      if (links.length === 0) {
        issues.push('Consider adding outbound links to authoritative sources');
      } else if (links.length > 0) {
        score += 10;
      }
    }

    return {
      count: links.length,
      internal: isInternal ? processedLinks : [],
      external: !isInternal ? processedLinks : [],
      score: Math.max(0, Math.min(100, score)),
      issues
    };
  }

  private async analyzeImages(images: { src: string; alt: string }[]): Promise<ImageAnalysis[]> {
    return images.map(img => {
      const issues: string[] = [];
      let score = 70;

      if (!img.alt || img.alt.trim() === '') {
        issues.push('Image missing alt text');
        score -= 20;
      } else {
        if (img.alt.toLowerCase().includes(this.targetKeyword)) {
          score += 20;
        } else {
          issues.push('Consider including keyword in image alt text');
          score -= 5;
        }
      }

      return {
        src: img.src,
        alt: img.alt || '',
        hasAlt: !!img.alt && img.alt.trim() !== '',
        hasKeyword: img.alt?.toLowerCase().includes(this.targetKeyword) || false,
        score: Math.max(0, Math.min(100, score)),
        issues
      };
    });
  }

  private async detectSchema(html: string): Promise<SchemaAnalysis> {
    const types: string[] = [];
    const properties: Record<string, any> = {};
    const missing: string[] = [];
    let score = 30;

    const jsonLdMatches = html.match(/<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi) || [];
    const microdataMatches = html.match(/itemtype=["']([^"']+)["']/gi) || [];

    for (const match of jsonLdMatches) {
      try {
        const jsonContent = match.replace(/<script[^>]*>/, '').replace(/<\/script>/, '');
        const parsed = JSON.parse(jsonContent);
        if (parsed['@type']) {
          types.push(parsed['@type']);
          Object.assign(properties, parsed);
        }
      } catch (e) {}
    }

    for (const match of microdataMatches) {
      const type = match.match(/itemtype=["']([^"']+)["']/)?.[1];
      if (type && !types.includes(type)) {
        types.push(type.replace('https://schema.org/', ''));
      }
    }

    if (types.length > 0) {
      score += 40;
    } else {
      missing.push('No structured data found');
    }

    const commonTypes = ['Article', 'Product', 'LocalBusiness', 'Organization', 'WebPage'];
    const foundCommon = commonTypes.find(t => types.some(ut => ut.includes(t)));
    if (!foundCommon) {
      missing.push(`Consider adding schema type: ${commonTypes.join(', ')}`);
    }

    return {
      types,
      properties,
      missing,
      score: Math.max(0, Math.min(100, score)),
      jsonLd: jsonLdMatches[0] || ''
    };
  }

  private async generateSuggestions(
    title: string,
    metaDescription: string,
    headings: { level: number; text: string }[],
    paragraphs: string[],
    images: { src: string; alt: string }[]
  ): Promise<Suggestion[]> {
    const suggestions: Suggestion[] = [];

    if (!title || title.length < 30) {
      suggestions.push({
        type: 'warning',
        category: 'Title',
        message: 'Title is too short or missing',
        priority: 1,
        fix: `Create a title between 30-60 characters with the keyword "${this.targetKeyword}"`
      });
    }

    if (!metaDescription || metaDescription.length < 120) {
      suggestions.push({
        type: 'warning',
        category: 'Meta Description',
        message: 'Meta description is too short or missing',
        priority: 2,
        fix: 'Write a compelling meta description between 120-160 characters'
      });
    }

    const h1Count = headings.filter(h => h.level === 1).length;
    if (h1Count === 0) {
      suggestions.push({
        type: 'error',
        category: 'Headings',
        message: 'No H1 heading found',
        priority: 1,
        fix: 'Add an H1 heading containing your primary keyword'
      });
    } else if (h1Count > 1) {
      suggestions.push({
        type: 'warning',
        category: 'Headings',
        message: 'Multiple H1 headings found',
        priority: 2,
        fix: 'Use only one H1 heading per page'
      });
    }

    const hasKeywordInHeadings = headings.some(h => h.text.toLowerCase().includes(this.targetKeyword));
    if (!hasKeywordInHeadings) {
      suggestions.push({
        type: 'info',
        category: 'Keywords',
        message: 'Primary keyword not found in any heading',
        priority: 3,
        fix: `Add "${this.targetKeyword}" to at least one subheading`
      });
    }

    const imagesWithoutAlt = images.filter(i => !i.alt || i.alt.trim() === '');
    if (imagesWithoutAlt.length > 0) {
      suggestions.push({
        type: 'warning',
        category: 'Images',
        message: `${imagesWithoutAlt.length} images missing alt text`,
        priority: 2,
        fix: 'Add descriptive alt text to all images'
      });
    }

    if (paragraphs.length < 2) {
      suggestions.push({
        type: 'warning',
        category: 'Content',
        message: 'Content seems thin',
        priority: 2,
        fix: 'Add more substantial content (at least 3 paragraphs)'
      });
    }

    return suggestions.sort((a, b) => a.priority - b.priority);
  }

  private calculateContentScore(data: {
    title: ContentScore;
    meta: ContentScore;
    headings: HeadingAnalysis[];
    keyword: KeywordAnalysis;
    readability: ReadabilityScore;
    internalLinks: LinkAnalysis;
    externalLinks: LinkAnalysis;
    images: ImageAnalysis[];
    schema: SchemaAnalysis;
  }): { total: number; breakdown: Record<string, number> } {
    const weights = {
      title: 15,
      meta: 10,
      headings: 10,
      keyword: 20,
      readability: 15,
      internalLinks: 8,
      externalLinks: 5,
      images: 7,
      schema: 10
    };

    const breakdown: Record<string, number> = {
      title: data.title.score,
      meta: data.meta.score,
      headings: data.headings.length > 0 ? Math.min(100, data.headings.filter(h => h.containsKeyword).length * 25 + 50) : 50,
      keyword: data.keyword.primary.score,
      readability: data.readability.score,
      internalLinks: data.internalLinks.score,
      externalLinks: data.externalLinks.score,
      images: data.images.length > 0 ? data.images.reduce((sum, img) => sum + img.score, 0) / data.images.length : 50,
      schema: data.schema.score
    };

    const total = Object.entries(weights).reduce((sum, [key, weight]) => {
      return sum + (breakdown[key] || 0) * (weight / 100);
    }, 0);

    return {
      total: Math.round(total),
      breakdown
    };
  }

  private optimizeTitle(title: string): string {
    const optimized = title.length < 30 ? title + ` | ${this.targetKeyword}` : title;
    return optimized.length > 60 ? optimized.substring(0, 57) + '...' : optimized;
  }

  private optimizeMetaDescription(meta: string): string {
    if (meta.length < 120) {
      return `${meta} Learn more about ${this.targetKeyword} and how we can help you.`;
    }
    return meta;
  }

  private generateKeywordVariations(keyword: string): string[] {
    const variations: string[] = [];
    const words = keyword.split(' ');

    if (words.length > 1) {
      variations.push(words.reverse().join(' '));
      variations.push(words.slice(0, -1).join(' '));
    }

    variations.push(keyword + ' guide');
    variations.push(keyword + ' tips');
    variations.push('best ' + keyword);
    variations.push(keyword + ' 2026');

    return [...new Set(variations)];
  }

  private escapeRegex(string: string): string {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
}

export default SEOAnalyzer;