from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app import schemas, models, dependencies, database

router = APIRouter(prefix="/api/v1/user", tags=["User Actions"])

@router.post("/languages", response_model=schemas.LanguageSelectionResponse)
async def save_user_languages(
    request: schemas.LanguageSelectionRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Verify that the user_id in the payload matches the authenticated user
    if request.user_id != current_user.uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user's languages")

    # Update user's primary language in the main User table
    current_user.primary_language = request.primary_language
    
    # Clear out any previously saved languages for this user
    await db.execute(delete(models.UserLanguage).where(models.UserLanguage.user_id == current_user.id))
    
    # Insert new language preferences
    for lang_detail in request.languages:
        is_primary = (lang_detail.language == request.primary_language)
        new_lang = models.UserLanguage(
            user_id=current_user.id,
            language_name=lang_detail.language,
            is_primary=is_primary,
            can_read=lang_detail.reading,
            can_write=lang_detail.writing,
            can_speak=lang_detail.speaking
        )
        db.add(new_lang)
        
    await db.commit()
    
    return {"success": True, "message": "Languages saved successfully"}

@router.get("/languages", response_model=schemas.UserLanguagesResponse)
async def get_user_languages(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    result = await db.execute(select(models.UserLanguage).filter(models.UserLanguage.user_id == current_user.id))
    user_languages = result.scalars().all()
    
    languages = [
        {
            "language": lang.language_name,
            "is_primary": lang.is_primary,
            "reading": lang.can_read,
            "writing": lang.can_write,
            "speaking": lang.can_speak
        }
        for lang in user_languages
    ]
    
    return {"success": True, "languages": languages}

@router.post("/expertise", response_model=schemas.ExpertiseResponse)
async def save_user_expertise(
    request: schemas.ExpertiseRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Update user's fields in the main users table (for redundancy/quick access)
    current_user.education = request.education
    current_user.age = request.age
    
    # Manage UserExpertise table
    result = await db.execute(select(models.UserExpertise).filter(models.UserExpertise.user_id == current_user.id))
    expertise = result.scalars().first()
    
    if expertise:
        expertise.preferred_language = request.preferred_language
        expertise.education = request.education
        expertise.age = request.age
    else:
        expertise = models.UserExpertise(
            user_id=current_user.id,
            preferred_language=request.preferred_language,
            education=request.education,
            age=request.age
        )
        db.add(expertise)
        
    # Manage UserBibleVersion table
    # Clear old selected versions
    await db.execute(delete(models.UserBibleVersion).where(models.UserBibleVersion.user_id == current_user.id))
    
    # Add new bible versions
    for version in request.bible_versions:
        new_version = models.UserBibleVersion(
            user_id=current_user.id,
            bible_version=version
        )
        db.add(new_version)
        
    await db.commit()
    
    return {"success": True, "message": "Expertise saved successfully"}

@router.get("/expertise", response_model=schemas.ExpertiseGetResponse)
async def get_user_expertise(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Fetch user expertise
    result = await db.execute(select(models.UserExpertise).filter(models.UserExpertise.user_id == current_user.id))
    expertise = result.scalars().first()
    
    # Fetch user bible versions
    result_versions = await db.execute(select(models.UserBibleVersion).filter(models.UserBibleVersion.user_id == current_user.id))
    bible_versions = result_versions.scalars().all()
    
    versions_list = [v.bible_version for v in bible_versions]
    
    if not expertise:
        return {
            "preferred_language": current_user.primary_language,
            "education": current_user.education,
            "age": current_user.age,
            "bible_versions": versions_list
        }
        
    return {
        "preferred_language": expertise.preferred_language,
        "education": expertise.education,
        "age": expertise.age,
        "bible_versions": versions_list
    }

@router.post("/complete-onboarding", response_model=schemas.OnboardingResponse)
async def complete_onboarding(
    request: schemas.OnboardingRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    current_user.is_onboarding_completed = request.is_onboarding_completed
    await db.commit()
    
    return {"success": True, "message": "Onboarding completed"}
