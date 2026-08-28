from __future__ import annotations

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_admin, require_admin_write, require_user, require_user_write
from app.db.session import get_db
from app.models.entities import (
    AIMessage,
    AgentRun,
    AuditEvent,
    Book,
    Bookmark,
    CanonicalContentSource,
    Chapter,
    ChapterProvenance,
    ContentState,
    ContentSourceStatus,
    Conversation,
    Entitlement,
    IdentityToken,
    JournalEntry,
    Mission,
    MissionStatus,
    Note,
    ReadingProgress,
    RunStatus,
    Specialist,
    SupportRequest,
    User,
    UserSession,
    Voyage,
    VoyageEnrollment,
    VoyageLesson,
    VoyageReflection,
    utcnow,
)
from app.schemas.product import (
    AdminChapterCreate,
    AdminContentState,
    AdminEntitlement,
    BookmarkCreate,
    ConversationCreate,
    EmailRequest,
    JournalCreate,
    JournalUpdate,
    MessageCreate,
    NoteCreate,
    PasswordChange,
    PasswordReset,
    ProfileUpdate,
    ProgressUpdate,
    ReflectionSave,
    SignIn,
    SignUp,
    SupportCreate,
    TokenRequest,
    UserOut,
)
from app.services.ai import ProviderError, route_completion
from app.services.identity import (
    audit,
    clear_session,
    hash_password,
    issue_session,
    normalize_email,
    resolve_session,
    token_hash,
    validate_new_password,
    verify_password,
)
from app.services.mission_control import fix_mission, mission_snapshot


router = APIRouter()
settings = get_settings()


def _public_user(user: User) -> dict:
    return UserOut.model_validate(user).model_dump(mode="json")


def _owned(db: Session, model, object_id: str, user_id: str):
    item = db.scalar(select(model).where(and_(model.id == object_id, model.user_id == user_id)))
    if item is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return item


def _active_entitlement(db: Session, user_id: str, book_id: str) -> Entitlement | None:
    return db.scalar(
        select(Entitlement).where(
            Entitlement.user_id == user_id,
            Entitlement.book_id == book_id,
            Entitlement.state.in_(["trial", "active", "grace"]),
            or_(Entitlement.expires_at.is_(None), Entitlement.expires_at > utcnow()),
        )
    )


def _issue_identity_token(db: Session, user: User, purpose: str, lifetime_minutes: int) -> str:
    raw = secrets.token_urlsafe(48)
    db.add(
        IdentityToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=token_hash(raw),
            expires_at=utcnow() + timedelta(minutes=lifetime_minutes),
        )
    )
    db.flush()
    return raw


def _development_token(raw: str) -> dict:
    return (
        {"development_token": raw}
        if settings.env == "development" and settings.expose_development_tokens
        else {}
    )


@router.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignUp, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    validate_new_password(payload.password)
    email = normalize_email(payload.email)
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        role="member",
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    verification = _issue_identity_token(db, user, "verify_email", 24 * 60)
    csrf = issue_session(db, response, user)
    audit(db, request, "account.created", user.id)
    return {"user": _public_user(user), "csrf_token": csrf, "verification_delivery": "pending", **_development_token(verification)}


@router.post("/auth/signin")
def signin(payload: SignIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    csrf = issue_session(db, response, user)
    audit(db, request, "session.created", user.id)
    return {"user": _public_user(user), "csrf_token": csrf}


@router.get("/auth/session")
def session(request: Request, db: Session = Depends(get_db)) -> dict:
    resolved = resolve_session(db, request)
    if resolved is None:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": _public_user(resolved[1]), "csrf_token": request.cookies.get("lanseir_csrf")}


@router.post("/auth/signout", status_code=status.HTTP_204_NO_CONTENT)
def signout(request: Request, response: Response, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> Response:
    clear_session(db, request, response)
    audit(db, request, "session.revoked", user.id)
    response.status_code = 204
    return response


@router.post("/auth/verify")
def verify_email(payload: TokenRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    record = db.scalar(select(IdentityToken).where(IdentityToken.token_hash == token_hash(payload.token), IdentityToken.purpose == "verify_email"))
    if record is None or record.used_at is not None or _as_aware(record.expires_at) <= utcnow():
        raise HTTPException(status_code=400, detail="Verification link is invalid or expired")
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Verification link is invalid or expired")
    record.used_at = utcnow()
    user.email_verified_at = utcnow()
    audit(db, request, "account.email_verified", user.id)
    return {"verified": True}


@router.post("/auth/password/forgot")
def forgot_password(payload: EmailRequest, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    result = {"accepted": True, "delivery": "pending"}
    if user is not None and user.is_active:
        raw = _issue_identity_token(db, user, "password_reset", 30)
        db.commit()
        result.update(_development_token(raw))
    return result


@router.post("/auth/password/reset")
def reset_password(payload: PasswordReset, request: Request, db: Session = Depends(get_db)) -> dict:
    validate_new_password(payload.new_password)
    record = db.scalar(select(IdentityToken).where(IdentityToken.token_hash == token_hash(payload.token), IdentityToken.purpose == "password_reset"))
    if record is None or record.used_at is not None or _as_aware(record.expires_at) <= utcnow():
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
    user.password_hash = hash_password(payload.new_password)
    db.execute(
        update(IdentityToken)
        .where(IdentityToken.user_id == user.id, IdentityToken.purpose == "password_reset", IdentityToken.used_at.is_(None))
        .values(used_at=utcnow())
    )
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    audit(db, request, "account.password_reset", user.id)
    return {"reset": True}


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("/me")
def me(user: User = Depends(require_user)) -> dict:
    return _public_user(user)


@router.patch("/me")
def update_profile(payload: ProfileUpdate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    user.display_name = payload.display_name.strip()
    audit(db, request, "account.profile_updated", user.id)
    db.refresh(user)
    return _public_user(user)


@router.post("/me/password")
def change_password(payload: PasswordChange, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    validate_new_password(payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    db.execute(
        update(IdentityToken)
        .where(IdentityToken.user_id == user.id, IdentityToken.purpose == "password_reset", IdentityToken.used_at.is_(None))
        .values(used_at=utcnow())
    )
    audit(db, request, "account.password_changed", user.id)
    return {"changed": True}


@router.get("/me/export")
def export_account(user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    conversation_ids = list(db.scalars(select(Conversation.id).where(Conversation.user_id == user.id)).all())
    return {
        "exported_at": utcnow().isoformat(),
        "account": _public_user(user),
        "reading_progress": [_progress(item) for item in db.scalars(select(ReadingProgress).where(ReadingProgress.user_id == user.id)).all()],
        "bookmarks": [_bookmark(item) for item in db.scalars(select(Bookmark).where(Bookmark.user_id == user.id)).all()],
        "notes": [_note(item) for item in db.scalars(select(Note).where(Note.user_id == user.id)).all()],
        "captains_log": [_journal(item) for item in db.scalars(select(JournalEntry).where(JournalEntry.user_id == user.id)).all()],
        "voyage_reflections": [{"id": item.id, "lesson_id": item.lesson_id, "body": item.body, "updated_at": item.updated_at} for item in db.scalars(select(VoyageReflection).where(VoyageReflection.user_id == user.id)).all()],
        "voyage_enrollments": [{"id": item.id, "voyage_id": item.voyage_id, "status": item.status, "current_lesson_id": item.current_lesson_id, "completed_lesson_ids": item.completed_lesson_ids, "started_at": item.started_at, "completed_at": item.completed_at, "updated_at": item.updated_at} for item in db.scalars(select(VoyageEnrollment).where(VoyageEnrollment.user_id == user.id)).all()],
        "entitlements": [{"id": item.id, "book_id": item.book_id, "state": item.state, "source": item.source, "expires_at": item.expires_at, "created_at": item.created_at} for item in db.scalars(select(Entitlement).where(Entitlement.user_id == user.id)).all()],
        "conversations": [_conversation(item) for item in db.scalars(select(Conversation).where(Conversation.user_id == user.id)).all()],
        "ai_messages": [{"id": item.id, "conversation_id": item.conversation_id, "role": item.role, "content": item.content, "provider": item.provider, "model": item.model, "created_at": item.created_at} for item in db.scalars(select(AIMessage).where(AIMessage.conversation_id.in_(conversation_ids))).all()] if conversation_ids else [],
        "support_requests": [{"id": item.id, "email": item.email, "subject": item.subject, "body": item.body, "status": item.status, "created_at": item.created_at} for item in db.scalars(select(SupportRequest).where(SupportRequest.user_id == user.id)).all()],
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(payload: SignIn, request: Request, response: Response, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> Response:
    if normalize_email(payload.email) != user.email or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Account confirmation is incorrect")
    user_id = user.id
    db.delete(user)
    audit(db, request, "account.deleted", None, "user", user_id)
    response.delete_cookie("lanseir_session", path="/")
    response.delete_cookie("lanseir_csrf", path="/")
    response.status_code = 204
    return response


def _progress(item: ReadingProgress | None) -> dict | None:
    if item is None:
        return None
    return {"id": item.id, "book_id": item.book_id, "chapter_id": item.chapter_id, "percent": item.percent, "locator": item.locator, "audio_seconds": item.audio_seconds, "playback_rate": item.playback_rate, "updated_at": item.updated_at}


def _book(db: Session, item: Book, user: User) -> dict:
    entitlement = _active_entitlement(db, user.id, item.id)
    progress = db.scalar(select(ReadingProgress).where(ReadingProgress.user_id == user.id, ReadingProgress.book_id == item.id))
    return {
        "id": item.id,
        "slug": item.slug,
        "title": item.title,
        "subtitle": item.subtitle,
        "author": item.author,
        "publisher": item.publisher,
        "description": item.description,
        "state": item.state.value,
        "cover_asset": item.cover_asset,
        "entitlement": entitlement.state if entitlement else None,
        "progress": _progress(progress),
    }


def _validate_book_context(db: Session, user: User, book_id: str, chapter_id: str | None) -> None:
    if db.get(Book, book_id) is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if user.role != "admin" and _active_entitlement(db, user.id, book_id) is None:
        raise HTTPException(status_code=403, detail="Active book entitlement required")
    if chapter_id and db.scalar(select(Chapter).where(Chapter.id == chapter_id, Chapter.book_id == book_id)) is None:
        raise HTTPException(status_code=422, detail="Chapter does not belong to this book")


@router.get("/library")
def library(user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    return [_book(db, item, user) for item in db.scalars(select(Book).where(Book.state != ContentState.archived).order_by(Book.title)).all()]


@router.get("/books/{slug}")
def book_detail(slug: str, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    book = db.scalar(select(Book).where(Book.slug == slug))
    if book is None or book.state == ContentState.archived:
        raise HTTPException(status_code=404, detail="Book not found")
    entitled = _active_entitlement(db, user.id, book.id) is not None or user.role == "admin"
    chapters = []
    if book.state == ContentState.available and entitled:
        chapters = [
            {"id": item.id, "title": item.title, "position": item.position, "body": item.body, "audio_asset": item.audio_asset, "duration_seconds": item.duration_seconds}
            for item in db.scalars(select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.position)).all()
        ]
    return {**_book(db, book, user), "chapters": chapters, "content_access": "available" if chapters else "awaiting_authorized_content" if book.state == ContentState.draft else "entitlement_required"}


@router.put("/books/{book_id}/progress")
def save_progress(book_id: str, payload: ProgressUpdate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if user.role != "admin" and _active_entitlement(db, user.id, book_id) is None:
        raise HTTPException(status_code=403, detail="Active book entitlement required")
    if payload.chapter_id and db.scalar(select(Chapter).where(Chapter.id == payload.chapter_id, Chapter.book_id == book_id)) is None:
        raise HTTPException(status_code=422, detail="Chapter does not belong to this book")
    item = db.scalar(select(ReadingProgress).where(ReadingProgress.user_id == user.id, ReadingProgress.book_id == book_id))
    if item is None:
        item = ReadingProgress(user_id=user.id, book_id=book_id)
        db.add(item)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    audit(db, request, "reading.progress_saved", user.id, "book", book_id, {"percent": payload.percent})
    db.refresh(item)
    progress = _progress(item)
    assert progress is not None
    return progress


def _bookmark(item: Bookmark) -> dict:
    return {"id": item.id, "book_id": item.book_id, "chapter_id": item.chapter_id, "locator": item.locator, "label": item.label, "created_at": item.created_at}


@router.get("/bookmarks")
def list_bookmarks(user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    return [_bookmark(item) for item in db.scalars(select(Bookmark).where(Bookmark.user_id == user.id).order_by(Bookmark.created_at.desc())).all()]


@router.post("/bookmarks", status_code=201)
def create_bookmark(payload: BookmarkCreate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    _validate_book_context(db, user, payload.book_id, payload.chapter_id)
    item = Bookmark(user_id=user.id, **payload.model_dump())
    db.add(item)
    db.flush()
    audit(db, request, "bookmark.created", user.id, "bookmark", item.id)
    db.refresh(item)
    return _bookmark(item)


@router.delete("/bookmarks/{item_id}", status_code=204)
def delete_bookmark(item_id: str, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> Response:
    item = _owned(db, Bookmark, item_id, user.id)
    db.delete(item)
    audit(db, request, "bookmark.deleted", user.id, "bookmark", item_id)
    return Response(status_code=204)


def _note(item: Note) -> dict:
    return {"id": item.id, "book_id": item.book_id, "chapter_id": item.chapter_id, "locator": item.locator, "body": item.body, "created_at": item.created_at, "updated_at": item.updated_at}


@router.get("/notes")
def list_notes(user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    return [_note(item) for item in db.scalars(select(Note).where(Note.user_id == user.id).order_by(Note.updated_at.desc())).all()]


@router.post("/notes", status_code=201)
def create_note(payload: NoteCreate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    _validate_book_context(db, user, payload.book_id, payload.chapter_id)
    item = Note(user_id=user.id, **payload.model_dump())
    db.add(item)
    db.flush()
    audit(db, request, "note.created", user.id, "note", item.id)
    db.refresh(item)
    return _note(item)


@router.put("/notes/{item_id}")
def update_note(item_id: str, payload: NoteCreate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    item = _owned(db, Note, item_id, user.id)
    _validate_book_context(db, user, payload.book_id, payload.chapter_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    audit(db, request, "note.updated", user.id, "note", item.id)
    db.refresh(item)
    return _note(item)


@router.delete("/notes/{item_id}", status_code=204)
def delete_note(item_id: str, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> Response:
    item = _owned(db, Note, item_id, user.id)
    db.delete(item)
    audit(db, request, "note.deleted", user.id, "note", item_id)
    return Response(status_code=204)


def _journal(item: JournalEntry) -> dict:
    return {"id": item.id, "title": item.title, "body": item.body, "prompt": item.prompt, "created_at": item.created_at, "updated_at": item.updated_at}


@router.get("/captains-log")
def list_journal(query: str = Query(default="", max_length=200), user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    statement = select(JournalEntry).where(JournalEntry.user_id == user.id)
    if query:
        escaped = query.replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(or_(JournalEntry.title.ilike(f"%{escaped}%", escape="\\"), JournalEntry.body.ilike(f"%{escaped}%", escape="\\")))
    return [_journal(item) for item in db.scalars(statement.order_by(JournalEntry.updated_at.desc()).limit(100)).all()]


@router.post("/captains-log", status_code=201)
def create_journal(payload: JournalCreate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    item = JournalEntry(user_id=user.id, **payload.model_dump())
    db.add(item)
    db.flush()
    audit(db, request, "journal.created", user.id, "journal", item.id)
    db.refresh(item)
    return _journal(item)


@router.put("/captains-log/{item_id}")
def update_journal(item_id: str, payload: JournalUpdate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    item = _owned(db, JournalEntry, item_id, user.id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    audit(db, request, "journal.updated", user.id, "journal", item.id)
    db.refresh(item)
    return _journal(item)


@router.delete("/captains-log/{item_id}", status_code=204)
def delete_journal(item_id: str, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> Response:
    item = _owned(db, JournalEntry, item_id, user.id)
    db.delete(item)
    audit(db, request, "journal.deleted", user.id, "journal", item_id)
    return Response(status_code=204)


def _voyage(db: Session, item: Voyage, user: User) -> dict:
    enrollment = db.scalar(select(VoyageEnrollment).where(VoyageEnrollment.user_id == user.id, VoyageEnrollment.voyage_id == item.id))
    lessons = db.scalars(select(VoyageLesson).where(VoyageLesson.voyage_id == item.id).order_by(VoyageLesson.position)).all()
    reflections = {}
    if enrollment:
        reflections = {entry.lesson_id: entry for entry in db.scalars(select(VoyageReflection).where(VoyageReflection.user_id == user.id, VoyageReflection.enrollment_id == enrollment.id)).all()}
    return {
        "id": item.id,
        "slug": item.slug,
        "title": item.title,
        "description": item.description,
        "state": item.state.value,
        "enrollment": None if not enrollment else {"id": enrollment.id, "status": enrollment.status, "current_lesson_id": enrollment.current_lesson_id, "completed_lesson_ids": enrollment.completed_lesson_ids, "started_at": enrollment.started_at, "completed_at": enrollment.completed_at},
        "lessons": [{"id": lesson.id, "position": lesson.position, "title": lesson.title, "guidance": lesson.guidance, "prompt": lesson.prompt, "reflection": reflections[lesson.id].body if lesson.id in reflections else "", "completed": bool(enrollment and lesson.id in enrollment.completed_lesson_ids)} for lesson in lessons],
    }


@router.get("/voyages")
def list_voyages(user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    return [_voyage(db, item, user) for item in db.scalars(select(Voyage).where(Voyage.state == ContentState.available).order_by(Voyage.created_at)).all()]


@router.post("/voyages/{voyage_id}/enroll", status_code=201)
def enroll(voyage_id: str, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    voyage = db.get(Voyage, voyage_id)
    if voyage is None or voyage.state != ContentState.available:
        raise HTTPException(status_code=404, detail="Voyage not found")
    item = db.scalar(select(VoyageEnrollment).where(VoyageEnrollment.user_id == user.id, VoyageEnrollment.voyage_id == voyage_id))
    if item is None:
        first_lesson = db.scalar(select(VoyageLesson).where(VoyageLesson.voyage_id == voyage_id).order_by(VoyageLesson.position))
        item = VoyageEnrollment(user_id=user.id, voyage_id=voyage_id, current_lesson_id=first_lesson.id if first_lesson else None)
        db.add(item)
        audit(db, request, "voyage.started", user.id, "voyage", voyage_id)
    return _voyage(db, voyage, user)


@router.put("/voyages/{voyage_id}/lessons/{lesson_id}/reflection")
def save_reflection(voyage_id: str, lesson_id: str, payload: ReflectionSave, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    voyage = db.get(Voyage, voyage_id)
    enrollment = db.scalar(select(VoyageEnrollment).where(VoyageEnrollment.user_id == user.id, VoyageEnrollment.voyage_id == voyage_id))
    lesson = db.scalar(select(VoyageLesson).where(VoyageLesson.id == lesson_id, VoyageLesson.voyage_id == voyage_id))
    if voyage is None or enrollment is None or lesson is None:
        raise HTTPException(status_code=404, detail="Active Voyage lesson not found")
    if lesson_id not in enrollment.completed_lesson_ids and enrollment.current_lesson_id != lesson_id:
        raise HTTPException(status_code=409, detail="Complete the current lesson before advancing")
    reflection = db.scalar(select(VoyageReflection).where(VoyageReflection.user_id == user.id, VoyageReflection.lesson_id == lesson_id))
    if reflection is None:
        reflection = VoyageReflection(user_id=user.id, enrollment_id=enrollment.id, lesson_id=lesson_id, body=payload.body)
        db.add(reflection)
    else:
        reflection.body = payload.body
    if payload.complete and lesson_id not in enrollment.completed_lesson_ids:
        enrollment.completed_lesson_ids = [*enrollment.completed_lesson_ids, lesson_id]
        next_lesson = db.scalar(select(VoyageLesson).where(VoyageLesson.voyage_id == voyage_id, VoyageLesson.position > lesson.position).order_by(VoyageLesson.position))
        if next_lesson:
            enrollment.current_lesson_id = next_lesson.id
        else:
            enrollment.status = "completed"
            enrollment.current_lesson_id = None
            enrollment.completed_at = utcnow()
    audit(db, request, "voyage.reflection_saved", user.id, "lesson", lesson_id, {"completed": payload.complete})
    return _voyage(db, voyage, user)


def _conversation(item: Conversation) -> dict:
    return {"id": item.id, "title": item.title, "context_kind": item.context_kind, "context_id": item.context_id, "created_at": item.created_at, "updated_at": item.updated_at}


@router.get("/ai/conversations")
def conversations(user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[dict]:
    return [_conversation(item) for item in db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()).limit(50)).all()]


@router.post("/ai/conversations", status_code=201)
def create_conversation(payload: ConversationCreate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    item = Conversation(user_id=user.id, **payload.model_dump())
    db.add(item)
    db.flush()
    audit(db, request, "ai.conversation_created", user.id, "conversation", item.id)
    db.refresh(item)
    return _conversation(item)


@router.get("/ai/conversations/{conversation_id}")
def conversation_detail(conversation_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    item = _owned(db, Conversation, conversation_id, user.id)
    messages = db.scalars(select(AIMessage).where(AIMessage.conversation_id == item.id).order_by(AIMessage.created_at).limit(200)).all()
    return {**_conversation(item), "messages": [{"id": message.id, "role": message.role, "content": message.content, "provider": message.provider, "model": message.model, "created_at": message.created_at} for message in messages]}


def _authorized_context(db: Session, user: User, conversation: Conversation) -> str:
    if conversation.context_kind == "notes":
        notes = db.scalars(select(Note).where(Note.user_id == user.id).order_by(Note.updated_at.desc()).limit(10)).all()
        return "\n\n".join(note.body for note in notes)[:12_000]
    if conversation.context_kind == "book" and conversation.context_id:
        book = db.get(Book, conversation.context_id)
        if book and (_active_entitlement(db, user.id, book.id) or user.role == "admin"):
            return f"{book.title}: {book.description}"
    if conversation.context_kind == "chapter" and conversation.context_id:
        chapter = db.get(Chapter, conversation.context_id)
        if chapter and (_active_entitlement(db, user.id, chapter.book_id) or user.role == "admin"):
            return chapter.body[:12_000]
    if conversation.context_kind == "voyage" and conversation.context_id:
        voyage = db.get(Voyage, conversation.context_id)
        enrollment = db.scalar(select(VoyageEnrollment).where(VoyageEnrollment.user_id == user.id, VoyageEnrollment.voyage_id == conversation.context_id))
        if voyage and enrollment:
            reflections = db.scalars(select(VoyageReflection).where(VoyageReflection.user_id == user.id, VoyageReflection.enrollment_id == enrollment.id)).all()
            return f"{voyage.title}\n" + "\n".join(item.body for item in reflections)[:12_000]
    return ""


@router.post("/ai/conversations/{conversation_id}/messages", status_code=201)
async def send_message(conversation_id: str, payload: MessageCreate, request: Request, user: User = Depends(require_user_write), db: Session = Depends(get_db)) -> dict:
    conversation = _owned(db, Conversation, conversation_id, user.id)
    since = utcnow() - timedelta(days=1)
    message_count = db.scalar(select(func.count(AIMessage.id)).join(Conversation).where(Conversation.user_id == user.id, AIMessage.role == "user", AIMessage.created_at >= since)) or 0
    if message_count >= settings.ai_daily_message_limit:
        raise HTTPException(status_code=429, detail="Daily reflection limit reached")
    user_message = AIMessage(conversation_id=conversation.id, role="user", content=payload.content)
    run = AgentRun(user_id=user.id, specialist_key="liv", task_kind="reflection", status=RunStatus.running, provider=settings.ai_provider, model=settings.ai_model)
    db.add_all([user_message, run])
    db.commit()
    try:
        result = await route_completion(payload.content, _authorized_context(db, user, conversation))
    except asyncio.CancelledError:
        run.status = RunStatus.failed
        run.error_code = "execution_cancelled"
        run.completed_at = utcnow()
        db.commit()
        raise
    except ProviderError as exc:
        run.status = RunStatus.failed
        run.error_code = "provider_unavailable"
        run.completed_at = utcnow()
        audit(db, request, "ai.run_failed", user.id, "agent_run", run.id, {"error_code": run.error_code})
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        run.status = RunStatus.failed
        run.error_code = "execution_failed"
        run.completed_at = utcnow()
        audit(db, request, "ai.run_failed", user.id, "agent_run", run.id, {"error_code": run.error_code})
        raise HTTPException(status_code=500, detail="Reflection execution failed") from exc
    assistant = AIMessage(conversation_id=conversation.id, role="assistant", content=result.content, provider=result.provider, model=result.model, latency_ms=result.latency_ms, usage=result.usage)
    run.status = RunStatus.completed
    run.provider = result.provider
    run.model = result.model
    run.latency_ms = result.latency_ms
    run.usage = result.usage
    run.result_summary = "Reflection response completed"
    run.completed_at = utcnow()
    conversation.updated_at = utcnow()
    db.add(assistant)
    db.flush()
    audit(db, request, "ai.run_completed", user.id, "agent_run", run.id, {"provider": result.provider, "model": result.model})
    db.refresh(assistant)
    return {"message": {"id": assistant.id, "role": assistant.role, "content": assistant.content, "provider": assistant.provider, "model": assistant.model, "created_at": assistant.created_at}, "run": {"id": run.id, "status": run.status.value, "provider": run.provider, "model": run.model, "latency_ms": run.latency_ms, "usage": run.usage}}


@router.post("/support", status_code=201)
def create_support(payload: SupportCreate, request: Request, db: Session = Depends(get_db)) -> dict:
    resolved = resolve_session(db, request)
    item = SupportRequest(user_id=resolved[1].id if resolved else None, **payload.model_dump())
    db.add(item)
    db.flush()
    audit(db, request, "support.created", item.user_id, "support_request", item.id)
    db.refresh(item)
    return {"id": item.id, "status": item.status, "created_at": item.created_at}


@router.get("/admin/mission-control")
def mission_control(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    mission_state = mission_snapshot(db)
    counts = {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "open_support": db.scalar(select(func.count(SupportRequest.id)).where(SupportRequest.status == "open")) or 0,
        "active_voyages": db.scalar(select(func.count(VoyageEnrollment.id)).where(VoyageEnrollment.status == "active")) or 0,
        "failed_runs": db.scalar(select(func.count(AgentRun.id)).where(AgentRun.status == RunStatus.failed)) or 0,
        "open_missions": len([item for item in mission_state["missions"] if item.status not in {MissionStatus.verified, MissionStatus.cancelled}]),
    }
    runs = db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(20)).all()
    specialists = db.scalars(select(Specialist).where(Specialist.is_active.is_(True)).order_by(Specialist.key)).all()
    return {
        "system": "CADRE",
        "environment": settings.env,
        "release": settings.release_id,
        "ai_policy": {"provider": settings.ai_provider, "model": settings.ai_model, "daily_message_limit": settings.ai_daily_message_limit},
        "counts": counts,
        "specialists": [{"key": item.key, "name": item.name, "responsibility": item.responsibility, "permissions": item.permissions, "routing_criteria": item.routing_criteria, "validation_requirements": item.validation_requirements} for item in specialists],
        "recent_runs": [{"id": item.id, "specialist": item.specialist_key, "task_kind": item.task_kind, "status": item.status.value, "provider": item.provider, "model": item.model, "latency_ms": item.latency_ms, "error_code": item.error_code, "created_at": item.created_at} for item in runs],
        "missions": [
            {
                "id": item.id,
                "brief_id": item.command_brief_id,
                "title": item.title,
                "specialist": item.specialist_key,
                "status": item.status.value,
                "failure_class": item.failure_class,
                "root_cause": item.root_cause,
                "fix_available": item.status in {
                    MissionStatus.failed,
                    MissionStatus.blocked,
                    MissionStatus.stalled,
                    MissionStatus.verification_failed,
                },
                "updated_at": item.updated_at,
            }
            for item in mission_state["missions"][:50]
        ],
        "evidence": [
            {
                "mission_id": item.mission_id,
                "kind": item.kind,
                "summary": item.summary,
                "locator": item.locator,
                "passed": item.passed,
                "created_at": item.created_at,
            }
            for item in mission_state["evidence"][:50]
        ],
    }


@router.post("/admin/missions/{mission_id}/fix")
def admin_fix_mission(
    mission_id: str,
    request: Request,
    admin: User = Depends(require_admin_write),
    db: Session = Depends(get_db),
) -> dict:
    recovery = fix_mission(db, mission_id)
    audit(db, request, "mission.fix_invoked", admin.id, "mission", mission_id, {"recovery_id": recovery.id})
    return {"recovery_id": recovery.id, "status": recovery.status.value}


@router.post("/admin/books/{book_id}/chapters", status_code=201)
def create_chapter(book_id: str, payload: AdminChapterCreate, request: Request, admin: User = Depends(require_admin_write), db: Session = Depends(get_db)) -> dict:
    if db.get(Book, book_id) is None:
        raise HTTPException(status_code=404, detail="Book not found")
    source = db.get(CanonicalContentSource, payload.source_id)
    if source is None or source.book_id != book_id or source.status != ContentSourceStatus.approved:
        raise HTTPException(status_code=409, detail="Approved canonical content source required")
    expected_hash = source.chapter_hashes.get(str(payload.position))
    content_hash = hashlib.sha256(payload.body.encode("utf-8")).hexdigest()
    if expected_hash is None or not secrets.compare_digest(expected_hash, content_hash):
        raise HTTPException(status_code=409, detail="Chapter content does not match the approved canonical source")
    values = payload.model_dump(exclude={"source_id"})
    item = Chapter(book_id=book_id, **values)
    try:
        db.add(item)
        db.flush()
        db.add(ChapterProvenance(chapter_id=item.id, source_id=source.id, content_sha256=content_hash))
        audit(db, request, "content.chapter_created", admin.id, "chapter", item.id, {"source_id": source.id, "sha256": content_hash})
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Chapter position already exists")
    db.refresh(item)
    return {"id": item.id, "book_id": item.book_id, "title": item.title, "position": item.position, "source_id": source.id, "sha256": content_hash}


@router.put("/admin/books/{book_id}/state")
def set_book_state(book_id: str, payload: AdminContentState, request: Request, admin: User = Depends(require_admin_write), db: Session = Depends(get_db)) -> dict:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if payload.state == "available":
        chapter_count = db.scalar(select(func.count(Chapter.id)).where(Chapter.book_id == book.id)) or 0
        approved_count = db.scalar(
            select(func.count(ChapterProvenance.id))
            .join(Chapter, ChapterProvenance.chapter_id == Chapter.id)
            .join(CanonicalContentSource, ChapterProvenance.source_id == CanonicalContentSource.id)
            .where(Chapter.book_id == book.id, CanonicalContentSource.status == ContentSourceStatus.approved)
        ) or 0
        if chapter_count == 0 or approved_count != chapter_count:
            raise HTTPException(status_code=409, detail="Every chapter requires approved canonical provenance before publication")
    book.state = ContentState(payload.state)
    audit(db, request, "content.state_changed", admin.id, "book", book.id, {"state": payload.state})
    return {"id": book.id, "state": book.state.value}


@router.post("/admin/entitlements", status_code=201)
def grant_entitlement(payload: AdminEntitlement, request: Request, admin: User = Depends(require_admin_write), db: Session = Depends(get_db)) -> dict:
    if db.get(User, payload.user_id) is None or db.get(Book, payload.book_id) is None:
        raise HTTPException(status_code=404, detail="User or book not found")
    item = db.scalar(select(Entitlement).where(Entitlement.user_id == payload.user_id, Entitlement.book_id == payload.book_id))
    if item is None:
        item = Entitlement(**payload.model_dump())
        db.add(item)
        db.flush()
    else:
        item.state = payload.state
        item.source = payload.source
    audit(db, request, "entitlement.changed", admin.id, "entitlement", item.id, {"state": item.state})
    db.refresh(item)
    return {"id": item.id, "user_id": item.user_id, "book_id": item.book_id, "state": item.state, "source": item.source}


@router.get("/admin/audit")
def admin_audit(_: User = Depends(require_admin), db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=100)) -> list[dict]:
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    return [{"id": item.id, "event_type": item.event_type, "user_id": item.user_id, "resource_type": item.resource_type, "resource_id": item.resource_id, "request_id": item.request_id, "metadata": item.metadata_json, "created_at": item.created_at} for item in events]
