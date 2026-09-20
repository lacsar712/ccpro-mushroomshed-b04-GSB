# MushroomShed-01 · 菇房出菇台账

食用菌菇房「出菇室环境记录与采收台账」种子项目（非库存 / 电商 / 医院 / 考勤）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · Flask · SQLAlchemy 2 · Marshmallow · Flask-JWT-Extended · passlib(bcrypt) · gunicorn |
| 前端 | SolidJS · Vite · TypeScript · @solidjs/router |
| 数据库 | MySQL 8（协议兼容原 MariaDB 设计） |
| 部署 | docker-compose · 前端 Nginx 反代 `/api` |

## 端口与账号

| 服务 | 端口 |
| --- | --- |
| 前端 | **3800** |
| 后端 API | **8800** |
| MySQL | **3310** |

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | admin（场长） |
| `fruiter` | `123456` | fruiter（出菇员） |

数据库：`mushroomshed` / `mushroomshed`，库名 `mushroomshed`。JWT 密钥环境变量 **`JWT_SECRET`**。

## 一键启动

```bash
cd MushroomShed-01
docker compose up --build
```

启动后访问：

- 前端：http://localhost:3800
- 后端健康检查：http://localhost:8800/api/health

后端 entrypoint 流程：等待 MySQL 就绪 → `create_all` 建表 → 幂等补齐新增可空列（如 `ended_at`）→ seed 初始数据 → 启动 gunicorn。

## 功能模块

1. **Auth**：JWT 登录（OAuth2 表单或 JSON），`/api/auth/login`、`/api/auth/me`，`Authorization: Bearer`
2. **Shed 菇房**：`name`、`location`、`notes`
3. **Room 出菇室**：`shedId`、`roomCode`、`species`、`capacityBags`、`status(fruiting|idle|sanitize)`；同菇房 `roomCode` 唯一
4. **ClimateLog 环境记录**：`roomId`、`recordedAt`、`tempC`、`humidityPct`、`co2Ppm`、`notes`；`humidityPct ∈ [1,100]`，否则 **400**
5. **FlushHarvest 采收潮次**：`roomId`、`harvestedAt`、`flushNo(≥1)`、`weightKg`、`grade(A|B|C)`、`operatorName`、可空 `endedAt`
   - `endedAt` 为空即**进行中（open）**，非空为**已称重结束**；进行中判定统一走 `services/flush_open.py` 的 `is_open` / `count_open`
   - 新建（开潮）：出菇室必须为 `fruiting`，否则 **409**（`room_not_fruiting`）；同室同时最多一条进行中，否则 **409** 并返回 `existingHarvestId`；进行中 `weightKg` 允许为 0；`endedAt` 一律由服务端置空，不接受客户端传入
   - 称重结束：`POST /api/flush-harvests/:id/end`，body `{ weightKg, endedAt }`；`weightKg` 必须 > 0、`endedAt` 必须晚于 `harvestedAt`，否则 **400**；已结束再结束 **409**（`harvest_already_ended`）；无 PUT 接口可绕过
   - 删除：进行中可删；已结束禁止删除（**409**）
   - 列表每条带 `open` 布尔（与 `endedAt` 同源 `is_open`）
   - 对账：`GET /api/flush-harvests/open-check` 返回 `{ totalOpen, byRoom }`
6. **Room 列表**：每行带 `openFlushHarvest` 布尔，来自统一的 `count_open(db, roomId)`
7. **Dashboard**：在原 4 项外增加 `openFlushHarvestCount`；该计数、`open-check.totalOpen`、出菇室列表标记与采收列表汇总全部共用 `count_open`，三边一致

> 前端不自行统计进行中数量，一律使用服务端返回的 `open` / `openFlushHarvest` / `openFlushHarvestCount` / `open-check`。

各实体 API：`GET/POST` 列表与创建、`DELETE` 按 ID 删除；FlushHarvest 另有 `POST /:id/end` 与 `GET /open-check`。

## 前端页面

Login · Dashboard · Sheds · Rooms · ClimateLogs · FlushHarvests（侧边栏布局）

## 本地开发（可选）

```bash
# 数据库（或用 compose 只起 db）
docker compose up -d db

# 后端
cd backend
pip install -r requirements.txt
set DATABASE_URL=mysql+pymysql://mushroomshed:mushroomshed@localhost:3310/mushroomshed
set JWT_SECRET=local-dev-secret
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
gunicorn wsgi:app --bind 0.0.0.0:8800 --reload

# 前端
cd frontend
npm install
npm run dev
```

## 目录结构

```
MushroomShed-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   ├── wsgi.py
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── database.py
│       ├── auth.py
│       ├── seed.py
│       ├── utils.py
│       ├── models/
│       ├── schemas/
│       └── routes/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/
        ├── components/
        └── api/
```
