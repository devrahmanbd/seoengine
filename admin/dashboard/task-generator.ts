import { DashboardTask, TaskCategory, TaskPriority, TaskStatus } from './types';
import { ContentAnalysis } from '../types';

export interface TaskGeneratorConfig {
  domain?: string;
  analysis?: ContentAnalysis;
  localBusiness?: boolean;
  competitors?: string[];
}

export class TaskGenerator {
  private taskIdCounter = 1;

  generateTasks(config: TaskGeneratorConfig): DashboardTask[] {
    const tasks: DashboardTask[] = [];

    if (config.analysis) {
      tasks.push(...this.generateFromAnalysis(config.analysis, config.domain));
    }

    tasks.push(...this.generateTechnicalTasks(config.domain));
    
    if (config.localBusiness) {
      tasks.push(...this.generateLocalSEOTasks(config.domain));
    }

    tasks.push(...this.generateWebmasterTasks(config.domain));
    
    tasks.push(...this.generateContentTasks(config.analysis, config.domain));

    return tasks.sort((a, b) => {
      const priorityOrder = { high: 0, medium: 1, low: 2 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });
  }

  private generateFromAnalysis(analysis: ContentAnalysis, domain?: string): DashboardTask[] {
    const tasks: DashboardTask[] = [];

    if (analysis.title.score < 80) {
      tasks.push({
        id: `task_${this.taskIdCounter++}`,
        title: 'Optimize Title Tag',
        description: `Current title score: ${analysis.title.score}/100. ${analysis.title.issues.join('. ')}`,
        category: 'content',
        priority: analysis.title.score < 50 ? 'high' : 'medium',
        status: 'requires_action',
        instructions: `Rewrite your title tag to include the primary keyword naturally within 50-60 characters. Consider:\n\n1. Place keyword near the beginning\n2. Add unique value proposition\n3. Include brand name if beneficial\n\nExample: "[Primary Keyword] - Complete Guide | [Brand]"`,
        estimatedTime: '10 minutes',
        tools: ['Yoast/RankMath', 'CMS Editor', 'API'],
        createdAt: new Date()
      });
    }

    if (analysis.metaDescription.score < 80) {
      tasks.push({
        id: `task_${this.taskIdCounter++}`,
        title: 'Rewrite Meta Description',
        description: `Current meta score: ${analysis.metaDescription.score}/100. ${analysis.metaDescription.issues.join('. ')}`,
        category: 'content',
        priority: 'medium',
        status: 'requires_action',
        instructions: `Write a compelling meta description (150-160 characters) that:\n\n1. Includes primary keyword\n2. Contains a clear CTA\n3. Highlights unique value\n4. Matches search intent\n\nCurrent: "${analysis.metaDescription.raw}"\n\nRecommended format: "[Hook] - [Value] - [CTA]"`,
        estimatedTime: '10 minutes',
        tools: ['Yoast/RankMath', 'CMS Editor'],
        createdAt: new Date()
      });
    }

    if (analysis.readability.score < 60) {
      tasks.push({
        id: `task_${this.taskIdCounter++}`,
        title: 'Improve Readability',
        description: `Readability score: ${analysis.readability.score}/100. Grade level: ${analysis.readability.grade}`,
        category: 'content',
        priority: 'high',
        status: 'requires_action',
        instructions: `Your content requires a ${analysis.readability.grade} reading level. To improve:\n\n1. Shorten sentences (aim for <20 words)\n2. Break long paragraphs into 2-3 sentences\n3. Use bullet points and numbered lists\n4. Replace complex words with simpler alternatives\n5. Add subheadings every 150-200 words\n\nCurrent avg sentence length: ${analysis.readability.avgSentenceLength} words\nTarget: < 15 words`,
        estimatedTime: '30 minutes',
        tools: ['AI Content Tools', 'Hemingway App', 'Grammarly'],
        createdAt: new Date()
      });
    }

    if (analysis.schema.score < 50) {
      tasks.push({
        id: `task_${this.taskIdCounter++}`,
        title: 'Add Schema Markup',
        description: `Schema score: ${analysis.schema.score}/100. Missing: ${analysis.schema.missing.join(', ')}`,
        category: 'technical',
        priority: 'medium',
        status: 'requires_action',
        instructions: `Add JSON-LD schema markup to your page. Based on your content type, implement:\n\n1. Article schema for blog posts\n2. Product schema for products\n3. FAQPage schema for Q&A content\n4. LocalBusiness schema for local businesses\n\nMissing schemas: ${analysis.schema.missing.join(', ')}\n\nUse Schema Markup Generator or Yoast/RankMath schema feature.`,
        estimatedTime: '20 minutes',
        tools: ['Google Schema Markup Helper', 'Yoast Schema', 'RankMath'],
        createdAt: new Date()
      });
    }

    if (analysis.internalLinks.count < 2) {
      tasks.push({
        id: `task_${this.taskIdCounter++}`,
        title: 'Add Internal Links',
        description: `Only ${analysis.internalLinks.count} internal links found. Need more cross-linking.`,
        category: 'link_building',
        priority: 'medium',
        status: 'requires_action',
        instructions: `Add 3-5 relevant internal links to related content on your site:\n\n1. Link to supporting articles\n2. Link to category pages\n3. Use descriptive anchor text\n4. Place links in first 100 words when possible\n\nUse Ahrefs/Semrush to find related pages on your site.`,
        estimatedTime: '25 minutes',
        tools: ['Ahrefs', 'Semrush', 'Screaming Frog'],
        createdAt: new Date()
      });
    }

    const imagesWithoutAlt = analysis.images.filter(img => !img.hasAlt);
    if (imagesWithoutAlt.length > 0) {
      tasks.push({
        id: `task_${this.taskIdCounter++}`,
        title: 'Add Alt Text to Images',
        description: `${imagesWithoutAlt.length} images missing alt text`,
        category: 'technical',
        priority: 'medium',
        status: 'requires_action',
        instructions: `Add descriptive alt text to ${imagesWithoutAlt.length} images:\n\n${imagesWithoutAlt.map((img, i) => `${i + 1}. ${img.src}`).join('\n')}\n\nAlt text should:\n- Describe the image accurately\n- Include primary keyword naturally (1-2 max)\n- Be 125 characters or less\n- Not start with "image of" or "picture of"`,
        estimatedTime: '15 minutes',
        tools: ['CMS Media Library', 'Bulk Alt Text Tools'],
        createdAt: new Date()
      });
    }

    return tasks;
  }

  private generateTechnicalTasks(domain?: string): DashboardTask[] {
    return [
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Submit XML Sitemap to Google',
        description: 'Ensure search engines can discover all your pages',
        category: 'webmaster',
        priority: 'high',
        status: 'requires_action',
        instructions: `1. Verify your site in Google Search Console
2. Go to Sitemaps section
3. Submit: /sitemap.xml (or your sitemap URL)
4. Check for errors within 24-48 hours

If you don't have a sitemap, generate one using:
- Yoast SEO plugin
- RankMath
- Screaming Frog
- Online XML sitemap generators`,
        estimatedTime: '15 minutes',
        tools: ['Google Search Console', 'XML Sitemap Generator'],
        createdAt: new Date(),
        dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Submit Sitemap to Bing Webmaster',
        description: 'Bing powers Yahoo - don\'t ignore it',
        category: 'webmaster',
        priority: 'medium',
        status: 'requires_action',
        instructions: `1. Go to bing.com/webmaster
2. Add your site (verify ownership)
3. Navigate to Configure > Sitemaps
4. Submit your sitemap URL
5. Import from GSC if available

Bing often indexes faster than Google for new content.`,
        estimatedTime: '15 minutes',
        tools: ['Bing Webmaster Tools'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Fix Crawl Errors',
        description: 'Identify and fix pages that Google can\'t crawl',
        category: 'technical',
        priority: 'high',
        status: 'requires_action',
        instructions: `In Google Search Console:\n1. Go to Pages > Crawl Errors\n2. Identify error types:\n   - Not Found (404): Redirect or remove\n   - Server Error (5xx): Check hosting/performance\n   - Blocked by robots: Review robots.txt\n3. Create 301 redirects for moved pages\n4. Remove or fix broken links

Check Bing Webmaster Tools for additional errors.`,
        estimatedTime: '1-2 hours',
        tools: ['Google Search Console', 'Screaming Frog', 'Ahrefs'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Optimize Core Web Vitals',
        description: 'LCP, INP, CLS - critical for ranking',
        category: 'technical',
        priority: 'high',
        status: 'requires_action',
        instructions: `Check in Google Search Console > Experience\n\nLCP (Largest Contentful Paint) - Target < 2.5s:\n- Optimize server response time\n- Use CDN for static assets\n- Implement lazy loading\n- Optimize images (WebP, AVIF)\n\nINP (Interaction to Next Paint) - Target < 200ms:\n- Minimize JavaScript blocking\n- Break up long tasks\n- Use requestIdleCallback\n\nCLS (Cumulative Layout Shift) - Target < 0.1:\n- Set dimensions for images/video\n- Reserve space for ads\n- Use font-display: swap`,
        estimatedTime: '2-4 hours',
        tools: ['PageSpeed Insights', 'GTmetrix', 'WebPageTest'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Implement HTTPS',
        description: 'Security is a confirmed ranking factor',
        category: 'technical',
        priority: 'high',
        status: 'requires_action',
        instructions: `If not already on HTTPS:\n\n1. Obtain SSL certificate (Let's Encrypt is free)\n2. Update server configuration\n3. 301 redirect HTTP to HTTPS\n4. Update all internal links\n5. Update Google Search Console property\n6. Update Bing Webmaster Tools\n\nUse SSL Labs test to verify configuration.`,
        estimatedTime: '1-2 hours',
        tools: ['Let\'s Encrypt', 'SSL Labs', 'Server Panel'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Review robots.txt',
        description: 'Ensure important pages aren\'t blocked',
        category: 'technical',
        priority: 'medium',
        status: 'requires_action',
        instructions: `Check your robots.txt at ${domain || 'yoursite.com'}/robots.txt\n\nCommon issues to fix:\n- Blocked CSS/JS files (never block these)\n- Accidentally blocking entire sections\n- Missing sitemap reference\n- Wrong directive order\n\nTest in Google Search Console > robots.txt Tester`,
        estimatedTime: '30 minutes',
        tools: ['Google Search Console', 'Screaming Frog'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Fix Canonical URL Issues',
        description: 'Prevent duplicate content problems',
        category: 'technical',
        priority: 'medium',
        status: 'requires_action',
        instructions: `1. Audit your site for duplicate content\n2. Ensure every page has self-referencing canonical\n3. Consolidate duplicate versions (HTTP/HTTPS, www/non-www, trailing slash)\n4. Use 301 redirects for deprecated URLs\n5. Set canonical in HTTP header for dynamic content\n\nCheck: https://www.example.com, https://example.com, https://www.example.com/`,
        estimatedTime: '1 hour',
        tools: ['Screaming Frog', 'Ahrefs', 'Google Search Console'],
        createdAt: new Date()
      }
    ];
  }

  private generateLocalSEOTasks(domain?: string): DashboardTask[] {
    return [
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Claim Google Business Profile',
        description: 'Essential for local SEO - free real estate',
        category: 'local',
        priority: 'high',
        status: 'requires_action',
        instructions: `1. Go to business.google.com
2. Search for your business name
3. If exists, claim ownership
4. If not, add new business
5. Complete ALL fields:
   - Business name (exact match to signage)
   - Category (primary + secondary)
   - Address (accurate to street)
   - Phone (local, toll-free avoided)
   - Website
   - Hours
   - Attributes
6. Verify via postcard/phone
7. Enable messaging`,
        estimatedTime: '45 minutes',
        tools: ['Google Business Profile', 'Google Maps'],
        createdAt: new Date(),
        dueDate: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000)
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Optimize Google Business Profile',
        description: 'Complete every field for maximum visibility',
        category: 'local',
        priority: 'high',
        status: 'requires_action',
        instructions: `Complete these optimization tasks:\n\n1. **Photos**: Add 10+ photos (exterior, interior, team, products, services)\n2. **Posts**: Weekly posts with offers, events, news\n3. **Products/Services**: List all services with descriptions\n4. **Questions**: Add and answer FAQs\n5. **Messaging**: Enable and set up auto-replies\n6. **Attributes**: Select all applicable (accessibility, payment, etc.)\n7. **Short name**: Claim your short name\n8. **Reviews**: Respond to ALL reviews (positive + negative)`,
        estimatedTime: '2 hours',
        tools: ['Google Business Profile', 'Canva (for photos)'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Build Local Citations',
        description: 'Get listed on top citation directories',
        category: 'local',
        priority: 'high',
        status: 'requires_action',
        instructions: `Claim and optimize listings on:\n\n**High Priority**:\n- Apple Maps\n- Bing Places\n- Yelp\n- Yellow Pages\n- Facebook (with address)\n\n**Industry Specific**:\n- Health: Healthgrades, ZocDoc\n- Real Estate: Zillow, Realtor.com\n- Restaurants: TripAdvisor, OpenTable\n\nEnsure NAP (Name, Address, Phone) is EXACTLY consistent across all.`,
        estimatedTime: '3-4 hours (distribute over weeks)',
        tools: ['BrightLocal', 'Moz Local', 'Yext'],
        createdAt: new Date(),
        dueDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000)
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Get More Google Reviews',
        description: 'Reviews = trust = conversions',
        category: 'local',
        priority: 'high',
        status: 'requires_action',
        instructions: `1. Create review link: https://search.google.com/local/writesitreview?placeid=[PLACE_ID]\n2. Train staff to request reviews (timing is key - after positive interaction)\n3. Send follow-up email/text with link\n4. Create QR code for in-store scanning\n5. Respond to ALL reviews within 48 hours\n6. Add review request to email signature\n7. Feature best reviews on website\n\nTarget: 50+ reviews with 4.5+ rating`,
        estimatedTime: 'Ongoing',
        tools: ['Google Business Profile', 'Review management software'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Build Local Backlinks',
        description: 'Get links from local organizations',
        category: 'link_building',
        priority: 'medium',
        status: 'requires_action',
        instructions: `Local link building strategies:\n\n1. **Local newspapers**: Pitch newsworthy stories\n2. **Chamber of Commerce**: Join and get listed\n3. **Local associations**: Industry groups, networking\n4. **Sponsorships**: Local events, sports teams\n5. **Guest posts**: Local blogs, news sites\n6. **Local directories**: Beyond citations\n7. **Partnerships**: Cross-promote with complementary businesses\n\nTrack all links in spreadsheet with DA, anchor text.`,
        estimatedTime: '2-3 hours/week',
        tools: ['Ahrefs', 'BrightLocal', 'Hunter.io'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Optimize for "Near Me" Searches',
        description: 'Capture mobile local searchers',
        category: 'local',
        priority: 'medium',
        status: 'requires_action',
        instructions: `Optimize content for "near me" / "[city] + [service]" queries:\n\n1. Create location-specific landing pages\n2. Include city/state in title tags, H1s\n3. Add schema: Address, ServiceArea, Geo coordinates\n4. Content about local events, news, community\n5. Mobile-first optimization (crucial for local)\n6. Page speed matters more for mobile\n\nCheck "People also search for" and "Related searches"`,
        estimatedTime: '1-2 hours per page',
        tools: ['Google Search Console', 'Ahrefs', 'Clearscope'],
        createdAt: new Date()
      }
    ];
  }

  private generateWebmasterTasks(domain?: string): DashboardTask[] {
    return [
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Set Up Google Search Console',
        description: 'Essential free tool for monitoring search presence',
        category: 'webmaster',
        priority: 'high',
        status: 'requires_action',
        instructions: `1. Go to search.google.com/search-console
2. Add property (domain prefix or URL prefix)
3. Verify ownership via:\n   - DNS TXT record (recommended)\n   - HTML file upload\n   - Google Analytics/Tag Manager\n4. Submit sitemap\n5. Set up email notifications\n\nRecommended settings:\n- Enable "Search appearance" emails\n- Enable "Index coverage" emails\n- Set preferred domain (www vs non-www)`,
        estimatedTime: '30 minutes',
        tools: ['Google Search Console', 'DNS Manager'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Connect Bing Webmaster Tools',
        description: 'Bing powers Yahoo - don\'t miss this traffic',
        category: 'webmaster',
        priority: 'medium',
        status: 'requires_action',
        instructions: `1. Go to bing.com/webmaster
2. Sign in (use Microsoft account)
3. Add your site
4. Verify via:\n   - XML file upload\n   - Meta tag\n   - DNS TXT record (same as GSC works)\n5. Import settings from GSC\n6. Submit sitemap

Bing often shows more detailed crawl data.`,
        estimatedTime: '20 minutes',
        tools: ['Bing Webmaster Tools'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Analyze Search Performance in GSC',
        description: 'Understand how users find your site',
        category: 'analytics',
        priority: 'high',
        status: 'requires_action',
        instructions: `In Google Search Console:\n\n1. **Performance > Search Results**\n   - Review top queries (position, clicks, CTR)\n   - Identify quick wins (high impressions, low clicks)\n   - Note content gaps\n\n2. **Pages**\n   - Find top performing pages\n   - Identify pages needing optimization\n\n3. **Devices**\n   - Check mobile vs desktop performance\n   - Mobile-first indexing implications\n\n4. **Countries**\n   - Geographic performance\n   - Localization opportunities`,
        estimatedTime: '45 minutes',
        tools: ['Google Search Console'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Monitor Index Coverage',
        description: 'Ensure Google can index your pages',
        category: 'webmaster',
        priority: 'high',
        status: 'requires_action',
        instructions: `In Google Search Console > Index > Coverage:\n\n1. **Error** (fix immediately):\n   - Not found (404): 301 redirect or update links\n   - Server errors: Check hosting\n   - Blocked: Review robots.txt\n\n2. **Valid with warnings** (review):\n   - Indexed though blocked: Check intent\n   - Page with redirect: Normal\n   - Alternate page with proper canonical: OK\n\n3. **Excluded** (usually OK):\n   - Duplicates, not selected, blocked by robots\n\nCreate spreadsheet to track and fix errors.`,
        estimatedTime: '1 hour',
        tools: ['Google Search Console', 'Screaming Frog'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Set Up URL Parameters',
        description: 'Prevent duplicate content from parameters',
        category: 'technical',
        priority: 'low',
        status: 'requires_action',
        instructions: `In Google Search Console > URL parameters:\n\n1. Identify parameters causing duplicates:\n   - ?sort= (sorting)\n   - ?filter= (filtering)\n   - ?session= (tracking)\n   - ?utm_= (campaign tracking)\n\n2. Configure properly:\n   - Specifies: Don't specify\n   - Clarifies: URLs with this parameter\n   - Collapses: Single parameter\n\n3. Test each parameter\n4. Most e-commerce needs parameter handling`,
        estimatedTime: '30 minutes',
        tools: ['Google Search Console', 'Google Analytics'],
        createdAt: new Date()
      }
    ];
  }

  private generateContentTasks(analysis?: ContentAnalysis, domain?: string): DashboardTask[] {
    return [
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Create Topic Cluster Content',
        description: 'Build semantic authority with content hubs',
        category: 'content',
        priority: 'high',
        status: 'requires_action',
        instructions: `Create a content hub around your primary topic:\n\n1. **Pillar Page** (3000+ words)\n   - Comprehensive guide on main topic\n   - Links to all cluster content\n   - Table of contents\n   - Schema: Article + FAQ\n\n2. **Cluster Content** (1000-1500 words each)\n   - Related subtopics\n   - Links to pillar and other clusters\n   - Each targets related keywords\n\n3. **Internal Linking**\n   - Pillar links to clusters\n   - Clusters link to pillar\n   - Clusters link to each other\n\nUse Ahrels to find content gaps.`,
        estimatedTime: '1-2 weeks',
        tools: ['Ahrefs', 'Clearscope', 'SurferSEO'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Optimize for Featured Snippets',
        description: 'Capture Position 0 - even for competitors',
        category: 'content',
        priority: 'medium',
        status: 'requires_action',
        instructions: `To win featured snippets:\n\n1. Find opportunities in GSC\n   - Queries with "people also ask"\n   - "Answer" questions in position 2-4\n\n2. Format content for snippets:\n   - Direct answers in 40-50 words\n   - Use bullet/numbered lists\n   - Include tables where relevant\n   - Add FAQ section with questions\n\n3. Structure with:\n   - Clear H2/H3 headings\n   - Question as heading\n   - Concise answer first, then detail\n\n4. Add FAQPage schema`,
        estimatedTime: '2-3 hours per page',
        tools: ['Google Search Console', 'Ahrefs', 'Also Asked'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Update Old Content',
        description: 'Refresh content to maintain rankings',
        category: 'content',
        priority: 'medium',
        status: 'requires_action',
        instructions: `Find and update underperforming content:\n\n1. In GSC, find:\n   - Pages dropping in rankings\n   - Pages with high impressions, low clicks\n\n2. In GA, find:\n   - Pages with high bounce rate\n   - Pages with low time on page\n\n3. For each page:\n   - Update statistics and data\n   - Add new insights\n   - Refresh examples\n   - Update internal links\n   - Add schema\n   - Update publication date\n   - Add "Updated" annotation`,
        estimatedTime: '1 hour per page',
        tools: ['Google Search Console', 'Google Analytics', 'Screaming Frog'],
        createdAt: new Date()
      },
      {
        id: `task_${this.taskIdCounter++}`,
        title: 'Create PAA Content Strategy',
        description: 'Capture People Also Ask boxes',
        category: 'content',
        priority: 'medium',
        status: 'requires_action',
        instructions: `People Also Ask optimization:\n\n1. Research PAA questions:\n   - Use AlsoAsked.com\n   - Search your keywords\n   - Check competitor PAA\n\n2. Create content that answers:\n   - Questions in 40-50 words\n   - Multiple related questions\n   - Follow-up questions section\n\n3. Format for PAA:\n   - Use question as H3\n   - Direct answer first\n   - Bullet points when possible\n   - Add schema: FAQPage\n\n4. Expand PAA coverage:\n   - 20+ Q&As per article\n   - Link between FAQs\n   - Regular updates`,
        estimatedTime: '2 hours per page',
        tools: ['Also Asked', 'AnswerThePublic', 'AlsoGenerate'],
        createdAt: new Date()
      }
    ];
  }
}

export default TaskGenerator;