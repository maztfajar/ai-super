from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, List
from datetime import datetime, timezone
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=gen_id, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True)
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    role: str = Field(default='admin')  # admin | subadmin
    # ── Email & 2FA ──────────────────────────────────────────
    totp_secret: Optional[str] = None          # Base32 secret for TOTP/2FA
    totp_enabled: bool = False                 # 2FA aktif atau tidak
    telegram_chat_id: Optional[str] = None    # Chat ID Telegram untuk OTP
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"
    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: str = Field(index=True)
    title: str = "New Chat"
    model_used: str = ""
    platform: str = "web"          # web | telegram | whatsapp | api
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    project_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: str = Field(default_factory=gen_id, primary_key=True)
    session_id: str = Field(index=True)
    user_id: str = Field(index=True)
    role: str                       # user | assistant | system
    content: str
    model: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    rag_sources: Optional[str] = None   # JSON list of source doc names
    thinking_process: Optional[str] = None  # Collected status/thinking steps for expandable section
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class KnowledgeDoc(SQLModel, table=True):
    __tablename__ = "knowledge_docs"
    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: str = Field(index=True)
    filename: str
    original_name: str
    doc_type: str                   # pdf | docx | txt | web | csv
    file_size_kb: int = 0
    chunks: int = 0
    status: str = "indexing"        # indexing | ready | error
    collection: str = "default"
    indexed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class WorkflowDef(SQLModel, table=True):
    __tablename__ = "workflow_defs"
    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: str = Field(index=True)
    name: str
    description: Optional[str] = None
    nodes_json: str = "[]"          # JSON: list of node defs
    edges_json: str = "[]"          # JSON: list of edge defs
    trigger_type: str = "manual"    # manual | schedule | webhook | message
    trigger_config: str = "{}"      # JSON
    is_active: bool = True
    run_count: int = 0
    last_run_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class WorkflowRun(SQLModel, table=True):
    __tablename__ = "workflow_runs"
    id: str = Field(default_factory=gen_id, primary_key=True)
    workflow_id: str = Field(index=True)
    status: str = "running"         # running | success | failed
    trigger_data: str = "{}"
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    finished_at: Optional[datetime] = None


class UserMemoryEntry(SQLModel, table=True):
    __tablename__ = "user_memories"
    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: str = Field(index=True)
    memory_type: str                # behavioral | preference | fact | summary
    content: str
    importance: float = 1.0
    source_session: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ModelConfig(SQLModel, table=True):
    __tablename__ = "model_configs"
    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: str = Field(index=True)
    model_id: str
    display_name: str
    provider: str                   # openai | anthropic | google | ollama | custom
    api_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    is_active: bool = True
    is_default: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ApiLog(SQLModel, table=True):
    __tablename__ = "api_logs"
    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: Optional[str] = None
    endpoint: str
    method: str
    status_code: int
    duration_ms: int
    model_used: Optional[str] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class LoginLog(SQLModel, table=True):
    """Riwayat percobaan login — untuk audit & deteksi brute-force."""
    __tablename__ = "login_logs"
    id: str = Field(default_factory=gen_id, primary_key=True)
    username: str = Field(index=True)
    success: bool
    ip_address: str = ""
    user_agent: str = ""
    reason: str = ""          # "" | wrong_password | locked | inactive
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class RecoveryToken(SQLModel, table=True):
    """Token sementara untuk reset password via email/kode."""
    __tablename__ = "recovery_tokens"
    id: str = Field(default_factory=gen_id, primary_key=True)
    user_id: str = Field(index=True)
    token_hash: str           # SHA-256 dari token asli
    used: bool = False
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class AgentPerformance(SQLModel, table=True):
    """Track per-agent performance metrics for the learning engine."""
    __tablename__ = "agent_performance"
    id: str = Field(default_factory=gen_id, primary_key=True)
    agent_type: str = Field(index=True)      # reasoning, coding, research, writing, etc
    model_used: str = Field(index=True)       # actual model ID (e.g. gpt-4o, claude-3-5-sonnet)
    task_type: str = ""                       # category of task handled
    task_id: Optional[str] = None             # link to TaskExecution
    success: bool = True
    confidence: float = 0.0                   # 0.0 - 1.0
    execution_time_ms: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class TaskExecution(SQLModel, table=True):
    """Track orchestrator task execution lifecycle."""
    __tablename__ = "task_executions"
    id: str = Field(default_factory=gen_id, primary_key=True)
    session_id: str = Field(index=True)
    user_id: str = Field(index=True)
    original_request: str = ""                # user's original message
    task_spec_json: Optional[str] = None      # JSON of TaskSpecification
    subtasks_json: Optional[str] = None       # JSON of decomposed subtasks
    dag_json: Optional[str] = None            # JSON of dependency graph
    assignments_json: Optional[str] = None    # JSON of agent assignments
    status: str = "preprocessing"             # preprocessing | decomposing | executing | validating | aggregating | completed | failed
    result_summary: Optional[str] = None
    total_time_ms: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    agents_used: Optional[str] = None         # JSON list of agent/model combos used
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    completed_at: Optional[datetime] = None
    vps_deployment_at: Optional[datetime] = None  # Track VPS deployment timing
