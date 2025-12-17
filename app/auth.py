
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

# from fastapi import Header
# from fastapi import Depends

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Returns the token if valid, raises 401 otherwise.
    """
    token = credentials.credentials
    
    if token not in settings.api_tokens:
        # return None
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authentication token"
        )
    
    return token

# def verify_token_header(authorization: str = Header(...)):
#     if not authorization.startswith("Bearer "):
#         raise HTTPException(status_code=401, detail="Invalid auth header")
#     return authorization.split(" ", 1)[1]
#
# def verify_token_optional(credentials: HTTPAuthorizationCredentials = Security(security)):
#     return credentials.credentials if credentials else None

