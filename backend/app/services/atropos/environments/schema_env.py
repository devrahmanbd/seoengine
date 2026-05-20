import asyncio
import time

from app.services.atropos.base_env import SEOEnvironment, SEOAction, State


RECOMMENDED_SCHEMA_TYPES = [
    "article_schema",
    "faq_schema",
    "breadcrumb_schema",
    "organization_schema",
    "local_business_schema",
]


class SchemaEnv(SEOEnvironment):
    def __init__(self, site_id: str = "default"):
        self.site_id = site_id
        self._step_count = 0
        self.max_steps = 20
        self.data: dict = {}

    async def reset(self) -> State:
        self._step_count = 0
        self.data = {
            "current_schema_types": ["organization_schema"],
            "schema_count": 1,
            "schema_errors": [
                {"type": "missing_@context", "severity": "error"},
                {"type": "invalid_date_format", "severity": "warning"},
            ],
            "missing_types": list(RECOMMENDED_SCHEMA_TYPES[1:]),
            "has_jsonld": True,
            "has_microdata": False,
            "validation_pass_rate": 0.65,
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

        schema_generators = {
            "generate_article_schema": "article_schema",
            "generate_faq_schema": "faq_schema",
            "generate_breadcrumb": "breadcrumb_schema",
            "generate_organization": "organization_schema",
            "generate_local_business": "local_business_schema",
        }

        if action.action_type in schema_generators:
            schema_type = schema_generators[action.action_type]
            if schema_type not in self.data["current_schema_types"]:
                self.data["current_schema_types"].append(schema_type)
                self.data["schema_count"] = len(self.data["current_schema_types"])
                if schema_type in self.data["missing_types"]:
                    self.data["missing_types"].remove(schema_type)
                coverage_delta = min(0.5, 1.0 / len(RECOMMENDED_SCHEMA_TYPES))
                validation_boost = 0.05 * len(self.data["current_schema_types"])
                self.data["validation_pass_rate"] = min(
                    1.0, self.data.get("validation_pass_rate", 0.65) + validation_boost
                )
                reward = min(0.5, coverage_delta + validation_boost)
                info["schema_type_added"] = schema_type
                info["schema_template"] = self._generate_schema(schema_type)
            else:
                reward = 0.0
                info["info"] = f"Schema type {schema_type} already present"

        elif action.action_type == "fix_schema_errors":
            errors = self.data.get("schema_errors", [])
            fixed_count = len(errors)
            self.data["schema_errors"] = []
            self.data["validation_pass_rate"] = min(
                1.0, self.data.get("validation_pass_rate", 0.65) + fixed_count * 0.1
            )
            reward = min(0.5, fixed_count * 0.1)
            info["errors_fixed"] = fixed_count

        coverage = len(self.data.get("current_schema_types", [])) / len(RECOMMENDED_SCHEMA_TYPES)
        reward += coverage * 0.1

        done = self._step_count >= self.max_steps
        if not done:
            if (
                len(self.data.get("missing_types", [])) == 0
                and len(self.data.get("schema_errors", [])) == 0
            ):
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
            "current_schema_types": self.data.get("current_schema_types", []),
            "schema_count": self.data.get("schema_count", 0),
            "schema_errors": self.data.get("schema_errors", []),
            "missing_types": self.data.get("missing_types", []),
            "has_jsonld": self.data.get("has_jsonld", False),
            "has_microdata": self.data.get("has_microdata", False),
            "validation_pass_rate": self.data.get("validation_pass_rate", 0),
            "coverage": len(self.data.get("current_schema_types", [])) / len(RECOMMENDED_SCHEMA_TYPES),
        }

    def _compute_schema_score(self, metrics: dict) -> float:
        validation = metrics.get("validation_pass_rate", 0)
        coverage = metrics.get("schema_coverage", 0)
        errors = metrics.get("schema_error_count", 0)
        error_penalty = max(0.0, 1.0 - errors * 0.2)
        has_jsonld = 0.1 if metrics.get("has_jsonld") else 0.0
        return round(
            0.35 * validation
            + 0.35 * coverage
            + 0.20 * error_penalty
            + 0.10 * has_jsonld,
            4,
        )

    def _collect_metrics(self) -> dict:
        schema_types = self.data.get("current_schema_types", [])
        coverage = len(schema_types) / len(RECOMMENDED_SCHEMA_TYPES)
        return {
            "current_schema_types": schema_types,
            "schema_count": len(schema_types),
            "schema_errors": self.data.get("schema_errors", []),
            "schema_error_count": len(self.data.get("schema_errors", [])),
            "missing_types": self.data.get("missing_types", []),
            "has_jsonld": self.data.get("has_jsonld", False),
            "has_microdata": self.data.get("has_microdata", False),
            "validation_pass_rate": self.data.get("validation_pass_rate", 0),
            "schema_coverage": coverage,
        }

    def _compute_features(self, metrics: dict) -> list[float]:
        return [
            metrics.get("schema_coverage", 0),
            metrics.get("validation_pass_rate", 0),
            metrics.get("schema_error_count", 0) / 5.0,
            len(metrics.get("missing_types", [])) / len(RECOMMENDED_SCHEMA_TYPES),
            1.0 if metrics.get("has_jsonld") else 0.0,
            1.0 if metrics.get("has_microdata") else 0.0,
        ]

    def _generate_schema(self, schema_type: str) -> dict:
        templates = {
            "article_schema": {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": "{{HEADLINE}}",
                "author": {
                    "@type": "Person",
                    "name": "{{AUTHOR_NAME}}",
                },
                "datePublished": "{{DATE_PUBLISHED}}",
                "dateModified": "{{DATE_MODIFIED}}",
                "image": "{{FEATURED_IMAGE_URL}}",
                "publisher": {
                    "@type": "Organization",
                    "name": "{{PUBLISHER_NAME}}",
                },
                "description": "{{META_DESCRIPTION}}",
                "mainEntityOfPage": {
                    "@type": "WebPage",
                    "@id": "{{PAGE_URL}}",
                },
            },
            "faq_schema": {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "{{QUESTION_1}}",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "{{ANSWER_1}}",
                        },
                    },
                ],
            },
            "breadcrumb_schema": {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "{{CRUMB_1_NAME}}",
                        "item": "{{CRUMB_1_URL}}",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "{{CRUMB_2_NAME}}",
                        "item": "{{CRUMB_2_URL}}",
                    },
                ],
            },
            "organization_schema": {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "{{ORGANIZATION_NAME}}",
                "url": "{{WEBSITE_URL}}",
                "logo": "{{LOGO_URL}}",
                "sameAs": [
                    "{{SOCIAL_LINK_1}}",
                    "{{SOCIAL_LINK_2}}",
                ],
            },
            "local_business_schema": {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": "{{BUSINESS_NAME}}",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "{{STREET_ADDRESS}}",
                    "addressLocality": "{{LOCALITY}}",
                    "addressRegion": "{{REGION}}",
                    "postalCode": "{{POSTAL_CODE}}",
                    "addressCountry": "{{COUNTRY}}",
                },
                "telephone": "{{PHONE_NUMBER}}",
                "openingHoursSpecification": [
                    {
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": "{{DAY}}",
                        "opens": "{{OPENS}}",
                        "closes": "{{CLOSES}}",
                    },
                ],
                "url": "{{WEBSITE_URL}}",
                "image": "{{IMAGE_URL}}",
            },
        }
        return templates.get(
            schema_type,
            {"@context": "https://schema.org", "@type": "Thing", "name": "{{NAME}}"},
        )
