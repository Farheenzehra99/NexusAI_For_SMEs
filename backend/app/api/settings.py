from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models.business import UserSettings, Business
from .dependencies import get_current_business

router = APIRouter()

class SettingsUpdate(BaseModel):
    language: str = None
    email_notifications: bool = None
    proactive_actions: bool = None

@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    settings = db.query(UserSettings).filter(UserSettings.business_id == business.id).first()
    if not settings:
        # Auto-create default settings
        settings = UserSettings(business_id=business.id, language="en", email_notifications=1, proactive_actions=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        "language": settings.language,
        "email_notifications": bool(settings.email_notifications),
        "proactive_actions": bool(settings.proactive_actions)
    }

@router.patch("/settings")
def update_settings(
    update: SettingsUpdate,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business)
):
    settings = db.query(UserSettings).filter(UserSettings.business_id == business.id).first()
    if not settings:
        settings = UserSettings(business_id=business.id, language="en", email_notifications=1, proactive_actions=1)
        db.add(settings)

    if update.language is not None:
        settings.language = update.language
    if update.email_notifications is not None:
        settings.email_notifications = 1 if update.email_notifications else 0
    if update.proactive_actions is not None:
        settings.proactive_actions = 1 if update.proactive_actions else 0
        
    db.commit()
    return {
        "language": settings.language,
        "email_notifications": bool(settings.email_notifications),
        "proactive_actions": bool(settings.proactive_actions)
    }
    return {"success": True}
