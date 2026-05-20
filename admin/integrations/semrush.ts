import axios from 'axios';
import { KeywordData } from '../types';

export class SEMrushAPI {
  private apiKey: string;
  private baseUrl = 'https://api.semrush.com';

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async getKeywordOverview(keyword: string, database: string = 'us'): Promise<KeywordData> {
    try {
      const url = `${this.baseUrl}/?type=phrase_all&key=${this.apiKey}&phrase=${encodeURIComponent(keyword)}&database=${database}`;
      const response = await axios.get(url);

      if (response.data && response.data.length > 0) {
        return this.parseKeywordData(response.data[0], keyword);
      }

      return this.createEmptyKeywordData(keyword);
    } catch (error: any) {
      console.error('SEMrush API error:', error.message);
      return this.createEmptyKeywordData(keyword);
    }
  }

  async getRelatedKeywords(keyword: string, database: string = 'us', limit: number = 10): Promise<string[]> {
    try {
      const url = `${this.baseUrl}/?type=phrase_related&key=${this.apiKey}&phrase=${encodeURIComponent(keyword)}&database=${database}&display_limit=${limit}`;
      const response = await axios.get(url);

      if (response.data && Array.isArray(response.data)) {
        return response.data.slice(1).map((row: any) => row[0]);
      }

      return [];
    } catch (error: any) {
      console.error('SEMrush related keywords error:', error.message);
      return [];
    }
  }

  async getKeywordDifficult(keyword: string, database: string = 'us'): Promise<number> {
    try {
      const url = `${this.baseUrl}/?type=phrase_kdi&key=${this.apiKey}&phrase=${encodeURIComponent(keyword)}&database=${database}`;
      const response = await axios.get(url);

      if (response.data && response.data.length > 0) {
        return parseFloat(response.data[0]?.[1]) || 0;
      }

      return 0;
    } catch (error: any) {
      console.error('SEMrush KDI error:', error.message);
      return 0;
    }
  }

  async getKeywordVolume(keyword: string, database: string = 'us'): Promise<number> {
    try {
      const url = `${this.baseUrl}/?type=phrase_all&key=${this.apiKey}&phrase=${encodeURIComponent(keyword)}&database=${database}`;
      const response = await axios.get(url);

      if (response.data && response.data.length > 0) {
        const volume = response.data[0]?.[2];
        return volume ? parseInt(volume.replace(/,/g, ''), 10) : 0;
      }

      return 0;
    } catch (error: any) {
      console.error('SEMrush volume error:', error.message);
      return 0;
    }
  }

  async getCPC(keyword: string, database: string = 'us'): Promise<number> {
    try {
      const url = `${this.baseUrl}/?type=phrase_all&key=${this.apiKey}&phrase=${encodeURIComponent(keyword)}&database=${database}`;
      const response = await axios.get(url);

      if (response.data && response.data.length > 0) {
        return parseFloat(response.data[0]?.[3]) || 0;
      }

      return 0;
    } catch (error: any) {
      console.error('SEMrush CPC error:', error.message);
      return 0;
    }
  }

  async getTrends(keyword: string, database: string = 'us'): Promise<number[]> {
    try {
      const url = `${this.baseUrl}/?type=phrase_trends&key=${this.apiKey}&phrase=${encodeURIComponent(keyword)}&database=${database}`;
      const response = await axios.get(url);

      if (response.data && response.data.length > 0 && response.data[0]?.['Monthly Searches']) {
        const monthlyData = response.data[0]['Monthly Searches'];
        return monthlyData.split(';').map((s: string) => parseInt(s, 10) || 0);
      }

      return Array(12).fill(0);
    } catch (error: any) {
      console.error('SEMrush trends error:', error.message);
      return Array(12).fill(0);
    }
  }

  async analyzeCompetitorDomains(domains: string[], database: string = 'us'): Promise<{
    domain: string;
    organicKeywords: number;
    traffic: number;
    trafficCost: number;
  }[]> {
    const results = [];

    for (const domain of domains) {
      try {
        const url = `${this.baseUrl}/?type=domain_organic&key=${this.apiKey}&domain=${encodeURIComponent(domain)}&database=${database}`;
        const response = await axios.get(url);

        if (response.data && response.data.length > 0) {
          results.push({
            domain,
            organicKeywords: parseInt(response.data[0]?.[1]?.replace(/,/g, ''), 10) || 0,
            traffic: parseInt(response.data[0]?.[4]?.replace(/,/g, ''), 10) || 0,
            trafficCost: parseFloat(response.data[0]?.[5]?.replace(/,/g, '')) || 0
          });
        }
      } catch (error: any) {
        console.error(`SEMrush competitor analysis error for ${domain}:`, error.message);
      }
    }

    return results;
  }

  async getFullKeywordAnalysis(keyword: string, database: string = 'us'): Promise<KeywordData> {
    const [overview, related, difficulty, cpc, trends] = await Promise.all([
      this.getKeywordOverview(keyword, database),
      this.getRelatedKeywords(keyword, database),
      this.getKeywordDifficult(keyword, database),
      this.getCPC(keyword, database),
      this.getTrends(keyword, database)
    ]);

    return {
      ...overview,
      relatedKeywords: related,
      difficulty,
      cpc,
      trends
    };
  }

  private parseKeywordData(data: any, keyword: string): KeywordData {
    const volume = data[2] ? parseInt(data[2].replace(/,/g, ''), 10) : 0;
    const cpcValue = data[3] ? parseFloat(data[3]) : 0;
    const competition = data[4] ? parseFloat(data[4]) : 0;
    const numberOfResults = data[5] ? parseInt(data[5].replace(/,/g, ''), 10) : 0;

    return {
      keyword,
      volume,
      difficulty: numberOfResults > 0 ? Math.min(100, (numberOfResults / 10000000) * 100) : 0,
      cpc: cpcValue,
      competition,
      trends: Array(12).fill(volume),
      relatedKeywords: [],
      intent: this.determineIntent(keyword)
    };
  }

  private createEmptyKeywordData(keyword: string): KeywordData {
    return {
      keyword,
      volume: 0,
      difficulty: 0,
      cpc: 0,
      competition: 0,
      trends: Array(12).fill(0),
      relatedKeywords: [],
      intent: 'informational'
    };
  }

  private determineIntent(keyword: string): 'informational' | 'transactional' | 'navigational' | 'commercial' {
    const lower = keyword.toLowerCase();
    
    if (lower.includes('buy') || lower.includes('purchase') || lower.includes('order') || lower.includes('price') || 
        lower.includes('cost') || lower.includes('cheap') || lower.includes('discount') || lower.includes('deal') || 
        lower.includes('shop')) {
      return 'transactional';
    }
    
    if (lower.includes('best') || lower.includes('top') || lower.includes('review') || lower.includes('compare') || 
        lower.includes('vs') || lower.includes('alternative') || lower.includes('software') || lower.includes('service')) {
      return 'commercial';
    }
    
    if (lower.includes('login') || lower.includes('signin') || lower.includes('app') || lower.includes('download') || 
        lower.includes('website') || lower.includes('official')) {
      return 'navigational';
    }
    
    return 'informational';
  }
}

export default SEMrushAPI;