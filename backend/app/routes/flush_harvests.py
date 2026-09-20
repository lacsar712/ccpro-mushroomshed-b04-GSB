from datetime import timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from app.database import SessionLocal
from app.models.flush_harvest import FlushHarvest
from app.models.room import Room
from app.schemas.flush_harvest import (
    FlushHarvestCreateSchema,
    FlushHarvestEndSchema,
    FlushHarvestOutSchema,
)
from app.services.flush_open import count_open, find_open, is_open
from app.utils import validation_error_response

bp = Blueprint("flush_harvests", __name__, url_prefix="/api/flush-harvests")

create_schema = FlushHarvestCreateSchema()
end_schema = FlushHarvestEndSchema()
out_schema = FlushHarvestOutSchema()
out_many = FlushHarvestOutSchema(many=True)


def _as_utc(dt):
    """MySQL DATETIME 不带时区，读回为 naive；统一按 UTC 对齐后再比较。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@bp.get("")
@jwt_required()
def list_flush_harvests():
    db = SessionLocal()
    try:
        room_id = request.args.get("roomId", type=int)
        q = db.query(FlushHarvest)
        if room_id is not None:
            q = q.filter(FlushHarvest.room_id == room_id)
        rows = q.order_by(FlushHarvest.harvested_at.desc()).all()
        # 每条带 open 布尔，统一由 is_open 判定
        return jsonify(out_many.dump(rows))
    finally:
        db.close()


@bp.get("/open-check")
@jwt_required()
def open_check():
    """对账接口：totalOpen 与 byRoom 均来自 count_open，与 stats / 室列表一致。"""
    db = SessionLocal()
    try:
        room_ids = [r.id for r in db.query(Room.id).order_by(Room.id).all()]
        by_room = {str(rid): count_open(db, room_id=rid) for rid in room_ids}
        return jsonify({"totalOpen": count_open(db), "byRoom": by_room})
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_flush_harvest():
    db = SessionLocal()
    try:
        try:
            data = create_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        room = db.query(Room).filter(Room.id == data["room_id"]).first()
        if not room:
            return jsonify({"detail": "出菇室不存在"}), 400
        if room.status != "fruiting":
            return jsonify({"detail": "出菇室非 fruiting 状态，禁止新建采收"}), 409
        existing = find_open(db, room.id)
        if existing is not None:
            return jsonify(
                {
                    "detail": "该出菇室已有进行中的采收，须先结束",
                    "existingHarvestId": existing.id,
                }
            ), 409
        item = FlushHarvest(
            room_id=data["room_id"],
            harvested_at=data["harvested_at"],
            ended_at=None,
            flush_no=data["flush_no"],
            weight_kg=data["weight_kg"],
            grade=data["grade"],
            operator_name=data["operator_name"],
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify(out_schema.dump(item)), 201
    finally:
        db.close()


@bp.post("/<int:harvest_id>/end")
@jwt_required()
def end_flush_harvest(harvest_id: int):
    """称重结束：服务端校验 endedAt > harvestedAt、weightKg > 0，不信客户端脏数据。"""
    db = SessionLocal()
    try:
        item = db.query(FlushHarvest).filter(FlushHarvest.id == harvest_id).first()
        if not item:
            return jsonify({"detail": "采收记录不存在"}), 404
        if not is_open(item):
            return jsonify({"detail": "采收已结束，禁止重复结束"}), 409
        try:
            data = end_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        if _as_utc(data["ended_at"]) <= _as_utc(item.harvested_at):
            return jsonify({"detail": "endedAt 必须晚于 harvestedAt"}), 400
        item.ended_at = data["ended_at"]
        item.weight_kg = data["weight_kg"]
        db.commit()
        db.refresh(item)
        return jsonify(out_schema.dump(item))
    finally:
        db.close()


@bp.delete("/<int:harvest_id>")
@jwt_required()
def delete_flush_harvest(harvest_id: int):
    db = SessionLocal()
    try:
        item = db.query(FlushHarvest).filter(FlushHarvest.id == harvest_id).first()
        if not item:
            return jsonify({"detail": "采收记录不存在"}), 404
        if not is_open(item):
            return jsonify({"detail": "已结束的采收记录禁止删除"}), 409
        db.delete(item)
        db.commit()
        return "", 204
    finally:
        db.close()
