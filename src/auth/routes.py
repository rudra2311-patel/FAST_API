from fastapi import APIRouter, Depends, HTTPException, status
from .schemas import UserCreateModel, UserModel, UserLoggingModel
from .services import UserService
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from .utlis import create_access_token,decode_access_token,verify_password
from datetime import timedelta
from fastapi.responses import JSONResponse
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
