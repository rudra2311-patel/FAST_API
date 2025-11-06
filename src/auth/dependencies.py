
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi import Request,status
from .utlis import decode_access_token
from fastapi.exceptions import HTTPException


class AccessTokenScheme(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        creds = await super().__call__(request)
        token = creds.credentials 
        token_data = decode_access_token(token)
        if not self.validate_token(token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")
        if  token_data['refresh'] is True:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Refresh token cannot be used here")
        return creds

    def validate_token(self, token: str) -> bool | None:
        token_data = decode_access_token(token)
        if token_data is not  None:
            return True
        else:
            return False