from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.config import settings
from app import models, schemas
from app.utils import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/swagger_login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Check if token is blacklisted
    is_blacklisted = await db.execute(select(models.BlacklistedToken).filter(models.BlacklistedToken.token == token))
    if is_blacklisted.scalars().first():
        logger.warning("Token validation failed: Token is blacklisted")
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token validation failed: no username in payload")
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError as e:
        logger.warning(f"Token validation failed: JWT Error - {e}")
        raise credentials_exception
    
    result = await db.execute(
        select(models.User).filter(
            (models.User.username == token_data.username) | 
            (models.User.email == token_data.username)
        )
    )
    user = result.scalars().first()
    if user is None:
        logger.warning(f"User not found for token: {token_data.username}")
        raise credentials_exception
    return user

async def get_current_admin_user(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        logger.warning(f"Unauthorized admin access attempt by user: {current_user.username}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user

async def get_current_admin(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized Admin",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        admin_uuid: str = payload.get("sub")
        if admin_uuid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(models.Admin).filter(models.Admin.admin_uuid == admin_uuid))
    admin = result.scalars().first()
    if admin is None:
        raise credentials_exception
        
    return admin
