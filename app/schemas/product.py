from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


Email = str
EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SignUp(BaseModel):
    email: Email = Field(pattern=EMAIL_PATTERN, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not (any(c.islower() for c in value) and any(c.isupper() for c in value) and any(c.isdigit() for c in value)):
            raise ValueError("Password must include upper-case, lower-case, and numeric characters")
        return value


class SignIn(BaseModel):
    email: Email = Field(pattern=EMAIL_PATTERN, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORMModel):
    id: str
    email: str
    display_name: str
    role: str
    email_verified_at: datetime | None
    created_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class EmailRequest(BaseModel):
    email: Email = Field(pattern=EMAIL_PATTERN, max_length=320)


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class PasswordReset(TokenRequest):
    new_password: str = Field(min_length=12, max_length=128)


class ProgressUpdate(BaseModel):
    chapter_id: str | None = Field(default=None, max_length=36)
    percent: float = Field(ge=0, le=100)
    locator: str = Field(default="", max_length=240)
    audio_seconds: int = Field(default=0, ge=0, le=10_000_000)
    playback_rate: float = Field(default=1.0, ge=0.5, le=2.5)


class BookmarkCreate(BaseModel):
    book_id: str = Field(max_length=36)
    chapter_id: str | None = Field(default=None, max_length=36)
    locator: str = Field(default="", max_length=240)
    label: str = Field(default="Bookmark", min_length=1, max_length=200)


class NoteCreate(BaseModel):
    book_id: str = Field(max_length=36)
    chapter_id: str | None = Field(default=None, max_length=36)
    locator: str = Field(default="", max_length=240)
    body: str = Field(min_length=1, max_length=20_000)


class JournalCreate(BaseModel):
    title: str = Field(default="Untitled entry", min_length=1, max_length=240)
    body: str = Field(default="", max_length=100_000)
    prompt: str = Field(default="", max_length=500)


class JournalUpdate(JournalCreate):
    pass


class ReflectionSave(BaseModel):
    body: str = Field(min_length=1, max_length=50_000)
    complete: bool = False


class ConversationCreate(BaseModel):
    title: str = Field(default="New reflection", min_length=1, max_length=240)
    context_kind: str = Field(default="general", pattern=r"^(general|book|chapter|voyage|notes)$")
    context_id: str | None = Field(default=None, max_length=36)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8_000)


class SupportCreate(BaseModel):
    email: Email = Field(pattern=EMAIL_PATTERN, max_length=320)
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=5, max_length=20_000)


class AdminContentState(BaseModel):
    state: str = Field(pattern=r"^(draft|available|archived)$")


class AdminChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    position: int = Field(ge=1, le=10_000)
    body: str = Field(min_length=1, max_length=500_000)
    audio_asset: str | None = Field(default=None, max_length=500)
    duration_seconds: int | None = Field(default=None, ge=1, le=10_000_000)


class AdminEntitlement(BaseModel):
    user_id: str = Field(max_length=36)
    book_id: str = Field(max_length=36)
    state: str = Field(default="active", pattern=r"^(trial|active|grace|canceled|expired)$")
    source: str = Field(default="admin", max_length=80)
