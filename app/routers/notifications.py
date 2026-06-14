from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import math
from typing import Optional
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

@router.get("", response_model=schemas.NotificationsResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    base_query = select(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_deleted == False
    )
    
    if is_read is not None:
        base_query = base_query.filter(models.Notification.is_read == is_read)
        
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    
    query = base_query.order_by(models.Notification.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    # Calculate unread count (unaffected by is_read filter)
    unread_query = select(func.count()).select_from(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False,
        models.Notification.is_deleted == False
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar() or 0
    
    data = []
    for noti in notifications:
        data.append({
            "notification_uuid": noti.notification_uuid,
            "title": noti.title,
            "message": noti.message,
            "notification_type": noti.notification_type,
            "reference_uuid": noti.reference_uuid,
            "is_read": noti.is_read,
            "created_at": noti.created_at
        })
        
    return {
        "success": True,
        "unread_count": unread_count,
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }

@router.post("/mark-as-read", response_model=schemas.MarkReadResponse)
async def mark_notifications_as_read(
    request: schemas.MarkReadRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    target_uuids = []
    if request.notification_uuids:
        target_uuids.extend(request.notification_uuids)
    if request.notification_uuid:
        target_uuids.append(request.notification_uuid)
        
    if not target_uuids:
        return JSONResponse(status_code=400, content={"success": False, "message": "No notification UUIDs provided"})
        
    query = select(models.Notification).filter(
        models.Notification.notification_uuid.in_(target_uuids),
        models.Notification.user_id == current_user.id,
        models.Notification.is_deleted == False
    )
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    if not notifications:
        return JSONResponse(status_code=404, content={"success": False, "message": "Notification not found"})
        
    for noti in notifications:
        noti.is_read = True
        
    await db.commit()
    
    return {
        "success": True,
        "message": "Notification marked as read"
    }

@router.delete("/{notification_uuid}", response_model=schemas.DeleteNotificationResponse)
async def delete_notification(
    notification_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.Notification).filter(
        models.Notification.notification_uuid == notification_uuid,
        models.Notification.user_id == current_user.id,
        models.Notification.is_deleted == False
    )
    result = await db.execute(query)
    notification = result.scalars().first()
    
    if not notification:
        return JSONResponse(status_code=404, content={"success": False, "message": "Notification not found"})
        
    notification.is_deleted = True
    await db.commit()
    
    return {
        "success": True,
        "message": "Notification deleted successfully"
    }
