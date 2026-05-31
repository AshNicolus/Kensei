from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.api import crud
from backend.api.auth import get_current_user
from backend.api.deps import get_db
from backend.api.models import User
from backend.core.logger import logger
from backend.core.security import (
    ACCESS_TOKEN_TTL_MINUTES,
    create_access_token,
    hash_password,
    verify_password,
)
from backend.forge.samples import seed_samples_for_user
from backend.registry.schemas import LoginRequest, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: User) -> Token:
    token = create_access_token(
        subject=user.id, extra_claims={"email": user.email}
    )
    return Token(access_token=token, expires_in=ACCESS_TOKEN_TTL_MINUTES * 60)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="email already registered")
    user = crud.create_user(
        db,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    logger.info(f"auth: registered user id={user.id} email={user.email}")
    try:
        seed_samples_for_user(db, user)
    except Exception as e:
        logger.warning(f"auth: sample seeding failed for user {user.id}: {e}")
    return UserOut.model_validate(user)


@router.post("/login", response_model=Token)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = crud.get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="account disabled")
    return _issue_token(user)


@router.post("/token", response_model=Token, include_in_schema=False)
def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = crud.get_user_by_email(db, form.username)
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="account disabled")
    return _issue_token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
