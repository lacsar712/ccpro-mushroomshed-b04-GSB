from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.database import SessionLocal
from app.models.climate_log import ClimateLog
from app.models.flush_harvest import FlushHarvest
from app.models.room import Room
from app.models.shed import Shed
from app.schemas.dashboard import DashboardStatsSchema
from app.services.flush_open import count_open

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

stats_schema = DashboardStatsSchema()


@bp.get("/stats")
@jwt_required()
def get_stats():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        shed_total = db.query(func.count(Shed.id)).scalar() or 0
        fruiting_room_count = (
            db.query(func.count(Room.id)).filter(Room.status == "fruiting").scalar() or 0
        )
        climate_last_24h = (
            db.query(func.count(ClimateLog.id))
            .filter(ClimateLog.recorded_at >= now - timedelta(hours=24))
            .scalar()
            or 0
        )
        harvest_kg_last_7d = (
            db.query(func.coalesce(func.sum(FlushHarvest.weight_kg), 0.0))
            .filter(FlushHarvest.harvested_at >= now - timedelta(days=7))
            .scalar()
            or 0.0
        )
        # 进行中计数与 open-check、出菇室列表共用 count_open。
        open_flush_harvest_count = count_open(db)
        payload = {
            "shed_total": shed_total,
            "fruiting_room_count": fruiting_room_count,
            "climate_last_24h": climate_last_24h,
            "harvest_kg_last_7d": float(harvest_kg_last_7d),
            "open_flush_harvest_count": open_flush_harvest_count,
        }
        return jsonify(stats_schema.dump(payload))
    finally:
        db.close()
