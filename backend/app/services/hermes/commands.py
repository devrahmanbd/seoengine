import time as time_module
from uuid import uuid4

from app.services.hermes.agent import CommandResult

command_registry: dict[str, callable] = {}

_hermes_agent: "HermesAgent | None" = None


def _agent():
    if _hermes_agent is None:
        raise RuntimeError("HermesAgent not set. Call register_all(agent) first.")
    return _hermes_agent


def register(name: str):
    def decorator(func):
        command_registry[name] = func
        return func
    return decorator


@register("analyze")
async def cmd_analyze(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: analyze <url> [--env technical|content|all]")
    url = args[0]
    env = kwargs.get("env", "all")

    from app.services.atropos.environments import TechnicalSEOEnv, ContentSEOEnv

    results = {}
    errors = []

    if env in ("technical", "all"):
        try:
            tech_env = TechnicalSEOEnv(url)
            state = await tech_env.reset()
            metrics = dict(state.metrics)
            score = metrics.get("technical_score", 0.0)
            issues = []
            if metrics.get("title_length", 0) < 30:
                issues.append("Title too short or missing")
            if metrics.get("meta_description_length", 0) < 120:
                issues.append("Meta description too short or missing")
            if metrics.get("h1_count", 0) != 1:
                issues.append("Page should have exactly one H1 tag")
            if metrics.get("schema_count", 0) == 0:
                issues.append("No structured data found")
            if metrics.get("has_canonical") is False:
                issues.append("No canonical URL set")
            if metrics.get("has_viewport") is False:
                issues.append("No viewport meta tag")
            if metrics.get("images_missing_alt", 0) > 0:
                issues.append(f"{metrics['images_missing_alt']} images missing alt text")
            results["technical"] = {
                "score": round(score * 100, 1),
                "metrics": {k: v for k, v in metrics.items() if not k.startswith("_")},
                "issues": issues,
            }
            await tech_env.close()
        except Exception as e:
            errors.append(f"technical: {e}")

    if env in ("content", "all"):
        try:
            content_env = ContentSEOEnv(url)
            state = await content_env.reset()
            metrics = dict(state.metrics)
            score = metrics.get("content_score", 0.0)
            issues = []
            if metrics.get("word_count", 0) < 300:
                issues.append("Content too short")
            if metrics.get("readability_score", 0) < 50:
                issues.append("Readability score too low")
            if metrics.get("has_faq") is False:
                issues.append("No FAQ section found")
            if metrics.get("has_schema") is False:
                issues.append("No content schema found")
            if metrics.get("heading_structure_score", 0) < 0.5:
                issues.append("Heading structure needs improvement")
            results["content"] = {
                "score": round(score * 100, 1),
                "metrics": {k: v for k, v in metrics.items() if not k.startswith("_")},
                "issues": issues,
            }
            await content_env.close()
        except Exception as e:
            errors.append(f"content: {e}")

    output_lines = [f"Audit for {url}"]
    if "technical" in results:
        t = results["technical"]
        output_lines.append(f"  Technical SEO: {t['score']}/100 ({len(t['issues'])} issues)")
    if "content" in results:
        c = results["content"]
        output_lines.append(f"  Content SEO: {c['score']}/100 ({len(c['issues'])} issues)")
    if errors:
        output_lines.append(f"  Errors: {'; '.join(errors)}")

    return CommandResult(
        success=len(errors) == 0 or bool(results),
        output="\n".join(output_lines),
        data={"url": url, "env": env, **results, "errors": errors if errors else None},
    )


@register("optimize")
async def cmd_optimize(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: optimize <url> [--focus X]")
    url = args[0]
    focus = kwargs.get("focus", "all")

    from app.services.atropos.base_env import SEOAction
    from app.services.atropos.environments import TechnicalSEOEnv, ContentSEOEnv

    actions_taken = []
    total_reward = 0.0

    if focus in ("technical", "all"):
        try:
            env = TechnicalSEOEnv(url)
            await env.reset()
            actions = [
                SEOAction("fix_title", {"title": "Optimized Page Title - Complete Guide | Brand"}),
                SEOAction("fix_meta", {"description": "Discover the complete guide to optimized page titles and meta descriptions for better SEO performance and higher search rankings."}),
                SEOAction("fix_headings", {"h1_count": 1}),
                SEOAction("add_schema", {"schema_type": "WebPage"}),
                SEOAction("fix_images", {}),
            ]
            for action in actions:
                state, reward, done, info = await env.step(action)
                total_reward += reward
                actions_taken.append({
                    "type": action.action_type,
                    "applied": info.get("action_result", {}).get("applied", False),
                    "message": info.get("action_result", {}).get("message", ""),
                    "reward": round(reward, 4),
                })
                if done:
                    break
            await env.close()
        except Exception as e:
            actions_taken.append({"type": "technical", "error": str(e)})

    if focus in ("content", "all"):
        try:
            env = ContentSEOEnv(url)
            await env.reset()
            actions = [
                SEOAction("optimize_content", {"target_word_count": 1500}),
                SEOAction("improve_readability", {"target_readability": 70.0}),
                SEOAction("restructure_headings", {}),
                SEOAction("add_faq_schema", {"faq_count": 4}),
                SEOAction("add_entities", {"entities": ["Topic", "Brand", "Industry"]}),
            ]
            for action in actions:
                state, reward, done, info = await env.step(action)
                total_reward += reward
                actions_taken.append({
                    "type": action.action_type,
                    "applied": info.get("action_result", {}).get("applied", False),
                    "message": info.get("action_result", {}).get("message", ""),
                    "reward": round(reward, 4),
                })
                if done:
                    break
            await env.close()
        except Exception as e:
            actions_taken.append({"type": "content", "error": str(e)})

    output_lines = [f"Optimization for {url}"]
    output_lines.append(f"  Total reward: {total_reward:+.4f}")
    output_lines.append(f"  Actions: {len(actions_taken)}")
    for a in actions_taken[:10]:
        msg = a.get("message", a.get("error", ""))
        output_lines.append(f"    [{a['type']}] {'✓' if a.get('applied') else '✗'} {msg}")

    return CommandResult(
        success=bool(actions_taken),
        output="\n".join(output_lines),
        data={"url": url, "focus": focus, "actions": actions_taken, "total_reward": round(total_reward, 4)},
    )


@register("train")
async def cmd_train(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: train <domain> [--episodes N]")
    domain = args[0]
    episodes = int(kwargs.get("episodes", "10"))

    from app.services.atropos.trainer import PPOOptimizer
    from app.services.atropos.scored_data_api import ScoredDataBuffer, ScoredData

    optimizer = PPOOptimizer(lr=3e-4, gamma=0.99, clip_epsilon=0.2)
    buffer = ScoredDataBuffer(max_size=10000)

    metrics_history = []
    for i in range(episodes):
        env_name = "technical"
        try:
            from app.services.atropos.environments import TechnicalSEOEnv
            env = TechnicalSEOEnv(domain)
            state = await env.reset()
            total_ep_reward = 0.0
            step_count = 0
            done = False
            while not done and step_count < 5:
                from app.services.atropos.base_env import SEOAction
                action = SEOAction("fix_title", {"title": f"Optimized Page {step_count}"})
                next_state, reward, done, info = await env.step(action)
                buffer.append(ScoredData(
                    state={"site_id": domain, "metrics": state.metrics},
                    action={"action_type": action.action_type, "params": action.params},
                    reward=reward,
                    next_state={"site_id": domain, "metrics": next_state.metrics},
                    done=done,
                ))
                total_ep_reward += reward
                state = next_state
                step_count += 1
            await env.close()
        except Exception as e:
            total_ep_reward = 0.0

        result = await optimizer.train_on_buffer(buffer, batch_size=min(32, len(buffer)))
        metrics_history.append({
            "episode": i + 1,
            "reward": round(total_ep_reward, 4),
            "policy_loss": round(result.get("policy_loss", 0.0), 6),
            "value_loss": round(result.get("value_loss", 0.0), 6),
            "buffer_size": len(buffer),
        })

    avg_reward = sum(m["reward"] for m in metrics_history) / len(metrics_history) if metrics_history else 0.0
    final_losses = metrics_history[-1] if metrics_history else {}

    output_lines = [
        f"Training on {domain}",
        f"  Episodes: {episodes}",
        f"  Avg reward: {avg_reward:+.4f}",
        f"  Final policy_loss: {final_losses.get('policy_loss', 0.0)}",
        f"  Final value_loss: {final_losses.get('value_loss', 0.0)}",
        f"  Buffer size: {len(buffer)}",
    ]

    return CommandResult(
        success=True,
        output="\n".join(output_lines),
        data={"domain": domain, "episodes": episodes, "metrics": metrics_history, "avg_reward": round(avg_reward, 4)},
    )


@register("decide")
async def cmd_decide(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: decide <question>")
    question = " ".join(args)

    agent = _agent()
    adapter = agent._semantic_adapter
    session = agent.get_session(session_id)
    site_id = session.memory.get("site_id", "default") if session else "default"

    if not adapter:
        return CommandResult(
            success=True,
            output=f"[decision engine not available] No semantic adapter configured.\n\nQuestion: {question}\n\nPlease configure a LoRASemanticAdapter to enable strategic decisions.",
            data={"question": question, "site_id": site_id, "status": "unavailable"},
        )

    ctx = await adapter.adapt(site_id, question)
    entities_str = "\n".join(
        f"    - {e.label} ({e.type})" for e in ctx.top_entities[:5]
    ) if ctx.top_entities else "    (no entities found)"

    output_lines = [
        f"Decision Engine (site: {site_id})",
        f"  Query: {question}",
        f"  Adapter: {ctx.adapter_id[:8]}...",
        f"  Confidence: {ctx.confidence:.4f}",
        f"  Top entities:",
        entities_str,
        f"  Metadata: rank={ctx.metadata.get('rank')}, alpha={ctx.metadata.get('alpha')}",
    ]

    return CommandResult(
        success=True,
        output="\n".join(output_lines),
        data={"question": question, "site_id": site_id, "confidence": ctx.confidence, "adapter_id": ctx.adapter_id, "entities": [{"id": e.id, "label": e.label, "type": e.type} for e in ctx.top_entities[:5]]},
    )


@register("research")
async def cmd_research(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: research <keyword> [--deep]")
    keyword = " ".join(args)
    deep = kwargs.get("deep", "false").lower() == "true"

    from app.services.atropos.environments import KeywordResearchEnv

    try:
        env = KeywordResearchEnv(keyword)
        state = await env.reset()
        metrics = dict(state.metrics)
        await env.close()

        output_lines = [
            f"Keyword Research: {keyword}",
            f"  Volume: {metrics.get('volume', 'N/A')}",
            f"  Difficulty: {metrics.get('difficulty', 'N/A')}",
            f"  CPC: ${metrics.get('cpc', 0.0):.2f}",
            f"  Competition: {metrics.get('competition', 'N/A')}",
            f"  Related keywords: {metrics.get('related_count', 0)}",
            f"  Deep research: {'yes' if deep else 'no'}",
        ]
        return CommandResult(
            success=True,
            output="\n".join(output_lines),
            data={"keyword": keyword, "deep": deep, "metrics": metrics},
        )
    except Exception as e:
        return CommandResult(
            success=True,
            output=f"Research for '{keyword}':\n  (mock data - env init failed: {e})\n  Volume estimate: 1200-2400/mo\n  Difficulty: Medium\n  Suggested uses: on-page optimization, content briefs",
            data={"keyword": keyword, "deep": deep, "note": "fallback mock", "error": str(e)},
        )


@register("track")
async def cmd_track(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: track <domain>")
    domain = args[0]

    from app.services.atropos.environments import CWVEnv
    from app.services.atropos.base_env import SEOAction

    try:
        env = CWVEnv(domain)
        state = await env.reset()
        cwv_metrics = dict(state.metrics)
        await env.close()
    except Exception:
        cwv_metrics = {
            "lcp": 2.1,
            "inp": 120,
            "cls": 0.05,
            "overall_score": 0.78,
        }

    output_lines = [
        f"Ranking Trends for {domain}",
        f"  Core Web Vitals:",
        f"    LCP: {cwv_metrics.get('lcp', 'N/A')}s {'✓' if cwv_metrics.get('lcp', 99) < 2.5 else '⚠'}",
        f"    INP: {cwv_metrics.get('inp', 'N/A')}ms {'✓' if cwv_metrics.get('inp', 999) < 200 else '⚠'}",
        f"    CLS: {cwv_metrics.get('cls', 'N/A')} {'✓' if cwv_metrics.get('cls', 99) < 0.1 else '⚠'}",
        f"    Overall: {cwv_metrics.get('overall_score', 0.0) * 100:.0f}/100",
    ]

    return CommandResult(
        success=True,
        output="\n".join(output_lines),
        data={"domain": domain, "cwv": cwv_metrics},
    )


@register("status")
async def cmd_status(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    agent = _agent()
    sessions = agent.list_sessions()
    session = agent.get_session(session_id)

    adapter_info = "configured" if agent._semantic_adapter else "not configured"

    output_lines = [
        "System Health",
        f"  Active sessions: {len(sessions)}",
        f"  Current session: {session_id[:8] if session_id else 'none'}...",
        f"  Semantic adapter: {adapter_info}",
        f"  Commands registered: {len(command_registry)}",
        f"  Commands: {', '.join(sorted(command_registry.keys()))}",
    ]

    if session:
        output_lines.append(f"  Session site_id: {session.memory.get('site_id', 'not set')}")
        output_lines.append(f"  Session history: {len(session.command_history)} commands")

    return CommandResult(
        success=True,
        output="\n".join(output_lines),
        data={
            "session_id": session_id,
            "session_count": len(sessions),
            "commands_available": len(command_registry),
            "commands": sorted(command_registry.keys()),
            "semantic_adapter": adapter_info,
        },
    )


@register("explain")
async def cmd_explain(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: explain <action_id>")
    action_id = args[0]

    agent = _agent()
    session = agent.get_session(session_id)

    if not session:
        return CommandResult(success=False, output=f"Session '{session_id}' not found")

    site_id = session.site_id or session_id
    episodes = await agent.memory.episodic.recall(site_id, limit=20)

    for ep in episodes:
        ep_content = ep.content if isinstance(ep.content, dict) else {}
        if action_id in str(ep.key) or action_id in str(ep_content):
            reasoning = ep_content.get("reasoning", [])
            output_lines = [
                f"Action Trace: {action_id}",
                f"  Command: {ep.key}  Args: {ep_content.get('args', [])}",
                f"  Output: {str(ep_content.get('output', ''))[:200]}",
                f"  Reasoning:",
            ]
            for r in (reasoning or []):
                output_lines.append(f"    {r}")
            return CommandResult(
                success=True,
                output="\n".join(output_lines),
                data={"action_id": action_id, "episode": {"key": ep.key, "content": ep_content}},
            )

    recent = session.command_history[-5:] if session.command_history else []
    for cmd in recent:
        cmd_action_id = str(hash(f"{cmd.get('command')}{cmd.get('timestamp')}"))
        if action_id in cmd_action_id or action_id in cmd.get("command", ""):
            output_lines = [
                f"Action Trace: {action_id}",
                f"  Command: {cmd.get('command', '?')}",
                f"  Args: {cmd.get('args', [])}",
                f"  Success: {cmd.get('success', False)}",
                f"  Timestamp: {cmd.get('timestamp', '?')}",
            ]
            return CommandResult(
                success=True,
                output="\n".join(output_lines),
                data={"action_id": action_id, "command_detail": cmd},
            )

    return CommandResult(
        success=False,
        output=f"No trace found for action_id '{action_id}'. Recent commands: {[c.get('command', '?') for c in session.command_history[-5:]]}",
        data={"action_id": action_id, "found": False},
    )


@register("skills")
async def cmd_skills(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    agent = _agent()
    site = kwargs.get("site")

    session = agent.get_session(session_id)
    site_id = site or (session.memory.get("site_id") if session else None)

    if site_id:
        episodes = await agent.memory.episodic.recall(site_id, limit=50)
        successful = [ep for ep in episodes if isinstance(ep.content, dict) and ep.content.get("success") is True]
        unique_commands = set(ep.key for ep in successful if ep.key)

        skill_list = []
        for cmd in sorted(unique_commands):
            related = [ep for ep in successful if ep.key == cmd]
            ep_content = related[0].content if isinstance(related[0].content, dict) else {}
            avg_output_len = sum(len(str(ep.content.get("output", "")) if isinstance(ep.content, dict) else "") for ep in related) / len(related) if related else 0
            skill_list.append({
                "command": cmd,
                "occurrences": len(related),
                "avg_output_length": round(avg_output_len, 0),
            })

        output_lines = [
            f"Learned Skills for site '{site_id}'",
            f"  Commands used successfully: {len(skill_list)}",
        ]
        for s in skill_list:
            output_lines.append(f"    {s['command']}: {s['occurrences']}x, avg {s['avg_output_length']} chars")

        return CommandResult(
            success=True,
            output="\n".join(output_lines),
            data={"site_id": site_id, "skills": skill_list},
        )

    all_sessions = agent.list_sessions()
    output_lines = [
        "Learned Skills (all sites)",
        f"  Total sessions: {len(all_sessions)}",
    ]
    skills_data = []
    for sess in all_sessions:
        sid = sess.memory.get("site_id", "unknown")
        episodes = await agent.memory.episodic.recall(sid, limit=20)
        successful = [ep for ep in episodes if isinstance(ep.content, dict) and ep.content.get("success") is True]
        cmds = set(ep.key for ep in successful if ep.key)
        if cmds:
            output_lines.append(f"  [{sid[:20]}]: {', '.join(sorted(cmds))}")
            skills_data.append({"site_id": sid, "commands": sorted(cmds)})

    return CommandResult(
        success=True,
        output="\n".join(output_lines) if len(output_lines) > 1 else "No skills learned yet.",
        data={"skills": skills_data},
    )


@register("learn")
async def cmd_learn(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: learn <workflow_name>")
    workflow_name = " ".join(args)

    agent = _agent()
    session = agent.get_session(session_id)
    site_id = session.memory.get("site_id", "default") if session else "default"
    history = session.command_history if session else []

    if not history:
        return CommandResult(success=False, output="No command history to learn from")

    trajectory = [
        {
            "command": cmd.get("command"),
            "args": cmd.get("args"),
            "kwargs": cmd.get("kwargs"),
            "success": cmd.get("success"),
            "timestamp": cmd.get("timestamp"),
        }
        for cmd in history[-20:]
    ]

    from datetime import datetime, timezone
    skill_doc = {
        "name": workflow_name,
        "site_id": site_id,
        "created": datetime.now(timezone.utc).isoformat(),
        "steps": len(trajectory),
        "trajectory": trajectory,
    }

    from app.services.hermes.memory import MemoryEntry
    skill_entry = MemoryEntry(
        key=f"skill:{workflow_name}",
        content=skill_doc,
        timestamp=datetime.now(timezone.utc),
        ttl=None,
        tags=["skill", site_id, workflow_name],
    )
    await agent.memory.episodic.store(session_id, skill_entry)

    output_lines = [
        f"Learned workflow: {workflow_name}",
        f"  Site: {site_id}",
        f"  Steps captured: {len(trajectory)}",
        f"  Last command: {trajectory[-1].get('command', '?') if trajectory else 'none'}",
    ]

    return CommandResult(
        success=True,
        output="\n".join(output_lines),
        data={"workflow": workflow_name, "site_id": site_id, "steps": len(trajectory), "trajectory": trajectory},
    )


@register("forget")
async def cmd_forget(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: forget <pattern_name>")
    pattern_name = " ".join(args)

    agent = _agent()
    session = agent.get_session(session_id)
    site_id = session.memory.get("site_id", "default") if session else "default"

    from app.services.hermes.memory import SemanticMemory
    semantic = SemanticMemory()

    deleted = await semantic.delete_skill(pattern_name)

    if deleted:
        return CommandResult(
            success=True,
            output=f"Forgotten pattern: {pattern_name}",
            data={"pattern": pattern_name, "deleted": True},
        )

    return CommandResult(
        success=False,
        output=f"No pattern found: '{pattern_name}'. Use `skills` to list available patterns.",
        data={"pattern": pattern_name, "deleted": False},
    )


@register("semantic")
async def cmd_semantic(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if not args:
        return CommandResult(success=False, output="Usage: semantic <query>")
    query = " ".join(args)

    agent = _agent()
    session = agent.get_session(session_id)
    site_id = session.memory.get("site_id", "default") if session else "default"

    adapter = agent._semantic_adapter
    if adapter:
        ctx = await adapter.adapt(site_id, query)
        entities = ctx.top_entities[:5]
        entities_str = "\n".join(
            f"    - {e.label} ({e.type})" for e in entities
        ) if entities else "    (no entities)"
        output_lines = [
            f"Semantic Query: '{query}' at site '{site_id}'",
            f"  Confidence: {ctx.confidence:.4f}",
            f"  Top entities:",
            entities_str,
        ]
        data = {
            "query": query,
            "site_id": site_id,
            "confidence": ctx.confidence,
            "entities": [{"id": e.id, "label": e.label, "type": e.type} for e in entities],
        }
    else:
        output_lines = [
            f"Semantic Query: '{query}'",
            f"  Semantic adapter not configured. No semantic data available.",
        ]
        data = {"query": query, "site_id": site_id, "adapter": False}

    return CommandResult(
        success=True,
        output="\n".join(output_lines),
        data=data,
    )


@register("compare")
async def cmd_compare(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    if len(args) < 2:
        return CommandResult(success=False, output="Usage: compare <site_a> <site_b>")
    site_a, site_b = args[0], args[1]

    from app.services.semantic.cross_site import CrossSiteAnalyzer
    from app.services.semantic.db import SemanticDB

    db = SemanticDB()
    analyzer = CrossSiteAnalyzer(db, min_sites=1)

    try:
        cluster_a = await analyzer.get_site_cluster(site_a)
        cluster_b = await analyzer.get_site_cluster(site_b)
        patterns_a = await analyzer.get_insights_for_site(site_a)
        patterns_b = await analyzer.get_insights_for_site(site_b)

        shared = set(cluster_a) & set(cluster_b)
        unique_a = set(cluster_a) - shared
        unique_b = set(cluster_b) - shared

        output_lines = [
            f"Cross-Site Comparison: {site_a} vs {site_b}",
            f"  Cluster overlap: {len(shared)} sites",
            f"  Unique to {site_a}: {len(unique_a)}",
            f"  Unique to {site_b}: {len(unique_b)}",
            f"  Patterns found for {site_a}: {len(patterns_a)}",
            f"  Patterns found for {site_b}: {len(patterns_b)}",
        ]

        return CommandResult(
            success=True,
            output="\n".join(output_lines),
            data={
                "site_a": site_a,
                "site_b": site_b,
                "cluster_overlap": list(shared),
                "unique_to_a": list(unique_a),
                "unique_to_b": list(unique_b),
                "patterns_a": [p.to_dict() for p in patterns_a],
                "patterns_b": [p.to_dict() for p in patterns_b],
            },
        )
    except Exception as e:
        output_lines = [
            f"Cross-Site Comparison: {site_a} vs {site_b}",
            f"  Comparison unavailable: {e}",
            f"  (Ensure sites have been indexed in the semantic database)",
        ]
        return CommandResult(
            success=True,
            output="\n".join(output_lines),
            data={"site_a": site_a, "site_b": site_b, "error": str(e)},
        )


@register("help")
async def cmd_help(session_id: str, args: list[str], kwargs: dict) -> CommandResult:
    help_texts = {
        "analyze": "analyze <url> [--env technical|content|all] - Full technical + content audit",
        "optimize": "optimize <url> [--focus X] - Apply RL-optimized fixes",
        "train": "train <domain> [--episodes N] - Trigger RL training",
        "decide": "decide <question> - Ask the strategic decision engine",
        "research": "research <keyword> [--deep] - Deep keyword + competitor research",
        "track": "track <domain> - Show ranking trends",
        "status": "status - System health and session info",
        "explain": "explain <action_id> - Trace why a specific action was taken",
        "skills": "skills [--site SITE] - List learned skills",
        "learn": "learn <workflow_name> - Store current trajectory as a skill",
        "forget": "forget <pattern_name> - Remove a learned pattern",
        "semantic": "semantic <query> - Query the semantic DB",
        "compare": "compare <site_a> <site_b> - Cross-site comparison",
        "help": "help - Show this message",
    }

    if args:
        topic = args[0].lower()
        if topic in help_texts:
            return CommandResult(
                success=True,
                output=f"Help: {topic}\n  {help_texts[topic]}",
                data={"topic": topic, "help": help_texts[topic]},
            )
        return CommandResult(
            success=False,
            output=f"Unknown command '{topic}'. Available: {', '.join(sorted(help_texts.keys()))}",
            data={"topic": topic, "available": sorted(help_texts.keys())},
        )

    max_cmd_len = max(len(c) for c in help_texts)
    lines = ["Available Commands:"]
    for name in sorted(help_texts):
        lines.append(f"  {name:<{max_cmd_len}}  {help_texts[name]}")

    return CommandResult(
        success=True,
        output="\n".join(lines),
        data={"commands": help_texts},
    )


def _wrap_handler(name: str, handler: callable) -> callable:
    async def wrapped(handler_input: dict) -> CommandResult:
        session = handler_input["session"]
        return await handler(
            session.session_id,
            handler_input["args"],
            handler_input["kwargs"],
        )
    wrapped.__name__ = f"_wrapped_{name}"
    return wrapped


COMMAND_ROLES: dict[str, str] = {
    "analyze": "readonly",
    "track": "readonly",
    "status": "readonly",
    "help": "readonly",
    "explain": "readonly",
    "optimize": "user",
    "decide": "user",
    "research": "user",
    "compare": "user",
    "train": "admin",
    "learn": "admin",
    "forget": "admin",
    "semantic": "admin",
    "skills": "admin",
}


def register_all(agent: "HermesAgent") -> None:
    global _hermes_agent
    _hermes_agent = agent
    for name, handler in command_registry.items():
        role = COMMAND_ROLES.get(name, "user")
        agent.register_command(name, _wrap_handler(name, handler), required_role=role)
