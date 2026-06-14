from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app import schemas, models, auth, database, dependencies
import uuid
from datetime import timedelta
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.get("/me", response_model=schemas.CurrentUserResponse)
async def get_me(current_user: models.User = Depends(dependencies.get_current_user)):
    return {
        "success": True,
        "user": {
            "id": current_user.uuid,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone_number": current_user.phone_number,
            "profile_image": current_user.profile_image or "",
            "primary_language": current_user.primary_language,
            "current_rank": current_user.current_rank,
            "current_level": current_user.current_level,
            "total_points": current_user.total_points,
            "daily_streak": current_user.daily_streak
        }
    }

@router.post("/register", response_model=schemas.RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: schemas.RegisterRequest, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.User).filter(models.User.email == user_data.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user_uuid = f"usr_{uuid.uuid4().hex}"
    password_hash = auth.get_password_hash(user_data.password)
    
    new_user = models.User(
        uuid=user_uuid,
        email=user_data.email,
        username=user_data.email, # set username as email since it's required in older schemas
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        country_code=user_data.country_code,
        password_hash=password_hash
    )
    db.add(new_user)
    await db.commit()
    
    return {
        "success": True,
        "message": "User registered successfully",
        "user_id": user_uuid
    }

@router.post("/login", response_model=schemas.LoginResponse)
async def login(request: schemas.LoginRequest, db: AsyncSession = Depends(database.get_db)):
    if not request.email and not request.phone_number:
        return JSONResponse(status_code=401, content={"success": False, "message": "Invalid credentials"})
        
    user = None
    if request.email:
        result = await db.execute(select(models.User).filter(models.User.email == request.email))
        user = result.scalars().first()
    elif request.phone_number:
        result = await db.execute(select(models.User).filter(models.User.phone_number == request.phone_number))
        user = result.scalars().first()

    if not user:
        return JSONResponse(status_code=401, content={"success": False, "message": "Invalid credentials"})

    if not auth.verify_password(request.password, user.password_hash):
        return JSONResponse(status_code=401, content={"success": False, "message": "Invalid credentials"})
        
    if not user.is_active or user.status != "active":
        return JSONResponse(status_code=401, content={"success": False, "message": "Invalid credentials"})

    # Generate tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.username or user.email}, expires_delta=access_token_expires
    )
    
    # Generate refresh token (longer expiry)
    refresh_token_expires = timedelta(days=7)
    refresh_token = auth.create_access_token(
        data={"sub": user.username or user.email, "type": "refresh"}, expires_delta=refresh_token_expires
    )
    
    # Update last login time
    user.last_login_at = func.now()
    await db.commit()

    return {
        "success": True,
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.uuid,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number
        }
    }

@router.post("/logout", response_model=schemas.LogoutResponse)
async def logout(
    token: str = Depends(dependencies.oauth2_scheme),
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    blacklisted_token = models.BlacklistedToken(token=token)
    db.add(blacklisted_token)
    await db.commit()
    
    return {
        "success": True,
        "message": "Logout successful"
    }

@router.post("/swagger_login", response_model=schemas.Token, include_in_schema=False)
async def swagger_login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(database.get_db)):
    """This endpoint is strictly for Swagger UI Authorize button to function."""
    result = await db.execute(select(models.User).filter(models.User.email == form_data.username))
    user = result.scalars().first()
    if not user:
        result = await db.execute(select(models.User).filter(models.User.username == form_data.username))
        user = result.scalars().first()

    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.username or user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
