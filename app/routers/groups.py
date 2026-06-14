import uuid
import random
import string
import math
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/api/v1/groups", tags=["Groups"])

def generate_invite_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@router.post("/create", response_model=schemas.CreateGroupResponse)
async def create_group(
    request: schemas.CreateGroupRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if request.group_type not in ["public", "private"]:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid group_type. Must be public or private."})

    # Validate IDs
    cat_query = select(models.Category).filter(models.Category.id == request.category_id)
    cat_result = await db.execute(cat_query)
    if not cat_result.scalars().first():
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid category_id"})

    lang_query = select(models.Language).filter(models.Language.id == request.language_id)
    lang_result = await db.execute(lang_query)
    if not lang_result.scalars().first():
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid language_id"})

    bv_query = select(models.BibleVersion).filter(models.BibleVersion.id == request.bible_version_id)
    bv_result = await db.execute(bv_query)
    if not bv_result.scalars().first():
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid bible_version_id"})

    group_uuid = f"grp_{uuid.uuid4().hex}"
    invite_code = generate_invite_code()

    # Ensure invite code is unique
    while True:
        check_code = await db.execute(select(models.Group).filter(models.Group.invite_code == invite_code))
        if check_code.scalars().first():
            invite_code = generate_invite_code()
        else:
            break

    new_group = models.Group(
        group_uuid=group_uuid,
        group_name=request.group_name,
        group_description=request.group_description,
        admin_user_id=current_user.id,
        category_id=request.category_id,
        language_id=request.language_id,
        bible_version_id=request.bible_version_id,
        max_members=request.max_members,
        current_members=1,
        group_type=request.group_type,
        invite_code=invite_code,
        status="active",
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)

    # Add creator as first member
    new_member = models.GroupMember(
        member_uuid=f"mem_{uuid.uuid4().hex}",
        group_uuid=new_group.group_uuid,
        user_id=current_user.id,
        role="admin",
        status="active"
    )
    db.add(new_member)
    await db.commit()

    return {
        "success": True,
        "message": "Group created successfully",
        "group_uuid": group_uuid,
        "invite_code": invite_code
    }

@router.post("/invite", response_model=schemas.GroupInviteResponse)
async def invite_users(
    request: schemas.GroupInviteRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    group_query = select(models.Group).filter(models.Group.group_uuid == request.group_uuid)
    group_result = await db.execute(group_query)
    group = group_result.scalars().first()
    if not group:
        return JSONResponse(status_code=400, content={"success": False, "message": "Group not found"})
        
    if group.admin_user_id != current_user.id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Only the group admin can invite users"})

    invited_count = 0
    for target_user_uuid in request.user_ids:
        tu_query = select(models.User).filter(models.User.uuid == target_user_uuid)
        tu_result = await db.execute(tu_query)
        target_user = tu_result.scalars().first()
        
        if not target_user:
            continue
            
        gm_query = select(models.GroupMember).filter(
            models.GroupMember.group_uuid == group.group_uuid,
            models.GroupMember.user_id == target_user.id
        )
        gm_result = await db.execute(gm_query)
        if gm_result.scalars().first():
            return JSONResponse(status_code=409, content={"success": False, "message": "User already exists in group"})

        inv_query = select(models.GroupInvitation).filter(
            models.GroupInvitation.group_uuid == request.group_uuid,
            models.GroupInvitation.receiver_user_id == target_user.id,
            models.GroupInvitation.status == "pending"
        )
        inv_result = await db.execute(inv_query)
        if inv_result.scalars().first():
            return JSONResponse(status_code=409, content={"success": False, "message": "Duplicate invitation"})

        invitation_uuid = f"inv_{uuid.uuid4().hex}"
        new_invitation = models.GroupInvitation(
            invitation_uuid=invitation_uuid,
            group_uuid=request.group_uuid,
            sender_user_id=current_user.id,
            receiver_user_id=target_user.id,
            status="pending"
        )
        db.add(new_invitation)
        invited_count += 1

    await db.commit()

    return {
        "success": True,
        "message": "Invitations sent successfully",
        "total_invites": invited_count
    }

@router.post("/accept-invite", response_model=schemas.AcceptInviteResponse)
async def accept_invite(
    request: schemas.AcceptInviteRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    inv_query = select(models.GroupInvitation).filter(models.GroupInvitation.invitation_uuid == request.invitation_uuid)
    inv_result = await db.execute(inv_query)
    invitation = inv_result.scalars().first()
    
    if not invitation:
        return JSONResponse(status_code=404, content={"success": False, "message": "Invitation not found"})
        
    if invitation.receiver_user_id != current_user.id:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized to accept this invitation"})
        
    if invitation.status != "pending":
        if invitation.status == "expired":
            return JSONResponse(status_code=400, content={"success": False, "message": "Invitation expired"})
        return JSONResponse(status_code=400, content={"success": False, "message": f"Invitation already {invitation.status}"})
        
    group_query = select(models.Group).filter(models.Group.group_uuid == invitation.group_uuid)
    group_result = await db.execute(group_query)
    group = group_result.scalars().first()
    
    if not group:
        return JSONResponse(status_code=404, content={"success": False, "message": "Group not found"})
        
    if group.current_members >= group.max_members:
        return JSONResponse(status_code=409, content={"success": False, "message": "Group is full"})
        
    gm_query = select(models.GroupMember).filter(
        models.GroupMember.group_uuid == group.group_uuid,
        models.GroupMember.user_id == current_user.id
    )
    gm_result = await db.execute(gm_query)
    if gm_result.scalars().first():
        invitation.status = "accepted"
        await db.commit()
        return JSONResponse(status_code=400, content={"success": False, "message": "User already in group"})
        
    new_member = models.GroupMember(
        member_uuid=f"mem_{uuid.uuid4().hex}",
        group_uuid=group.group_uuid,
        user_id=current_user.id,
        role="member",
        status="active"
    )
    db.add(new_member)
    
    invitation.status = "accepted"
    group.current_members += 1
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Invitation accepted successfully",
        "group_uuid": group.group_uuid,
        "group_name": group.group_name
    }

@router.get("/{group_uuid}", response_model=schemas.GroupDetailsResponse)
async def get_group_details(
    group_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = (
        select(models.Group, models.User, models.Category, models.Language, models.BibleVersion)
        .join(models.User, models.Group.admin_user_id == models.User.id)
        .join(models.Category, models.Group.category_id == models.Category.id)
        .join(models.Language, models.Group.language_id == models.Language.id)
        .join(models.BibleVersion, models.Group.bible_version_id == models.BibleVersion.id)
        .filter(models.Group.group_uuid == group_uuid)
    )
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        return JSONResponse(status_code=404, content={"success": False, "message": "Group not found"})
        
    group, admin, category, language, bible_version = row

    return {
        "success": True,
        "data": {
            "group_uuid": group.group_uuid,
            "group_name": group.group_name,
            "group_description": group.group_description,
            "invite_code": group.invite_code,
            "group_type": group.group_type,
            "status": group.status,
            "max_members": group.max_members,
            "current_members": group.current_members,
            "admin": {
                "user_uuid": admin.uuid,
                "full_name": admin.full_name or "",
                "profile_image": admin.profile_image
            },
            "challenge": {
                "category_name": category.name,
                "language": language.name,
                "bible_version": bible_version.short_name,
                "start_date": group.start_date,
                "end_date": group.end_date
            }
        }
    }

@router.get("/{group_uuid}/members", response_model=schemas.GroupMembersResponse)
async def get_group_members(
    group_uuid: str,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    group_query = select(models.Group).filter(models.Group.group_uuid == group_uuid)
    group_result = await db.execute(group_query)
    group = group_result.scalars().first()
    
    if not group:
        return JSONResponse(status_code=404, content={"success": False, "message": "Group not found"})
        
    cu_gm_query = select(models.GroupMember).filter(
        models.GroupMember.group_uuid == group_uuid,
        models.GroupMember.user_id == current_user.id
    )
    cu_gm_result = await db.execute(cu_gm_query)
    if not cu_gm_result.scalars().first():
        return JSONResponse(status_code=401, content={"success": False, "message": "You are not a member of this group"})
        
    count_query = select(func.count()).select_from(models.GroupMember).filter(models.GroupMember.group_uuid == group_uuid)
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    
    query = (
        select(models.GroupMember, models.User, func.coalesce(models.GroupScore.score, 0).label("score"))
        .join(models.User, models.GroupMember.user_id == models.User.id)
        .outerjoin(
            models.GroupScore,
            (models.GroupScore.user_id == models.GroupMember.user_id) &
            (models.GroupScore.group_uuid == group_uuid)
        )
        .filter(models.GroupMember.group_uuid == group_uuid)
        .order_by(func.coalesce(models.GroupScore.score, 0).desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    current_rank = offset + 1
    for member_record, user_record, score in rows:
        data.append({
            "member_uuid": member_record.member_uuid,
            "user_uuid": user_record.uuid,
            "full_name": user_record.full_name or "",
            "profile_image": user_record.profile_image,
            "role": member_record.role,
            "group_rank": current_rank,
            "group_score": score,
            "joined_at": member_record.joined_at
        })
        current_rank += 1
        
    return {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }

@router.get("/{group_uuid}/leaderboard", response_model=schemas.GroupLeaderboardResponse)
async def get_group_leaderboard(
    group_uuid: str,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    group_query = select(models.Group).filter(models.Group.group_uuid == group_uuid)
    group_result = await db.execute(group_query)
    group = group_result.scalars().first()
    
    if not group:
        return JSONResponse(status_code=404, content={"success": False, "message": "Group not found"})
        
    cu_gm_query = select(models.GroupMember).filter(
        models.GroupMember.group_uuid == group_uuid,
        models.GroupMember.user_id == current_user.id
    )
    cu_gm_result = await db.execute(cu_gm_query)
    if not cu_gm_result.scalars().first():
        return JSONResponse(status_code=401, content={"success": False, "message": "You are not a member of this group"})

    count_query = select(func.count()).select_from(models.GroupMember).filter(models.GroupMember.group_uuid == group_uuid)
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    
    query = (
        select(
            models.User,
            func.coalesce(models.GroupScore.score, 0).label("score"),
            func.coalesce(models.GroupScore.correct_answers, 0).label("correct"),
            func.coalesce(models.GroupScore.wrong_answers, 0).label("wrong"),
            func.coalesce(models.GroupScore.accuracy_percentage, 0.0).label("accuracy"),
            func.coalesce(models.GroupScore.points_earned, 0).label("points")
        )
        .select_from(models.GroupMember)
        .join(models.User, models.GroupMember.user_id == models.User.id)
        .outerjoin(
            models.GroupScore,
            (models.GroupScore.user_id == models.GroupMember.user_id) &
            (models.GroupScore.group_uuid == group_uuid)
        )
        .filter(models.GroupMember.group_uuid == group_uuid)
        .order_by(func.coalesce(models.GroupScore.score, 0).desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    current_rank = offset + 1
    for user_record, score, correct, wrong, accuracy, points in rows:
        data.append({
            "rank": current_rank,
            "user_uuid": user_record.uuid,
            "full_name": user_record.full_name or "",
            "profile_image": user_record.profile_image,
            "group_score": score,
            "correct_answers": correct,
            "wrong_answers": wrong,
            "accuracy_percentage": accuracy,
            "points_earned": points
        })
        current_rank += 1
        
    cu_score_query = select(models.GroupScore).filter(
        models.GroupScore.group_uuid == group_uuid,
        models.GroupScore.user_id == current_user.id
    )
    cu_score_result = await db.execute(cu_score_query)
    cu_score = cu_score_result.scalars().first()
    cu_score_value = cu_score.score if cu_score else 0

    higher_scores_query = select(func.count()).select_from(
        select(models.GroupMember)
        .outerjoin(
            models.GroupScore,
            (models.GroupScore.user_id == models.GroupMember.user_id) &
            (models.GroupScore.group_uuid == group_uuid)
        )
        .filter(models.GroupMember.group_uuid == group_uuid)
        .filter(func.coalesce(models.GroupScore.score, 0) > cu_score_value)
        .subquery()
    )
    higher_scores_result = await db.execute(higher_scores_query)
    cu_rank = (higher_scores_result.scalar() or 0) + 1

    current_user_data = {
        "rank": cu_rank,
        "group_score": cu_score_value
    }
        
    return {
        "success": True,
        "data": data,
        "current_user": current_user_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }
