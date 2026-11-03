from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db, TrafficLog, ViolationRecord
from typing import Dict, Any, List

router = APIRouter(prefix="/api/statistics", tags=["Statistics"])

@router.get("/summary")
def get_summary_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    total_violations = db.query(ViolationRecord).count()
    violations_by_type_rows = db.query(
        ViolationRecord.violation_type, func.count(ViolationRecord.id)
    ).group_by(ViolationRecord.violation_type).all()
    violations_by_type = {row[0]: row[1] for row in violations_by_type_rows}

    violations_by_vehicle_rows = db.query(
        ViolationRecord.vehicle_type, func.count(ViolationRecord.id)
    ).group_by(ViolationRecord.vehicle_type).all()
    violations_by_vehicle = {row[0]: row[1] for row in violations_by_vehicle_rows}

    # Latest traffic log
    latest_log = db.query(TrafficLog).order_by(TrafficLog.id.desc()).first()

    return {
        "total_violations_recorded": total_violations,
        "violations_by_type": violations_by_type,
        "violations_by_vehicle": violations_by_vehicle,
        "latest_density": latest_log.density_level if latest_log else "LOW",
        "latest_active_count": latest_log.active_vehicles if latest_log else 0
    }

@router.get("/timeline")
def get_traffic_timeline(limit: int = 30, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    logs = db.query(TrafficLog).order_by(TrafficLog.id.desc()).limit(limit).all()
    logs.reverse() # chronological order
    
    timeline = []
    for log in logs:
        timeline.append({
            "timestamp": log.timestamp.strftime("%H:%M:%S") if log.timestamp else "",
            "total": log.total_vehicles,
            "active": log.active_vehicles,
            "cars": log.car_count,
            "bikes": log.bike_count,
            "density": log.density_level
        })
    return timeline
