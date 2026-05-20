from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


# User Models
class UserBase(BaseModel):
    email: str
    name: str
    plan: str = "free"
    subscription_status: str = "active"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    plan: Optional[str] = None
    subscription_status: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    api_calls_used: int = 0
    api_calls_limit: int = 1000
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Website Models
class WebsiteBase(BaseModel):
    url: str
    name: str
    platform: str = "wordpress"


class WebsiteResponse(WebsiteBase):
    id: UUID
    user_id: UUID
    api_key: str
    status: str
    seo_score: int = 0
    last_scan_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# API Key Models
class APIKeyCreate(BaseModel):
    user_id: UUID
    label: Optional[str] = None
    rate_limit: int = 1000
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    id: UUID
    user_id: UUID
    key_prefix: str
    label: Optional[str]
    rate_limit: int
    calls_count: int = 0
    last_used_at: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


# SEO Result Models
class SEOResultResponse(BaseModel):
    id: UUID
    website_id: UUID
    result_type: str
    score: int
    data: dict
    issues: List[dict]
    scanned_at: datetime

    class Config:
        from_attributes = True


# Task Models
class TaskResponse(BaseModel):
    id: UUID
    website_id: UUID
    task_type: str
    status: str
    priority: str
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Error Log Models
class ErrorLogResponse(BaseModel):
    id: UUID
    level: str
    source: str
    message: str
    stack_trace: Optional[str]
    context: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# AI Log Models
class AgentLogResponse(BaseModel):
    id: UUID
    agent_type: str
    task_id: Optional[str]
    status: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    execution_time_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# Pagination
class PaginatedResponse(BaseModel):
    data: List[Any]
    meta: dict