from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi import Request, status
from fastapi.exceptions import HTTPException
from src.db.redis import is_jti_blacklisted
from .utlis import decode_access_token


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True, allow_refresh: bool = False):
        super().__init__(auto_error=auto_error)
        self.allow_refresh = allow_refresh  # determines if refresh tokens are allowed

    async def __call__(self, request: Request) -> dict:
        creds: HTTPAuthorizationCredentials = await super().__call__(request)
        token = creds.credentials

        # Decode JWT token
        token_data = decode_access_token(token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired token"
            )

        # Block refresh tokens for protected (non-refresh) routes
        if not self.allow_refresh and token_data["refresh"] is True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Refresh token cannot be used for this endpoint"
            )

        # Check Redis blacklist (revoked tokens)
        if await is_jti_blacklisted(token_data["jti"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token has been revoked. Please login again."
            )

        # Verify type of token in subclass
        self.verify_token(token_data)
        return token_data

    def verify_token(self, token_data):
        raise NotImplementedError("Subclasses must implement verify_token().")


# ✅ Used for all normal authenticated routes
class AccessTokenBearer(TokenBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error, allow_refresh=False)

    def verify_token(self, token_data: dict) -> None:
        if token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access token required, not refresh token"
            )


# ✅ Used only for refresh endpoint
class RefreshTokenBearer(TokenBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error, allow_refresh=True)

    def verify_token(self, token_data: dict) -> None:
        if not token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Refresh token required"
            )
