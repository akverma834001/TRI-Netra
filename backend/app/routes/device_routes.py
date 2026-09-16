from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db, DeviceProfile

router = APIRouter(prefix="/devices", tags=["Device Management"])

DEFAULT_DEVICES = [
    {
        "device_id": "DEV-CAM-01",
        "camera_model": "Remidio FOP NM-v3 (Handheld Non-Mydriatic)",
        "connection_type": "USB-3 Direct Stream",
        "calibration_status": "Calibrated (FOV=45 deg)",
        "calibrated_focus_threshold": 110.0,
        "error_count": 2,
        "total_captures": 142
    },
    {
        "device_id": "DEV-CAM-02",
        "camera_model": "Forus 3nethra Classic Fundus Camera",
        "connection_type": "Gigabit Ethernet Direct Link",
        "calibration_status": "Calibrated (FOV=40 deg)",
        "calibrated_focus_threshold": 125.0,
        "error_count": 0,
        "total_captures": 310
    },
    {
        "device_id": "DEV-CAM-03",
        "camera_model": "Topcon TRC-NW400 Robotic Fundus System",
        "connection_type": "DICOM / LAN Auto-Transfer",
        "calibration_status": "Calibrated (FOV=45 deg)",
        "calibrated_focus_threshold": 105.0,
        "error_count": 1,
        "total_captures": 580
    }
]

@router.get("")
def list_devices(db: Session = Depends(get_db)):
    devices = db.query(DeviceProfile).all()
    if not devices:
        for d in DEFAULT_DEVICES:
            dp = DeviceProfile(
                device_id=d["device_id"],
                camera_model=d["camera_model"],
                connection_type=d["connection_type"],
                calibration_status=d["calibration_status"],
                calibrated_focus_threshold=d["calibrated_focus_threshold"],
                error_count=d["error_count"],
                total_captures=d["total_captures"]
            )
            db.add(dp)
        db.commit()
        devices = db.query(DeviceProfile).all()
        
    return [
        {
            "id": dev.id,
            "device_id": dev.device_id,
            "camera_model": dev.camera_model,
            "connection_type": dev.connection_type,
            "calibration_status": dev.calibration_status,
            "calibrated_focus_threshold": dev.calibrated_focus_threshold,
            "last_capture_at": dev.last_capture_at,
            "error_count": dev.error_count,
            "total_captures": dev.total_captures
        }
        for dev in devices
    ]
