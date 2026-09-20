from marshmallow import Schema, fields, validate

from app.services.flush_open import is_open


class FlushHarvestCreateSchema(Schema):
    """新建即「进行中」：endedAt 不接受客户端传入（unknown 字段 400），weightKg 允许为 0。"""

    room_id = fields.Int(required=True, data_key="roomId")
    harvested_at = fields.DateTime(required=True, data_key="harvestedAt")
    flush_no = fields.Int(required=True, data_key="flushNo", validate=validate.Range(min=1))
    weight_kg = fields.Float(
        required=True,
        data_key="weightKg",
        validate=validate.Range(min=0, error="weightKg 不得为负"),
    )
    grade = fields.Str(required=True, validate=validate.OneOf(["A", "B", "C"]))
    operator_name = fields.Str(required=True, data_key="operatorName", validate=validate.Length(min=1, max=64))


class FlushHarvestEndSchema(Schema):
    """结束（称重）服务端校验：weightKg 必须 > 0；endedAt > harvestedAt 在路由内比对。"""

    ended_at = fields.DateTime(required=True, data_key="endedAt")
    weight_kg = fields.Float(
        required=True,
        data_key="weightKg",
        validate=validate.Range(min=0.0001, error="weightKg 须大于 0"),
    )


class FlushHarvestOutSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(data_key="roomId")
    harvested_at = fields.DateTime(data_key="harvestedAt")
    ended_at = fields.DateTime(data_key="endedAt")
    flush_no = fields.Int(data_key="flushNo")
    weight_kg = fields.Float(data_key="weightKg")
    grade = fields.Str()
    operator_name = fields.Str(data_key="operatorName")
    open = fields.Function(lambda obj: is_open(obj), dump_only=True)
