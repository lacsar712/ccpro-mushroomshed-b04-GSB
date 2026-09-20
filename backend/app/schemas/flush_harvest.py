from marshmallow import Schema, fields, validate

from app.services.flush_open import is_open


class FlushHarvestCreateSchema(Schema):
    room_id = fields.Int(required=True, data_key="roomId")
    harvested_at = fields.DateTime(required=True, data_key="harvestedAt")
    flush_no = fields.Int(required=True, data_key="flushNo", validate=validate.Range(min=1))
    # 进行中潮次开潮时允许重量为 0；称重结束时才要求 > 0。
    weight_kg = fields.Float(
        required=True,
        data_key="weightKg",
        validate=validate.Range(min=0),
    )
    grade = fields.Str(required=True, validate=validate.OneOf(["A", "B", "C"]))
    operator_name = fields.Str(required=True, data_key="operatorName", validate=validate.Length(min=1, max=64))
    # 注意：不接受 endedAt —— 进行中只能由服务端置空，结束只能走 /end。


class FlushHarvestEndSchema(Schema):
    weight_kg = fields.Float(
        required=True,
        data_key="weightKg",
        validate=validate.Range(min=0.0001, error="weightKg 须大于 0"),
    )
    ended_at = fields.DateTime(required=True, data_key="endedAt")


class FlushHarvestOutSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(data_key="roomId")
    harvested_at = fields.DateTime(data_key="harvestedAt")
    flush_no = fields.Int(data_key="flushNo")
    weight_kg = fields.Float(data_key="weightKg")
    grade = fields.Str()
    operator_name = fields.Str(data_key="operatorName")
    ended_at = fields.DateTime(data_key="endedAt", allow_none=True)
    open = fields.Method("get_open")

    def get_open(self, obj) -> bool:
        return is_open(obj)
