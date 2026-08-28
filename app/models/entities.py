import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class ProjectStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class BriefStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    active = "active"
    completed = "completed"
    blocked = "blocked"


class ContentState(str, enum.Enum):
    draft = "draft"
    available = "available"
    archived = "archived"


class ContentSourceStatus(str, enum.Enum):
    validated = "validated"
    approved = "approved"
    superseded = "superseded"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    blocked = "blocked"


class SchemaMigration(Base):
    __tablename__ = "schema_migrations"
    version: Mapped[str] = mapped_column(String(80), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MissionStatus(str, enum.Enum):
    queued = "queued"
    dispatched = "dispatched"
    running = "running"
    verification_pending = "verification_pending"
    verified = "verified"
    failed = "failed"
    blocked = "blocked"
    stalled = "stalled"
    verification_failed = "verification_failed"
    recovering = "recovering"
    cancelled = "cancelled"


class ArtifactState(str, enum.Enum):
    generated = "generated"
    validated = "validated"
    installed = "installed"
    registered = "registered"
    archived = "archived"


class DoctrineEntry(Base):
    __tablename__ = "doctrine_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="principle")
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.active)
    source_of_truth: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    briefs: Mapped[list["CommandBrief"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class CommandBrief(Base):
    __tablename__ = "command_briefs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    objective: Mapped[str] = mapped_column(Text)
    authority: Mapped[str] = mapped_column(Text, default="Master Operating Doctrine")
    current_state: Mapped[str] = mapped_column(Text, default="")
    constraints: Mapped[list] = mapped_column(JSON, default=list)
    dependencies: Mapped[list] = mapped_column(JSON, default=list)
    expected_outputs: Mapped[list] = mapped_column(JSON, default=list)
    validation_criteria: Mapped[list] = mapped_column(JSON, default=list)
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    specialist_roles: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[BriefStatus] = mapped_column(Enum(BriefStatus), default=BriefStatus.draft)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    project: Mapped[Project] = relationship(back_populates="briefs")
    missions: Mapped[list["Mission"]] = relationship(back_populates="command_brief", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(32), default="member", index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship()


class IdentityToken(Base):
    __tablename__ = "identity_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Book(Base):
    __tablename__ = "books"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    subtitle: Mapped[str] = mapped_column(String(240), default="")
    author: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    publisher: Mapped[str] = mapped_column(String(160), default="Sirrah Publishing")
    state: Mapped[ContentState] = mapped_column(Enum(ContentState), default=ContentState.draft)
    cover_asset: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "position", name="uq_chapter_book_position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    position: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    audio_asset: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    book: Mapped[Book] = relationship(back_populates="chapters")


class CanonicalContentSource(Base):
    __tablename__ = "canonical_content_sources"
    __table_args__ = (UniqueConstraint("book_id", "manifest_sha256", name="uq_content_source_book_manifest"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    source_locator: Mapped[str] = mapped_column(String(500))
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    chapter_hashes: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[ContentSourceStatus] = mapped_column(Enum(ContentSourceStatus), default=ContentSourceStatus.validated, index=True)
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    approval_receipt: Mapped[str] = mapped_column(String(500), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChapterProvenance(Base):
    __tablename__ = "chapter_provenance"
    __table_args__ = (UniqueConstraint("chapter_id", name="uq_chapter_provenance_chapter"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("canonical_content_sources.id", ondelete="RESTRICT"), index=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Entitlement(Base):
    __tablename__ = "entitlements"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_entitlement_user_book"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String(32), default="active")
    source: Mapped[str] = mapped_column(String(80), default="admin")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_progress_user_book"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[str | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    percent: Mapped[float] = mapped_column(Float, default=0.0)
    locator: Mapped[str] = mapped_column(String(240), default="")
    audio_seconds: Mapped[int] = mapped_column(Integer, default=0)
    playback_rate: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (Index("ix_bookmarks_owner_book", "user_id", "book_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    chapter_id: Mapped[str | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    locator: Mapped[str] = mapped_column(String(240), default="")
    label: Mapped[str] = mapped_column(String(200), default="Bookmark")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (Index("ix_notes_owner_book", "user_id", "book_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    chapter_id: Mapped[str | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    locator: Mapped[str] = mapped_column(String(240), default="")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (Index("ix_journal_owner_updated", "user_id", "updated_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), default="Untitled entry")
    body: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Voyage(Base):
    __tablename__ = "voyages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    state: Mapped[ContentState] = mapped_column(Enum(ContentState), default=ContentState.draft)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    lessons: Mapped[list["VoyageLesson"]] = relationship(back_populates="voyage", cascade="all, delete-orphan")


class VoyageLesson(Base):
    __tablename__ = "voyage_lessons"
    __table_args__ = (UniqueConstraint("voyage_id", "position", name="uq_voyage_lesson_position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    voyage_id: Mapped[str] = mapped_column(ForeignKey("voyages.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(240))
    guidance: Mapped[str] = mapped_column(Text)
    prompt: Mapped[str] = mapped_column(Text)
    voyage: Mapped[Voyage] = relationship(back_populates="lessons")


class VoyageEnrollment(Base):
    __tablename__ = "voyage_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "voyage_id", name="uq_enrollment_user_voyage"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    voyage_id: Mapped[str] = mapped_column(ForeignKey("voyages.id", ondelete="CASCADE"), index=True)
    current_lesson_id: Mapped[str | None] = mapped_column(ForeignKey("voyage_lessons.id", ondelete="SET NULL"), nullable=True)
    completed_lesson_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class VoyageReflection(Base):
    __tablename__ = "voyage_reflections"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_reflection_user_lesson"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("voyage_enrollments.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("voyage_lessons.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), default="New reflection")
    context_kind: Mapped[str] = mapped_column(String(32), default="general")
    context_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AIMessage(Base):
    __tablename__ = "ai_messages"
    __table_args__ = (Index("ix_ai_message_conversation_created", "conversation_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Specialist(Base):
    __tablename__ = "specialists"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    responsibility: Mapped[str] = mapped_column(Text)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    routing_criteria: Mapped[list] = mapped_column(JSON, default=list)
    validation_requirements: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    specialist_key: Mapped[str] = mapped_column(String(80), index=True)
    task_kind: Mapped[str] = mapped_column(String(80))
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.queued, index=True)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    result_summary: Mapped[str] = mapped_column(Text, default="")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Mission(Base):
    __tablename__ = "missions"
    __table_args__ = (Index("ix_missions_dispatch", "status", "priority", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    command_brief_id: Mapped[str] = mapped_column(ForeignKey("command_briefs.id", ondelete="CASCADE"), index=True)
    recovery_for_id: Mapped[str | None] = mapped_column(ForeignKey("missions.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240))
    action_key: Mapped[str] = mapped_column(String(80), index=True)
    specialist_key: Mapped[str] = mapped_column(String(80), default="al", index=True)
    status: Mapped[MissionStatus] = mapped_column(Enum(MissionStatus), default=MissionStatus.queued, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    dependency_ids: Mapped[list] = mapped_column(JSON, default=list)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_outputs: Mapped[list] = mapped_column(JSON, default=list)
    validation_criteria: Mapped[list] = mapped_column(JSON, default=list)
    failure_class: Mapped[str | None] = mapped_column(String(40), nullable=True)
    root_cause: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    command_brief: Mapped[CommandBrief] = relationship(back_populates="missions")
    evidence: Mapped[list["MissionEvidence"]] = relationship(back_populates="mission", cascade="all, delete-orphan")
    artifacts: Mapped[list["MissionArtifact"]] = relationship(back_populates="mission", cascade="all, delete-orphan")


class MissionEvidence(Base):
    __tablename__ = "mission_evidence"
    __table_args__ = (Index("ix_mission_evidence_mission_created", "mission_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(Text)
    locator: Mapped[str] = mapped_column(String(500), default="")
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    mission: Mapped[Mission] = relationship(back_populates="evidence")


class MissionArtifact(Base):
    __tablename__ = "mission_artifacts"
    __table_args__ = (UniqueConstraint("mission_id", "sha256", name="uq_mission_artifact_hash"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(240))
    source_locator: Mapped[str] = mapped_column(String(500))
    destination_locator: Mapped[str] = mapped_column(String(500), default="")
    archive_locator: Mapped[str] = mapped_column(String(500), default="")
    sha256: Mapped[str] = mapped_column(String(64))
    state: Mapped[ArtifactState] = mapped_column(Enum(ArtifactState), default=ArtifactState.generated, index=True)
    source_cleaned: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    mission: Mapped[Mission] = relationship(back_populates="artifacts")


class SupportRequest(Base):
    __tablename__ = "support_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
