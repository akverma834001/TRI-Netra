import hmac
import hashlib
import base64
import json
import time
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db, User

security = HTTPBearer(auto_error=False)

# Seed credentials for 5 key roles
DEMO_USERS = [
    {
        "username": "operator_rampur",
        "password": "password123",
        "role": "phc_operator",
        "full_name": "Sunita Devi (PHC Operator)",
        "facility": "PHC Rampur (Block A)",
        "language": "hi"
    },
    {
        "username": "dr_sharma",
        "password": "password123",
        "role": "ophthalmologist",
        "full_name": "Dr. A. Sharma, MS (Ophthalmology)",
        "facility": "District Hospital Tele-Retina Center",
        "language": "en"
    },
    {
        "username": "admin_district",
        "password": "password123",
        "role": "district_admin",
        "full_name": "Rajesh Kumar (District Program Officer)",
        "facility": "District Health Mission Office",
        "language": "en"
    },
    {
        "username": "ml_researcher",
        "password": "password123",
        "role": "ml_admin",
        "full_name": "Priya Verma, PhD (Lead AI Scientist)",
        "facility": "AI Medical Research Core",
        "language": "en"
    },
    {
        "username": "sysadmin",
        "password": "password123",
        "role": "sysadmin",
        "full_name": "V. K. Meena (System & Edge Administrator)",
        "facility": "Central Telehealth IT Infrastructure",
        "language": "en"
    }
]

def hash_password(password: str) -> str:
    """Deterministic salted SHA-256 for prototype."""
    salt = "trinetra-salt-2026"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def create_access_token(data: Dict[str, Any]) -> str:
    """Creates a signed HMAC-SHA256 web token."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = data.copy()
    payload["exp"] = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        f"{header}.{payload_str}".encode(),
        hashlib.sha256
    ).digest()
    sig_str = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header}.{payload_str}.{sig_str}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_str, payload_str, sig_str = parts
        
        # Verify signature
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(),
            f"{header_str}.{payload_str}".encode(),
            hashlib.sha256
        ).digest()
        expected_sig_str = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        
        if not hmac.compare_digest(sig_str, expected_sig_str):
            return None
            
        # Decode payload
        padding = "=" * (4 - len(payload_str) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_str + padding)
        payload = json.loads(payload_bytes.decode())
        
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def seed_users(db: Session):
    for u in DEMO_USERS:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if not existing:
            new_user = User(
                username=u["username"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
                full_name=u["full_name"],
                facility=u["facility"],
                language=u["language"]
            )
            db.add(new_user)
    db.commit()

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        # Fallback to default operator for seamless exploration if no token is passed
        default_user = db.query(User).filter(User.username == "operator_rampur").first()
        if default_user:
            return default_user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")
        
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
