import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from sse_starlette.sse import EventSourceResponse

from ..database import get_db
from ..models.business import Notification, Business
from .dependencies import get_current_business

router = APIRouter()

# Event queue for live notifications
clients = set()

def notify_clients(notification: Notification):
    for q in clients:
        q.put_nowait({
            "id": notification.id,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat()
        })

@router.get("/notifications")
def get_notifications(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    notifications = (
        db.query(Notification)
        .filter(Notification.business_id == business.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return [{
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "is_read": bool(n.is_read),
        "created_at": n.created_at.isoformat()
    } for n in notifications]

@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.business_id == 1).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = 1
    db.commit()
    return {"success": True}

@router.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.business_id == 1).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notification)
    db.commit()
    return {"success": True}

@router.get("/notifications/stream")
async def message_stream(request: Request):
    q = asyncio.Queue()
    clients.add(q)
    
    async def event_generator():
        try:
            while True:
                # Disconnect if client leaves
                if await request.is_disconnected():
                    break
                
                # Wait for new notification
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield {
                        "event": "notification",
                        "data": str(data)
                    }
                except asyncio.TimeoutError:
                    # Keep-alive
                    yield {
                        "event": "ping",
                        "data": "ping"
                    }
        finally:
            clients.remove(q)

    return EventSourceResponse(event_generator())
