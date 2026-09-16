import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db, AuditLog, User
from ..auth import get_current_user

router = APIRouter(prefix="/audit", tags=["Compliance & Audit Trail"])

@router.get("/logs")
def list_audit_logs(
    action: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "role": log.role,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "metadata": json.loads(log.metadata_json) if log.metadata_json else {},
            "created_at": log.created_at
        }
        for log in logs
    ]
