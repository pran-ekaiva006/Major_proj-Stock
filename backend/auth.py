import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import hashlib
import hmac
import base64
import json

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_key_that_should_be_in_env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- Simple password hashing using hashlib (no heavy dependencies) ---

def _hash_pw(password: str, salt: bytes = None) -> tuple:
    """Hash a password with a random salt using PBKDF2."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return salt, key


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored hash."""
    try:
        parts = hashed_password.split('$')
        if len(parts) == 3 and parts[0] == 'pbkdf2':
            salt = base64.b64decode(parts[1])
            stored_key = base64.b64decode(parts[2])
            _, computed_key = _hash_pw(plain_password, salt)
            return hmac.compare_digest(stored_key, computed_key)
        # Fallback: try bcrypt format
        try:
            import bcrypt
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except ImportError:
            return False
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hashes a plain password using PBKDF2-SHA256."""
    salt, key = _hash_pw(password)
    return f"pbkdf2${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"


# --- Simple JWT implementation (no heavy dependencies) ---

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64url_decode(s: str) -> bytes:
    s += '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generates a JWT access token using HMAC-SHA256."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": int(expire.timestamp())})

    # Try PyJWT first (fast, lightweight)
    try:
        import jwt
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    except ImportError:
        pass

    # Manual JWT implementation as fallback
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps(to_encode, default=str).encode())
    signature = hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    sig_encoded = _b64url_encode(signature)
    return f"{header}.{payload}.{sig_encoded}"


def _decode_token(token: str) -> dict:
    """Decode and verify a JWT token."""
    # Try PyJWT first
    try:
        import jwt
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ImportError:
        pass

    # Manual decode
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid token")

    header, payload, signature = parts
    expected_sig = hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    actual_sig = _b64url_decode(signature)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid signature")

    data = json.loads(_b64url_decode(payload))

    # Check expiration
    if "exp" in data and data["exp"] < datetime.now(timezone.utc).timestamp():
        raise ValueError("Token expired")

    return data


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Decodes JWT token and returns the username."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = _decode_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    return username
