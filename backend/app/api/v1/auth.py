from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta

from app.core.database import get_db
from app.core.db_models import Admin
from app.core.auth import authenticate_admin, create_access_token, get_password_hash, get_current_admin

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str


class AdminCreate(BaseModel):
    email: str
    name: str
    password: str


class AdminResponse(BaseModel):
    id: str
    email: str
    name: str


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    admin = authenticate_admin(db, form_data.username, form_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        data={"sub": admin.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=AdminResponse)
async def register(
    admin_data: AdminCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    admin = Admin(
        email=admin_data.email,
        name=admin_data.name,
        password_hash=get_password_hash(admin_data.password)
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    return AdminResponse(id=admin.id, email=admin.email, name=admin.name)


@router.get("/me", response_model=AdminResponse)
async def get_me(current_admin: Admin = Depends(get_current_admin)):
    return AdminResponse(id=current_admin.id, email=current_admin.email, name=current_admin.name)