from fastapi import APIRouter, Depends, HTTPException, status

from src.db.redis import add_jti_to_blocklist
from .schemas import UserCreateModel, UserModel, UserLoggingModel
from .services import UserService
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from .utlis import create_access_token,decode_access_token,verify_password
from datetime import timedelta, datetime
from fastapi.responses import JSONResponse
from .dependencies import RefreshTokenBearer, AccessTokenBearer
auth_router = APIRouter()
user_service = UserService()  
REFRESH_TOKEN_EXPIRE_DAYS = 2

@auth_router.post("/signup", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def create_user_account(user_data: UserCreateModel, session: AsyncSession = Depends(get_session)):
    email = user_data.email
    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    new_user = await user_service.create_user(user_data, session)
    return new_user  # ✅ Return full user model object


@auth_router.post("/login")
async def login_user(user_data: UserLoggingModel, session: AsyncSession = Depends(get_session)):
    email = user_data.email
    password = user_data.password

    user = await user_service.get_user_by_email(email, session)
    if user is not None :
        is_password_valid = verify_password(password, user.password_hash)
        if is_password_valid:
            access_token = create_access_token(
                user_data = {
                    "user_id": str(user.id),
                    "email": user.email
                }
            )
            refresh_token = create_access_token(
                user_data = {
                    "user_id": str(user.id),
                    "email": user.email
                },
                refresh=True,
                expiry=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "user_id": str(user.id),
                        "email": user.email
                    }   
                }
            )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password"
    )
@auth_router.post("/refresh-token")
async def get_new_access_token(token_details: dict = Depends(RefreshTokenBearer()), session: AsyncSession = Depends(get_session)):
    expiry_timestamp =  token_details['exp']
    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():
        new_access_token = create_access_token(
            user_data={
                "user_id": token_details['user_id'],
                "email": token_details['email']
            }
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "access_token": new_access_token
            }
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired refresh token"
    )

@auth_router.post("/logout")
async def logout_user(token_details: dict = Depends(RefreshTokenBearer())):
    jti = token_details['jti']
    await add_jti_to_blocklist(jti)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Logout successful"
        }
    )


@auth_router.get("/me")
async def get_current_user(
    token_data: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session)
):
    """Get current authenticated user profile"""
    user_id = token_data["user"]["user_id"]
    
    user = await user_service.get_user_by_id(user_id, session)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "user_id": str(user.id),
            "email": user.email,
            "username": user.username if hasattr(user, 'username') and user.username else user.email.split("@")[0],
            "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
        }
    )