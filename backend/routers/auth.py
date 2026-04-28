"""
Authentication Router
======================
User registration, login, Google OAuth, and JWT management.
"""

import os
import logging
from datetime import timedelta

import psycopg
from fastapi import APIRouter, HTTPException, Depends, status

from backend.database import get_db_connection
from backend.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES,
)
from backend.models import (
    UserCreate, UserLogin, GoogleAuthRequest, TokenResponse, UserResponse,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
def register(user: UserCreate, conn: psycopg.Connection = Depends(get_db_connection)):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")
        cur.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Username already taken")
        hashed = get_password_hash(user.password)
        cur.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s) RETURNING id, username, email",
            (user.username, user.email, hashed),
        )
        new_user = cur.fetchone()
    conn.commit()
    uid, uname, uemail = new_user
    token = create_access_token(data={"sub": uname, "user_id": uid}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return TokenResponse(access_token=token, username=uname, email=uemail)


@router.post("/login", response_model=TokenResponse)
def login(creds: UserLogin, conn: psycopg.Connection = Depends(get_db_connection)):
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, email, hashed_password FROM users WHERE email = %s", (creds.email,))
        user = cur.fetchone()
    if not user or not verify_password(creds.password, user[3]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    uid, uname, uemail = user[0], user[1], user[2]
    token = create_access_token(data={"sub": uname, "user_id": uid}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return TokenResponse(access_token=token, username=uname, email=uemail)


@router.post("/google", response_model=TokenResponse)
def google_login(req: GoogleAuthRequest, conn: psycopg.Connection = Depends(get_db_connection)):
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as greq
        cid = os.getenv("GOOGLE_CLIENT_ID")
        if not cid:
            raise HTTPException(status_code=501, detail="Google OAuth not configured")
        idinfo = id_token.verify_oauth2_token(req.token, greq.Request(), cid)
        gid, email, name = idinfo["sub"], idinfo.get("email", ""), idinfo.get("name", "user")
    except ImportError:
        raise HTTPException(status_code=501, detail="google-auth not installed")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    with conn.cursor() as cur:
        cur.execute("SELECT id, username, email FROM users WHERE google_id = %s", (gid,))
        user = cur.fetchone()
        if not user:
            cur.execute("SELECT id, username, email FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            if user:
                cur.execute("UPDATE users SET google_id = %s WHERE email = %s", (gid, email))
            else:
                uname = name.lower().replace(" ", "_")[:50]
                cur.execute("SELECT id FROM users WHERE username = %s", (uname,))
                if cur.fetchone():
                    uname = f"{uname}_{gid[:6]}"
                cur.execute(
                    "INSERT INTO users (username, email, hashed_password, google_id) VALUES (%s,%s,%s,%s) RETURNING id, username, email",
                    (uname, email, "GOOGLE_OAUTH", gid),
                )
                user = cur.fetchone()
    conn.commit()
    uid, uname, uemail = user
    token = create_access_token(data={"sub": uname, "user_id": uid}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return TokenResponse(access_token=token, username=uname, email=uemail)


@router.get("/me")
def get_me(current_user: str = Depends(get_current_user), conn: psycopg.Connection = Depends(get_db_connection)):
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, email FROM users WHERE username = %s", (current_user,))
        user = cur.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(id=user[0], username=user[1], email=user[2])
