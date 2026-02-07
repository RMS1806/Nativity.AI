"""
Authentication Dependencies for Nativity.ai API
Handles Clerk JWT verification and user extraction

Uses JWKS (JSON Web Key Set) to verify tokens from Clerk.
"""

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from functools import lru_cache

from config import settings

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)

# Cache for JWKS client to avoid repeated fetches
_jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> Optional[PyJWKClient]:
    """
    Get or create a cached JWKS client for Clerk token verification.
    Returns None if CLERK_ISSUER_URL is not configured.
    """
    global _jwks_client
    
    if not settings.CLERK_ISSUER_URL:
        return None
    
    if _jwks_client is None:
        # Clerk's JWKS endpoint follows the standard OAuth2 pattern
        jwks_url = f"{settings.CLERK_ISSUER_URL}/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
    
    return _jwks_client


def verify_token(token: str) -> dict:
    """
    Verify a Clerk JWT token and return the decoded payload.
    
    Args:
        token: The JWT token string
        
    Returns:
        dict: Decoded token payload containing user claims
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    jwks_client = get_jwks_client()
    
    if jwks_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured. Set CLERK_ISSUER_URL."
        )
    
    try:
        # Get the signing key from JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and verify the token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.CLERK_ISSUER_URL,
            options={
                "verify_aud": False,  # Clerk doesn't always include audience
                "verify_exp": True,
                "verify_iss": True,
            }
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    FastAPI dependency to get the current authenticated user.
    
    Usage in routes:
        @router.post("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            user_id = user["sub"]
            ...
    
    Returns:
        dict: User information including:
            - sub: User ID (Clerk user ID)
            - email: User's email (if available)
            - ... other Clerk claims
    
    Raises:
        HTTPException: 401 if not authenticated
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user ID (Clerk uses 'sub' claim)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    FastAPI dependency for optionally authenticated routes.
    Returns None if not authenticated, user info if authenticated.
    
    Usage in routes:
        @router.get("/public-or-private")
        async def flexible_route(user: Optional[dict] = Depends(get_optional_user)):
            if user:
                # Logged in behavior
            else:
                # Guest behavior
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        return verify_token(token)
    except HTTPException:
        return None
