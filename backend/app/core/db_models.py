from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    plan = Column(String, default="free")
    subscription_status = Column(String, default="active")
    api_calls_used = Column(Integer, default=0)
    api_calls_limit = Column(Integer, default=1000)
    openrouter_key = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    websites = relationship("Website", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")


class Website(Base):
    __tablename__ = "websites"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    name = Column(String)
    platform = Column(String, default="wordpress")
    api_key = Column(String, unique=True)
    status = Column(String, default="connected")
    seo_score = Column(Integer, default=0)
    last_scan_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="websites")
    results = relationship("SEOResult", back_populates="website")
    tasks = relationship("Task", back_populates="website")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    label = Column(String)
    rate_limit = Column(Integer, default=1000)
    calls_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="api_keys")


class SEOResult(Base):
    __tablename__ = "seo_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    website_id = Column(String, ForeignKey("websites.id"), nullable=False)
    result_type = Column(String, nullable=False)
    score = Column(Integer)
    data = Column(JSON)
    issues = Column(JSON, default=[])
    scanned_at = Column(DateTime, server_default=func.now())

    website = relationship("Website", back_populates="results")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    website_id = Column(String, ForeignKey("websites.id"), nullable=False)
    task_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    priority = Column(String, default="medium")
    input_data = Column(JSON)
    result_data = Column(JSON)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    website = relationship("Website", back_populates="tasks")


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    level = Column(String, nullable=False)
    source = Column(String, nullable=False)
    message = Column(String, nullable=False)
    stack_trace = Column(Text)
    context = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_type = Column(String, nullable=False)
    task_id = Column(String)
    status = Column(String, nullable=False)
    input_data = Column(JSON)
    output_data = Column(JSON)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class Admin(Base):
    __tablename__ = "admins"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())