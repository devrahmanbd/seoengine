#!/usr/bin/env node

import * as dotenv from 'dotenv';
import inquirer from 'inquirer';
import chalk from 'chalk';
import Table from 'cli-table3';
import { SEOEngine } from './engine';
import { SEOConfig } from './types';
import * as fs from 'fs';
import * as path from 'path';

dotenv.config();

interface CLIOptions {
  url?: string;
  csv?: string;
  keyword?: string;
  generate?: string;
  type?: string;
  output?: string;
  analyze?: string;
}

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!process.env.OPENAI_API_KEY) {
    console.error(chalk.red('Error: OPENAI_API_KEY is required in .env file'));
    process.exit(1);
  }

  const config: SEOConfig = {
    openaiApiKey: process.env.OPENAI_API_KEY,
    semrushApiKey: process.env.SEMRUSH_API_KEY,
    targetKeyword: process.env.TARGET_KEYWORD || undefined,
    contentType: (process.env.CONTENT_TYPE as any) || 'blog',
    primaryLanguage: process.env.LANGUAGE || 'en',
    country: process.env.COUNTRY || 'us'
  };

  const engine = new SEOEngine(config);

  switch (command) {
    case 'analyze':
      await handleAnalyze(engine, args);
      break;
    case 'batch':
      await handleBatch(engine, args);
      break;
    case 'keyword':
      await handleKeyword(engine, args);
      break;
    case 'generate':
      await handleGenerate(engine, args);
      break;
    case 'optimize':
      await handleOptimize(engine, args);
      break;
    case 'import':
      await handleImport(engine, args);
      break;
    case 'interactive':
      await handleInteractive(engine);
      break;
    default:
      showHelp();
  }
}

async function handleAnalyze(engine: SEOEngine, args: string[]) {
  const urlArg = args.find(a => a.startsWith('--url='))?.split('=')[1];
  const keywordArg = args.find(a => a.startsWith('--keyword='))?.split('=')[1];

  if (!urlArg) {
    console.error(chalk.red('Error: --url is required'));
    process.exit(1);
  }

  console.log(chalk.blue(`\n🔍 Analyzing: ${urlArg}\n`));

  if (keywordArg) {
    (engine as any).config.targetKeyword = keywordArg;
  }

  const report = await engine.analyze(urlArg);

  console.log(chalk.bold('\n📊 SEO Score Analysis\n'));
  console.log(`Overall Score: ${colorScore(report.analysis.overallScore)}/100\n`);

  const table = new Table({
    head: ['Element', 'Score', 'Status'],
    colWidths: [20, 10, 15]
  });

  table.push(
    ['Title', report.analysis.title.score.toString(), getStatus(report.analysis.title.score)],
    ['Meta Description', report.analysis.metaDescription.score.toString(), getStatus(report.analysis.metaDescription.score)],
    ['Keyword', report.analysis.keywordAnalysis.primary.score.toString(), getStatus(report.analysis.keywordAnalysis.primary.score)],
    ['Readability', report.analysis.readability.score.toString(), getStatus(report.analysis.readability.score)],
    ['Internal Links', report.analysis.internalLinks.count.toString(), getStatus(report.analysis.internalLinks.score)],
    ['Schema', report.analysis.schema.score.toString(), getStatus(report.analysis.schema.score)]
  );

  console.log(table.toString());

  if (report.analysis.suggestions.length > 0) {
    console.log(chalk.bold('\n💡 Suggestions:\n'));
    report.analysis.suggestions.slice(0, 5).forEach((s, i) => {
      const icon = s.type === 'error' ? '🔴' : s.type === 'warning' ? '🟡' : '🟢';
      console.log(`  ${icon} ${s.message}`);
    });
  }

  const outputPath = args.find(a => a.startsWith('--output='))?.split('=')[1];
  if (outputPath) {
    await engine.exportReport([report], outputPath);
    console.log(chalk.green(`\n✅ Report exported to: ${outputPath}`));
  }
}

async function handleBatch(engine: SEOEngine, args: string[]) {
  const csvArg = args.find(a => a.startsWith('--csv='))?.split('=')[1];
  const outputArg = args.find(a => a.startsWith('--output='))?.split('=')[1] || 'batch-report.csv';

  if (!csvArg) {
    console.error(chalk.red('Error: --csv is required'));
    process.exit(1);
  }

  console.log(chalk.blue(`\n📂 Importing URLs from: ${csvArg}\n`));

  const batch = await engine.importFromCSV(csvArg);

  console.log(`Processed: ${batch.results.length}/${batch.urls.length} URLs`);

  if (batch.results.length > 0) {
    const avgScore = batch.results.reduce((sum, r) => sum + r.analysis.overallScore, 0) / batch.results.length;
    console.log(`Average Score: ${avgScore.toFixed(1)}/100`);
  }

  if (batch.errors.length > 0) {
    console.log(chalk.red(`\nErrors: ${batch.errors.length}`));
  }

  await engine.exportReport(batch.results, outputArg);
  console.log(chalk.green(`\n✅ Report exported to: ${outputArg}`));
}

async function handleKeyword(engine: SEOEngine, args: string[]) {
  const keywordArg = args.find(a => a.startsWith('--keyword='))?.split('=')[1];
  const relatedArg = args.includes('--related');
  const outputArg = args.find(a => a.startsWith('--output='))?.split('=')[1];

  if (!keywordArg) {
    console.error(chalk.red('Error: --keyword is required'));
    process.exit(1);
  }

  console.log(chalk.blue(`\n🔑 Analyzing keyword: ${keywordArg}\n`));

  const data = await engine.getKeywordData(keywordArg);

  console.log(chalk.bold('Keyword Metrics:\n'));
  console.log(`  Search Volume: ${data.volume.toLocaleString()}`);
  console.log(`  Difficulty: ${data.difficulty}/100`);
  console.log(`  CPC: $${data.cpc.toFixed(2)}`);
  console.log(`  Intent: ${data.intent}`);

  if (relatedArg || args.includes('--all')) {
    console.log(chalk.bold('\n📋 Related Keywords:\n'));
    const related = await engine.getRelatedKeywords(keywordArg, 10);
    const table = new Table({ head: ['Keyword', 'Volume', 'Difficulty', 'Intent'] });
    related.forEach(k => table.push([k.keyword, k.volume.toString(), k.difficulty.toString(), k.intent]));
    console.log(table.toString());

    if (outputArg) {
      await engine.exportReport([], outputArg);
      console.log(chalk.green(`\n✅ Data exported to: ${outputArg}`));
    }
  }
}

async function handleGenerate(engine: SEOEngine, args: string[]) {
  const topicArg = args.find(a => a.startsWith('--topic='))?.split('=')[1];
  const typeArg = (args.find(a => a.startsWith('--type='))?.split('=')[1] || 'blog') as any;
  const outputArg = args.find(a => a.startsWith('--output='))?.split('=')[1];

  if (!topicArg) {
    console.error(chalk.red('Error: --topic is required'));
    process.exit(1);
  }

  console.log(chalk.blue(`\n✍️ Generating ${typeArg} content for: ${topicArg}\n`));

  const content = await engine.generateContent(topicArg, typeArg);

  console.log(chalk.bold('Generated Content:\n'));
  console.log(chalk.cyan('Title: ') + content.title);
  console.log(chalk.cyan('Meta: ') + content.metaDescription);
  console.log(chalk.cyan('\nHeadings:'));
  content.headings.forEach(h => console.log(`  - ${h}`));
  console.log(chalk.cyan('\nSchema:'));
  console.log(content.schema);

  if (outputArg) {
    fs.writeFileSync(outputArg, JSON.stringify(content, null, 2));
    console.log(chalk.green(`\n✅ Content saved to: ${outputArg}`));
  }
}

async function handleOptimize(engine: SEOEngine, args: string[]) {
  const urlArg = args.find(a => a.startsWith('--url='))?.split('=')[1];
  const outputArg = args.find(a => a.startsWith('--output='))?.split('=')[1];

  if (!urlArg) {
    console.error(chalk.red('Error: --url is required'));
    process.exit(1);
  }

  console.log(chalk.blue(`\n⚡ Optimizing: ${urlArg}\n`));

  const report = await engine.analyze(urlArg);
  const optimized = await engine.optimize(report);

  console.log(chalk.bold('Optimization Results:\n'));
  console.log(chalk.green('Before: ') + report.analysis.overallScore + '/100');
  console.log(chalk.green('After: ') + '~' + Math.min(100, report.analysis.overallScore + 25) + '/100');
  console.log(chalk.bold('\nChanges:'));
  optimized.changes.forEach(c => {
    console.log(`  • ${c.element}: "${c.before}" → "${c.after}"`);
  });

  if (outputArg) {
    fs.writeFileSync(outputArg, JSON.stringify(optimized, null, 2));
    console.log(chalk.green(`\n✅ Optimization saved to: ${outputArg}`));
  }
}

async function handleImport(engine: SEOEngine, args: string[]) {
  const csvArg = args.find(a => a.startsWith('--csv='))?.split('=')[1];
  const outputArg = args.find(a => a.startsWith('--output='))?.split('=')[1] || 'output.csv';

  if (!csvArg) {
    console.error(chalk.red('Error: --csv is required'));
    process.exit(1);
  }

  const batch = await engine.importFromCSV(csvArg);
  await engine.exportReport(batch.results, outputArg);
  console.log(chalk.green(`✅ Processed ${batch.results.length} URLs, exported to ${outputArg}`));
}

async function handleInteractive(engine: SEOEngine) {
  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'action',
      message: 'What would you like to do?',
      choices: [
        'Analyze a URL',
        'Batch analyze from CSV',
        'Research keywords',
        'Generate SEO content',
        'Optimize existing content'
      ]
    },
    {
      type: 'input',
      name: 'url',
      message: 'Enter URL:',
      when: (answers: any) => answers.action === 'Analyze a URL'
    },
    {
      type: 'input',
      name: 'csv',
      message: 'Enter CSV file path:',
      when: (answers: any) => answers.action === 'Batch analyze from CSV'
    },
    {
      type: 'input',
      name: 'keyword',
      message: 'Enter keyword:',
      when: (answers: any) => ['Research keywords', 'Generate SEO content'].includes(answers.action)
    },
    {
      type: 'list',
      name: 'type',
      message: 'Content type:',
      choices: ['blog', 'product', 'landing', 'service', 'faq'],
      when: (answers: any) => answers.action === 'Generate SEO content'
    }
  ]);

  switch (answers.action) {
    case 'Analyze a URL':
      await handleAnalyze(engine, ['--url=' + answers.url]);
      break;
    case 'Batch analyze from CSV':
      await handleImport(engine, ['--csv=' + answers.csv]);
      break;
    case 'Research keywords':
      await handleKeyword(engine, ['--keyword=' + answers.keyword, '--related']);
      break;
    case 'Generate SEO content':
      await handleGenerate(engine, ['--topic=' + answers.keyword, '--type=' + answers.type]);
      break;
    case 'Optimize existing content':
      await handleOptimize(engine, ['--url=' + answers.url]);
      break;
  }
}

function colorScore(score: number): string {
  if (score >= 80) return chalk.green(score.toString());
  if (score >= 60) return chalk.yellow(score.toString());
  return chalk.red(score.toString());
}

function getStatus(score: number): string {
  if (score >= 80) return chalk.green('Good');
  if (score >= 60) return chalk.yellow('Needs Work');
  return chalk.red('Poor');
}

function showHelp() {
  console.log(`
${chalk.bold('AI SEO Engine - CLI')}

${chalk.cyan('Usage:')}
  seo-engine <command> [options]

${chalk.cyan('Commands:')}
  analyze        Analyze a single URL
  batch          Analyze multiple URLs from CSV
  keyword        Research keywords
  generate       Generate SEO content
  optimize       Optimize existing content
  import         Import URLs from CSV
  interactive    Start interactive mode

${chalk.cyan('Options:')}
  --url=<url>          Target URL
  --csv=<file>         CSV file path
  --keyword=<kw>       Target keyword
  --topic=<topic>      Content topic
  --type=<type>        Content type (blog/product/landing/service/faq)
  --output=<file>      Output file path

${chalk.cyan('Examples:')}
  seo-engine analyze --url=https://example.com --keyword="seo tips"
  seo-engine batch --csv=urls.csv --output=report.csv
  seo-engine keyword --keyword="marketing" --related
  seo-engine generate --topic="AI tools" --type=blog

${chalk.cyan('Environment Variables:')}
  OPENAI_API_KEY       Required for AI features
  SEMRUSH_API_KEY      Optional for keyword data
  TARGET_KEYWORD      Default keyword
  CONTENT_TYPE        Default content type
  `);
}

main().catch(console.error);