# ZenSEO AI - Admin Dashboard Specification

## 1. Project Overview

**Project Name:** ZenSEO AI Admin Dashboard  
**Type:** B2B SaaS Admin Panel  
**Core Functionality:** Centralized management platform for SEO service provider to monitor subscribers, their connected websites, API usage, SEO results, backend services, and AI agent activity.  
**Target Users:** SaaS owner / Administrator  
**Tech Stack:** React + TypeScript (Vite) | FastAPI (Python) | PostgreSQL | Redis

---

## 2. UI/UX Design

### 2.1 Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER (Logo | Search | Notifications | Profile)           │
├──────────┬───────────────────────────────────────────────────┤
│          │                                                    │
│  SIDEBAR │              MAIN CONTENT AREA                    │
│          │                                                    │
│  - Users │   (Dynamic based on selected menu item)          │
│  - Sites │                                                    │
│  - API   │                                                    │
│  - Results│                                                   │
│  - Backend│                                                   │
│  - AI Logs│                                                   │
│          │                                                    │
└──────────┴───────────────────────────────────────────────────┘
```

**Layout Specifications:**
- **Sidebar:** 240px fixed width, collapsible to 64px (icon only)
- **Header:** 64px fixed height
- **Content Area:** Fluid, responsive grid
- **Breakpoints:** Mobile (<768px), Tablet (768-1024px), Desktop (>1024px)

### 2.2 Visual Design

**Color Palette:**
| Role | Color | Hex |
|------|-------|-----|
| Primary | Deep Indigo | #4F46E5 |
| Primary Hover | Indigo 600 | #4338CA |
| Secondary | Slate Gray | #64748B |
| Accent | Emerald | #10B981 |
| Warning | Amber | #F59E0B |
| Error | Rose | #F43F5E |
| Background | White | #FFFFFF |
| Surface | Slate 50 | #F8FAFC |
| Border | Slate 200 | #E2E8F0 |
| Text Primary | Slate 900 | #0F172A |
| Text Secondary | Slate 500 | #64748B |

**Typography:**
- **Font Family:** Inter (sans-serif), JetBrains Mono (code/logs)
- **Headings:** H1: 28px/700, H2: 24px/600, H3: 20px/600, H4: 16px/600
- **Body:** 14px/400, Small: 12px/400
- **Line Height:** 1.5 for body, 1.2 for headings

**Spacing System:**
- Base unit: 4px
- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64px

**Visual Effects:**
- **Card Shadow:** 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)
- **Elevated Shadow:** 0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)
- **Border Radius:** 6px (buttons), 8px (cards), 12px (modals)
- **Transitions:** 150ms ease-out

### 2.3 Navigation

**Sidebar Items:**
| Icon | Label | Route |
|------|-------|-------|
| 👥 | Users | `/users` |
| 🌐 | Websites | `/websites` |
| 🔑 | API Keys | `/api-keys` |
| 📊 | Results | `/results` |
| ⚙️ | Backend | `/backend` |
| 🤖 | AI Logs | `/ai-logs` |

**Navigation Behavior:**
- Active state: Primary color background with 10% opacity, left border accent
- Hover state: Surface background color
- Collapsed: Show icon only with tooltip on hover

### 2.4 Component Library

**Core Components:**

1. **DataTable**
   - Sortable columns
   - Pagination (10/25/50/100 per page)
   - Row selection (single/multi)
   - Inline actions (edit/delete)
   - Export (CSV/JSON)

2. **StatCard**
   - Icon, Label, Value, Trend indicator
   - Optional chart sparkline
   - Click to drill-down

3. **StatusBadge**
   - States: active, inactive, pending, error, success
   - Color-coded dots

4. **SearchBar**
   - Debounced input (300ms)
   - Filter dropdown support
   - Clear button

5. **Modal**
   - Sizes: sm (400px), md (560px), lg (720px)
   - Header, Body, Footer sections
   - Close on backdrop click (configurable)

6. **Tabs**
   - Horizontal layout
   - Active indicator underline

7. **Toast/Notification**
   - Position: top-right
   - Auto-dismiss: 5 seconds
   - Types: success, error, warning, info

8. **CodeEditor/LogViewer**
   - Syntax highlighting for JSON
   - Line numbers
   - Copy button

---

## 3. Data Models

### 3.1 Database Schema (PostgreSQL)

```sql
-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(50) DEFAULT 'active',
    api_calls_used INTEGER DEFAULT 0,
    api_calls_limit INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

-- Websites Table
CREATE TABLE websites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    url VARCHAR(2048) NOT NULL,
    name VARCHAR(255),
    platform VARCHAR(50) DEFAULT 'wordpress',
    api_key VARCHAR(64) UNIQUE,
    status VARCHAR(50) DEFAULT 'connected',
    last_scan_at TIMESTAMP NULL,
    seo_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API Keys Table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_prefix VARCHAR(20) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    label VARCHAR(100),
    rate_limit INTEGER DEFAULT 1000,
    calls_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- SEO Results Table
CREATE TABLE seo_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    result_type VARCHAR(50) NOT NULL,
    score INTEGER,
    data JSONB,
    issues JSONB DEFAULT '[]',
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks Table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    input_data JSONB,
    result_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Error Logs Table
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level VARCHAR(20) NOT NULL,
    source VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Agent Logs Table
CREATE TABLE agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    task_id VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Sessions (Redis for caching)
-- Key pattern: session:{user_id}
-- TTL: 24 hours
```

### 3.2 TypeScript Interfaces

```typescript
// User
interface User {
  id: string;
  email: string;
  name: string;
  plan: 'free' | 'starter' | 'pro' | 'enterprise';
  subscriptionStatus: 'active' | 'inactive' | 'cancelled' | 'trial';
  apiCallsUsed: number;
  apiCallsLimit: number;
  createdAt: Date;
  updatedAt: Date;
}

// Website
interface Website {
  id: string;
  userId: string;
  url: string;
  name: string;
  platform: 'wordpress' | 'custom' | 'shopify' | 'wix';
  apiKey: string;
  status: 'connected' | 'disconnected' | 'error';
  lastScanAt: Date | null;
  seoScore: number;
  createdAt: Date;
}

// API Key
interface APIKey {
  id: string;
  userId: string;
  keyPrefix: string;
  label: string;
  rateLimit: number;
  callsCount: number;
  lastUsedAt: Date | null;
  createdAt: Date;
  expiresAt: Date | null;
  isActive: boolean;
}

// SEO Result
interface SEOResult {
  id: string;
  websiteId: string;
  resultType: 'technical' | 'content' | 'ranking' | 'backlinks' | 'core-web-vitals';
  score: number;
  data: Record<string, any>;
  issues: Issue[];
  scannedAt: Date;
}

interface Issue {
  type: 'error' | 'warning' | 'info';
  category: string;
  message: string;
  fix?: string;
}

// Task
interface Task {
  id: string;
  websiteId: string;
  taskType: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high';
  inputData: Record<string, any>;
  resultData: Record<string, any> | null;
  errorMessage: string | null;
  startedAt: Date | null;
  completedAt: Date | null;
  createdAt: Date;
}

// Error Log
interface ErrorLog {
  id: string;
  level: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  source: string;
  message: string;
  stackTrace: string | null;
  context: Record<string, any> | null;
  createdAt: Date;
}

// AI Agent Log
interface AgentLog {
  id: string;
  agentType: string;
  taskId: string | null;
  status: 'started' | 'running' | 'completed' | 'failed';
  inputData: Record<string, any>;
  outputData: Record<string, any> | null;
  executionTimeMs: number;
  createdAt: Date;
}
```

---

## 4. API Endpoints

### 4.1 Admin API Routes

```
Base URL: /api/admin/v1
Auth: Bearer Token (admin access)
Rate Limit: 1000 req/min
```

#### Users Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all users (paginated) |
| GET | `/users/:id` | Get user details |
| POST | `/users` | Create new user |
| PUT | `/users/:id` | Update user |
| DELETE | `/users/:id` | Soft delete user |
| GET | `/users/:id/websites` | Get user's websites |
| PUT | `/users/:id/plan` | Change user's plan |

#### Websites Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/websites` | List all websites |
| GET | `/websites/:id` | Get website details |
| DELETE | `/websites/:id` | Disconnect website |
| GET | `/websites/:id/results` | Get website SEO results |
| POST | `/websites/:id/scan` | Trigger new scan |
| GET | `/websites/:id/tasks` | Get website tasks |

#### API Keys Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api-keys` | List all API keys |
| GET | `/api-keys/:id` | Get key details |
| POST | `/api-keys` | Generate new key |
| DELETE | `/api-keys/:id` | Revoke key |
| PUT | `/api-keys/:id` | Update key (rate limit, label) |

#### Results & Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/results` | List all results |
| GET | `/results/summary` | Get aggregate stats |
| GET | `/results/websites/:id/history` | Get website result history |
| GET | `/results/issues` | List all issues |

#### Backend & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/backend/status` | Get backend service status |
| GET | `/backend/health` | Health check |
| GET | `/logs/errors` | Get error logs (filterable) |
| GET | `/logs/errors/:id` | Get error detail |
| GET | `/tasks` | List tasks (filterable) |
| GET | `/tasks/:id` | Get task details |

#### AI Agent Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ai-logs` | List agent logs (paginated) |
| GET | `/ai-logs/agents` | List agent types |
| GET | `/ai-logs/:id` | Get agent log detail |
| GET | `/ai-logs/stats` | Get agent statistics |

### 4.2 API Contract (JSON Schema)

```json
{
  "users": {
    "list": {
      "GET /api/admin/v1/users": {
        "query": {
          "page": "integer",
          "limit": "integer",
          "search": "string",
          "plan": "string",
          "status": "string",
          "sortBy": "string",
          "sortOrder": "asc|desc"
        },
        "response": {
          "data": ["User"],
          "meta": {
            "total": "integer",
            "page": "integer",
            "limit": "integer",
            "totalPages": "integer"
          }
        }
      }
    },
    "create": {
      "POST /api/admin/v1/users": {
        "body": {
          "email": "string",
          "name": "string",
          "password": "string",
          "plan": "free|starter|pro|enterprise"
        },
        "response": { "User" }
      }
    }
  },
  "websites": {
    "list": {
      "GET /api/admin/v1/websites": {
        "query": {
          "page": "integer",
          "limit": "integer",
          "userId": "string",
          "status": "string",
          "platform": "string",
          "search": "string"
        },
        "response": {
          "data": ["Website"],
          "meta": { "total": "integer", "page": "integer", "limit": "integer" }
        }
      }
    },
    "scan": {
      "POST /api/admin/v1/websites/:id/scan": {
        "body": {
          "scanTypes": ["technical", "content", "core-web-vitals"]
        },
        "response": {
          "taskId": "string",
          "message": "Scan initiated"
        }
      }
    }
  },
  "apiKeys": {
    "list": {
      "GET /api/admin/v1/api-keys": {
        "query": {
          "page": "integer",
          "limit": "integer",
          "userId": "string",
          "isActive": "boolean"
        },
        "response": {
          "data": ["APIKey"],
          "meta": { "total": "integer" }
        }
      }
    },
    "create": {
      "POST /api/admin/v1/api-keys": {
        "body": {
          "userId": "string",
          "label": "string",
          "rateLimit": "integer",
          "expiresIn": "integer (days)"
        },
        "response": {
          "apiKey": "string",
          "apiKeyId": "string"
        }
      }
    }
  },
  "results": {
    "summary": {
      "GET /api/admin/v1/results/summary": {
        "response": {
          "totalWebsites": "integer",
          "avgSeoScore": "integer",
          "totalIssues": "integer",
          "issuesByType": {
            "error": "integer",
            "warning": "integer",
            "info": "integer"
          },
          "topPerformers": ["Website"],
          "needsAttention": ["Website"]
        }
      }
    }
  },
  "backend": {
    "status": {
      "GET /api/admin/v1/backend/status": {
        "response": {
          "api": { "status": "online|offline", "uptime": "string", "version": "string" },
          "database": { "status": "connected|disconnected", "latency": "integer" },
          "redis": { "status": "connected|disconnected" },
          "agents": { "active": "integer", "idle": "integer" }
        }
      }
    }
  },
  "logs": {
    "errors": {
      "GET /api/admin/v1/logs/errors": {
        "query": {
          "page": "integer",
          "limit": "integer",
          "level": "error|critical",
          "source": "string",
          "from": "datetime",
          "to": "datetime",
          "search": "string"
        },
        "response": {
          "data": ["ErrorLog"],
          "meta": { "total": "integer" }
        }
      }
    },
    "agents": {
      "GET /api/admin/v1/ai-logs": {
        "query": {
          "page": "integer",
          "limit": "integer",
          "agentType": "string",
          "status": "string",
          "from": "datetime",
          "to": "datetime"
        },
        "response": {
          "data": ["AgentLog"],
          "meta": { "total": "integer" }
        }
      }
    }
  }
}
```

---

## 5. Page-by-Page Features

### 5.1 Users Page (`/users`)

**Purpose:** Manage all subscribed users

**Features:**
- **User Table**
  - Columns: Avatar, Name, Email, Plan, Status, API Usage, Websites, Created, Actions
  - Sortable by all columns
  - Filter by plan (free/starter/pro/enterprise) and status
  - Search by name or email

- **User Actions:**
  - View: Opens user detail modal with full profile
  - Edit: Edit name, email, plan
  - Delete: Soft delete with confirmation
  - Reset Password: Generate reset link

- **Stats Cards (Top):**
  - Total Users
  - Active Subscriptions
  - Free Trial Users
  - New This Month

- **Add User Button:** Opens create user modal

**User Detail Modal Tabs:**
- Overview: Profile info, plan details, usage
- Websites: List of user's connected websites
- API Keys: List of API keys
- Activity: Recent actions/logs

### 5.2 Websites Page (`/websites`)

**Purpose:** View and manage all connected websites across users

**Features:**
- **Website Table**
  - Columns: Site Name, URL, Owner (User), Platform, Status, SEO Score, Last Scan, Actions
  - Status indicators: connected (green), disconnected (gray), error (red)
  - SEO Score: Color-coded (0-40 red, 41-70 yellow, 71-100 green)

- **Filters:**
  - By user (dropdown)
  - By status (dropdown)
  - By platform (dropdown)
  - By score range (slider)

- **Actions:**
  - View Details: Shows full website analysis
  - Trigger Scan: Manual re-scan
  - Disconnect: Remove connection
  - View Results: Jump to results page filtered

- **Stats Cards:**
  - Total Connected
  - Active Scans
  - Avg SEO Score
  - Issues Found

### 5.3 API Keys Page (`/api-keys`)

**Purpose:** Manage API keys for user access

**Features:**
- **API Key Table**
  - Columns: Label, User, Key (masked), Rate Limit, Usage, Last Used, Created, Expires, Status, Actions
  - Show first 8 chars + asterisks (e.g., `zenseo_abc...`)

- **Filters:**
  - By user
  - By status (active/expired/revoked)

- **Actions:**
  - Generate: Opens create key modal
  - Revoke: Disable key (confirmation)
  - Edit: Change label or rate limit
  - Copy: Copy full key to clipboard (only shown once on creation)

- **Create Key Modal:**
  - Select user
  - Label (optional)
  - Rate limit (requests/day)
  - Expiration (days, optional)

- **Stats Cards:**
  - Total Keys
  - Active Keys
  - Total API Calls (24h)

### 5.4 Results Page (`/results`)

**Purpose:** View SEO analysis results across all websites

**Features:**
- **Overview Stats Cards:**
  - Average SEO Score (with trend)
  - Total Issues (error/warning/info breakdown)
  - Pages Scanned
  - Keywords Tracked

- **Results Tabs:**
  - Overview: Aggregate stats
  - Technical: Technical SEO issues
  - Content: Content quality scores
  - Rankings: Keyword positions
  - Core Web Vitals: LCP, INP, CLS metrics

- **Issue Table (when "Technical" tab selected):**
  - Columns: Website, Issue Type, Category, Message, Severity, Detected, Status
  - Filter by severity (error/warning/info)
  - Filter by category
  - Click to view full issue details and suggested fix

- **Content Scores Table:**
  - Columns: Website, Page, Title Score, Meta Score, Readability, Keywords, Overall
  - Sortable
  - Click row to view detailed content analysis

- **Core Web Vitals Grid:**
  - LCP (Largest Contentful Paint) - Good/Needs Improvement/Poor
  - INP (Interaction to Next Paint) - Good/Needs Improvement/Poor
  - CLS (Cumulative Layout Shift) - Good/Needs Improvement/Poor
  - Color-coded badges

- **Export:** Download results as CSV/PDF

### 5.5 Backend Page (`/backend`)

**Purpose:** Monitor backend services, logs, and task queues

**Features:**
- **Service Status Panel:**
  - API Server: Online/Offline indicator with uptime
  - Database: Connected/Disconnected with latency
  - Redis: Connected/Disconnected
  - AI Agents: Count of active/idle agents
  - Last check timestamp
  - Refresh button

- **Task Queue Panel:**
  - Current queue size
  - Processing count
  - Failed count
  - Recent tasks table: ID, Type, Website, Status, Started, Duration
  - Filter by status
  - View task detail modal

- **Error Logs Panel:**
  - Real-time error log stream (optional toggle)
  - Log table: Timestamp, Level, Source, Message
  - Filter by level (error/critical)
  - Filter by source
  - Date range picker
  - Search in messages
  - Click row to view full error detail (stack trace, context)

- **Log Detail Modal:**
  - Full error message
  - Stack trace (formatted)
  - Context data (JSON)
  - Copy button
  - Timestamp

### 5.6 AI Logs Page (`/ai-logs`)

**Purpose:** Debug and monitor AI agent activity

**Features:**
- **Agent Activity Overview:**
  - Total runs (24h)
  - Success rate
  - Avg execution time
  - Active agents count

- **Agent Types Panel:**
  - List of agent types: Technical Auditor, Content Analyst, Schema Generator, etc.
  - Shows: Type, Runs (24h), Avg Time, Last Run
  - Click to filter logs by agent

- **Agent Log Table:**
  - Columns: Agent Type, Task ID, Status, Input (summary), Output (summary), Duration, Timestamp
  - Filter by agent type
  - Filter by status (completed/failed/running)
  - Date range filter
  - Search by task ID

- **Log Detail Modal:**
  - Full input data (JSON formatted)
  - Full output data (JSON formatted)
  - Execution time
  - Status
  - Retry button (if failed)

- **Debug Mode Toggle:**
  - When enabled, shows raw API requests/responses
  - Useful for troubleshooting

---

## 6. Implementation Order

### Phase 1: Foundation (Week 1-2)
1. Set up React project with Vite + TypeScript
2. Install dependencies: React Router, TanStack Table, Axios, TailwindCSS
3. Create component library (Button, Input, Modal, Card, Badge)
4. Set up layout (Sidebar, Header, Main content area)
5. Configure routing for all 6 pages
6. Set up API client with interceptors

### Phase 2: Users & Websites (Week 3)
1. Users page - list, create, edit, delete
2. Websites page - list, filters, detail view
3. Connect to mock backend (or real FastAPI)
4. Implement pagination and sorting

### Phase 3: API Keys (Week 4)
1. API Keys page - list, generate, revoke
2. Copy to clipboard functionality
3. Usage tracking display

### Phase 4: Results (Week 5)
1. Results page with tabs
2. Issue list with filters
3. Core Web Vitals grid
4. Export functionality

### Phase 5: Backend Monitoring (Week 6)
1. Service status panel with polling
2. Task queue table
3. Error logs with filtering
4. Log detail modal

### Phase 6: AI Logs (Week 7)
1. Agent activity overview stats
2. Agent logs table with filters
3. Log detail modal with JSON viewer
4. Debug toggle

### Phase 7: Polish (Week 8)
1. Toast notifications
2. Loading states / skeletons
3. Empty states
4. Responsive design adjustments
5. Final QA and bug fixes

---

## 7. Wireframes (ASCII)

### 7.1 Main Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  🔍 Search...                              🔔        👤 Admin   │
├────────┬───────────────────────────────────────────────────────────┤
│        │                                                           │
│ 👥     │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│ Users  │   │   142   │ │   89%   │ │  1,234  │ │   12    │      │
│        │   │  Users  │ │ Active  │ │ API Calls│ │ Issues  │      │
│ 🌐     │   └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│ Sites  │                                                           │
│        │   ┌─────────────────────────────────────────────────────┐ │
│ 🔑     │   │  Name      │ Email      │ Plan │ Status │ Actions│ │
│ API    │   ├─────────────────────────────────────────────────────┤ │
│        │   │ John Doe   │ john@...   │ Pro  │ Active │ ⋯      │ │
│ 📊     │   │ Jane Smith │ jane@...   │ Free │ Active │ ⋯      │ │
│ Results│   │ ...       │ ...        │ ...  │ ...    │ ⋯      │ │
│        │   └─────────────────────────────────────────────────────┘ │
│ ⚙️     │                                                           │
│ Backend│   ◀ 1 2 3 4 5 ▶  Showing 1-10 of 142                     │
│        │                                                           │
│ 🤖     │                                                           │
│ AI Logs│                                                           │
│        │                                                           │
└────────┴───────────────────────────────────────────────────────────┘
```

### 7.2 User Detail Modal

```
┌──────────────────────────────────────────────────────────┐
│  User Details                               ✕            │
├──────────────────────────────────────────────────────────┤
│  👤 John Doe                                              │
│  📧 john@example.com                                      │
│  📅 Joined: Jan 15, 2024                                 │
├──────────────────────────────────────────────────────────┤
│  [Overview] [Websites] [API Keys] [Activity]            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Plan: Pro ($49/month)                    [Change Plan]  │
│  Status: Active                                       │
│                                                          │
│  API Usage: 7,234 / 10,000 calls                       │
│  ████████████░░░░░░ 73%                                │
│                                                          │
│  Connected Websites: 5                                 │
│  API Keys: 2 active                                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 7.3 Results Page - Core Web Vitals

```
┌─────────────────────────────────────────────────────────────────┐
│  Results                                    [Export ▼]        │
├──────────────────────────────────────────────────────────────────┤
│  [Overview] [Technical] [Content] [Rankings] [Web Vitals]     │
├──────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│   │      LCP     │  │      INP     │  │     CLS      │        │
│   │   ✓ Good     │  │   ⚠ Needs    │  │   ✓ Good     │        │
│   │    2.1s      │  │    290ms     │  │    0.08      │        │
│   └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│   LCP (Largest Contentful Paint):                             │
│   ┌─────────┬──────────┬──────────┬──────────┐               │
│   │ Website │  Value   │  Status  │ Scanned  │               │
│   ├─────────┼──────────┼──────────┼──────────┤               │
│   │ site1   │   2.1s   │   Good   │ 2m ago   │               │
│   │ site2   │   4.2s   │   Poor   │ 2m ago   │               │
│   │ site3   │   2.8s   │   Fair   │ 2m ago   │               │
│   └─────────┴──────────┴──────────┴──────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.4 Backend Page

```
┌─────────────────────────────────────────────────────────────────┐
│  Backend Status                             [⟳ Refresh]       │
├──────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐     │
│   │  API Server     │  │  Database      │  │  Redis      │     │
│   │  ● Online       │  │  ● Connected   │  │  ● Connected│     │
│   │  Uptime: 5d 3h  │  │  Latency: 12ms │  │             │     │
│   └─────────────────┘  └─────────────────┘  └─────────────┘     │
│                                                                 │
│   Tasks: Queue: 23 | Processing: 5 | Failed: 2                │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │ Filter: [All ▼] [Error ▼] [Search...]    [From] [To]    │ │
│   ├──────────────────────────────────────────────────────────┤ │
│   │ Time       │ Level │ Source   │ Message         │        │ │
│   ├──────────────────────────────────────────────────────────┤ │
│   │ 14:32:05   │ ERROR │ api      │ Connection...   │ 👁     │ │
│   │ 14:31:22   │ ERROR │ agent    │ Timeout on...    │ 👁     │ │
│   │ 14:30:15   │ CRIT  │ db       │ Lost connect... │ 👁     │ │
│   └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Multi-Agent Architecture Reference

### Agent Types (for AI Logs)

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **Technical Auditor** | Analyze technical SEO | URL, HTML | Issues, recommendations |
| **Content Analyst** | Evaluate content quality | Content, keyword | Score, suggestions |
| **Schema Generator** | Generate JSON-LD | Page data, type | Schema.org markup |
| **Core Web Vitals** | Measure performance | URL | LCP, INP, CLS scores |
| **Backlink Agent** | Analyze backlinks | Domain | Backlink profile |
| **Competitor Analyzer** | Compare with competitors | Domain, keywords | Competitor insights |
| **Keyword Researcher** | Find keyword opportunities | Seed keyword | Related keywords, metrics |
| **Local SEO** | Optimize local presence | Business data | NAP, citation suggestions |
| **Rank Tracker** | Monitor keyword positions | Domain, keywords | Position history |

### Agent Communication Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Plugin    │─────▶│   FastAPI   │─────▶│ Orchestrator│
│   (WP/Any)  │      │   Gateway   │      │   Agent     │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                  │
                    ┌─────────────────────────────┼─────────────┐
                    │                             │             │
              ┌─────▼──────┐              ┌───────▼─────┐ ┌────▼────┐
              │ Technical  │              │  Content    │ │ Schema  │
              │  Auditor   │              │  Analyst    │ │ Generator
              └────────────┘              └─────────────┘ └─────────┘
```

---

## 9. Future Considerations (Post-MVP)

- **Billing Integration:** Stripe/Paddle for subscription management
- **Webhooks:** Notify users on events (scan complete, issues found)
- **White-label:** Custom branding for agencies
- **Team Access:** Multi-user per account
- **Report Scheduling:** Automated PDF reports
- **Mobile App:** iOS/Android companion
- **AI Chat:** ChatGPT-like interface for SEO questions

---

*Document Version: 1.0*  
*Created: 2026-05-19*  
*Status: Ready for Implementation*