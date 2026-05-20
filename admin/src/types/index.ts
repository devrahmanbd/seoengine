export interface ContentAnalysis {
  title: ContentScore;
  metaDescription: ContentScore;
  headings: HeadingAnalysis[];
  keywordAnalysis: KeywordAnalysis;
  contentScore: { total: number; breakdown: Record<string, number> };
  readability: ReadabilityScore;
  internalLinks: LinkAnalysis;
  outboundLinks: LinkAnalysis;
  images: ImageAnalysis[];
  schema: SchemaAnalysis;
  suggestions: Suggestion[];
  overallScore: number;
}

export interface ContentScore {
  score: number;
  raw: string;
  optimized: string;
  issues: string[];
  suggestions: string[];
}

export interface HeadingAnalysis {
  level: number;
  text: string;
  containsKeyword: boolean;
  keyword: string;
}

export interface KeywordAnalysis {
  primary: KeywordScore;
  secondary: KeywordScore[];
  density: number;
  placement: KeywordPlacement;
  variations: string[];
}

export interface KeywordScore {
  keyword: string;
  count: number;
  density: number;
  score: number;
}

export interface KeywordPlacement {
  title: boolean;
  firstParagraph: boolean;
  headings: boolean;
  lastParagraph: boolean;
  altText: boolean;
}

export interface ReadabilityScore {
  fleschKincaid: number;
  fleschKincaidGrade: number;
  GunningFog: number;
  ColemanLiau: number;
  automatedReadability: number;
  avgSentenceLength: number;
  avgWordLength: number;
  totalSentences: number;
  totalWords: number;
  totalSyllables: number;
  score: number;
  grade: string;
}

export interface LinkAnalysis {
  count: number;
  internal: Link[];
  external: Link[];
  score: number;
  issues: string[];
}

export interface Link {
  url: string;
  text: string;
  isFollow: boolean;
  isExternal: boolean;
}

export interface ImageAnalysis {
  src: string;
  alt: string;
  hasAlt: boolean;
  hasKeyword: boolean;
  score: number;
  issues: string[];
}

export interface SchemaAnalysis {
  types: string[];
  properties: Record<string, any>;
  missing: string[];
  score: number;
  jsonLd: string;
}

export interface Suggestion {
  type: 'error' | 'warning' | 'info' | 'success';
  category: string;
  message: string;
  priority: number;
  fix?: string;
}

export interface SEOReport {
  url: string;
  title: string;
  description: string;
  keyword: string;
  analysis: ContentAnalysis;
  timestamp: Date;
}

export interface KeywordData {
  keyword: string;
  volume: number;
  difficulty: number;
  cpc: number;
  competition: number;
  trends: number[];
  relatedKeywords: string[];
  intent: 'informational' | 'transactional' | 'navigational' | 'commercial';
}

export interface SEOConfig {
  openaiApiKey: string;
  semrushApiKey?: string;
  targetKeyword?: string;
  contentType?: 'blog' | 'product' | 'landing' | 'service' | 'faq';
  primaryLanguage?: string;
  country?: string;
  schemaTypes?: string[];
}

export interface BatchAnalysis {
  id: string;
  urls: string[];
  status: 'pending' | 'processing' | 'completed' | 'failed';
  results: SEOReport[];
  errors: string[];
  createdAt: Date;
  completedAt?: Date;
}

export interface CSVRow {
  url: string;
  title?: string;
  metaDescription?: string;
  keyword?: string;
  targetKeyword?: string;
  [key: string]: any;
}

export interface OptimizationResult {
  original: string;
  optimized: string;
  changes: Change[];
  scoreBefore: number;
  scoreAfter: number;
}

export interface Change {
  type: 'add' | 'remove' | 'modify';
  element: string;
  before: string;
  after: string;
}

export interface GrowthState {
  website_id: string;
  growth_score: number;
  trend: 'accelerating' | 'decelerating' | 'plateauing' | 'declining' | 'unknown';
  trajectory_count: number;
  avg_reward: number;
  score_history: number[];
  action_effectiveness: Record<string, { count: number; avg_reward: number }>;
}

export interface Opportunity {
  action_type: string;
  expected_reward: number;
  confidence: 'high' | 'medium' | 'low';
  source: 'policy' | 'cross_site' | 'heuristic';
  effort: 'low' | 'medium' | 'high';
  description: string;
  evidence: string[];
}

export interface ScheduledAction {
  action_type: string;
  expected_reward: number;
  confidence: string;
  source: string;
  effort: string;
  description: string;
  priority_score: number;
  scheduled_at: string | null;
  status: 'pending' | 'scheduled' | 'in_progress' | 'completed' | 'failed';
}