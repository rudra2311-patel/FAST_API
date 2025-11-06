from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from src.config import Config
import uuid
import logging 
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOCKEN_EXPIRE = 3600
def generate_password_hash(password: str) -> str:
    hash =  password_context.hash(password)
    return hash

def verify_password(password: str, hash: str) -> bool:
    return password_context.verify(password, hash) 

def create_access_token(user_data: dict, expiry: timedelta = None, refresh: bool = False):
    payload = {

    }
    payload['user'] = user_data
    payload['exp'] = datetime.now() + (expiry if expiry else timedelta(minutes=ACCESS_TOCKEN_EXPIRE))
    payload['jti'] = str(uuid.uuid4())
    payload['refresh'] = refresh
    token = jwt.encode(
        claims=payload,                         
        key=Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM      
   )
    return token
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logging.error("Token expired.")
        return None
    except jwt.JWTError as e:
        logging.error(f"Invalid token: {e}")
        return None
