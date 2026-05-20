import axios from 'axios';

export interface OAuthConfig {
  clientId: string;
  clientSecret: string;
  redirectUri: string;
}

export interface TokenData {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: Date;
  scope: string;
}

export interface GoogleOAuthTokens {
  access_token: string;
  refresh_token?: string;
  expires_in: number;
  token_type: string;
  scope: string;
}

export interface MicrosoftOAuthTokens {
  access_token: string;
  refresh_token?: string;
  expires_in: number;
  token_type: string;
  scope: string;
}

export class OAuthHandler {
  private config: OAuthConfig;

  constructor(config: OAuthConfig) {
    this.config = config;
  }

  getGoogleAuthUrl(state: string): string {
    const params = new URLSearchParams({
      client_id: this.config.clientId,
      redirect_uri: this.config.redirectUri,
      response_type: 'code',
      scope: [
        'https://www.googleapis.com/auth/webmasters',
        'https://www.googleapis.com/auth/analytics.readonly',
        'https://www.googleapis.com/auth/devstorage.full_control'
      ].join(' '),
      access_type: 'offline',
      prompt: 'consent',
      state
    });

    return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
  }

  getMicrosoftAuthUrl(state: string): string {
    const params = new URLSearchParams({
      client_id: this.config.clientId,
      redirect_uri: this.config.redirectUri,
      response_type: 'code',
      scope: 'https://api.bing.com/webmasterapi https://graph.microsoft.com/User.Read',
      state
    });

    return `https://login.microsoftonline.com/common/oauth2/v2.0/authorize?${params.toString()}`;
  }

  async exchangeGoogleCode(code: string): Promise<TokenData> {
    const response = await axios.post<GoogleOAuthTokens>(
      'https://oauth2.googleapis.com/token',
      {
        code,
        client_id: this.config.clientId,
        client_secret: this.config.clientSecret,
        redirect_uri: this.config.redirectUri,
        grant_type: 'authorization_code'
      }
    );

    return {
      accessToken: response.data.access_token,
      refreshToken: response.data.refresh_token,
      expiresAt: new Date(Date.now() + response.data.expires_in * 1000),
      scope: response.data.scope
    };
  }

  async refreshGoogleToken(refreshToken: string): Promise<TokenData> {
    const response = await axios.post<GoogleOAuthTokens>(
      'https://oauth2.googleapis.com/token',
      {
        refresh_token: refreshToken,
        client_id: this.config.clientId,
        client_secret: this.config.clientSecret,
        grant_type: 'refresh_token'
      }
    );

    return {
      accessToken: response.data.access_token,
      refreshToken: response.data.refresh_token || refreshToken,
      expiresAt: new Date(Date.now() + response.data.expires_in * 1000),
      scope: response.data.scope
    };
  }

  async exchangeMicrosoftCode(code: string): Promise<TokenData> {
    const response = await axios.post<MicrosoftOAuthTokens>(
      'https://login.microsoftonline.com/common/oauth2/v2.0/token',
      new URLSearchParams({
        code,
        client_id: this.config.clientId,
        client_secret: this.config.clientSecret,
        redirect_uri: this.config.redirectUri,
        grant_type: 'authorization_code'
      }),
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      }
    );

    return {
      accessToken: response.data.access_token,
      refreshToken: response.data.refresh_token,
      expiresAt: new Date(Date.now() + response.data.expires_in * 1000),
      scope: response.data.scope
    };
  }

  async refreshMicrosoftToken(refreshToken: string): Promise<TokenData> {
    const response = await axios.post<MicrosoftOAuthTokens>(
      'https://login.microsoftonline.com/common/oauth2/v2.0/token',
      new URLSearchParams({
        refresh_token: refreshToken,
        client_id: this.config.clientId,
        client_secret: this.config.clientSecret,
        grant_type: 'refresh_token'
      }),
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      }
    );

    return {
      accessToken: response.data.access_token,
      refreshToken: response.data.refresh_token || refreshToken,
      expiresAt: new Date(Date.now() + response.data.expires_in * 1000),
      scope: response.data.scope
    };
  }
}

export class GoogleAnalyticsAPI {
  private accessToken: string;
  private propertyId: string;
  private baseUrl = 'https://analyticsdata.googleapis.com/v1beta';

  constructor(accessToken: string, propertyId: string) {
    this.accessToken = accessToken;
    this.propertyId = propertyId;
  }

  async getAnalytics(startDate: string, endDate: string): Promise<any> {
    try {
      const response = await axios.post(
        `${this.baseUrl}/properties/${this.propertyId}:runReport`,
        {
          dateRanges: [{ startDate, endDate }],
          metrics: [
            { name: 'sessions' },
            { name: 'totalUsers' },
            { name: 'screenPageViews' },
            { name: 'bounceRate' },
            { name: 'averageSessionDuration' },
            { name: 'sessionsPerUser' }
          ],
          dimensions: [
            { name: 'country' },
            { name: 'deviceCategory' },
            { name: 'sessionSource' }
          ],
          limit: 20
        },
        {
          headers: { Authorization: `Bearer ${this.accessToken}` }
        }
      );

      return this.parseAnalyticsResponse(response.data);
    } catch (error: any) {
      console.error('GA4 API error:', error.message);
      return null;
    }
  }

  async getPageViews(startDate: string, endDate: string): Promise<{ page: string; views: number }[]> {
    try {
      const response = await axios.post(
        `${this.baseUrl}/properties/${this.propertyId}:runReport`,
        {
          dateRanges: [{ startDate, endDate }],
          metrics: [{ name: 'screenPageViews' }],
          dimensions: [{ name: 'pagePath' }],
          limit: 20
        },
        {
          headers: { Authorization: `Bearer ${this.accessToken}` }
        }
      );

      return (response.data.rows || []).map((row: any) => ({
        page: row.dimensionValues[0].value,
        views: parseInt(row.metricValues[0].value, 10)
      }));
    } catch (error: any) {
      return [];
    }
  }

  async getTrafficSources(): Promise<{ source: string; sessions: number; percentage: number }[]> {
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

    try {
      const response = await axios.post(
        `${this.baseUrl}/properties/${this.propertyId}:runReport`,
        {
          dateRanges: [{ startDate: thirtyDaysAgo.toISOString().split('T')[0], endDate: today.toISOString().split('T')[0] }],
          metrics: [{ name: 'sessions' }],
          dimensions: [{ name: 'sessionSource' }],
          limit: 10
        },
        {
          headers: { Authorization: `Bearer ${this.accessToken}` }
        }
      );

      const totalSessions = response.data.rows?.reduce((sum: number, row: any) => 
        sum + parseInt(row.metricValues[0].value, 10), 0) || 1;

      return (response.data.rows || []).map((row: any) => {
        const sessions = parseInt(row.metricValues[0].value, 10);
        return {
          source: row.dimensionValues[0].value,
          sessions,
          percentage: Math.round((sessions / totalSessions) * 100)
        };
      });
    } catch (error: any) {
      return [];
    }
  }

  private parseAnalyticsResponse(data: any): any {
    const rows = data.rows || [];
    const totals = data.totals?.[0]?.metricValues || [];

    return {
      sessions: parseInt(totals[0]?.value || '0', 10),
      pageviews: parseInt(totals[2]?.value || '0', 10),
      bounceRate: parseFloat(totals[3]?.value || '0'),
      avgSessionDuration: parseFloat(totals[4]?.value || '0'),
      topPages: [],
      trafficSources: [],
      deviceBreakdown: []
    };
  }
}

export { GoogleSearchConsoleAPI, BingWebmasterAPI } from './webmaster-api';

export default { OAuthHandler, GoogleAnalyticsAPI };