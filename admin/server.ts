import express from 'express';
import * as dotenv from 'dotenv';
import { SEOEngine } from './engine';
import { SEOConfig } from './types';
import * as fs from 'fs';

dotenv.config();

const app = express();
app.use(express.json({ limit: '10mb' }));

const config: SEOConfig = {
  openaiApiKey: process.env.OPENAI_API_KEY || '',
  semrushApiKey: process.env.SEMRUSH_API_KEY,
  targetKeyword: process.env.TARGET_KEYWORD,
  contentType: (process.env.CONTENT_TYPE as any) || 'blog',
  primaryLanguage: process.env.LANGUAGE || 'en',
  country: process.env.COUNTRY || 'us'
};

const engine = new SEOEngine(config);

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.post('/api/analyze', async (req, res) => {
  try {
    const { url, keyword } = req.body;

    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }

    if (keyword) {
      (engine as any).config.targetKeyword = keyword;
    }

    const report = await engine.analyze(url);
    res.json(report);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/batch', async (req, res) => {
  try {
    const { urls, csvPath } = req.body;

    if (csvPath) {
      const batch = await engine.importFromCSV(csvPath);
      return res.json(batch);
    }

    if (!urls || !Array.isArray(urls)) {
      return res.status(400).json({ error: 'urls array is required' });
    }

    const batch = await engine.analyzeBatch(urls);
    res.json(batch);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/keyword', async (req, res) => {
  try {
    const { keyword, related } = req.body;

    if (!keyword) {
      return res.status(400).json({ error: 'keyword is required' });
    }

    const data = await engine.getKeywordData(keyword);

    if (related) {
      const relatedKeywords = await engine.getRelatedKeywords(keyword, 10);
      return res.json({ main: data, related: relatedKeywords });
    }

    res.json(data);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/generate', async (req, res) => {
  try {
    const { topic, type } = req.body;

    if (!topic) {
      return res.status(400).json({ error: 'topic is required' });
    }

    const content = await engine.generateContent(topic, type || 'blog');
    res.json(content);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/optimize', async (req, res) => {
  try {
    const { url } = req.body;

    if (!url) {
      return res.status(400).json({ error: 'url is required' });
    }

    const report = await engine.analyze(url);
    const optimized = await engine.optimize(report);

    res.json({
      originalScore: report.analysis.overallScore,
      estimatedScore: Math.min(100, report.analysis.overallScore + 25),
      ...optimized
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/schema', async (req, res) => {
  try {
    const { type, data } = req.body;

    if (!type || !data) {
      return res.status(400).json({ error: 'type and data are required' });
    }

    const schema = engine.generateSchema(type, data);
    res.json({ schema });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/breadcrumb', async (req, res) => {
  try {
    const { items } = req.body;

    if (!items || !Array.isArray(items)) {
      return res.status(400).json({ error: 'items array is required' });
    }

    const breadcrumb = engine.generateBreadcrumb(items);
    res.json({ breadcrumb });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/import', async (req, res) => {
  try {
    const { csvContent, outputPath } = req.body;

    if (csvContent) {
      const CSVHandler = (await import('./utils/csv-handler')).default;
      const handler = new CSVHandler();
      const rows = handler.importFromString(csvContent);
      const urls = rows.map((r: any) => r.url).filter(Boolean);
      const batch = await engine.analyzeBatch(urls);

      if (outputPath) {
        await engine.exportReport(batch.results, outputPath);
      }

      return res.json(batch);
    }

    res.status(400).json({ error: 'csvContent is required' });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`🚀 AI SEO Engine running on port ${PORT}`);
});

export default app;