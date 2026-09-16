from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db, User, AuditLog
from ..schemas import LoginRequest, TokenResponse, UserResponse
from ..auth import hash_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or user.password_hash != hash_password(req.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        
    token = create_access_token({"sub": user.username, "role": user.role, "facility": user.facility})
    
    # Audit log
    audit = AuditLog(
        user_id=str(user.id),
        username=user.username,
        role=user.role,
        action="LOGIN",
        target_type="user",
        target_id=str(user.id),
        metadata_json=f'{{"facility": "{user.facility}"}}'
    )
    db.add(audit)
    db.commit()
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user

@router.post("/switch-role", response_model=TokenResponse)
def switch_role(role: str, db: Session = Depends(get_db)):
    """Convenience endpoint for research and demonstration to effortlessly toggle between the 5 roles."""
    user = db.query(User).filter(User.role == role).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"No user found for role: {role}")
        
    token = create_access_token({"sub": user.username, "role": user.role, "facility": user.facility})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }
