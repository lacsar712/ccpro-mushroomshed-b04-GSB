"""极简幂等结构补齐（项目未引入 Alembic）。

create_all 只能建新表，不会给旧表加列。这里在启动时检查并补上
迭代新增的可空列，保证 B04 之前的持久化库（compose 命名卷）可直接升级。
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_EXPECTED_COLUMNS = {
    "flush_harvests": {
        "ended_at": "ALTER TABLE flush_harvests ADD COLUMN ended_at DATETIME NULL",
    },
}


def ensure_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _EXPECTED_COLUMNS.items():
            if table not in existing_tables:
                continue  # create_all 会按最新模型建表
            present = {col["name"] for col in inspector.get_columns(table)}
            for column, ddl in columns.items():
                if column not in present:
                    conn.execute(text(ddl))
