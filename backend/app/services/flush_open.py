"""采收「进行中」判定与统计的唯一来源。

进行中 = ended_at 为空（未称重结束）。列表 open 标记、Room 列表
openFlushHarvest、Dashboard openFlushHarvestCount、open-check 对账
全部必须调用本模块，禁止各自重写 ended_at 判断。
"""

from typing import Optional

from sqlalchemy import func

from app.models.flush_harvest import FlushHarvest


def is_open(harvest: FlushHarvest) -> bool:
    """单条记录是否进行中。"""
    return harvest.ended_at is None


def count_open(db, room_id: Optional[int] = None) -> int:
    """进行中采收条数；room_id 为空时统计全部出菇室。"""
    q = db.query(func.count(FlushHarvest.id)).filter(FlushHarvest.ended_at.is_(None))
    if room_id is not None:
        q = q.filter(FlushHarvest.room_id == room_id)
    return int(q.scalar() or 0)


def find_open(db, room_id: int) -> Optional[FlushHarvest]:
    """取某出菇室当前进行中的采收（同室同时最多一条）。"""
    return (
        db.query(FlushHarvest)
        .filter(FlushHarvest.room_id == room_id, FlushHarvest.ended_at.is_(None))
        .first()
    )
