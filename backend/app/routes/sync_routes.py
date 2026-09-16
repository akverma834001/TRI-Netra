import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, SyncQueueItem, ScreeningSession, User
from ..auth import get_current_user

router = APIRouter(prefix="/sync", tags=["Offline-First Synchronization"])

# Global simulated network state
CURRENT_NETWORK_STATE = {
    "mode": "Mode A",  # Mode A (4G/Fiber), Mode B (2G/3G), Mode C (Blackout)
    "bandwidth_kbps": 5000.0,
    "packet_loss_rate": 0.005,
    "latency_ms": 45.0,
    "status": "ONLINE"  # ONLINE, LIMITED, OFFLINE, SYNCING
}

@router.get("/status")
def get_sync_status(db: Session = Depends(get_db)):
    pending_count = db.query(SyncQueueItem).filter(SyncQueueItem.status == "PENDING").count()
    failed_count = db.query(SyncQueueItem).filter(SyncQueueItem.status == "FAILED").count()
    synced_count = db.query(SyncQueueItem).filter(SyncQueueItem.status == "SYNCED").count()
    
    return {
        "network": CURRENT_NETWORK_STATE,
        "sync_metrics": {
            "pending_count": pending_count,
            "failed_count": failed_count,
            "synced_count": synced_count,
            "total_items": pending_count + failed_count + synced_count
        }
    }

@router.get("/queue")
def get_sync_queue(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(SyncQueueItem).order_by(SyncQueueItem.created_at.desc()).limit(limit).all()
    return [
        {
            "id": it.id,
            "entity_type": it.entity_type,
            "entity_id": it.entity_id,
            "status": it.status,
            "retry_count": it.retry_count,
            "error_log": it.error_log,
            "created_at": it.created_at,
            "updated_at": it.updated_at
        }
        for it in items
    ]

@router.post("/trigger")
def trigger_synchronization(db: Session = Depends(get_db)):
    """
    Executes synchronization of pending queue items according to active network conditions.
    If in Mode C (Blackout), fails with simulated network unreachable and increments retries.
    If in Mode A or B, pushes all pending records and marks as SYNCED.
    """
    mode = CURRENT_NETWORK_STATE["mode"]
    pending_items = db.query(SyncQueueItem).filter(SyncQueueItem.status.in_(["PENDING", "FAILED"])).all()
    
    if mode == "Mode C":
        # Blackout simulation: Network failure
        for it in pending_items:
            it.status = "FAILED"
            it.retry_count += 1
            it.error_log = "Network Blackout: Connection timeout (128.0.0.1:443 unreachable). Buffered locally."
            it.updated_at = datetime.utcnow()
        db.commit()
        return {
            "success": False,
            "synced_count": 0,
            "failed_count": len(pending_items),
            "message": "Synchronization failed: Local PHC is in network blackout. Cases remain safely buffered in local SQLite store."
        }
    else:
        # Success (Mode A or Mode B)
        synced_count = 0
        for it in pending_items:
            it.status = "SYNCED"
            it.error_log = None
            it.updated_at = datetime.utcnow()
            synced_count += 1
            
            # Also update parent screening sync status if applicable
            if it.entity_type == "screening":
                sc = db.query(ScreeningSession).filter(ScreeningSession.id == it.entity_id).first()
                if sc:
                    sc.sync_status = "synced"
                    
        db.commit()
        return {
            "success": True,
            "synced_count": synced_count,
            "failed_count": 0,
            "message": f"Successfully synchronized {synced_count} records via {mode} link."
        }

@router.post("/enqueue/{screening_id}")
def enqueue_screening_for_sync(screening_id: str, db: Session = Depends(get_db)):
    """Queues a screening session for offline sync."""
    sc = db.query(ScreeningSession).filter(ScreeningSession.id == screening_id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Screening not found")
        
    queue_item = SyncQueueItem(
        entity_type="screening",
        entity_id=screening_id,
        payload=json.dumps({"screening_id": screening_id, "patient_id": sc.patient_id}),
        status="PENDING"
    )
    db.add(queue_item)
    sc.sync_status = "pending"
    db.commit()
    return {"message": "Enqueued in local sync queue", "queue_id": queue_item.id}
