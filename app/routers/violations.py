import csv
import io
import os
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db, ViolationRecord
from app.schemas import ViolationRecordResponse
from app.config import BASE_DIR

router = APIRouter(prefix="/api/violations", tags=["Violations"])

@router.get("", response_model=List[ViolationRecordResponse])
def get_violations(
    violation_type: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(ViolationRecord)
    
    if violation_type and violation_type != "all":
        query = query.filter(ViolationRecord.violation_type == violation_type)
    
    if vehicle_type and vehicle_type != "all":
        query = query.filter(ViolationRecord.vehicle_type == vehicle_type)

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (ViolationRecord.details.ilike(search_fmt)) |
            (ViolationRecord.video_source.ilike(search_fmt))
        )

    records = query.order_by(ViolationRecord.id.desc()).offset(offset).limit(limit).all()
    return records

@router.get("/export/csv")
def export_violations_csv(db: Session = Depends(get_db)):
    records = db.query(ViolationRecord).order_by(ViolationRecord.id.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp (UTC)", "Violation Type", "Vehicle Type", "Vehicle ID", "Confidence", "Evidence Path", "Video Source", "Details", "Status"])
    
    for r in records:
        writer.writerow([
            r.id,
            r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "",
            r.violation_type,
            r.vehicle_type,
            r.vehicle_id,
            r.confidence,
            r.evidence_path,
            r.video_source,
            r.details,
            r.status
        ])
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=traffic_violations_export.csv"}
    )

@router.delete("/{violation_id}")
def delete_violation(violation_id: int, db: Session = Depends(get_db)):
    record = db.query(ViolationRecord).filter(ViolationRecord.id == violation_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Violation record not found")

    # Attempt to remove evidence file if exists
    if record.evidence_path and record.evidence_path.startswith("/static/evidence/"):
        fname = record.evidence_path.replace("/static/evidence/", "")
        fpath = BASE_DIR / "static" / "evidence" / fname
        if fpath.exists():
            try:
                os.remove(fpath)
            except Exception:
                pass

    db.delete(record)
    db.commit()
    return {"status": "success", "message": f"Violation #{violation_id} deleted"}

@router.post("/clear")
def clear_all_violations(db: Session = Depends(get_db)):
    db.query(ViolationRecord).delete()
    db.commit()
    return {"status": "success", "message": "All violation records cleared"}
