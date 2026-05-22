import asyncio
import random
import time

from app.atropos.base_env import SEOEnvironment, SEOAction, State


MOCK_CWV_DATA: dict = {
    "lcp_score": 0.45,
    "inp_score": 0.50,
    "cls_score": 0.35,
    "fcp_score": 0.55,
    "tbt_score": 0.40,
    "mobile_score": 52,
    "desktop_score": 68,
    "opportunities": [
        {"type": "optimize_images", "impact": "high", "desc": "Compress largest contentful paint images"},
        {"type": "lazy_load", "impact": "medium", "desc": "Implement lazy loading for below-fold images"},
        {"type": "reduce_js", "impact": "high", "desc": "Defer unused JavaScript"},
        {"type": "optimize_fonts", "impact": "low", "desc": "Optimize font loading with font-display: swap"},
        {"type": "improve_server_response", "impact": "medium", "desc": "Reduce Time to First Byte"},
    ],
}

CWV_PASS_THRESHOLDS = {
    "lcp_score": 0.75,
    "inp_score": 0.70,
    "cls_score": 0.80,
    "fcp_score": 0.70,
    "tbt_score": 0.65,
}


class CWVEnv(SEOEnvironment):
    def __init__(self, site_id: str = "default"):
        self.site_id = site_id
        self._step_count = 0
        self.max_steps = 20
        self.data: dict = {}

    async def reset(self) -> State:
        self._step_count = 0
        self.data = {
            "lcp_score": MOCK_CWV_DATA["lcp_score"],
            "inp_score": MOCK_CWV_DATA["inp_score"],
            "cls_score": MOCK_CWV_DATA["cls_score"],
            "fcp_score": MOCK_CWV_DATA["fcp_score"],
            "tbt_score": MOCK_CWV_DATA["tbt_score"],
            "mobile_score": MOCK_CWV_DATA["mobile_score"],
            "desktop_score": MOCK_CWV_DATA["desktop_score"],
            "opportunities": [dict(o) for o in MOCK_CWV_DATA["opportunities"]],
        }
        metrics = self._collect_metrics()
        features = self._compute_features(metrics)
        return State(
            site_id=self.site_id,
            metrics=metrics,
            timestamp=time.time(),
            features=features,
        )

    async def step(self, action: SEOAction) -> tuple[State, float, bool, dict]:
        self._step_count += 1
        await asyncio.sleep(0)

        reward = 0.0
        info = {"action": action.action_type, "params": action.params}

        if action.action_type == "optimize_images":
            boost = random.uniform(0.04, 0.09)
            self.data["lcp_score"] = min(1.0, self.data.get("lcp_score", 0) + boost)
            self.data["cls_score"] = min(1.0, self.data.get("cls_score", 0) + boost * 0.3)
            self._mark_opportunity_done("optimize_images")
            reward = min(0.5, boost * 2.5)
            info["lcp_boost"] = round(boost, 3)

        elif action.action_type == "lazy_load":
            boost = random.uniform(0.03, 0.07)
            self.data["lcp_score"] = min(1.0, self.data.get("lcp_score", 0) + boost * 0.5)
            self.data["cls_score"] = min(1.0, self.data.get("cls_score", 0) + boost)
            self._mark_opportunity_done("lazy_load")
            reward = min(0.5, boost * 2.0)
            info["cls_boost"] = round(boost, 3)

        elif action.action_type == "reduce_js":
            boost = random.uniform(0.05, 0.10)
            self.data["tbt_score"] = min(1.0, self.data.get("tbt_score", 0) + boost)
            self.data["inp_score"] = min(1.0, self.data.get("inp_score", 0) + boost * 0.7)
            self.data["fcp_score"] = min(1.0, self.data.get("fcp_score", 0) + boost * 0.4)
            self._mark_opportunity_done("reduce_js")
            reward = min(0.5, boost * 2.5)
            info["tbt_boost"] = round(boost, 3)

        elif action.action_type == "optimize_fonts":
            boost = random.uniform(0.02, 0.05)
            self.data["fcp_score"] = min(1.0, self.data.get("fcp_score", 0) + boost)
            self.data["lcp_score"] = min(1.0, self.data.get("lcp_score", 0) + boost * 0.3)
            self._mark_opportunity_done("optimize_fonts")
            reward = min(0.5, boost * 2.0)
            info["fcp_boost"] = round(boost, 3)

        elif action.action_type == "improve_server_response":
            boost = random.uniform(0.04, 0.08)
            self.data["fcp_score"] = min(1.0, self.data.get("fcp_score", 0) + boost)
            self.data["lcp_score"] = min(1.0, self.data.get("lcp_score", 0) + boost * 0.6)
            self.data["tbt_score"] = min(1.0, self.data.get("tbt_score", 0) + boost * 0.3)
            self._mark_opportunity_done("improve_server_response")
            reward = min(0.5, boost * 2.2)
            info["fcp_boost"] = round(boost, 3)

        mobile_base = self.data.get("mobile_score", 0)
        desktop_base = self.data.get("desktop_score", 0)
        avg_cwv = (
            self.data.get("lcp_score", 0)
            + self.data.get("inp_score", 0)
            + self.data.get("cls_score", 0)
            + self.data.get("fcp_score", 0)
            + self.data.get("tbt_score", 0)
        ) / 5.0
        self.data["mobile_score"] = min(100, int(mobile_base + (avg_cwv * 100 - mobile_base) * 0.2))
        self.data["desktop_score"] = min(100, int(desktop_base + (avg_cwv * 100 - desktop_base) * 0.15))

        pass_rate = self._compute_pass_rate()
        reward += min(0.5, pass_rate * 0.5)
        info["pass_rate"] = pass_rate

        done = self._step_count >= self.max_steps
        if not done and pass_rate >= 1.0:
            done = True

        metrics = self._collect_metrics()
        features = self._compute_features(metrics)
        next_state = State(
            site_id=self.site_id,
            metrics=metrics,
            timestamp=time.time(),
            features=features,
        )
        return next_state, reward, done, info

    async def render(self) -> dict:
        return {
            "site_id": self.site_id,
            "step": self._step_count,
            "max_steps": self.max_steps,
            "lcp_score": self.data.get("lcp_score", 0),
            "inp_score": self.data.get("inp_score", 0),
            "cls_score": self.data.get("cls_score", 0),
            "fcp_score": self.data.get("fcp_score", 0),
            "tbt_score": self.data.get("tbt_score", 0),
            "mobile_score": self.data.get("mobile_score", 0),
            "desktop_score": self.data.get("desktop_score", 0),
            "pass_rate": self._compute_pass_rate(),
            "opportunities": self.data.get("opportunities", []),
        }

    def _compute_cwv_score(self, metrics: dict) -> float:
        lcp = metrics.get("lcp_score", 0)
        inp = metrics.get("inp_score", 0)
        cls = metrics.get("cls_score", 0)
        fcp = metrics.get("fcp_score", 0)
        tbt = metrics.get("tbt_score", 0)
        composite = (lcp + inp + cls + fcp + tbt) / 5.0
        mobile = metrics.get("mobile_score", 0) / 100.0
        desktop = metrics.get("desktop_score", 0) / 100.0
        return round(0.5 * composite + 0.25 * mobile + 0.25 * desktop, 4)

    def _compute_pass_rate(self) -> float:
        passed = 0
        total = len(CWV_PASS_THRESHOLDS)
        for metric, threshold in CWV_PASS_THRESHOLDS.items():
            if self.data.get(metric, 0) >= threshold:
                passed += 1
        return passed / total if total > 0 else 0.0

    def _collect_metrics(self) -> dict:
        return {
            "lcp_score": self.data.get("lcp_score", 0),
            "inp_score": self.data.get("inp_score", 0),
            "cls_score": self.data.get("cls_score", 0),
            "fcp_score": self.data.get("fcp_score", 0),
            "tbt_score": self.data.get("tbt_score", 0),
            "mobile_score": self.data.get("mobile_score", 0),
            "desktop_score": self.data.get("desktop_score", 0),
            "pass_rate": self._compute_pass_rate(),
            "opportunities_remaining": sum(
                1 for o in self.data.get("opportunities", []) if not o.get("done")
            ),
        }

    def _compute_features(self, metrics: dict) -> list[float]:
        return [
            metrics.get("lcp_score", 0),
            metrics.get("inp_score", 0),
            metrics.get("cls_score", 0),
            metrics.get("fcp_score", 0),
            metrics.get("tbt_score", 0),
            metrics.get("mobile_score", 0) / 100.0,
            metrics.get("desktop_score", 0) / 100.0,
            metrics.get("pass_rate", 0),
            metrics.get("opportunities_remaining", 0) / 5.0,
        ]

    def _mark_opportunity_done(self, opp_type: str):
        for opp in self.data.get("opportunities", []):
            if opp.get("type") == opp_type and not opp.get("done"):
                opp["done"] = True
                break
