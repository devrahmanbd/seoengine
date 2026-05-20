import { TaskGenerator } from './task-generator';
import { GoogleSearchConsoleAPI, BingWebmasterAPI } from './webmaster-api';
import { OAuthHandler, GoogleAnalyticsAPI } from './oauth';
import { DashboardTask, WebmasterData, AnalyticsData, DashboardConfig } from './types';
import { SEOEngine } from '../engine';
import { ContentAnalysis } from '../types';

export interface DashboardState {
  tasks: DashboardTask[];
  googleData: WebmasterData | null;
  bingData: WebmasterData | null;
  analyticsData: AnalyticsData | null;
  config: DashboardConfig;
}

export class SEODashboard {
  private config: DashboardConfig;
  private taskGenerator: TaskGenerator;
  private seoEngine: SEOEngine | null = null;
  private state: DashboardState;

  constructor(config: DashboardConfig) {
    this.config = config;
    this.taskGenerator = new TaskGenerator();
    this.state = {
      tasks: [],
      googleData: null,
      bingData: null,
      analyticsData: null,
      config
    };
  }

  setSEOEngine(engine: SEOEngine): void {
    this.seoEngine = engine;
  }

  async generateTasks(analysis?: ContentAnalysis): Promise<DashboardTask[]> {
    const tasks = this.taskGenerator.generateTasks({
      analysis,
      domain: this.config.googleSearchConsole.siteUrl,
      localBusiness: this.config.localSEO.businessName ? true : false
    });

    this.state.tasks = tasks;
    return tasks;
  }

  async connectGoogleSearchConsole(accessToken: string): Promise<WebmasterData> {
    const gsc = new GoogleSearchConsoleAPI({
      siteUrl: this.config.googleSearchConsole.siteUrl,
      accessToken
    });

    this.state.googleData = await gsc.getFullData();
    return this.state.googleData;
  }

  async connectBingWebmaster(): Promise<WebmasterData> {
    if (!this.config.bingWebmaster.apiKey) {
      throw new Error('Bing API key not configured');
    }

    const bing = new BingWebmasterAPI({
      apiKey: this.config.bingWebmaster.apiKey,
      siteUrl: this.config.bingWebmaster.siteUrl
    });

    this.state.bingData = await bing.getFullData();
    return this.state.bingData;
  }

  async connectGoogleAnalytics(accessToken: string, propertyId: string): Promise<AnalyticsData> {
    const ga = new GoogleAnalyticsAPI(accessToken, propertyId);

    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

    const [analytics, pageViews, trafficSources] = await Promise.all([
      ga.getAnalytics(
        thirtyDaysAgo.toISOString().split('T')[0],
        today.toISOString().split('T')[0]
      ),
      ga.getPageViews(
        thirtyDaysAgo.toISOString().split('T')[0],
        today.toISOString().split('T')[0]
      ),
      ga.getTrafficSources()
    ]);

    this.state.analyticsData = {
      sessions: analytics?.sessions || 0,
      pageviews: analytics?.pageviews || 0,
      bounceRate: analytics?.bounceRate || 0,
      avgSessionDuration: analytics?.avgSessionDuration || 0,
      topPages: pageViews,
      trafficSources,
      deviceBreakdown: []
    };

    return this.state.analyticsData;
  }

  async submitSitemap(sitemapUrl: string, platform: 'google' | 'bing'): Promise<{ success: boolean; message: string }> {
    try {
      if (platform === 'google' && this.state.googleData) {
        const gsc = new GoogleSearchConsoleAPI({
          siteUrl: this.config.googleSearchConsole.siteUrl,
          accessToken: ''
        });
        await gsc.submitSitemap(sitemapUrl);
      } else if (platform === 'bing' && this.state.bingData) {
        const bing = new BingWebmasterAPI({
          apiKey: this.config.bingWebmaster.apiKey,
          siteUrl: this.config.bingWebmaster.siteUrl
        });
        await bing.submitSitemap(sitemapUrl);
      }

      return { success: true, message: 'Sitemap submitted successfully' };
    } catch (error: any) {
      return { success: false, message: error.message };
    }
  }

  getTaskSummary(): { high: number; medium: number; low: number; completed: number } {
    return {
      high: this.state.tasks.filter(t => t.priority === 'high' && t.status !== 'completed').length,
      medium: this.state.tasks.filter(t => t.priority === 'medium' && t.status !== 'completed').length,
      low: this.state.tasks.filter(t => t.priority === 'low' && t.status !== 'completed').length,
      completed: this.state.tasks.filter(t => t.status === 'completed').length
    };
  }

  getRankingSummary(): { totalKeywords: number; topGainers: number; topLosers: number; avgPosition: number } {
    const gscKeywords = this.state.googleData?.keywords || [];
    const bingKeywords = this.state.bingData?.keywords || [];
    const allKeywords = [...gscKeywords, ...bingKeywords];

    const avgPosition = allKeywords.length > 0
      ? allKeywords.reduce((sum, k) => sum + k.position, 0) / allKeywords.length
      : 0;

    return {
      totalKeywords: allKeywords.length,
      topGainers: allKeywords.filter(k => k.trend === 'up').length,
      topLosers: allKeywords.filter(k => k.trend === 'down').length,
      avgPosition: Math.round(avgPosition * 10) / 10
    };
  }

  getIndexingSummary(): { total: number; indexed: number; errors: number; warnings: number } {
    const gscSitemaps = this.state.googleData?.sitemaps || [];
    const bingSitemaps = this.state.bingData?.sitemaps || [];
    const allSitemaps = [...gscSitemaps, ...bingSitemaps];

    return {
      total: allSitemaps.length,
      indexed: allSitemaps.filter(s => s.status === 'indexed').length,
      errors: allSitemaps.filter(s => s.status === 'error').length,
      warnings: allSitemaps.filter(s => s.status === 'submitted').length
    };
  }

  getTrafficSummary(): { sessions: number; pageviews: number; topSource: string; bounceRate: number } {
    const analytics = this.state.analyticsData;
    if (!analytics) {
      return { sessions: 0, pageviews: 0, topSource: 'N/A', bounceRate: 0 };
    }

    const topSource = analytics.trafficSources.length > 0
      ? analytics.trafficSources.sort((a, b) => b.sessions - a.sessions)[0].source
      : 'N/A';

    return {
      sessions: analytics.sessions,
      pageviews: analytics.pageviews,
      topSource,
      bounceRate: Math.round(analytics.bounceRate * 10) / 10
    };
  }

  async analyzeAndRecommend(analysis: ContentAnalysis): Promise<{
    priorityTasks: DashboardTask[];
    aiInsights: string[];
  }> {
    const priorityTasks = this.state.tasks
      .filter(t => t.priority === 'high' && t.status === 'requires_action')
      .slice(0, 5);

    const insights: string[] = [];

    if (analysis.overallScore < 50) {
      insights.push('Your content score is below 50. Focus on basic SEO fundamentals first.');
    }

    if (analysis.readability.score < 50) {
      insights.push('Poor readability is hurting your rankings. Simplify your content.');
    }

    if (analysis.schema.score < 30) {
      insights.push('Add schema markup - this can significantly boost featured snippet chances.');
    }

    const ranking = this.getRankingSummary();
    if (ranking.avgPosition > 20) {
      insights.push(`Average position is ${ranking.avgPosition}. Optimize for Position 0 with PAA content.`);
    }

    if (ranking.topGainers > ranking.topLosers) {
      insights.push('Your rankings are improving. Keep doing what you\'re doing!');
    }

    const traffic = this.getTrafficSummary();
    if (traffic.bounceRate > 70) {
      insights.push(`High bounce rate (${traffic.bounceRate}%). Improve content engagement and page speed.`);
    }

    return { priorityTasks, aiInsights: insights };
  }

  completeTask(taskId: string): void {
    const task = this.state.tasks.find(t => t.id === taskId);
    if (task) {
      task.status = 'completed';
      task.completedAt = new Date();
    }
  }

  getState(): DashboardState {
    return this.state;
  }

  getHTMLDashboard(): string {
    const tasks = this.state.tasks;
    const taskSummary = this.getTaskSummary();
    const ranking = this.getRankingSummary();
    const indexing = this.getIndexingSummary();
    const traffic = this.getTrafficSummary();

    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ZenSEO Dashboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; }
    .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
    .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #06b6d4, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .connect-btns { display: flex; gap: 10px; }
    .btn { padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; transition: all 0.2s; }
    .btn-google { background: #4285f4; color: white; }
    .btn-bing { background: #00809d; color: white; }
    .btn-analytics { background: #f59e0b; color: black; }
    .btn:hover { transform: translateY(-2px); filter: brightness(1.1); }
    
    .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
    .card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
    .card-title { font-size: 14px; color: #94a3b8; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
    .card-value { font-size: 32px; font-weight: 700; }
    .card-sub { font-size: 14px; color: #64748b; margin-top: 5px; }
    
    .positive { color: #10b981; }
    .negative { color: #ef4444; }
    .neutral { color: #f59e0b; }
    
    .section { margin-bottom: 30px; }
    .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .section-title { font-size: 20px; font-weight: 600; }
    
    .tasks-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
    .task-card { background: #1e293b; border-radius: 10px; padding: 15px; border-left: 4px solid; }
    .task-card.high { border-color: #ef4444; }
    .task-card.medium { border-color: #f59e0b; }
    .task-card.low { border-color: #10b981; }
    .task-card.completed { border-color: #64748b; opacity: 0.6; }
    .task-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
    .task-title { font-weight: 600; font-size: 15px; }
    .task-priority { font-size: 11px; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }
    .task-priority.high { background: #fee2e2; color: #dc2626; }
    .task-priority.medium { background: #fef3c7; color: #d97706; }
    .task-priority.low { background: #d1fae5; color: #059669; }
    .task-desc { font-size: 13px; color: #94a3b8; margin-bottom: 10px; }
    .task-instructions { font-size: 12px; color: #64748b; padding: 10px; background: #0f172a; border-radius: 6px; white-space: pre-wrap; }
    .task-actions { display: flex; gap: 10px; margin-top: 10px; }
    .btn-small { padding: 6px 12px; font-size: 12px; border-radius: 6px; border: none; cursor: pointer; }
    .btn-complete { background: #10b981; color: white; }
    .btn-skip { background: #475569; color: white; }
    
    .platform-section { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px; }
    .platform-card { background: #1e293b; border-radius: 12px; padding: 20px; }
    .platform-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
    .platform-logo { width: 32px; height: 32px; border-radius: 8px; }
    .platform-name { font-size: 18px; font-weight: 600; }
    .metric-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #334155; }
    .metric-label { color: #94a3b8; }
    .metric-value { font-weight: 600; }
    
    .keywords-table { width: 100%; border-collapse: collapse; }
    .keywords-table th { text-align: left; padding: 12px; background: #0f172a; border-bottom: 2px solid #334155; color: #94a3b8; font-size: 12px; }
    .keywords-table td { padding: 12px; border-bottom: 1px solid #334155; font-size: 14px; }
    .position-cell { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: 600; }
    .position-good { background: #d1fae5; color: #059669; }
    .position-warning { background: #fef3c7; color: #d97706; }
    .position-bad { background: #fee2e2; color: #dc2626; }
    
    .tab-container { margin-bottom: 20px; }
    .tab { padding: 10px 20px; background: transparent; border: none; color: #94a3b8; cursor: pointer; font-size: 14px; border-bottom: 2px solid transparent; }
    .tab.active { color: #06b6d4; border-color: #06b6d4; }
    
    .insight-box { background: linear-gradient(135deg, #1e293b, #334155); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .insight-title { font-size: 16px; font-weight: 600; margin-bottom: 10px; color: #06b6d4; }
    .insight-list { list-style: none; }
    .insight-list li { padding: 8px 0; border-bottom: 1px solid #475569; }
    .insight-list li:last-child { border: none; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">⚡ ZenSEO Dashboard</div>
      <div class="connect-btns">
        <button class="btn btn-google" onclick="connectGoogle()">🔗 Connect Google</button>
        <button class="btn btn-bing" onclick="connectBing()">🔗 Connect Bing</button>
        <button class="btn btn-analytics" onclick="connectAnalytics()">📊 Connect Analytics</button>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="card-title">📈 Traffic (30d)</div>
        <div class="card-value">${traffic.sessions.toLocaleString()}</div>
        <div class="card-sub">${traffic.pageviews.toLocaleString()} pageviews • ${traffic.bounceRate}% bounce</div>
      </div>
      <div class="card">
        <div class="card-title">🔍 Rankings</div>
        <div class="card-value">${ranking.totalKeywords}</div>
        <div class="card-sub">Avg pos: ${ranking.avgPosition} • ${ranking.topGainers}↑ ${ranking.topLosers}↓</div>
      </div>
      <div class="card">
        <div class="card-title">📋 Tasks</div>
        <div class="card-value">${taskSummary.high + taskSummary.medium + taskSummary.low}</div>
        <div class="card-sub">${taskSummary.completed} completed • ${taskSummary.high} high priority</div>
      </div>
      <div class="card">
        <div class="card-title">🕷️ Indexing</div>
        <div class="card-value">${indexing.indexed}</div>
        <div class="card-sub">${indexing.errors} errors • ${indexing.warnings} warnings</div>
      </div>
    </div>

    <div class="insight-box">
      <div class="insight-title">🤖 AI Insights & Recommendations</div>
      <ul class="insight-list">
        <li>🔍 Submit your sitemap to Google Search Console if not done yet</li>
        <li>📝 High-priority task: Fix ${taskSummary.high} critical SEO issues</li>
        <li>📈 Your average ranking position is ${ranking.avgPosition} - target Position < 10</li>
        <li>⚡ Check Core Web Vitals in Google Search Console for technical issues</li>
      </ul>
    </div>

    <div class="tab-container">
      <button class="tab active" onclick="showTab('tasks')">📋 Tasks</button>
      <button class="tab" onclick="showTab('google')">🔍 Google</button>
      <button class="tab" onclick="showTab('bing')">📊 Bing</button>
      <button class="tab" onclick="showTab('analytics')">📈 Analytics</button>
    </div>

    <div id="tab-tasks">
      <div class="tasks-grid">
        ${tasks.slice(0, 10).map(task => `
          <div class="task-card ${task.priority}">
            <div class="task-header">
              <div class="task-title">${task.title}</div>
              <span class="task-priority ${task.priority}">${task.priority}</span>
            </div>
            <div class="task-desc">${task.description}</div>
            <div class="task-instructions">${task.instructions.substring(0, 200)}...</div>
            <div class="task-actions">
              <button class="btn-small btn-complete" onclick="completeTask('${task.id}')">✓ Complete</button>
              <button class="btn-small btn-skip" onclick="skipTask('${task.id}')">Skip</button>
            </div>
          </div>
        `).join('')}
      </div>
    </div>

    <div id="tab-google" style="display:none;">
      <div class="platform-section">
        <div class="platform-card">
          <div class="platform-header">
            <div class="platform-logo" style="background: #4285f4;"></div>
            <div class="platform-name">Google Search Console</div>
          </div>
          <div class="metric-row"><span class="metric-label">Indexed Pages</span><span class="metric-value">${this.state.googleData?.indexedPages || 0}</span></div>
          <div class="metric-row"><span class="metric-label">Impressions</span><span class="metric-value">${(this.state.googleData?.performance?.impressions || 0).toLocaleString()}</span></div>
          <div class="metric-row"><span class="metric-label">Clicks</span><span class="metric-value">${(this.state.googleData?.performance?.clicks || 0).toLocaleString()}</span></div>
          <div class="metric-row"><span class="metric-label">CTR</span><span class="metric-value">${(this.state.googleData?.performance?.ctr || 0).toFixed(2)}%</span></div>
          <div class="metric-row"><span class="metric-label">Avg Position</span><span class="metric-value">${this.state.googleData?.performance?.avgPosition || 0}</span></div>
        </div>
      </div>
      <h3 style="margin: 20px 0;">Top Keywords</h3>
      <table class="keywords-table">
        <thead><tr><th>Keyword</th><th>Clicks</th><th>Impressions</th><th>Position</th><th>CTR</th></tr></thead>
        <tbody>
          ${(this.state.googleData?.keywords || []).slice(0, 10).map(kw => `
            <tr>
              <td>${kw.keyword}</td>
              <td>${kw.clicks}</td>
              <td>${kw.impressions}</td>
              <td><span class="position-cell ${kw.position <= 10 ? 'position-good' : kw.position <= 20 ? 'position-warning' : 'position-bad'}">${kw.position}</span></td>
              <td>${kw.ctr.toFixed(1)}%</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>

    <div id="tab-bing" style="display:none;">
      <div class="platform-section">
        <div class="platform-card">
          <div class="platform-header">
            <div class="platform-logo" style="background: #00809d;"></div>
            <div class="platform-name">Bing Webmaster</div>
          </div>
          <div class="metric-row"><span class="metric-label">Indexed Pages</span><span class="metric-value">${this.state.bingData?.indexedPages || 0}</span></div>
          <div class="metric-row"><span class="metric-label">Impressions</span><span class="metric-value">${(this.state.bingData?.performance?.impressions || 0).toLocaleString()}</span></div>
          <div class="metric-row"><span class="metric-label">Clicks</span><span class="metric-value">${(this.state.bingData?.performance?.clicks || 0).toLocaleString()}</span></div>
          <div class="metric-row"><span class="metric-label">Avg Position</span><span class="metric-value">${this.state.bingData?.performance?.avgPosition || 0}</span></div>
        </div>
      </div>
      <h3 style="margin: 20px 0;">Top Keywords</h3>
      <table class="keywords-table">
        <thead><tr><th>Keyword</th><th>Clicks</th><th>Impressions</th><th>Position</th><th>Trend</th></tr></thead>
        <tbody>
          ${(this.state.bingData?.keywords || []).slice(0, 10).map(kw => `
            <tr>
              <td>${kw.keyword}</td>
              <td>${kw.clicks}</td>
              <td>${kw.impressions}</td>
              <td><span class="position-cell ${kw.position <= 10 ? 'position-good' : kw.position <= 20 ? 'position-warning' : 'position-bad'}">${kw.position}</span></td>
              <td>${kw.trend === 'up' ? '📈' : kw.trend === 'down' ? '📉' : '➡️'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>

    <div id="tab-analytics" style="display:none;">
      <div class="platform-section">
        <div class="platform-card">
          <div class="platform-header">
            <div class="platform-logo" style="background: #f59e0b;"></div>
            <div class="platform-name">Google Analytics</div>
          </div>
          <div class="metric-row"><span class="metric-label">Sessions</span><span class="metric-value">${this.state.analyticsData?.sessions || 0}</span></div>
          <div class="metric-row"><span class="metric-label">Page Views</span><span class="metric-value">${this.state.analyticsData?.pageviews || 0}</span></div>
          <div class="metric-row"><span class="metric-label">Bounce Rate</span><span class="metric-value">${this.state.analyticsData?.bounceRate?.toFixed(1) || 0}%</span></div>
          <div class="metric-row"><span class="metric-label">Avg Duration</span><span class="metric-value">${Math.round(this.state.analyticsData?.avgSessionDuration || 0)}s</span></div>
        </div>
      </div>
      <h3 style="margin: 20px 0;">Traffic Sources</h3>
      <table class="keywords-table">
        <thead><tr><th>Source</th><th>Sessions</th><th>%</th></tr></thead>
        <tbody>
          ${(this.state.analyticsData?.trafficSources || []).map(ts => `
            <tr>
              <td>${ts.source}</td>
              <td>${ts.sessions}</td>
              <td>${ts.percentage}%</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  </div>

  <script>
    function showTab(tab) {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      event.target.classList.add('active');
      ['tasks', 'google', 'bing', 'analytics'].forEach(t => {
        document.getElementById('tab-' + t).style.display = t === tab ? 'block' : 'none';
      });
    }

    function connectGoogle() { window.location.href = '/auth/google'; }
    function connectBing() { window.location.href = '/auth/microsoft'; }
    function connectAnalytics() { window.location.href = '/auth/analytics'; }
    function completeTask(id) { fetch('/api/task/complete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}) }).then(() => location.reload()); }
    function skipTask(id) { fetch('/api/task/skip', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id}) }).then(() => location.reload()); }
  </script>
</body>
</html>
    `;
  }
}

export default SEODashboard;