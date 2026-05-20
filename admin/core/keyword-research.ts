import natural from 'natural';
import compromise from 'compromise';

export interface KeywordCluster {
  primary: string;
  keywords: string[];
  volume: number;
  difficulty: number;
}

export interface KeywordSuggestion {
  keyword: string;
  volume: number;
  difficulty: number;
  intent: string;
  score: number;
}

export class KeywordResearch {
  private tokenizer: natural.WordTokenizer;
  private TfIdf: typeof natural.TfIdf;

  constructor() {
    this.tokenizer = new natural.WordTokenizer();
    this.TfIdf = natural.TfIdf;
  }

  analyzeKeyword(keyword: string): {
    length: number;
    wordCount: number;
    difficulty: 'easy' | 'medium' | 'hard';
    type: 'short-tail' | 'mid-tail' | 'long-tail';
    question: boolean;
  } {
    const words = keyword.split(/\s+/);
    const length = keyword.length;
    const wordCount = words.length;

    let type: 'short-tail' | 'mid-tail' | 'long-tail' = 'short-tail';
    if (wordCount >= 4) type = 'long-tail';
    else if (wordCount >= 2) type = 'mid-tail';

    const question = ['what', 'how', 'why', 'when', 'where', 'which', 'who'].some(w =>
      keyword.toLowerCase().startsWith(w)
    ) || keyword.endsWith('?');

    let difficulty: 'easy' | 'medium' | 'hard' = 'medium';
    if (wordCount <= 2 && length <= 12) difficulty = 'hard';
    else if (wordCount >= 4 || length >= 30) difficulty = 'easy';

    return { length, wordCount, difficulty, type, question };
  }

  extractKeywordsFromContent(content: string, maxKeywords: number = 20): string[] {
    const doc = compromise(content);
    const nouns = doc.nouns().toSingular().out('array') as string[];

    const tfidf = new this.TfIdf();
    tfidf.addDocument(content);

    const wordCounts: Record<string, number> = {};
    const words = content.toLowerCase().split(/\s+/);

    const stopWords = new Set([
      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
      'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had',
      'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
      'shall', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
      'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each',
      'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not',
      'only', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there'
    ]);

    words.forEach(word => {
      const cleaned = word.replace(/[^a-z0-9]/g, '');
      if (cleaned.length > 3 && !stopWords.has(cleaned)) {
        wordCounts[cleaned] = (wordCounts[cleaned] || 0) + 1;
      }
    });

    return Object.entries(wordCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, maxKeywords)
      .map(([word]) => word);
  }

  clusterKeywords(keywords: { keyword: string; volume: number; difficulty: number }[]): KeywordCluster[] {
    const clusters: KeywordCluster[] = [];
    const used = new Set<string>();

    for (const kw of keywords) {
      if (used.has(kw.keyword)) continue;

      const clusterKeywords = [kw.keyword];
      const primaryWords = kw.keyword.split(/\s+/);

      for (const other of keywords) {
        if (used.has(other.keyword) || other.keyword === kw.keyword) continue;

        const otherWords = other.keyword.split(/\s+/);
        const overlap = primaryWords.filter(w => otherWords.includes(w)).length;

        if (overlap >= Math.min(primaryWords.length, otherWords.length) * 0.5) {
          clusterKeywords.push(other.keyword);
          used.add(other.keyword);
        }
      }

      used.add(kw.keyword);

      clusters.push({
        primary: kw.keyword,
        keywords: clusterKeywords,
        volume: clusterKeywords.reduce((sum, k) => {
          const found = keywords.find(pk => pk.keyword === k);
          return sum + (found?.volume || 0);
        }, 0),
        difficulty: Math.round(clusterKeywords.reduce((sum, k) => {
          const found = keywords.find(pk => pk.keyword === k);
          return sum + (found?.difficulty || 0);
        }, 0) / clusterKeywords.length)
      });
    }

    return clusters.sort((a, b) => b.volume - a.volume);
  }

  generateKeywordVariations(seedKeyword: string): string[] {
    const variations: string[] = [seedKeyword];

    const prefixes = ['best', 'top', 'how to', 'what is', 'guide to', 'tips for', 'review of', 'vs'];
    const suffixes = ['2026', 'for beginners', 'examples', 'tutorial', 'pricing', 'free', 'online', 'near me'];

    prefixes.forEach(prefix => {
      if (!seedKeyword.toLowerCase().startsWith(prefix)) {
        variations.push(`${prefix} ${seedKeyword}`);
      }
    });

    suffixes.forEach(suffix => {
      if (!seedKeyword.toLowerCase().endsWith(suffix)) {
        variations.push(`${seedKeyword} ${suffix}`);
      }
    });

    const words = seedKeyword.split(/\s+/);
    if (words.length > 1) {
      variations.push(words.slice(0, -1).join(' '));
      variations.push(words.slice(1).join(' '));
      variations.push(words.reverse().join(' '));
    }

    return [...new Set(variations)];
  }

  calculateKeywordDifficulty(keyword: string, competitiveKeywords: string[]): number {
    const keywordWords = keyword.toLowerCase().split(/\s+/);
    let score = 50;

    if (keywordWords.length <= 2) {
      score += 20;
    } else if (keywordWords.length >= 4) {
      score -= 15;
    }

    const overlap = competitiveKeywords.filter(kw =>
      keywordWords.some(w => kw.toLowerCase().includes(w))
    ).length;

    if (overlap > 10) score += 20;
    else if (overlap > 5) score += 10;
    else if (overlap > 0) score -= 5;

    return Math.max(0, Math.min(100, score));
  }

  determineSearchIntent(keyword: string): 'informational' | 'transactional' | 'navigational' | 'commercial' {
    const lower = keyword.toLowerCase();

    const transactional = ['buy', 'purchase', 'order', 'price', 'cost', 'shop', 'discount', 'deal', 'coupon', 'cheap', 'rent', 'hire'];
    const commercial = ['best', 'top', 'review', 'compare', 'vs', 'alternatives', 'software', 'service', 'tool'];
    const navigational = ['login', 'sign in', 'app', 'download', 'official', 'website', 'home'];

    if (transactional.some(w => lower.includes(w))) return 'transactional';
    if (commercial.some(w => lower.includes(w))) return 'commercial';
    if (navigational.some(w => lower.includes(w))) return 'navigational';

    return 'informational';
  }

  scoreKeywords(keywords: { keyword: string; volume: number; difficulty: number }[]): KeywordSuggestion[] {
    return keywords.map(kw => {
      const analysis = this.analyzeKeyword(kw.keyword);
      const intent = this.determineSearchIntent(kw.keyword);

      let score = 50;

      if (kw.volume > 10000) score += 20;
      else if (kw.volume > 1000) score += 10;
      else if (kw.volume > 100) score += 5;

      if (kw.difficulty < 30) score += 15;
      else if (kw.difficulty < 50) score += 10;
      else if (kw.difficulty > 70) score -= 10;

      if (analysis.type === 'long-tail') score += 10;
      if (analysis.question) score += 5;

      if (intent === 'transactional') score += 10;
      else if (intent === 'commercial') score += 5;

      return {
        keyword: kw.keyword,
        volume: kw.volume,
        difficulty: kw.difficulty,
        intent,
        score: Math.max(0, Math.min(100, score))
      };
    }).sort((a, b) => b.score - a.score);
  }
}

export default KeywordResearch;