import { parse } from 'csv-parse/sync';
import { stringify } from 'csv-stringify/sync';
import * as fs from 'fs';
import { CSVRow, SEOReport, ContentAnalysis } from '../types';

export class CSVHandler {
  async importCSV(filePath: string): Promise<CSVRow[]> {
    try {
      const fileContent = fs.readFileSync(filePath, 'utf-8');
      const records = parse(fileContent, {
        columns: true,
        skip_empty_lines: true,
        trim: true,
        relax_column_count: true
      });

      return records.map((record: any) => ({
        url: record.url || record.URL || record.link || record.href || '',
        title: record.title || record.Title || record.meta_title || '',
        metaDescription: record.description || record.Description || record.meta_description || '',
        keyword: record.keyword || record.Keyword || record.target_keyword || record.target || '',
        targetKeyword: record.targetKeyword || record['target keyword'] || '',
        ...record
      }));
    } catch (error) {
      console.error('CSV import error:', error);
      throw new Error(`Failed to import CSV: ${(error as Error).message}`);
    }
  }

  exportCSV(data: SEOReport[], outputPath: string): void {
    const rows = data.map(report => ({
      URL: report.url,
      Title: report.title,
      'Meta Description': report.description,
      'Target Keyword': report.keyword,
      'Overall Score': report.analysis.overallScore,
      'Title Score': report.analysis.title.score,
      'Meta Score': report.analysis.metaDescription.score,
      'Keyword Score': report.analysis.keywordAnalysis.primary.score,
      'Readability Score': report.analysis.readability.score,
      'Internal Links': report.analysis.internalLinks.count,
      'External Links': report.analysis.outboundLinks.count,
      'Image Count': report.analysis.images.length,
      'Schema Types': report.analysis.schema.types.join('; '),
      'Suggestions Count': report.analysis.suggestions.length,
      'Flesch Reading Ease': report.analysis.readability.fleschKincaid,
      'Grade Level': report.analysis.readability.grade,
      'Keyword Density': report.analysis.keywordAnalysis.density,
      'Timestamp': report.timestamp.toISOString()
    }));

    const csvContent = stringify(rows, { header: true });
    fs.writeFileSync(outputPath, csvContent, 'utf-8');
  }

  exportOptimizedContent(data: {
    original: string;
    optimized: string;
    url: string;
    changes: any[];
    scoreBefore: number;
    scoreAfter: number;
  }[], outputPath: string): void {
    const rows = data.map(item => ({
      URL: item.url,
      'Original Content': item.original.substring(0, 500),
      'Optimized Content': item.optimized.substring(0, 500),
      'Changes Count': item.changes.length,
      'Score Before': item.scoreBefore,
      'Score After': item.scoreAfter,
      'Improvement': item.scoreAfter - item.scoreBefore
    }));

    const csvContent = stringify(rows, { header: true });
    fs.writeFileSync(outputPath, csvContent, 'utf-8');
  }

  exportKeywordData(data: {
    keyword: string;
    volume: number;
    difficulty: number;
    cpc: number;
    intent: string;
    related: string[];
  }[], outputPath: string): void {
    const rows = data.map(kw => ({
      Keyword: kw.keyword,
      'Search Volume': kw.volume,
      'Difficulty': kw.difficulty,
      'CPC': kw.cpc,
      'Intent': kw.intent,
      'Related Keywords': kw.related.join('; ')
    }));

    const csvContent = stringify(rows, { header: true });
    fs.writeFileSync(outputPath, csvContent, 'utf-8');
  }

  importFromString(csvContent: string): CSVRow[] {
    try {
      const records = parse(csvContent, {
        columns: true,
        skip_empty_lines: true,
        trim: true
      });

      return records.map((record: any) => ({
        url: record.url || record.URL || record.link || record.href || '',
        title: record.title || record.Title || '',
        metaDescription: record.description || record.Description || '',
        keyword: record.keyword || record.Keyword || '',
        ...record
      }));
    } catch (error) {
      console.error('CSV parsing error:', error);
      throw new Error(`Failed to parse CSV: ${(error as Error).message}`);
    }
  }

  async exportToExcelCompatible(data: any[], outputPath: string): Promise<void> {
    const csvContent = stringify(data, { header: true });
    fs.writeFileSync(outputPath, csvContent, 'utf-8');
  }
}

export default CSVHandler;