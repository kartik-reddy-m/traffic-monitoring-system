import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ViolationRecord(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    violation_type = Column(String(50), nullable=False, index=True)
    vehicle_type = Column(String(30), nullable=False)
    vehicle_id = Column(Integer, nullable=False)
    confidence = Column(Float, default=0.0)
    evidence_path = Column(String(255), nullable=False)
    video_source = Column(String(100), default="Live Stream")
    details = Column(Text, default="")
    status = Column(String(20), default="Logged")

class TrafficLog(Base):
    __tablename__ = "traffic_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    total_vehicles = Column(Integer, default=0)
    active_vehicles = Column(Integer, default=0)
    car_count = Column(Integer, default=0)
    bike_count = Column(Integer, default=0)
    bus_count = Column(Integer, default=0)
    truck_count = Column(Integer, default=0)
    density_level = Column(String(20), default="LOW")
    video_source = Column(String(100), default="")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
