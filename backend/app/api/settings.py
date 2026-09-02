from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.business import UserSettings, Business

router = APIRouter()

class SettingsUpdate(BaseModel):
    language: str = None
    email_notifications: bool = None
    proactive_actions: bool = None

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    # Assuming business_id=1
    settings = db.query(UserSettings).filter(UserSettings.business_id == 1).first()
    if not settings:
        # Auto-create default settings
        settings = UserSettings(business_id=1, language="en", email_notifications=1, proactive_actions=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        "language": settings.language,
        "email_notifications": bool(settings.email_notifications),
        "proactive_actions": bool(settings.proactive_actions)
    }

@router.patch("/settings")
def update_settings(update: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(UserSettings).filter(UserSettings.business_id == 1).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    if update.language is not None:
        settings.language = update.language
    if update.email_notifications is not None:
        settings.email_notifications = 1 if update.email_notifications else 0
    if update.proactive_actions is not None:
        settings.proactive_actions = 1 if update.proactive_actions else 0
        
    db.commit()
    return {"success": True}
