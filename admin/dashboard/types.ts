export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'requires_action' | 'blocked';
export type TaskCategory = 'technical' | 'content' | 'local' | 'link_building' | 'analytics' | 'webmaster';
export type TaskPriority = 'high' | 'medium' | 'low';

export interface DashboardTask {
  id: string;
  title: string;
  description: string;
  category: TaskCategory;
  priority: TaskPriority;
  status: TaskStatus;
  instructions: string;
  estimatedTime: string;
  tools: string[];
  completedAt?: Date;
  createdAt: Date;
  dueDate?: Date;
}

export interface WebmasterData {
  platform: 'google' | 'bing';
  siteUrl: string;
  indexedPages: number;
  sitemaps: SitemapStatus[];
  crawlErrors: CrawlError[];
  performance: SearchPerformance;
  keywords: KeywordPerformance[];
  lastUpdated: Date;
}

export interface SitemapStatus {
  url: string;
  status: 'pending' | 'submitted' | 'indexed' | 'error';
  pagesSubmitted: number;
  pagesIndexed: number;
  lastSubmitted: Date;
  errors: string[];
}

export interface CrawlError {
  url: string;
  errorType: string;
  firstDetected: Date;
  fixed: boolean;
}

export interface SearchPerformance {
  impressions: number;
  clicks: number;
  ctr: number;
  avgPosition: number;
  topQueries: { query: string; clicks: number; position: number }[];
}

export interface KeywordPerformance {
  keyword: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
  trend: 'up' | 'down' | 'stable';
}

export interface LocalSEOTask {
  id: string;
  businessName: string;
  category: TaskCategory;
  task: string;
  action: string;
  platform: 'google_business' | 'apple_maps' | 'bing_places' | 'yelp' | 'local_citations';
  status: TaskStatus;
  dueDate?: Date;
}

export interface AnalyticsData {
  sessions: number;
  pageviews: number;
  bounceRate: number;
  avgSessionDuration: number;
  topPages: { page: string; views: number }[];
  trafficSources: { source: string; sessions: number; percentage: number }[];
  deviceBreakdown: { device: string; sessions: number; percentage: number }[];
}

export interface DashboardConfig {
  googleSearchConsole: {
    enabled: boolean;
    siteUrl: string;
    apiKey?: string;
  };
  bingWebmaster: {
    enabled: boolean;
    apiKey: string;
    siteUrl: string;
  };
  localSEO: {
    businessName: string;
    locations: string[];
  };
  analytics: {
    propertyId?: string;
    apiSecret?: string;
  };
  autoGenerateTasks: boolean;
  notificationEmail?: string;
}