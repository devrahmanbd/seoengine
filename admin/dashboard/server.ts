import express from 'express';
import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';
import { SEODashboard } from './engine';
import { OAuthHandler } from './oauth';
import { DashboardConfig, DashboardTask } from './types';
import { SEOEngine } from '../engine';

dotenv.config();

const app = express();
app.use(express.json());

const config: DashboardConfig = {
  googleSearchConsole: {
    enabled: !!process.env.GOOGLE_CLIENT_ID,
    siteUrl: process.env.SITE_URL || 'https://example.com',
    apiKey: process.env.GOOGLE_API_KEY
  },
  bingWebmaster: {
    enabled: !!process.env.BING_API_KEY,
    apiKey: process.env.BING_API_KEY || '',
    siteUrl: process.env.SITE_URL || 'https://example.com'
  },
  localSEO: {
    businessName: process.env.BUSINESS_NAME || '',
    locations: (process.env.LOCATIONS || '').split(',').filter(Boolean)
  },
  analytics: {
    propertyId: process.env.GA4_PROPERTY_ID,
    apiSecret: process.env.GA4_API_SECRET
  },
  autoGenerateTasks: process.env.AUTO_GENERATE_TASKS !== 'false',
  notificationEmail: process.env.NOTIFICATION_EMAIL
};

const seoConfig = {
  openaiApiKey: process.env.OPENAI_API_KEY || '',
  semrushApiKey: process.env.SEMRUSH_API_KEY,
  targetKeyword: process.env.TARGET_KEYWORD,
  contentType: (process.env.CONTENT_TYPE as any) || 'blog',
  country: process.env.COUNTRY || 'us'
};

const seoEngine = new SEOEngine(seoConfig);
const dashboard = new SEODashboard(config);
dashboard.setSEOEngine(seoEngine);

const oauth = process.env.GOOGLE_CLIENT_ID ? new OAuthHandler({
  clientId: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET || '',
  redirectUri: process.env.OAUTH_REDIRECT_URI || 'http://localhost:3000/auth/callback'
}) : null;

const sessions: Map<string, { accessToken: string; refreshToken?: string; platform: string }> = new Map();

app.get('/', (req, res) => {
  const html = dashboard.getHTMLDashboard();
  res.send(html);
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/auth/google', (req, res) => {
  if (!oauth) {
    return res.status(400).json({ error: 'OAuth not configured' });
  }
  const state = Math.random().toString(36).substring(7);
  const authUrl = oauth.getGoogleAuthUrl(state);
  res.redirect(authUrl);
});

app.get('/auth/microsoft', (req, res) => {
  if (!oauth) {
    return res.status(400).json({ error: 'OAuth not configured' });
  }
  const state = Math.random().toString(36).substring(7);
  const authUrl = oauth.getMicrosoftAuthUrl(state);
  res.redirect(authUrl);
});

app.get('/auth/callback', async (req, res) => {
  const { code, state } = req.query;

  if (!code || !oauth) {
    return res.status(400).send('Missing code or OAuth not configured');
  }

  try {
    const tokenData = await oauth.exchangeGoogleCode(code as string);
    const sessionId = Math.random().toString(36).substring(7);
    sessions.set(sessionId, { ...tokenData, platform: 'google' });
    
    res.cookie('session', sessionId, { httpOnly: true, maxAge: 7 * 24 * 60 * 60 * 1000 });
    res.redirect('/');
  } catch (error: any) {
    res.status(500).send(`Auth failed: ${error.message}`);
  }
});

app.get('/auth/analytics', (req, res) => {
  if (!oauth) {
    return res.status(400).json({ error: 'OAuth not configured' });
  }
  const authUrl = oauth.getGoogleAuthUrl('analytics');
  res.redirect(authUrl);
});

function getSessionToken(req: express.Request): string | null {
  const sessionId = req.cookies?.session;
  if (sessionId) {
    const session = sessions.get(sessionId);
    return session?.accessToken || null;
  }
  return null;
}

app.get('/api/dashboard', (req, res) => {
  const state = dashboard.getState();
  res.json(state);
});

app.get('/api/tasks', (req, res) => {
  const tasks = dashboard.getState().tasks;
  res.json(tasks);
});

app.post('/api/tasks/generate', async (req, res) => {
  const { analysis } = req.body;
  const tasks = await dashboard.generateTasks(analysis);
  res.json(tasks);
});

app.post('/api/task/complete', (req, res) => {
  const { id } = req.body;
  dashboard.completeTask(id);
  res.json({ success: true });
});

app.post('/api/task/skip', (req, res) => {
  const { id } = req.body;
  const tasks = dashboard.getState().tasks;
  const task = tasks.find(t => t.id === id);
  if (task) {
    task.status = 'completed';
  }
  res.json({ success: true });
});

app.post('/api/webmaster/connect', async (req, res) => {
  const { platform, accessToken } = req.body;

  try {
    if (platform === 'google') {
      const data = await dashboard.connectGoogleSearchConsole(accessToken);
      return res.json({ success: true, data });
    } else if (platform === 'bing') {
      const data = await dashboard.connectBingWebmaster();
      return res.json({ success: true, data });
    }
    res.status(400).json({ error: 'Invalid platform' });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/webmaster/sitemap', async (req, res) => {
  const { sitemapUrl, platform } = req.body;

  try {
    const result = await dashboard.submitSitemap(sitemapUrl, platform);
    res.json(result);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/analytics/connect', async (req, res) => {
  const { accessToken, propertyId } = req.body;

  try {
    const data = await dashboard.connectGoogleAnalytics(accessToken, propertyId);
    res.json({ success: true, data });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/summary', (req, res) => {
  res.json({
    tasks: dashboard.getTaskSummary(),
    rankings: dashboard.getRankingSummary(),
    indexing: dashboard.getIndexingSummary(),
    traffic: dashboard.getTrafficSummary()
  });
});

app.post('/api/analyze-url', async (req, res) => {
  const { url, keyword } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }

  try {
    if (keyword) {
      (seoEngine as any).config.targetKeyword = keyword;
    }

    const report = await seoEngine.analyze(url);
    const tasks = await dashboard.generateTasks(report.analysis);

    res.json({
      report,
      tasks,
      insights: await dashboard.analyzeAndRecommend(report.analysis)
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/optimize-url', async (req, res) => {
  const { url, keyword } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }

  try {
    if (keyword) {
      (seoEngine as any).config.targetKeyword = keyword;
    }

    const report = await seoEngine.analyze(url);
    const optimized = await seoEngine.optimize(report);

    res.json({
      original: report,
      optimized,
      tasks: await dashboard.generateTasks(report.analysis)
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/ai-insights', async (req, res) => {
  const analysis = dashboard.getState();
  const insights = await dashboard.analyzeAndRecommend(null as any);
  res.json(insights);
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════════════════╗
║              ⚡ ZenSEO Dashboard Ready ⚡                 ║
╠══════════════════════════════════════════════════════════╣
║  Server: http://localhost:${PORT}                          ║
║                                                          ║
║  Endpoints:                                             ║
║  • GET  /                    Dashboard UI                ║
║  • GET  /api/dashboard       Dashboard state             ║
║  • GET  /api/tasks           SEO tasks list              ║
║  • POST /api/analyze-url     Analyze URL                 ║
║  • POST /api/optimize-url    Optimize URL                ║
║  • POST /api/webmaster/connect  Connect GSC/Bing          ║
║  • POST /api/analytics/connect  Connect GA4             ║
║  • GET  /auth/google         OAuth login (Google)        ║
║  • GET  /auth/microsoft      OAuth login (Bing)          ║
╚══════════════════════════════════════════════════════════╝
  `);
});

export default app;