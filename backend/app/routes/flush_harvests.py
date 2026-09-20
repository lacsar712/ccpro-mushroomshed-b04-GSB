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
    """把无时区时间按 UTC 处理，保证可与带时区时间比较。"""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


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
        # open 字段由 schema 调用统一的 is_open 输出。
        return jsonify(out_many.dump(rows))
    finally:
        db.close()


@bp.get("/open-check")
@jwt_required()
def open_check():
    db = SessionLocal()
    try:
        # 总数与分室计数全部来自 count_open，禁止另写 predicates。
        total_open = count_open(db)
        by_room = {
            room_id: count_open(db, room_id)
            for room_id, in db.query(Room.id).order_by(Room.id).all()
        }
        return jsonify({"totalOpen": total_open, "byRoom": by_room})
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
            return (
                jsonify(
                    {
                        "detail": "出菇室非 fruiting 状态，不能开新潮次",
                        "code": "room_not_fruiting",
                    }
                ),
                409,
            )
        # 同室同时最多一条进行中。
        existing = find_open(db, room.id)
        if existing is not None:
            return (
                jsonify(
                    {
                        "detail": "该出菇室已存在进行中的潮次，请先称重结束",
                        "code": "open_harvest_exists",
                        "existingHarvestId": existing.id,
                    }
                ),
                409,
            )
        # ended_at 一律由服务端置空：进行中判定不接受客户端数据。
        item = FlushHarvest(
            room_id=data["room_id"],
            harvested_at=data["harvested_at"],
            flush_no=data["flush_no"],
            weight_kg=data["weight_kg"],
            grade=data["grade"],
            operator_name=data["operator_name"],
            ended_at=None,
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
    db = SessionLocal()
    try:
        try:
            data = end_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        item = db.query(FlushHarvest).filter(FlushHarvest.id == harvest_id).first()
        if not item:
            return jsonify({"detail": "采收记录不存在"}), 404
        if not is_open(item):
            return (
                jsonify(
                    {
                        "detail": "该采收记录已结束，不能重复结束",
                        "code": "harvest_already_ended",
                    }
                ),
                409,
            )
        if _as_utc(data["ended_at"]) <= _as_utc(item.harvested_at):
            return jsonify({"detail": "endedAt 必须晚于 harvestedAt"}), 400
        item.weight_kg = data["weight_kg"]
        item.ended_at = data["ended_at"]
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
            return (
                jsonify(
                    {
                        "detail": "已称重结束的采收记录禁止删除",
                        "code": "harvest_already_ended",
                    }
                ),
                409,
            )
        db.delete(item)
        db.commit()
        return "", 204
    finally:
        db.close()
