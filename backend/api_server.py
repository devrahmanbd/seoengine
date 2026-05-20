"""
ZenSEO Multi-Agent Brain REST API Server
=========================================

FastAPI-based REST API that exposes the multi-agent brain to the WordPress plugin
for external mode operation.

Start: uvicorn api_server:app --reload --port 8000
"""

import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from multi_agent_brain import (
    OrchestratorAgent,
    AgentFactory,
    AgentType,
    AgentTask,
    BaseAgent
)

app = FastAPI(
    title="ZenSEO AI Brain API",
    description="Multi-agent SEO intelligence system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator: Optional[OrchestratorAgent] = None
agents: Dict[AgentType, BaseAgent] = {}

# Learning & growth components (initialized on startup)
ppo_trainer = None
decision_integrator = None
growth_scorer = None

class AnalysisRequest(BaseModel):
    url: Optional[str] = None
    content: Optional[str] = None
    keyword: Optional[str] = None
    keywords: Optional[List[str]] = None
    domain: Optional[str] = None
    competitors: Optional[List[str]] = None
    page_type: Optional[str] = "Article"
    page_data: Optional[Dict] = {}
    business: Optional[Dict] = {}
    location: Optional[Dict] = {}
    analysis_type: str = "full"

class WorkflowRequest(BaseModel):
    workflow: str
    context: Dict[str, Any]

class AgentRequest(BaseModel):
    agent_type: str
    context: Dict[str, Any]

@app.on_event("startup")
async def startup():
    """Initialize the multi-agent system and learning components"""
    global orchestrator, agents, ppo_trainer, decision_integrator, growth_scorer
    
    orchestrator = OrchestratorAgent()
    await orchestrator.initialize()
    
    agents = AgentFactory.create_all()
    
    for agent_type, agent in agents.items():
        await agent.initialize()
        orchestrator.register(agent_type, agent)
    
    # Initialize learning components
    try:
        from app.services.atropos.trainer import PPOTrainer
        from app.services.learning.decision_integrator import DecisionIntegrator
        from app.services.learning.growth_scorer import GrowthScorer
        from app.services.learning.data_collector import DataCollector
        from app.core.database import SessionLocal
        
        collector = DataCollector(db_session_factory=SessionLocal)
        ppo_trainer = PPOTrainer()
        decision_integrator = DecisionIntegrator(trainer=ppo_trainer)
        growth_scorer = GrowthScorer(collector=collector)
        
        import os
        model_path = os.path.join(os.path.dirname(__file__), "data", "ppo_model.pt")
        if os.path.exists(model_path):
            ppo_trainer.load(model_path)
            print(f"   PPO Model loaded (step={ppo_trainer._train_step})")
        
        print(f"   Learning components: PPOTrainer, DecisionIntegrator, GrowthScorer")
    except Exception as e:
        print(f"   Warning: Learning components not available - {e}")
    
    print(f"✅ ZenSEO AI Brain initialized")
    print(f"   Agents: {len(agents)}")
    print(f"   Workflows: {len(orchestrator.workflows)}")

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "active",
        "service": "ZenSEO AI Brain",
        "version": "1.0.0",
        "agents": len(agents),
        "workflows": len(orchestrator.workflows) if orchestrator else 0
    }

@app.get("/agents")
async def list_agents():
    """List all available agents"""
    return {
        "agents": [
            {
                "type": at.value,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
                "status": agent.status.value
            }
            for at, agent in agents.items()
        ]
    }

@app.get("/workflows")
async def list_workflows():
    """List all available workflows"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    
    return {
        "workflows": [
            {
                "name": name,
                "agents": [a.value for a in agents_list]
            }
            for name, agents_list in orchestrator.workflows.items()
        ]
    }

@app.post("/analyze/technical")
async def analyze_technical(request: AnalysisRequest):
    """Run technical SEO analysis"""
    agent = agents.get(AgentType.TECHNICAL_AUDITOR)
    if not agent:
        raise HTTPException(status_code=500, detail="Technical Auditor not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="technical_audit",
        priority=8,
        description="Technical SEO audit",
        context={"url": request.url, "content": request.content}
    )
    
    result = await agent.process_task(task)
    return {"agent": "technical_auditor", "result": result}

@app.post("/analyze/core-web-vitals")
async def analyze_cwv(request: AnalysisRequest):
    """Run Core Web Vitals analysis"""
    agent = agents.get(AgentType.CORE_WEB_VITALS)
    if not agent:
        raise HTTPException(status_code=500, detail="Core Web Vitals Agent not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="core_web_vitals",
        priority=10,
        description="Core Web Vitals audit",
        context={"url": request.url}
    )
    
    result = await agent.process_task(task)
    return {"agent": "core_web_vitals", "result": result}

@app.post("/analyze/content")
async def analyze_content(request: AnalysisRequest):
    """Run content analysis"""
    agent = agents.get(AgentType.CONTENT_ANALYST)
    if not agent:
        raise HTTPException(status_code=500, detail="Content Analyst not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="content_analysis",
        priority=7,
        description="Content quality analysis",
        context={
            "url": request.url,
            "content": request.content,
            "target_keyword": request.keyword
        }
    )
    
    result = await agent.process_task(task)
    return {"agent": "content_analyst", "result": result}

@app.post("/analyze/schema")
async def analyze_schema(request: AnalysisRequest):
    """Generate schema markup"""
    agent = agents.get(AgentType.SCHEMA_GENERATOR)
    if not agent:
        raise HTTPException(status_code=500, detail="Schema Generator not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="schema_generation",
        priority=5,
        description="Generate schema markup",
        context={
            "page_type": request.page_type,
            "page_data": request.page_data
        }
    )
    
    result = await agent.process_task(task)
    return {"agent": "schema_generator", "result": result}

@app.post("/analyze/backlinks")
async def analyze_backlinks(request: AnalysisRequest):
    """Run backlink analysis"""
    agent = agents.get(AgentType.BACKLINK_AGENT)
    if not agent:
        raise HTTPException(status_code=500, detail="Backlink Agent not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="backlink_analysis",
        priority=7,
        description="Backlink profile analysis",
        context={
            "domain": request.domain,
            "competitors": request.competitors or []
        }
    )
    
    result = await agent.process_task(task)
    return {"agent": "backlink_agent", "result": result}

@app.post("/analyze/competitors")
async def analyze_competitors(request: AnalysisRequest):
    """Run competitor analysis"""
    agent = agents.get(AgentType.COMPETITOR_ANALYZER)
    if not agent:
        raise HTTPException(status_code=500, detail="Competitor Analyzer not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="competitor_analysis",
        priority=6,
        description="Competitor analysis",
        context={
            "domain": request.domain,
            "competitors": request.competitors or [],
            "analysis_type": request.analysis_type
        }
    )
    
    result = await agent.process_task(task)
    return {"agent": "competitor_analyzer", "result": result}

@app.post("/analyze/local-seo")
async def analyze_local_seo(request: AnalysisRequest):
    """Run local SEO analysis"""
    agent = agents.get(AgentType.LOCAL_SEO)
    if not agent:
        raise HTTPException(status_code=500, detail="Local SEO Agent not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="local_seo",
        priority=7,
        description="Local SEO audit",
        context={
            "business": request.business or {},
            "location": request.location or {}
        }
    )
    
    result = await agent.process_task(task)
    return {"agent": "local_seo", "result": result}

@app.post("/track/keywords")
async def track_keywords(request: AnalysisRequest):
    """Track keyword rankings"""
    agent = agents.get(AgentType.RANK_TRACKER)
    if not agent:
        raise HTTPException(status_code=500, detail="Rank Tracker not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="rank_tracking",
        priority=8,
        description="Keyword rank tracking",
        context={
            "domain": request.domain,
            "keywords": request.keywords or [],
            "location": "US"
        }
    )
    
    result = await agent.process_task(task)
    return {"agent": "rank_tracker", "result": result}

@app.post("/workflow")
async def run_workflow(request: WorkflowRequest):
    """Run a predefined workflow"""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    
    if request.workflow not in orchestrator.workflows:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown workflow: {request.workflow}"
        )
    
    result = await orchestrator.execute_workflow(request.workflow, request.context)
    return {"workflow": request.workflow, "result": result}

@app.post("/agent")
async def run_agent(request: AgentRequest):
    """Run a specific agent directly"""
    try:
        agent_type = AgentType(request.agent_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown agent type: {request.agent_type}")
    
    agent = agents.get(agent_type)
    if not agent:
        raise HTTPException(status_code=500, detail=f"Agent {request.agent_type} not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type=request.agent_type,
        priority=5,
        description=f"Direct agent execution: {request.agent_type}",
        context=request.context
    )
    
    result = await agent.process_task(task)
    return {"agent": request.agent_type, "result": result}

@app.post("/batch")
async def run_batch(requests: List[AgentRequest]):
    """Run multiple agents in parallel"""
    tasks = []
    
    for req in requests:
        try:
            agent_type = AgentType(req.agent_type)
        except ValueError:
            continue
        
        agent = agents.get(agent_type)
        if agent:
            task = AgentTask(
                task_id=str(uuid.uuid4()),
                task_type=req.agent_type,
                priority=5,
                description=f"Batch: {req.agent_type}",
                context=req.context
            )
            tasks.append(agent.process_task(task))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "results": [
            {"agent": r[0], "result": r[1] if not isinstance(r[1], Exception) else {"error": str(r[1])}}
            for r in zip([r.agent_type for r in requests[:len(results)]], results)
        ]
    }

class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 2000
    model: str = "gpt-4"

class ChatResponse(BaseModel):
    response: str
    model: str

@app.get("/health")
async def health_check():
    """Health check for WordPress plugin connectivity"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint for WordPress plugin - routes to content analyst"""
    agent = agents.get(AgentType.CONTENT_ANALYST)
    if not agent:
        raise HTTPException(status_code=500, detail="Content Analyst not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="chat",
        priority=5,
        description="AI Chat",
        context={"prompt": request.prompt, "max_tokens": request.max_tokens}
    )
    
    result = await agent.process_task(task)
    return {"response": f"Analysis: {result.get('quality_score', {}).get('score', 'N/A')}/100", "model": request.model}

@app.post("/api/analyze")
async def analyze(request: AnalysisRequest):
    """Analyze endpoint for WordPress plugin - full content analysis"""
    results = {}
    
    if request.content and request.keyword:
        content_agent = agents.get(AgentType.CONTENT_ANALYST)
        if content_agent:
            task = AgentTask(
                task_id=str(uuid.uuid4()),
                task_type="content_analysis",
                priority=8,
                description="Content analysis",
                context={"content": request.content, "target_keyword": request.keyword, "url": request.url}
            )
            results["content_analysis"] = await content_agent.process_task(task)
    
    if request.url:
        tech_agent = agents.get(AgentType.TECHNICAL_AUDITOR)
        if tech_agent:
            task = AgentTask(
                task_id=str(uuid.uuid4()),
                task_type="technical_audit",
                priority=8,
                description="Technical audit",
                context={"url": request.url}
            )
            results["technical_audit"] = await tech_agent.process_task(task)
        
        cwv_agent = agents.get(AgentType.CORE_WEB_VITALS)
        if cwv_agent:
            task = AgentTask(
                task_id=str(uuid.uuid4()),
                task_type="core_web_vitals",
                priority=10,
                description="Core Web Vitals",
                context={"url": request.url}
            )
            results["core_web_vitals"] = await cwv_agent.process_task(task)
    
    return results

@app.post("/api/keyword-research")
async def keyword_research(request: AnalysisRequest):
    """Keyword research endpoint for WordPress plugin"""
    keyword_agent = agents.get(AgentType.KEYWORD_RESEARCHER)
    if not keyword_agent:
        raise HTTPException(status_code=500, detail="Keyword Researcher not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="keyword_research",
        priority=6,
        description="Keyword research",
        context={"keyword": request.keyword}
    )
    
    result = await keyword_agent.process_task(task)
    return result

@app.post("/api/schema")
async def generate_schema(request: AnalysisRequest):
    """Schema generation endpoint for WordPress plugin"""
    schema_agent = agents.get(AgentType.SCHEMA_GENERATOR)
    if not schema_agent:
        raise HTTPException(status_code=500, detail="Schema Generator not available")
    
    task = AgentTask(
        task_id=str(uuid.uuid4()),
        task_type="schema_generation",
        priority=5,
        description="Schema generation",
        context={"page_type": request.page_type, "page_data": request.page_data}
    )
    
    result = await schema_agent.process_task(task)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)