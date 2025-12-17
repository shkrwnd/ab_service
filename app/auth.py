"""Bearer token authentication.

This is very simple token checking (not full user auth).
"""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify Bearer token from request.
    Returns the token if valid, raises 401 otherwise.
    """
    token = credentials.credentials
    
    # Check if token is in our allowed list
    if token not in settings.api_tokens:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authentication token"
        )
    
    return token

