"""进行中（open）采收的唯一判定来源。

- is_open: 单条记录是否进行中（ended_at 为空即进行中）。
- count_open: 统计进行中数量，可限定出菇室。

列表 open 标记、出菇室 openFlushHarvest、仪表盘计数、open-check、
新建/结束/删除拦截必须共用本模块，禁止各处自行判 ended_at 或自行计数。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.flush_harvest import FlushHarvest


def is_open(h: FlushHarvest) -> bool:
    """进行中判定：endedAt 为空表示进行中。"""
    return h.ended_at is None


def count_open(db: Session, room_id: Optional[int] = None) -> int:
    """统计进行中潮次数量；room_id 不为空时仅限该出菇室。"""
    q = db.query(FlushHarvest).filter(FlushHarvest.ended_at.is_(None))
    if room_id is not None:
        q = q.filter(FlushHarvest.room_id == room_id)
    return q.count()


def find_open(db: Session, room_id: int) -> Optional[FlushHarvest]:
    """取该室当前进行中的潮次（同室同时最多一条）；无则 None。"""
    return (
        db.query(FlushHarvest)
        .filter(FlushHarvest.room_id == room_id, FlushHarvest.ended_at.is_(None))
        .order_by(FlushHarvest.harvested_at.desc())
        .first()
    )
