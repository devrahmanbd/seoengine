import axios from 'axios';
import { WebmasterData, SitemapStatus, CrawlError, SearchPerformance, KeywordPerformance } from './types';

export interface GoogleSearchConsoleConfig {
  siteUrl: string;
  accessToken: string;
}

export interface BingWebmasterConfig {
  apiKey: string;
  siteUrl: string;
}

export class GoogleSearchConsoleAPI {
  private accessToken: string;
  private siteUrl: string;
  private baseUrl = 'https://searchconsole.googleapis.com/v1';

  constructor(config: GoogleSearchConsoleConfig) {
    this.accessToken = config.accessToken;
    this.siteUrl = config.siteUrl;
  }

  async getSiteVerification(): Promise<{ ownership: string[]; permissionLevel: string }> {
    try {
      const response = await axios.get(
        `${this.baseUrl}/sites/${encodeURIComponent(this.siteUrl)}`,
        { headers: { Authorization: `Bearer ${this.accessToken}` } }
      );
      return {
        ownership: [response.data.permissionLevel],
        permissionLevel: response.data.permissionLevel
      };
    } catch (error: any) {
      throw new Error(`GSC verification failed: ${error.message}`);
    }
  }

  async submitSitemap(sitemapUrl: string): Promise<{ notificationTime: string }> {
    const sitemapPath = new URL(sitemapUrl).pathname;
    try {
      const response = await axios.put(
        `${this.baseUrl}/sites/${encodeURIComponent(this.siteUrl)}/sitemaps/${encodeURIComponent(sitemapPath)}`,
        {},
        { headers: { Authorization: `Bearer ${this.accessToken}` } }
      );
      return { notificationTime: response.data.notificationTime };
    } catch (error: any) {
      throw new Error(`Sitemap submission failed: ${error.message}`);
    }
  }

  async getSitemaps(): Promise<SitemapStatus[]> {
    try {
      const response = await axios.get(
        `${this.baseUrl}/sites/${encodeURIComponent(this.siteUrl)}/sitemaps`,
        { headers: { Authorization: `Bearer ${this.accessToken}` } }
      );
      
      return (response.data.sitemaps || []).map((s: any) => ({
        url: s.path,
        status: this.mapSitemapStatus(s.contents?.[0]?.state),
        pagesSubmitted: s.contents?.[0]?.submittedToGoogleAs || 0,
        pagesIndexed: s.contents?.[0]?.indexedByGoogle || 0,
        lastSubmitted: new Date(s.lastSubmitted || s.path),
        errors: s.contents?.[0]?.errors || []
      }));
    } catch (error: any) {
      throw new Error(`Failed to get sitemaps: ${error.message}`);
    }
  }

  private mapSitemapStatus(state: string): 'pending' | 'submitted' | 'indexed' | 'error' {
    if (state === 'SUCCESS') return 'indexed';
    if (state === 'PENDING') return 'submitted';
    if (state === 'ERROR') return 'error';
    return 'pending';
  }

  async getCrawlErrors(): Promise<CrawlError[]> {
    try {
      const response = await axios.get(
        `${this.baseUrl}/sites/${encodeURIComponent(this.siteUrl)}/urlCrawlErrorsSamples`,
        { headers: { Authorization: `Bearer ${this.accessToken}` } }
      );
      
      const errors: CrawlError[] = [];
      for (const [url, data] of Object.entries(response.data || {})) {
        const errorData = data as any;
        errors.push({
          url,
          errorType: errorData.latestResponseType || 'UNKNOWN',
          firstDetected: new Date(errorData.firstDetected || Date.now()),
          fixed: errorData.isResolved || false
        });
      }
      return errors.slice(0, 50);
    } catch (error: any) {
      return [];
    }
  }

  async getSearchAnalytics(startDate: string, endDate: string): Promise<SearchPerformance> {
    try {
      const response = await axios.post(
        `${this.baseUrl}/sites/${encodeURIComponent(this.siteUrl)}/searchAnalytics:query`,
        {
          startDate,
          endDate,
          dimensions: ['query'],
          rowLimit: 10
        },
        { headers: { Authorization: `Bearer ${this.accessToken}` } }
      );

      const rows = response.data.rows || [];
      const totalImpressions = rows.reduce((sum: number, r: any) => sum + (r.impressions || 0), 0);
      const totalClicks = rows.reduce((sum: number, r: any) => sum + (r.clicks || 0), 0);
      const avgPosition = rows.length > 0 
        ? rows.reduce((sum: number, r: any) => sum + (r.position || 0), 0) / rows.length 
        : 0;

      return {
        impressions: totalImpressions,
        clicks: totalClicks,
        ctr: totalImpressions > 0 ? (totalClicks / totalImpressions) * 100 : 0,
        avgPosition: Math.round(avgPosition * 10) / 10,
        topQueries: rows.map((r: any) => ({
          query: r.keys[0],
          clicks: r.clicks,
          position: Math.round(r.position * 10) / 10
        }))
      };
    } catch (error: any) {
      throw new Error(`Failed to get search analytics: ${error.message}`);
    }
  }

  async getUrlInspection(url: string): Promise<any> {
    try {
      const response = await axios.get(
        `${this.baseUrl}/sites/${encodeURIComponent(this.siteUrl)}/urlInspection/index`,
        {
          params: { inspectionUrl: url },
          headers: { Authorization: `Bearer ${this.accessToken}` }
        }
      );
      return response.data;
    } catch (error: any) {
      return null;
    }
  }

  async getIndexCoverage(): Promise<{ indexed: number; excluded: number; errors: number; warnings: number }> {
    try {
      const response = await axios.post(
        `${this.baseUrl}/sites/${encodeURIComponent(this.siteUrl)}/urlIndex:query`,
        {
          filter: { type: 'PAGE_IS_INDEXED' }
        },
        { headers: { Authorization: `Bearer ${this.accessToken}` } }
      );

      return {
        indexed: response.data.rowCount || 0,
        excluded: 0,
        errors: 0,
        warnings: 0
      };
    } catch (error: any) {
      return { indexed: 0, excluded: 0, errors: 0, warnings: 0 };
    }
  }

  async getKeywords(): Promise<KeywordPerformance[]> {
    try {
      const today = new Date();
      const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
      
      const response = await axios.post(
        `${this.baseUrl}/sites/${encodeURIComponent(this.siteUrl)}/searchAnalytics:query`,
        {
          startDate: thirtyDaysAgo.toISOString().split('T')[0],
          endDate: today.toISOString().split('T')[0],
          dimensions: ['query'],
          rowLimit: 50
        },
        { headers: { Authorization: `Bearer ${this.accessToken}` } }
      );

      return (response.data.rows || []).map((r: any) => ({
        keyword: r.keys[0],
        clicks: r.clicks || 0,
        impressions: r.impressions || 0,
        ctr: (r.clicks / r.impressions * 100) || 0,
        position: Math.round(r.position * 10) / 10,
        trend: 'stable' as const
      }));
    } catch (error: any) {
      return [];
    }
  }

  async getFullData(): Promise<WebmasterData> {
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    const startDate = thirtyDaysAgo.toISOString().split('T')[0];
    const endDate = today.toISOString().split('T')[0];

    const [sitemaps, crawlErrors, performance, keywords] = await Promise.all([
      this.getSitemaps(),
      this.getCrawlErrors(),
      this.getSearchAnalytics(startDate, endDate),
      this.getKeywords()
    ]);

    return {
      platform: 'google',
      siteUrl: this.siteUrl,
      indexedPages: performance.clicks > 0 ? performance.impressions : 0,
      sitemaps,
      crawlErrors,
      performance,
      keywords,
      lastUpdated: new Date()
    };
  }
}

export class BingWebmasterAPI {
  private apiKey: string;
  private siteUrl: string;
  private baseUrl = 'https://www.bing.com/webmaster/api.svc/json';

  constructor(config: BingWebmasterConfig) {
    this.apiKey = config.apiKey;
    this.siteUrl = config.siteUrl;
  }

  async getSiteInfo(): Promise<{ indexedUrlCount: number;urlCount: number }> {
    try {
      const url = encodeURIComponent(this.siteUrl);
      const response = await axios.get(
        `${this.baseUrl}/GetSiteInfo?siteUrl=${url}&apiKey=${this.apiKey}`
      );
      return {
        indexedUrlCount: response.data.d?.IndexedUrlCount || 0,
        urlCount: response.data.d?.UrlCount || 0
      };
    } catch (error: any) {
      throw new Error(`Bing get site info failed: ${error.message}`);
    }
  }

  async submitSitemap(sitemapUrl: string): Promise<{ message: string }> {
    try {
      const url = encodeURIComponent(this.siteUrl);
      const sitemap = encodeURIComponent(sitemapUrl);
      const response = await axios.get(
        `${this.baseUrl}/SubmitUrl?siteUrl=${url}&url=${sitemap}&apiKey=${this.apiKey}`
      );
      return { message: response.data.d?.Message || 'Submitted' };
    } catch (error: any) {
      throw new Error(`Bing sitemap submission failed: ${error.message}`);
    }
  }

  async getSitemaps(): Promise<SitemapStatus[]> {
    try {
      const url = encodeURIComponent(this.siteUrl);
      const response = await axios.get(
        `${this.baseUrl}/GetSitemaps?siteUrl=${url}&apiKey=${this.apiKey}`
      );

      return (response.data.d?.Sitemaps || []).map((s: any) => ({
        url: s.Path,
        status: s.SubmissionState === 'Success' ? 'indexed' : s.SubmissionState === 'Pending' ? 'submitted' : 'error',
        pagesSubmitted: s.SubmittedUrlCount || 0,
        pagesIndexed: s.IndexedUrlCount || 0,
        lastSubmitted: new Date(s.LastSubmitted || Date.now()),
        errors: s.Errors || []
      }));
    } catch (error: any) {
      return [];
    }
  }

  async getCrawlErrors(): Promise<CrawlError[]> {
    try {
      const url = encodeURIComponent(this.siteUrl);
      const response = await axios.get(
        `${this.baseUrl}/GetCrawlErrors?siteUrl=${url}&apiKey=${this.apiKey}`
      );

      return (response.data.d?.Errors || []).map((e: any) => ({
        url: e.Url,
        errorType: e.ErrorType,
        firstDetected: new Date(e.Date || Date.now()),
        fixed: e.Status === 'Fixed'
      }));
    } catch (error: any) {
      return [];
    }
  }

  async getSearchAnalytics(): Promise<SearchPerformance> {
    try {
      const url = encodeURIComponent(this.siteUrl);
      const response = await axios.get(
        `${this.baseUrl}/GetSearchAnalytics?siteUrl=${url}&apiKey=${this.apiKey}`
      );

      const data = response.data.d || {};
      return {
        impressions: data.Impressions || 0,
        clicks: data.Clicks || 0,
        ctr: data.Ctr * 100 || 0,
        avgPosition: data.AvgPosition || 0,
        topQueries: []
      };
    } catch (error: any) {
      return { impressions: 0, clicks: 0, ctr: 0, avgPosition: 0, topQueries: [] };
    }
  }

  async getKeywords(): Promise<KeywordPerformance[]> {
    try {
      const url = encodeURIComponent(this.siteUrl);
      const response = await axios.get(
        `${this.baseUrl}/GetTopKeywords?siteUrl=${url}&apiKey=${this.apiKey}`
      );

      return (response.data.d || []).map((k: any) => ({
        keyword: k.Keyword || '',
        clicks: k.Clicks || 0,
        impressions: k.Impressions || 0,
        ctr: (k.Clicks / k.Impressions * 100) || 0,
        position: k.Position || 0,
        trend: k.Trend === 'Up' ? 'up' : k.Trend === 'Down' ? 'down' : 'stable'
      }));
    } catch (error: any) {
      return [];
    }
  }

  async getFullData(): Promise<WebmasterData> {
    const [sitemaps, crawlErrors, performance, keywords, siteInfo] = await Promise.all([
      this.getSitemaps(),
      this.getCrawlErrors(),
      this.getSearchAnalytics(),
      this.getKeywords(),
      this.getSiteInfo()
    ]);

    return {
      platform: 'bing',
      siteUrl: this.siteUrl,
      indexedPages: siteInfo.indexedUrlCount,
      sitemaps,
      crawlErrors,
      performance,
      keywords,
      lastUpdated: new Date()
    };
  }
}

export default { GoogleSearchConsoleAPI, BingWebmasterAPI };