from .models import User
from .schemas import UserCreateModel, UserModel
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from .utlis import generate_password_hash

class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        
        result = await session.exec(statement)
        user = result.first()
        return user 
    
    async def get_user_by_id(self, user_id: str, session: AsyncSession):
        statement = select(User).where(User.id == user_id)
        
        result = await session.exec(statement)
        user = result.first()
        return user 
       
    
    async def user_exists(self, email: str, session: AsyncSession):
        user = await self.get_user_by_email(email, session)
        if user is not None:
            return True
        return False
    async def create_user(self, user_data: UserCreateModel, session: AsyncSession):
        user_data_dict = user_data.model_dump()
        new_user = User(**user_data_dict)
        new_user.password_hash = generate_password_hash(user_data_dict.pop("password"))
        session.add(new_user)
        await session.commit()

        return new_user