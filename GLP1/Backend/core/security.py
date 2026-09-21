"""
Token verification dependency for GLP-1's protected routes (Task C).
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from core.config import settings

_ALGORITHM = "HS256"
_bearer_scheme = HTTPBearer()


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    token = credentials.credentials
    try:
        claims = jwt.decode(token, settings.shared_secret_key, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if "glp1" not in claims.get("app_access", []):
        raise HTTPException(status_code=403, detail="This account doesn't have access to GLP-1")

    return claims