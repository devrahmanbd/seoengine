# AI SEO Engine — Full Product Specification

**Product:** Fully autonomous AI SEO Engine (SaaS)
**Target:** WordPress site owners (SMBs) and Agencies
**Deployment:** Cloud multi-tenant SaaS
**Differentiator:** Full AI autonomy — not just suggests, automatically fixes
**Status:** Design Document v1.1
**Date:** 2026-05-19

> **Scope Note:** This document covers the full 7-phase product vision. Each phase has clear boundaries and dependencies. Implementation planning will decompose into independent sub-specs per phase.

---

## Table of Contents

1. [Overall Architecture](#1-overall-architecture)
2. [Data Layer](#2-data-layer)
3. [AI Agent Pipeline](#3-ai-agent-pipeline)
4. [WordPress Plugin](#4-wordpress-plugin)
5. [User Onboarding & RAG Personalization](#5-user-onboarding--rag-personalization)
6. [Admin Dashboard & Billing](#6-admin-dashboard--billing)
7. [Automation Scenarios](#7-automation-scenarios)
8. [Anti-Piracy & Tenant Security](#8-anti-piracy--tenant-security)
9. [OpenRouter & LLM Cost Management](#9-openrouter--llm-cost-management)
10. [SemRush Integration](#10-semrush-integration)
11. [Implementation Phases](#11-implementation-phases)

---

## 1. Overall Architecture

### 1.1 High-Level System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      WordPress Plugin                            │
│  (Lightweight connector: collects data, applies fixes, reports)  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTPS / WebSocket (signed heartbeats)
┌──────────────────────────▼───────────────────────────────────────┐
│                      API Gateway (FastAPI)                       │
│  Auth | Rate Limit | Tenant Isolation | Domain Verification      │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                    Event Bus (Redis Streams)                      │
│  Events: site_connected | scan_requested | fix_needed | ...      │
└──────────┬──────────────────────────────┬────────────────────────┘
           │                              │
┌──────────▼──────────┐    ┌──────────────▼────────────────────────┐
│   Orchestrator      │    │    AI Agent Workers (async pool)      │
│   Agent             │    │                                      │
│  • Plans tasks      │    │  ┌──────────────────────────────────┐│
│  • Dispatches work  │    │  │ Content Writer     (LLM-heavy)   ││
│  • Tracks progress  │    │  │ Technical Scanner  (crawler)     ││
│  • Validates fixes  │    │  │ Schema Generator   (template+LLM)││
│  • Confidence gates │    │  │ Keyword Researcher  (SemRush+LLM)││
│                     │    │  │ Competitor Analyzer (SemRush+LLM)││
└──────────────────────┘    │  │ Rank Tracker       (SemRush)    ││
                            │  │ AEO Optimizer      (LLM-heavy)  ││
                            │  │ CWV Engineer       (analyzer)   ││
                            │  └──────────────────────────────────┘│
                            └──────────────────────────────────────┘
```

### 1.2 Core Services

| Service | Stack | Purpose |
|---------|-------|---------|
| **API Gateway** | FastAPI + Redis | Auth, rate limiting, domain verification, tenant isolation |
| **Orchestrator** | Python async (event-driven) | Task planning, dispatching, result validation, confidence gating |
| **AI Workers** | Python + OpenRouter API | All SEO agent tasks, model-routed by task type |
| **Data Pipeline** | Python + Celery | Plugin data ingestion, crawling, analytics fetch, embedding gen |
| **Admin API** | FastAPI | Dashboard backend, billing, user management |

### 1.3 Event Bus — Core Backbone

All communication is event-driven. Every action is an event.

**Event Types:**

| Event | Producer | Consumers | Description |
|-------|----------|-----------|-------------|
| `site.connected` | Plugin | Orchestrator | New site connected, plan initial audit |
| `page.scanned` | Technical Scanner | Data Pipeline | Page HTML/metadata ready for processing |
| `fix.needed` | Orchestrator | Plugin | A fix is ready to apply |
| `fix.applied` | Plugin | Orchestrator | Confirmation that fix was applied |
| `content.needed` | User/Dashboard | Content Writer | User requested content creation |
| `content.published` | Plugin | Schema Agent, Orchestrator | New content detected |
| `weekly.scan` | Cron | Orchestrator | Scheduled weekly maintenance |
| `rank.check` | Cron | Rank Tracker | Scheduled keyword position check |
| `competitor.refresh` | Cron/Admin | Competitor Analyzer | Re-analyze competitor landscape |

---

## 2. Data Layer

### 2.1 Data Stores

| Store | Technology | Purpose |
|-------|-----------|---------|
| **Relational** | PostgreSQL | Users, sites, subscriptions, tasks, audit logs |
| **Vector DB** | Qdrant (self-hosted) | Semantic search, user context embeddings, content similarity |
| **Graph DB** | Neo4j | Niche knowledge graph: entities, topics, relationships |
| **Cache/Queue** | Redis | Session cache, event stream, task queue, rate limiting |
| **Object Store** | S3-compatible (MinIO) | Page snapshots, crawled assets, exported reports |

### 2.2 PostgreSQL Schema

```sql
-- Core tables (extendable):

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter',
    subscription_status VARCHAR(50) DEFAULT 'active',
    onboarded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'owner',
    password_hash VARCHAR(255) NOT NULL,
    openrouter_api_key VARCHAR(255),  -- encrypted at rest
    openrouter_model VARCHAR(100),    -- per-user model override
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    url VARCHAR(2048) NOT NULL,
    name VARCHAR(255),
    platform VARCHAR(50) DEFAULT 'wordpress',
    plugin_version VARCHAR(50),
    plugin_checksum VARCHAR(64),
    api_key_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, connected, degraded, disconnected
    last_heartbeat_at TIMESTAMP NULL,
    last_scan_at TIMESTAMP NULL,
    seo_score INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}',  -- plugin config, scan preferences
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, url)
);

CREATE TABLE site_heartbeats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
    domain_verified BOOLEAN DEFAULT FALSE,
    checksum_valid BOOLEAN DEFAULT FALSE,
    plugin_version VARCHAR(50),
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE onboarding_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    step VARCHAR(100) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    embedding_id VARCHAR(100),  -- reference to Qdrant vector ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    confidence FLOAT,  -- 0-1, auto-apply if > threshold
    auto_applied BOOLEAN DEFAULT FALSE,
    input_data JSONB,
    result_data JSONB,
    error_message TEXT,
    llm_model_used VARCHAR(100),
    llm_cost_cents INTEGER DEFAULT 0,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE auto_fixes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES sites(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id),
    fix_type VARCHAR(100) NOT NULL,  -- meta_title, meta_desc, schema, heading, alt_text, internal_link
    page_url VARCHAR(2048),
    original_value TEXT,
    new_value TEXT,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, applied, rejected, rolled_back
    applied_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    task_id UUID REFERENCES tasks(id),
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) DEFAULT 'openrouter',
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_cents NUMERIC(10, 4) DEFAULT 0,
    cached BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Vector DB (Qdrant) Collections

| Collection | Purpose | Vector Dimension | Payload |
|-----------|---------|------------------|---------|
| `{tenant_id}_user_context` | Onboarding answers, niche info | 1536 (text-embedding-3) | tenant_id, step, question, raw_answer |
| `{tenant_id}_page_embeddings` | Page content vectors | 1536 | url, title, word_count, last_updated |
| `{tenant_id}_keyword_clusters` | Related keyword groups | 1536 | keyword, volume, difficulty, cluster_id |
| `{tenant_id}_competitor_pages` | Competitor content embeddings | 1536 | competitor_domain, url, title |

Every collection is namespaced by tenant_id for data isolation.

### 2.4 Graph DB (Neo4j) — Knowledge Graph

**Nodes:**

| Label | Properties |
|-------|-----------|
| `Topic` | id, name, description, volume, difficulty, tenant_id |
| `Page` | id, url, title, word_count, published_at |
| `Entity` | id, name, type (Person/Org/Product/Concept) |
| `Keyword` | id, keyword, volume, difficulty, position |
| `Competitor` | id, domain, domain_authority |
| `ContentGap` | id, description, priority |

**Relationships:**

| Type | From | To | Properties |
|------|------|----|-----------|
| `COVERS` | Page | Topic | strength (0-1) |
| `RELATES_TO` | Topic | Topic | strength, type (parent/child/related) |
| `TARGETS` | Keyword | Topic | |
| `COMPETES_ON` | Competitor | Topic | competitor_strength |
| `GAPS_IN` | ContentGap | Topic | urgency |

**Purpose:** Enables RAG queries like "Which topics does user X have weak coverage on that their competitors rank for?" — the graph connects all dots.

---

> **Tech Decision:** Redis Streams chosen for Phase 1-2 (familiar infrastructure, reuses existing Redis, good enough throughput for MVP). NATS can be introduced in Phase 3+ if throughput requirements exceed Redis Streams' capabilities (e.g., 10k+ events/sec at scale). The event interface is abstracted behind a thin adapter so the backend can swap without changing producer/consumer code.

## 3. AI Agent Pipeline

### 3.1 Orchestrator

The Orchestrator is the central brain. It listens to events and dispatches pipeline stages.

**Logic:**

```
On event:
  1. Determine task type from event
  2. Load tenant context (onboarding answers, graph state, recent history)
  3. Break task into pipeline stages (ordered)
  4. For each stage:
     a. Check prerequisites met
     b. Dispatch to appropriate AI Worker
     c. Monitor completion
     d. If stage fails → retry (max 3), then notify admin
  5. After all stages complete → validate results
  6. If confidence > 90% AND risk is low → auto-apply fix
  7. If confidence < 90% → create recommendation for user review
  8. Emit completion event
```

**Confidence Gating:**
- **Auto-apply threshold:** >90% confidence for low-risk fixes (meta tags, alt text, schema)
- **Require review:** <90% confidence OR high-risk changes (content rewriting, URL changes)
- **Confidence calculated from:** LLM self-evaluation + historical fix success rate for similar tasks

### 3.2 AI Workers

| Worker | Trigger | Input | Output | Model Tier |
|--------|---------|-------|--------|-----------|
| **Technical Scanner** | `site.connected`, `scan.scheduled` | URL list, crawl config | Issues list, page inventory, CWV data | Cheap (extraction) |
| **Content Writer** | `content.needed` | Topic, keywords, graph context | Full article with AEO optimization | Premium |
| **Schema Generator** | `schema.needed`, `page.updated` | Page type, content, entities | JSON-LD schema markup | Cheap |
| **Keyword Researcher** | `keyword.research.needed` | Seed keywords, competitor data | Keyword clusters with metrics | Medium |
| **Competitor Analyzer** | `competitor.analysis.needed` | User domain, competitor domains | Gap analysis, opportunity map | Medium |
| **Rank Tracker** | `rank.check.scheduled` | Keywords, site URL | Current positions, change delta | Cheap (API only) |
| **AEO Optimizer** | `aeo.optimization.needed` | Existing content | Structured answers, FAQ blocks, snippet optimization | Premium |
| **CWV Engineer**\* | `cwv.fix.needed` | CWV metrics, page HTML | Specific fix instructions (CSS/JS/HTML changes) | Medium |

> \* CWV Engineer requires the PerformanceObserver JS snippet (built in Phase 5) for real-user metrics. Agent logic is built in Phase 5 alongside its data source.

### 3.3 RAG Pipeline

> **Phase Dependency:** Full RAG (Vector + Graph + PG) requires Phase 3. In Phase 2, agents operate with Vector DB + PostgreSQL context only — graph-dependent features (content gap analysis, competitor overlays) are deferred. The system degrades gracefully with a `requires_graph` flag on features.

Every AI task goes through RAG enrichment:

```
User Request
    │
    ▼
┌──────────────────────┐
│  1. Retrieve Context │
│  ┌─────────────────┐ │
│  │ Vector DB       │ │── Similar pages, user context, keyword clusters
│  │ Graph DB        │ │── Topic relationships, gaps, competitor data
│  │ PostgreSQL      │ │── Site config, historical data, onboarding answers
│  └─────────────────┘ │
└──────────────────────┘
    │
    ▼
┌──────────────────────┐
│  2. Build Prompt     │
│  ┌─────────────────┐ │
│  │ System: Niche   │ │── "You are an SEO expert for [niche]..."
│  │ Context: Graph  │ │── "Your site covers [topics], gaps in [areas]"
│  │ Examples: Past  │ │── "Previously, content like [X] performed well"
│  │ Instruction     │ │── "Write a 1500-word post targeting [keywords]"
│  └─────────────────┘ │
└──────────────────────┘
    │
    ▼
┌──────────────────────┐
│  3. LLM Call        │── Via OpenRouter (user's key or platform key)
│  4. Validate Output │── Check quality, relevance, safety
│  5. Store Result    │── Update graph, vector store, task log
│  6. Return          │
└──────────────────────┘
```

---

## 4. WordPress Plugin

### 4.1 Design Principle

**The plugin is thin.** All heavy processing happens server-side. The plugin is a data collector + fix applier + communication bridge.

### 4.2 Plugin Capabilities

**Connection & Auth:**
- API key + domain registration at activation
- Signed heartbeat every 15 minutes (HMAC-SHA256 with tenant secret)
- Automatic reconnection with exponential backoff

**Data Collection:**
- Full page inventory (titles, URLs, meta descriptions, headings)
- Content extraction (body text, word count, readability)
- Schema audit (what schema exists, what's missing)
- Internal link map (link graph between pages)
- Image inventory (alt text, file sizes, lazy loading status)
- Google Analytics data (if Site Kit plugin detected) — traffic, bounce rate, top pages
- Google Search Console data (if Site Kit detected) — impressions, clicks, avg position
- Core Web Vitals from real users (via injected JS snippet with PerformanceObserver)
- Active plugin list (detect conflicts)

**Fix Application:**
- Update meta titles and descriptions (via wp_postmeta)
- Update heading tags (H1-H6)
- Add/update alt text on images
- Inject/update JSON-LD schema (via wp_head hook)
- Insert internal links (with relevance scoring from API)
- Update Open Graph / Twitter Card tags
- Remove duplicate meta tags
- Fix broken internal links (301 redirect suggestions)
- Add/update canonical URLs
- Optimize image attributes (loading="lazy", decoding="async")

**Dashboard Widget:**
- Real-time SEO score
- Recent auto-fixes (with rollback option)
- Pending recommendations
- "One-click fix all" for low-risk items
- Quick action: "Write a new post" → opens AI content creator

**Content Editor Integration:**
- **Gutenberg sidebar panel:** AI-suggested title, meta description, internal links
- **Classic editor metabox:** Same suggestions
- **Real-time analysis:** As user types, check readability, keyword density, heading structure
- **Schema preview:** Visual preview of how search engines will see the page

**Anti-Tampering:**
- Plugin files checksum verified at each heartbeat
- If plugin is deactivated or license code removed → SaaS flags site as `degraded`
- Degraded sites still serve data but don't receive fixes until re-authenticated

### 4.3 Page Builder Compatibility

Most WordPress sites use page builders. The plugin must detect and adapt to the active builder for content extraction and fix application.

**Detection:** On first scan, detect active page builders (from active plugins list via `get_option('active_plugins')`). Store builder type per-site in `sites.config.builder`.

**Supported Builders & Integration Strategy:**

| Builder | Storage Format | Read Strategy | Write Strategy |
|---------|---------------|--------------|----------------|
| **Gutenberg (core)** | `wp_posts.post_content` (HTML comments) | Native `post_content` read | `wp_update_post()` for content |
| **Elementor** | `wp_postmeta._elementor_data` (JSON) + `_elementor_css` | Elementor's `\Elementor\Plugin::$instance->documents->get()` API | Elementor's API for controlled edits; for auto-fixes, modify meta tags separately (builder-agnostic) |
| **Kadence Blocks** | `wp_posts.post_content` (HTML with Kadence comments) | Native read + Kadence block parser | Content updates work natively; Kadence-specific CSS/JS optimizations require separate handling |
| **Droip** | Custom post type + serialized JSON in post meta | Droip API helpers if available, else raw meta parsing | Meta tag fixes only (builder-agnostic); content editing within Droip requires their API |
| **Beaver Builder** | `wp_postmeta._fl_builder_data` (JSON) + `_fl_builder_draft` | Beaver Builder's `FLBuilderModel::get_node_data()` | Meta tag fixes; content changes best done via their API |
| **Divi** | `wp_posts.post_content` (shortcodes) + `_et_pb_custom_css` | Shortcode parsing for content extraction | Meta tag fixes; full content edits via Divi API |
| **WPBakery** | `wp_posts.post_content` (shortcodes) + custom meta | Shortcode parsing | Meta tag fixes |

**Universal (Builder-Agnostic) Fixes — always safe regardless of builder:**
- Meta titles, descriptions (`wp_postmeta._yoast_wpseo_title`, `_aioseo_title`, or direct `post_title`)
- JSON-LD schema injection (via `wp_head` hook)
- Open Graph / Twitter Card tags (via `wp_head` hook)
- Canonical URLs (via `wp_head` hook or Yoast/AIOSEO meta)
- Alt text on images (stored in `wp_postmeta` regardless of builder)
- Internal links (stored in `post_content` — some builders need care)

**Builder-Aware Fixes — require builder detection:**
- Content rewriting inside builder blocks (must be done via builder's own API or saved as draft for user approval)
- Heading restructuring within builder elements
- CSS/JS optimization for Core Web Vitals (different builders inline differently)
- Image lazy loading / dimension attributes (builder-specific wrappers)

**Fallback:** If builder is not recognized or is unsupported, plugin applies only universal fixes and flags content-level improvements as "manual review recommended" in the dashboard.

### 4.4 Plugin Tech Stack

- PHP 8.0+ (WordPress plugin standard)
- JS/React for Gutenberg block editor integration
- Webpack for asset bundling
- REST API calls to SaaS backend
- Local storage for offline queue (if SaaS temporarily unreachable)
- Builder detection library (per-builder adapters)

---

## 5. User Onboarding & RAG Personalization

### 5.1 Onboarding Flow

Triggered after plugin activation + first site connection. User is redirected to a hosted onboarding wizard.

**Step 1: Niche & Goals**
- "What's your website about?" (free text + auto-suggest from site content analysis)
- "What type of website is this?" (Blog / E-commerce / Local Business / SaaS / Portfolio / Media)
- "What's your primary goal?" (Increase traffic / Generate leads / Sell products / Build authority)

**Step 2: Target Audience**
- "Who is your ideal reader/customer?" (free text)
- "What problem do you solve for them?" (free text)
- "What tone should your content have?" (Professional / Conversational / Technical / Storytelling)

**Step 3: Keywords**
- "What are the 3-5 most important keywords for your business?" (auto-suggest from site crawl)
- "What topics do you want to be known for?" (free text, comma separated)
- "What search queries bring you the most traffic?" (auto-detected if analytics connected)

**Step 4: Competitors**
- "Who are your top competitors?" (user enters 1-3 domains OR we auto-detect from SemRush)
- "What do they do better than you?" (optional free text)

**Step 5: Content Strategy**
- "How often do you publish?" (Daily / Weekly / Bi-weekly / Monthly)
- "What content types work best?" (Articles / Videos / Infographics / Podcasts)
- "Do you have seasonal content needs?" (free text)

### 5.2 Personalization Pipeline

```
Onboarding Answers
    │
    ├── PostgreSQL (structured storage)
    │
    ├── Embedding & Store in Qdrant
    │   └── Collection: {tenant_id}_user_context
    │   └── Vector: text-embedding-3-small (1536d)
    │   └── Retrieval: "Find relevant onboarding context" → top-K most related
    │
    └── Entity Extraction & Graph Insertion
        └── Extract niche entities, topics, competitors
        └── Insert into Neo4j: (Topic {name})-[RELATES_TO]->(Topic)
        └── Link to existing site pages
```

Every AI prompt is enriched with:
```python
context = {
    "niche": onboarding.answers["niche"],
    "goals": onboarding.answers["goals"],
    "target_audience": onboarding.answers["audience"],
    "tone": onboarding.answers["tone"],
    "topics_covered": graph.topics_for_tenant(tenant_id, limit=20),
    "topical_gaps": graph.content_gaps_for_tenant(tenant_id, limit=10),
    "competitor_insights": competitor_analyzer.insights(tenant_id),
}
```

---

## 6. Admin Dashboard & Billing

### 6.1 Dashboard Pages

| Page | Route | Purpose |
|------|-------|---------|
| Overview | `/` | Global stats: total users, active sites, revenue, AI usage |
| Tenants | `/tenants` | List all tenants, filter by plan/status |
| Tenant Detail | `/tenants/:id` | Single tenant: sites, usage, billing, activity |
| Sites | `/sites` | All connected sites with status, score, last scan |
| Site Detail | `/sites/:id` | Deep SEO audit for a specific site |
| LLM Usage | `/llm-usage` | Cost breakdown per user, per model, per task type |
| Model Config | `/models` | Set global default model, per-user overrides, routing rules |
| Tasks | `/tasks` | View all tasks, filter by status/type/tenant |
| Audit Log | `/audit` | All auto-fixes, who/what/when |
| Billing | `/billing` | Plans, pricing, revenue, failed payments |
| Alerts | `/alerts` | Configure alerts (LLM spend spike, site down, etc.) |
| System | `/system` | Service health, queue depth, error logs |

### 6.2 Billing Tiers

| Feature | Free | Starter ($29/mo) | Pro ($79/mo) | Agency ($199/mo) |
|---------|------|-------------------|--------------|-------------------|
| Sites | 1 | 3 | 10 | 50+ |
| AI Actions/month | 50 | 500 | 2,000 | 10,000 |
| Auto-fix technical SEO | ❌ (manual only) | ✅ | ✅ | ✅ |
| Semantic content analysis | ❌ | ✅ | ✅ | ✅ |
| AI content generation | ❌ | 5 articles/mo | 50 articles/mo | Unlimited |
| Schema automation | ❌ | ✅ | ✅ | ✅ |
| AEO optimization | ❌ | ❌ | ✅ | ✅ |
| Core Web Vitals fixes | ❌ | ❌ | ✅ | ✅ |
| Rank tracking | 5 keywords | 50 keywords | 200 keywords | 1,000 keywords |
| Competitor analysis | ❌ | 1 competitor | 3 competitors | 10 competitors |
| SemRush integration | ❌ | ✅ (API) | ✅ (API + CSV) | ✅ (full) |
| Bring your own API key | ✅ | ✅ | ✅ | ✅ |
| White-label | ❌ | ❌ | ❌ | ✅ |
| Team seats | 1 | 1 | 3 | 10+ |
| Priority support | ❌ | ❌ | ✅ | ✅ |

### 6.3 Payment
- Stripe integration
- Monthly and annual billing (annual = 2 months free)
- Usage-based overage for AI actions beyond plan limit
- Prorated upgrades/downgrades

---

## 7. Automation Scenarios

### 7.1 New Site Connection (Full Autopilot)

1. User installs plugin → enters API key → `site.connected` event fires
2. Orchestrator plans audit pipeline:
   - **Stage 1:** Technical Scanner crawls all pages (up to 50 for free/Starter, unlimited for Pro+)
   - **Stage 2:** Content Analyst processes each page → embeddings in Qdrant, entities in Neo4j
   - **Stage 3:** Keyword Researcher queries SemRush against found keywords → opportunities
   - **Stage 4:** Competitor Analyzer identifies top 3 competitors (from SemRush or onboarding)
   - **Stage 5:** Orchestrator cross-references all data → generates priority fix list

3. Auto-apply (high confidence, low risk):
   - Missing meta descriptions → generate from page content
   - Missing alt text → describe images
   - Missing JSON-LD schema → generate Organization + Website + Article schema
   - Duplicate meta tags → remove duplicates
   - Missing canonical URLs → add self-referencing canonicals
   - Open Graph / Twitter Card tags → generate from meta data

4. Flag for review (medium confidence or higher risk):
   - Title tag improvements (more keyword-rich)
   - Heading structure fixes (only one H1, proper hierarchy)
   - Content gaps (topics not covered)
   - Internal link suggestions

5. Weekly follow-up:
   - Rescan → compare scores → measure improvement → report

### 7.2 AI Content Creation

1. User clicks "Write Article" in plugin dashboard or SaaS dashboard
2. User provides: topic, target keywords (optional), tone (optional)
3. Content Writer agent:
   - Retrieves user's niche context from RAG
   - Analyzes graph to find related topics and coverage gaps
   - Queries SemRush for keyword data (volume, trends, SERP features)
   - Researches competitor content on same topic
   - Generates outline → user approves → generates full article
   - Article includes: AEO-optimized answers, FAQ schema, internal links to existing content
4. Plugin creates WordPress draft → user reviews and publishes
5. Schema Generator creates Article JSON-LD → plugin applies on publish
6. `content.published` event fires:
   - Vector DB updated with new content
   - Graph updated with new topic coverage
   - Internal links re-evaluated across all pages

### 7.3 Weekly Auto-Maintenance

Cron trigger → orchestrator:

1. Full technical re-scan (check for regressions)
2. Rank tracking update (keyword position changes)
3. Competitor re-analysis (new competitor content, changes)
4. Score update:
   - Technical SEO score
   - Content quality score
   - Topical authority score
   - Average keyword position
5. Delta report:
   - "Your SEO score improved from 62 to 71 (+14%)"
   - "3 issues were automatically fixed"
   - "You gained 4 keyword positions, lost 2"
   - "Your competitor X published 3 new articles about [topics]"
   - "Recommended: Write about [content gap] to close the gap with competitor X"

### 7.4 CWV Optimization

1. Plugin collects real-user CWV metrics via PerformanceObserver
2. If LCP > 2.5s or CLS > 0.1 or INP > 200ms → CWV event fires
3. CWV Engineer analyzes page:
   - LCP: Identify largest element, optimize image/font loading
   - CLS: Find layout-shifting elements, suggest dimensions
   - INP: Identify slow event handlers, suggest debouncing
4. If fix is CSS/JS/HTML → plugin applies automatically
5. If fix requires server changes (hosting, CDN) → recommend with instructions

---

## 8. Anti-Piracy & Tenant Security

### 8.1 Domain Binding

- Every plugin activation generates a unique tenant secret stored server-side
- Plugin signs each heartbeat with: `HMAC-SHA256(tenant_secret, domain + timestamp)`
- API Gateway verifies signature AND checks request domain matches registered domain
- Key rotation: Tenant secret rotated every 30 days, plugin auto-updates

### 8.2 Heartbeat System

- Plugin sends heartbeat every 15 minutes
- Heartbeat payload: `{ site_id, domain, plugin_version, checksum, timestamp, signature }`
- Server validates: domain matches, checksum matches, signature valid
- Missed 4 consecutive heartbeats (1 hour) → site status set to `degraded`
- In `degraded` mode: plugin can still collect data but cannot apply fixes
- Re-activation requires fresh heartbeat with valid credentials

### 8.3 Plugin Integrity

- Plugin build process generates a checksum manifest of all PHP/JS files
- Checksum stored on SaaS at activation time
- Each heartbeat includes current checksum → compare against stored
- If checksum doesn't match → plugin has been modified → SaaS refuses connections
- Licensed plugin files cannot be copied to another domain — domain mismatch = rejection

### 8.4 API Key Scoping

- API keys are domain-scoped: key generated for `example.com` rejected on `other.com`
- Key format: `zenseo_{domain_hash}_{random}` (prefix identifies the site)
- Rate limits per-site, not per-key (sharing a key still shares quota)
- Admin can revoke/reissue keys instantly

### 8.5 Suspicious Activity Detection

- Dashboard shows IP geo-location for last 100 API calls per site
- Flags: same account accessed from 3+ countries in 1 hour
- Flags: API call volume 10x above normal
- Flags: rapid domain changes (site URL changed 3+ times in 24h)
- Flags: plugin deactivation/re-activation cycling
- Suspicious activities trigger admin alert + temporary rate limit increase

### 8.6 Data Isolation

- PostgreSQL: Row-Level Security (RLS) on all tables by `tenant_id`
- Qdrant: Separate collections per tenant (`{tenant_id}_collection_name`)
- Neo4j: Every node tagged with `tenant_id`, Cypher queries filtered by tenant
- Redis: Key prefix per tenant (`{tenant_id}:key`)
- S3: Prefix-based isolation (`/tenants/{tenant_id}/...`)

### 8.7 License Enforcement API

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/license/validate` | Validate license key for domain |
| `POST /api/v1/license/activate` | Activate license for domain |
| `POST /api/v1/license/deactivate` | Deactivate license (domain change) |
| `GET /api/v1/license/status` | Current license status |
| `POST /api/v1/license/heartbeat` | 15-min heartbeat with signed payload |

---

## 9. OpenRouter & LLM Cost Management

### 9.1 Bring Your Own Key (BYOK)

- User provides their OpenRouter API key during onboarding or in settings
- Key stored encrypted (AES-256-GCM) in PostgreSQL `users.openrouter_api_key`
- Decrypted only in-memory when making LLM calls for that user
- User can rotate their key anytime

**Routing Logic (in every AI Worker):**

```python
def get_llm_config(user_id, task_type):
    user = get_user(user_id)
    tenant = get_tenant(user.tenant_id)

    if user.openrouter_api_key:
        # User provides their own key
        return LLMConfig(
            api_key=decrypt(user.openrouter_api_key),
            model=user.openrouter_model or tenant.default_model or "anthropic/claude-sonnet-4",
            provider="openrouter"
        )
    else:
        # Use platform key (counted against their plan's AI actions)
        return LLMConfig(
            api_key=PLATFORM_OPENROUTER_KEY,
            model=tenant.default_model or "openai/gpt-4o-mini",
            provider="openrouter"
        )
```

### 9.2 Admin Model Configuration

**Global Defaults (in Admin Dashboard → Models):**

| Setting | Description | Example |
|---------|-------------|---------|
| Default Model | Model used when user has no override | `anthropic/claude-sonnet-4` |
| Content Writing Model | Model for content generation (premium tier) | `openai/gpt-4o` |
| Analysis Model | Model for extraction/classification | `openai/gpt-4o-mini` |
| Keyword Model | Model for keyword research | `openai/gpt-4o-mini` |
| Max Tokens | Per-request limit | 8192 |
| Temperature | Default creativity | 0.7 |
| Cache TTL | LLM response cache duration | 24 hours |

**Per-User Override:**
- Admin can set a specific model for any user
- Overrides both the user's own choice and the global default
- Useful for: testing new models, giving premium users better models, throttling abusive users

**Tiered Model Routing (configurable per tenant plan):**

```
Free/Starter:
  - Content: gpt-4o-mini
  - All other tasks: gpt-4o-mini

Pro:
  - Content: claude-sonnet-4
  - AEO: claude-sonnet-4
  - Analysis: gpt-4o-mini
  - Keyword: gpt-4o-mini

Agency:
  - Content: claude-sonnet-4 or gpt-4o
  - AEO: claude-opus-4 or gpt-4o
  - All tasks: best available
```

### 9.3 Cost Optimization

**Semantic Caching:**
- Cache LLM responses keyed by: `hash(prompt + model + niche_context)`
- Cache store: Redis with TTL (configurable, default 24h)
- Estimated 30-40% cache hit rate for common SEO tasks (meta descriptions, schema, alt text)
- Cache invalidated when site content changes significantly

**Tiered Model Selection:**
- Not all tasks need premium models
- Extraction/classification → cheap models
- Content writing → premium models
- Dynamic routing based on task type (configurable)

**Usage Monitoring:**
- Real-time LLM usage dashboard (cost per user, per task type, per model)
- Daily cost alerts: "User X spent $Y on LLM calls today (200% above average)"
- Monthly cost cap per user (configurable by admin)
- Auto-switch to cheaper model if user exceeds cost threshold

**Cost Reporting:**

| Metric | Description |
|--------|-------------|
| Total LLM spend | Platform-wide cost |
| Cost per user | By tenant, with breakdown by task type |
| Cost per task type | Content vs Technical vs Schema vs Keyword |
| Cost per model | gpt-4o vs claude-3.5 vs others |
| Cache hit rate | % of requests served from cache |
| Savings from BYOK | How much platform saved because users brought their own keys |

---

## 10. SemRush Integration

### 10.1 API Integration

**Endpoints used:**

| SemRush API | Purpose | Frequency |
|-------------|---------|-----------|
| Domain Analytics → Domain Overview | Domain authority, traffic, top keywords | Weekly |
| Domain Analytics → Organic Research | Organic keyword positions, competitors | Weekly |
| Domain Analytics → Backlink Overview | Backlink profile, referring domains | Weekly |
| Keyword Analytics → Keyword Overview | Keyword volume, difficulty, CPC | On demand |
| Keyword Analytics → Keyword Magic | Related keywords, question-based, long-tail | On demand |
| Domain Analytics → Competitors | Identify organic competitors | Weekly |
| Traffic Analytics | Traffic sources, top pages, geography | Weekly |

**Cost model:** The platform maintains a primary SemRush API subscription (paid by us). API calls are pooled across all tenants. Per-tenant daily limits prevent one user from exhausting the pool. Pro+ plan tiers include full API access in their subscription price. For large-scale Agency accounts requiring dedicated SemRush quota, the cost can be passed through as an add-on fee.

**Alternative:** Users on any plan can upload SemRush CSV exports instead of using the live API — this is free for us and gives users full control over their data.

### 10.2 CSV Import

- Admin/user can upload SemRush CSV exports for any report
- CSV parser extracts: keyword data, competitor data, backlink data
- Data merged with API data (CSV fills gaps that API might miss)
- CSV data tagged with import timestamp in DB for freshness tracking

### 10.3 Competitor Analysis Flow

```
1. Identify competitors (SemRush API + user input)
2. For each competitor:
   a. Get top organic keywords
   b. Get backlink profile
   c. Get top pages by traffic
   d. Compare vs user's content graph
3. Generate gap analysis:
   - "Competitor X ranks for 47 keywords you don't"
   - "You have no content covering: [topic list]"
   - "Competitor X has 3x more backlinks to their [topic] content"
4. Prioritize gaps:
   - High priority: high volume, low difficulty, competitor dominates
   - Medium: moderate opportunity
   - Low: already partially covered
```

---

## 11. Implementation Phases

### Phase 1: Foundation (Weeks 1-4)
- Project scaffolding (monorepo, Docker, CI/CD)
- PostgreSQL schema + migrations
- API Gateway with auth, rate limiting, tenant isolation
- Redis Streams event bus setup
- Basic WordPress plugin (connection, heartbeat, domain binding)
- Admin dashboard: login, tenant listing, basic site overview

### Phase 2: AI Pipeline Core (Weeks 5-8)
- Orchestrator agent (event handling, task planning, confidence gating)
- OpenRouter integration (BYOK + platform keys, model config)
- Event bus with all core event types
- Technical Scanner agent (crawl, meta analysis, technical audit)
- Schema Generator agent (Organization, Website, Article, FAQ, LocalBusiness)
- Qdrant setup + embedding pipeline
- RAG context builder

### Phase 3: Data & Personalization (Weeks 9-11)
- User onboarding wizard (5-step flow)
- Neo4j knowledge graph setup
- Entity extraction pipeline (pages → entities → graph)
- Content embedding pipeline (pages → vectors → Qdrant)
- Onboarding answers → embedding → Qdrant
- RAG integration with all AI Workers

### Phase 4: Advanced AI Agents (Weeks 12-15)
- Content Writer agent (with AEO optimization)
- Keyword Researcher agent (SemRush API + graph analysis)
- Competitor Analyzer agent (SemRush + graph gap analysis)
- Rank Tracker agent
- AEO Optimizer agent

### Phase 5: Plugin Full Features + CWV (Weeks 16-18)
- Page builder detection system (Elementor, Kadence, Droip, Beaver Builder, Divi, WPBakery)
- Builder-aware content extraction adapters per supported builder
- All fix application types (meta, schema, headings, alt text, internal links) — universal + builder-aware
- Gutenberg sidebar panel + Classic editor metabox
- Plugin dashboard widget (score, recent fixes, quick actions)
- Content editor real-time analysis
- JS snippet for CWV data collection
- CWV Engineer agent (now has data source from JS snippet)
- Offline queue for intermittent connectivity

### Phase 6: Anti-Piracy & Admin (Weeks 19-20)
- Full heartbeat system with integrity verification
- Suspicious activity detection + alerts
- Admin dashboard: LLM usage/cost dashboard, model config UI, alerts config
- License management API
- Automated domain validation

### Phase 7: Billing & Launch (Weeks 21-22)
- Stripe integration (subscriptions, metered billing)
- Tiered plan enforcement (feature gating per plan)
- Usage tracking and overage billing
- Onboarding email sequence
- Public landing page + docs
- Beta launch → GA launch

---

*Document Version: 1.1*
*Created: 2026-05-19*
*Status: Design Document*
