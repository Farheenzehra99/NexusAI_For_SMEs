from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.business import Business
from ..core.security import hash_password, verify_password, create_access_token
from ..services.seeder import seed_business_data
from .dependencies import get_current_business

router = APIRouter()


class SignupRequest(BaseModel):
    business_name: str
    owner_name: str
    email: EmailStr
    password: str
    location: str = "Karachi, Pakistan"
    tagline: str = "Premium Retail & Clothing"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):
    business_name: str
    owner_name: str
    location: str
    tagline: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    business: dict


@router.post("/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(Business).filter(Business.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    biz = Business(
        name=req.business_name,
        owner_name=req.owner_name,
        email=req.email,
        password_hash=hash_password(req.password),
        location=req.location,
        tagline=req.tagline,
        currency="PKR",
        established_year=2024,
        total_customers=847,
        health_score=72,
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)

    # Seed the new business with realistic initial SME dataset so agents have full context immediately
    seed_business_data(db, biz)

    token = create_access_token(biz.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "business": {
            "id": biz.id,
            "name": biz.name,
            "owner_name": biz.owner_name,
            "email": biz.email,
            "location": biz.location,
            "tagline": biz.tagline,
        }
    }


@router.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    biz = db.query(Business).filter(Business.email == req.email).first()
    if not biz or not verify_password(req.password, biz.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    token = create_access_token(biz.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "business": {
            "id": biz.id,
            "name": biz.name,
            "owner_name": biz.owner_name,
            "email": biz.email,
            "location": biz.location,
            "tagline": biz.tagline,
        }
    }


@router.get("/auth/me")
def get_me(biz: Business = Depends(get_current_business)):
    return {
        "id": biz.id,
        "name": biz.name,
        "owner_name": biz.owner_name,
        "email": biz.email,
        "location": biz.location,
        "tagline": biz.tagline,
        "established_year": biz.established_year,
        "total_customers": biz.total_customers,
        "health_score": biz.health_score,
    }


@router.put("/auth/profile")
def update_profile(req: ProfileUpdateRequest, biz: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    biz.name = req.business_name
    biz.owner_name = req.owner_name
    biz.location = req.location
    biz.tagline = req.tagline
    db.commit()
    db.refresh(biz)
    return {
        "message": "Profile updated successfully",
        "business": {
            "id": biz.id,
            "name": biz.name,
            "owner_name": biz.owner_name,
            "email": biz.email,
            "location": biz.location,
            "tagline": biz.tagline,
        }
    }
