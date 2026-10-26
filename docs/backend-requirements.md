# 车队配件库存管理系统 - 后端开发需求文档

## 一、项目概述

为车队配件库存管理系统开发 RESTful API 后端，支持配件、车辆、仓库、库存、库存件实例、入库、出库、调拨、盘点、维修工单、报表、扫码识别等功能。

- 语言：Python 3.11+
- 框架：FastAPI
- ORM：SQLAlchemy 2.0（async）
- 迁移：Alembic
- 校验：Pydantic v2
- 数据库：MySQL 8.0
- 缓存：Redis（可选，用于 token 黑名单、扫码缓存）
- 鉴权：JWT（python-jose）
- 密码：passlib + bcrypt
- 二维码：qrcode + Pillow
- 条码：python-barcode
- Excel：openpyxl
- 日志：loguru
- 测试：pytest + httpx

## 二、技术栈详细

| 类别 | 选型 | 版本 |
|---|---|---|
| Python | Python | 3.11+ |
| Web 框架 | FastAPI | 0.110+ |
| ASGI | uvicorn | 0.29+ |
| ORM | SQLAlchemy | 2.0+ |
| 异步驱动 | asyncmy | 0.2+ |
| 迁移 | Alembic | 1.13+ |
| 校验 | Pydantic | 2.6+ |
| 配置 | pydantic-settings | 2.2+ |
| JWT | python-jose[cryptography] | 3.3+ |
| 密码 | passlib[bcrypt] | 1.7+ |
| 二维码 | qrcode[pil] | 7.4+ |
| 条码 | python-barcode | 0.15+ |
| Excel | openpyxl | 3.1+ |
| 日志 | loguru | 0.7+ |
| 测试 | pytest、httpx | 最新 |
| 代码规范 | ruff、mypy | 最新 |

## 三、目录结构

```
backend/
├── alembic/                    # 数据库迁移
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py           # 配置
│   │   ├── security.py         # JWT、密码
│   │   ├── deps.py             # 依赖注入
│   │   ├── exceptions.py       # 自定义异常
│   │   ├── response.py         # 统一响应
│   │   └── logging.py          # 日志配置
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # Base 模型
│   │   ├── session.py          # 数据库会话
│   │   └── init_db.py          # 初始化数据
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── base.py             # 审计字段 Mixin
│   │   ├── user.py
│   │   ├── vehicle.py
│   │   ├── part.py
│   │   ├── supplier.py
│   │   ├── warehouse.py
│   │   ├── inventory.py
│   │   ├── inventory_item.py
│   │   ├── inbound.py
│   │   ├── outbound.py
│   │   ├── transfer.py
│   │   ├── stocktake.py
│   │   ├── work_order.py
│   │   ├── stock_alert.py
│   │   └── operation_log.py
│   ├── schemas/                # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── common.py           # 分页、响应
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── vehicle.py
│   │   ├── part.py
│   │   ├── supplier.py
│   │   ├── warehouse.py
│   │   ├── inventory.py
│   │   ├── inventory_item.py
│   │   ├── inbound.py
│   │   ├── outbound.py
│   │   ├── transfer.py
│   │   ├── stocktake.py
│   │   ├── work_order.py
│   │   └── report.py
│   ├── api/                    # 路由
│   │   ├── __init__.py
│   │   ├── router.py           # 汇总路由
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── user.py
│   │       ├── vehicle.py
│   │       ├── part.py
│   │       ├── supplier.py
│   │       ├── warehouse.py
│   │       ├── inventory.py
│   │       ├── inventory_item.py
│   │       ├── inbound.py
│   │       ├── outbound.py
│   │       ├── transfer.py
│   │       ├── stocktake.py
│   │       ├── work_order.py
│   │       ├── report.py
│   │       └── scan.py         # 扫码统一入口
│   ├── services/               # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── part_service.py
│   │   ├── inventory_service.py
│   │   ├── inventory_item_service.py
│   │   ├── inbound_service.py
│   │   ├── outbound_service.py
│   │   ├── transfer_service.py
│   │   ├── stocktake_service.py
│   │   ├── work_order_service.py
│   │   ├── code_generator.py   # 编码生成
│   │   ├── qrcode_service.py   # 二维码生成
│   │   └── report_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── datetime_utils.py
│   │   ├── decimal_utils.py
│   │   └── excel_utils.py
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_part.py
│       ├── test_inbound.py
│       ├── test_outbound.py
│       └── test_scan.py
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 四、配置项 `.env`

```env
# 应用
APP_NAME=FleetPartsSystem
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8080

# 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=fleet_parts
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 文件存储
UPLOAD_DIR=./uploads
QRCODE_DIR=./uploads/qrcode
BARCODE_DIR=./uploads/barcode

# 跨域
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 日志
LOG_LEVEL=INFO
LOG_DIR=./logs
```

## 五、统一响应格式

所有接口返回统一结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

分页响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [],
    "total": 100,
    "page": 1,
    "pageSize": 20
  }
}
```

错误响应：

```json
{
  "code": 400,
  "message": "配件编码已存在",
  "data": null
}
```

业务错误码约定：

| code | 含义 |
|---|---|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 未登录 |
| 403 | 无权限 |
| 404 | 不存在 |
| 409 | 冲突（重复、状态不允许） |
| 500 | 服务器错误 |
| 1001 | 配件编码重复 |
| 1002 | 条码重复 |
| 2001 | 库存不足 |
| 2002 | 库存件不在库 |
| 2003 | 库存件已出库 |
| 2004 | 库存件已被锁定 |
| 3001 | 单据状态不允许操作 |
| 3002 | 单据已审核 |
| 4001 | 扫码内容无法识别 |

## 六、数据库模型（SQLAlchemy）

### 6.1 Base 与审计 Mixin

```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

```python
# app/models/base.py
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

class AuditMixin:
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )
    is_deleted: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

class ReadOnlyMixin:
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
```

### 6.2 模型清单

按 `database-design.md` 定义 25 张表，对应 25 个模型文件。关键模型示例：

```python
# app/models/inventory_item.py
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.base import AuditMixin

class InventoryItem(Base, AuditMixin):
    __tablename__ = "inventory_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    qrcode: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    qrcode_image: Mapped[str | None] = mapped_column(String(255))
    part_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    location_id: Mapped[int | None] = mapped_column(BigInteger)
    batch_no: Mapped[str | None] = mapped_column(String(50), index=True)
    serial_no: Mapped[str | None] = mapped_column(String(100))
    production_date: Mapped[date | None] = mapped_column(Date)
    expire_date: Mapped[date | None] = mapped_column(Date)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    status: Mapped[int] = mapped_column(Integer, default=1, index=True)
    inbound_item_id: Mapped[int | None] = mapped_column(BigInteger)
    outbound_item_id: Mapped[int | None] = mapped_column(BigInteger)
    vehicle_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    work_order_id: Mapped[int | None] = mapped_column(BigInteger)
    in_at: Mapped[datetime | None] = mapped_column(DateTime)
    out_at: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        Index("idx_part_status", "part_id", "status"),
        Index("idx_warehouse_location", "warehouse_id", "location_id"),
    )
```

### 6.3 状态常量

```python
# app/models/enums.py
class InventoryItemStatus:
    IN_STOCK = 1      # 在库
    LOCKED = 2        # 锁定
    OUT = 3           # 已出库
    SCRAPPED = 4      # 已报废
    LOST = 5          # 已盘亏

class OrderStatus:
    DRAFT = 1
    PENDING = 2
    COMPLETED = 3
    CANCELLED = 4

class TransferStatus:
    DRAFT = 1
    PENDING = 2
    OUT_DONE = 3
    IN_DONE = 4
    CANCELLED = 5

class WorkOrderStatus:
    WAITING = 1
    REPAIRING = 2
    FINISHED = 3
    SETTLED = 4
```

## 七、编码生成规则

```python
# app/services/code_generator.py

def generate_item_code(seq: int) -> str:
    """库存件编码：IT + yyyyMMdd + 6位流水"""
    return f"IT{datetime.now():%Y%m%d}{seq:06d}"

def generate_inbound_no(seq: int) -> str:
    return f"IN{datetime.now():%Y%m%d}{seq:06d}"

def generate_outbound_no(seq: int) -> str:
    return f"OUT{datetime.now():%Y%m%d}{seq:06d}"

def generate_transfer_no(seq: int) -> str:
    return f"TR{datetime.now():%Y%m%d}{seq:06d}"

def generate_stocktake_no(seq: int) -> str:
    return f"ST{datetime.now():%Y%m%d}{seq:06d}"

def generate_work_order_no(seq: int) -> str:
    return f"WO{datetime.now():%Y%m%d}{seq:06d}"
```

序列号可用 Redis `INCR` 或数据库序列表实现，要求并发安全。

## 八、二维码生成

```python
# app/services/qrcode_service.py
import qrcode
from pathlib import Path

def generate_qrcode(content: str, save_path: Path) -> str:
    """生成二维码图片，返回相对路径"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path)
    return str(save_path)
```

二维码内容 = `item_code`，直接扫码即可定位 `inventory_item`。

## 九、API 接口清单

### 9.1 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/v1/auth/login | 登录，返回 token |
| POST | /api/v1/auth/logout | 登出 |
| GET | /api/v1/auth/me | 当前用户信息 |

登录请求：

```json
{ "username": "admin", "password": "admin123" }
```

响应：

```json
{
  "code": 200,
  "data": {
    "token": "eyJ...",
    "userInfo": {
      "id": 1,
      "username": "admin",
      "realName": "管理员",
      "role": "admin"
    }
  }
}
```

### 9.2 用户

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/users | 分页列表 |
| POST | /api/v1/users | 新增 |
| PUT | /api/v1/users/{id} | 编辑 |
| DELETE | /api/v1/users/{id} | 逻辑删除 |
| PUT | /api/v1/users/{id}/password | 重置密码 |
| PUT | /api/v1/users/{id}/status | 启用/停用 |

### 9.3 车型与车辆

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/vehicle-models | 车型分页 |
| POST | /api/v1/vehicle-models | 新增车型 |
| PUT | /api/v1/vehicle-models/{id} | 编辑 |
| DELETE | /api/v1/vehicle-models/{id} | 删除 |
| GET | /api/v1/vehicles | 车辆分页 |
| POST | /api/v1/vehicles | 新增车辆 |
| PUT | /api/v1/vehicles/{id} | 编辑 |
| DELETE | /api/v1/vehicles/{id} | 删除 |
| GET | /api/v1/vehicles/{id} | 详情 |

### 9.4 配件

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/parts | 分页列表 |
| POST | /api/v1/parts | 新增 |
| PUT | /api/v1/parts/{id} | 编辑 |
| DELETE | /api/v1/parts/{id} | 逻辑删除 |
| GET | /api/v1/parts/{id} | 详情 |
| GET | /api/v1/parts/{id}/models | 适配车型 |
| POST | /api/v1/parts/{id}/models | 添加适配车型 |
| DELETE | /api/v1/parts/{id}/models/{modelId} | 移除适配 |
| GET | /api/v1/part-categories/tree | 分类树 |
| POST | /api/v1/part-categories | 新增分类 |
| PUT | /api/v1/part-categories/{id} | 编辑分类 |
| DELETE | /api/v1/part-categories/{id} | 删除分类 |

### 9.5 库存

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/inventory | 库存汇总分页 |
| GET | /api/v1/inventory/warning | 低库存预警 |
| GET | /api/v1/inventory-items | 库存件分页 |
| GET | /api/v1/inventory-items/{id} | 库存件详情 |
| GET | /api/v1/inventory-items/{id}/transactions | 库存件流水 |
| PUT | /api/v1/inventory-items/{id} | 编辑库存件资料（仅 admin / keeper） |
| POST | /api/v1/inventory-items/print | 批量获取打印数据 |

编辑库存件说明：

- 可改字段：`warehouseId`、`locationId`（传 `null` 表示改为仓库级存放）、`batchNo`、`serialNo`、`productionDate`、`expireDate`、`unitCost`（≥0）、`remark`；支持 camelCase，未传字段保持不变。
- 锁定字段：`itemCode`、`qrcode`、`quantity`（恒为 1）、`status`，由入库 / 出库 / 调拨 / 盘点单据维护，请求中出现会被忽略。
- 仓库 / 库位变更按「单件调拨」记账：同步更新两侧库存汇总的 `quantity` / `item_count`，并写入 `TRANSFER_OUT` + `TRANSFER_IN` 流水（`ref_type=TRANSFER`）；仅「在库」状态可调整位置。
- 修改 `unitCost` 时按移动加权平均重算对应库存汇总的 `avg_cost`。
- 错误码：`2001 INSUFFICIENT_STOCK`、`2002 ITEM_NOT_IN_STOCK`、`2003 ITEM_ALREADY_OUT`、`2004 ITEM_LOCKED`。

### 9.6 入库

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/inbound-orders | 分页 |
| POST | /api/v1/inbound-orders | 新建 |
| GET | /api/v1/inbound-orders/{id} | 详情 |
| PUT | /api/v1/inbound-orders/{id} | 编辑草稿 |
| POST | /api/v1/inbound-orders/{id}/submit | 提交审核 |
| POST | /api/v1/inbound-orders/{id}/approve | 审核通过 |
| POST | /api/v1/inbound-orders/{id}/cancel | 作废 |
| GET | /api/v1/inbound-orders/{id}/items | 明细 |
| GET | /api/v1/inbound-orders/{id}/print-items | 获取待打印库存件 |

### 9.7 出库

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/outbound-orders | 分页 |
| POST | /api/v1/outbound-orders | 新建 |
| GET | /api/v1/outbound-orders/{id} | 详情 |
| PUT | /api/v1/outbound-orders/{id} | 编辑草稿 |
| POST | /api/v1/outbound-orders/{id}/submit | 提交审核 |
| POST | /api/v1/outbound-orders/{id}/approve | 审核通过 |
| POST | /api/v1/outbound-orders/{id}/cancel | 作废 |

### 9.8 扫码（核心）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/scan/inventory-item?code=xxx | 扫码查询库存件 |
| GET | /api/v1/scan/part?code=xxx | 扫码查询配件（非追踪件） |
| GET | /api/v1/scan/location?code=xxx | 扫码查询库位 |

扫码响应（成功）：

```json
{
  "code": 200,
  "data": {
    "itemId": 50001,
    "itemCode": "IT20261022000001",
    "qrcode": "IT20261022000001",
    "partId": 1001,
    "partCode": "FLT-BOSCH-0986",
    "partName": "机油滤芯",
    "spec": "0986AF1",
    "unit": "个",
    "batchNo": "B20261001",
    "status": 1,
    "statusText": "在库",
    "warehouseId": 1,
    "warehouseName": "主仓",
    "locationId": 3,
    "locationCode": "A-01-03",
    "unitCost": 35.50,
    "inAt": "2026-10-01 10:00:00"
  }
}
```

扫码响应（失败）：

```json
{
  "code": 2003,
  "message": "该件已出库，不能重复出库",
  "data": null
}
```

### 9.9 调拨

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/transfer-orders | 分页 |
| POST | /api/v1/transfer-orders | 新建 |
| GET | /api/v1/transfer-orders/{id} | 详情 |
| POST | /api/v1/transfer-orders/{id}/transfer-out | 确认调出 |
| POST | /api/v1/transfer-orders/{id}/transfer-in | 确认调入 |
| POST | /api/v1/transfer-orders/{id}/cancel | 作废 |

### 9.10 盘点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/stocktake-orders | 分页 |
| POST | /api/v1/stocktake-orders | 新建 |
| GET | /api/v1/stocktake-orders/{id} | 详情 |
| POST | /api/v1/stocktake-orders/{id}/start | 开始盘点 |
| POST | /api/v1/stocktake-orders/{id}/scan | 扫码盘点 |
| PUT | /api/v1/stocktake-orders/{id}/items/{itemId} | 修改实盘数量 |
| POST | /api/v1/stocktake-orders/{id}/finish | 完成盘点 |
| POST | /api/v1/stocktake-orders/{id}/cancel | 作废 |

### 9.11 维修工单

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/work-orders | 分页 |
| POST | /api/v1/work-orders | 新建 |
| GET | /api/v1/work-orders/{id} | 详情 |
| PUT | /api/v1/work-orders/{id} | 编辑 |
| POST | /api/v1/work-orders/{id}/start | 开始维修 |
| POST | /api/v1/work-orders/{id}/finish | 完工 |
| POST | /api/v1/work-orders/{id}/settle | 结算 |
| GET | /api/v1/work-orders/{id}/parts | 领料记录 |

### 9.12 报表

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/v1/reports/inventory | 库存报表 |
| GET | /api/v1/reports/inventory/export | 导出 Excel |
| GET | /api/v1/reports/transaction | 流水报表 |
| GET | /api/v1/reports/vehicle-cost | 单车成本 |
| GET | /api/v1/reports/dashboard | 首页看板数据 |

## 十、核心业务逻辑

### 10.1 入库审核通过（关键）

```python
async def approve_inbound_order(order_id: int, db: AsyncSession, user_id: int):
    order = await get_order_or_404(order_id, db)
    if order.status != OrderStatus.PENDING:
        raise BizException(3001, "单据状态不允许审核")

    for item in order.items:
        part = await get_part(item.part_id, db)

        # 更新库存汇总
        inventory = await get_or_create_inventory(
            item.part_id, order.warehouse_id, item.location_id, db
        )

        if part.track_by_item == 1:
            # 逐件追踪：生成 N 个库存件实例
            for _ in range(int(item.quantity)):
                seq = await next_sequence("inventory_item", db)
                item_code = generate_item_code(seq)
                qr_path = generate_qrcode(
                    item_code,
                    Path(settings.QRCODE_DIR) / f"{item_code}.png"
                )
                inv_item = InventoryItem(
                    item_code=item_code,
                    qrcode=item_code,
                    qrcode_image=qr_path,
                    part_id=item.part_id,
                    warehouse_id=order.warehouse_id,
                    location_id=item.location_id,
                    batch_no=item.batch_no,
                    production_date=item.production_date,
                    expire_date=item.expire_date,
                    unit_cost=item.unit_price,
                    status=InventoryItemStatus.IN_STOCK,
                    inbound_item_id=item.id,
                    in_at=datetime.now(),
                    created_by=user_id,
                )
                db.add(inv_item)
            item.generate_item_qty = int(item.quantity)
            item.generated = 1
            inventory.item_count += int(item.quantity)

        # 更新库存数量和成本
        before_qty = inventory.quantity
        inventory.quantity += item.quantity
        inventory.avg_cost = calc_avg_cost(
            before_qty, inventory.avg_cost, item.quantity, item.unit_price
        )
        inventory.last_in_at = datetime.now()

        # 写流水
        db.add(InventoryTransaction(
            part_id=item.part_id,
            warehouse_id=order.warehouse_id,
            location_id=item.location_id,
            biz_type="IN",
            change_qty=item.quantity,
            before_qty=before_qty,
            after_qty=inventory.quantity,
            unit_cost=item.unit_price,
            ref_type="INBOUND",
            ref_id=order.id,
            ref_no=order.order_no,
            batch_no=item.batch_no,
            scan_code=item.scan_code,
            operator_id=user_id,
            created_by=user_id,
        ))

    order.status = OrderStatus.COMPLETED
    order.audit_user_id = user_id
    order.audit_at = datetime.now()
    order.inbound_at = datetime.now()
    await db.commit()
```

### 10.2 扫码查询库存件

```python
async def scan_inventory_item(code: str, db: AsyncSession):
    # 去空格、去前缀
    code = code.strip()
    if code.startswith("QR:"):
        code = code[3:]

    item = await db.scalar(
        select(InventoryItem).where(
            InventoryItem.qrcode == code,
            InventoryItem.is_deleted == 0,
        )
    )
    if not item:
        raise BizException(4001, "扫码内容无法识别")

    if item.status == InventoryItemStatus.OUT:
        raise BizException(2003, "该件已出库，不能重复出库")
    if item.status == InventoryItemStatus.LOCKED:
        raise BizException(2004, "该件已被锁定")
    if item.status == InventoryItemStatus.SCRAPPED:
        raise BizException(2002, "该件已报废")
    if item.status == InventoryItemStatus.LOST:
        raise BizException(2002, "该件已盘亏")

    # 聚合配件、仓库、库位信息返回
    return await build_scan_vo(item, db)
```

### 10.3 出库审核通过

```python
async def approve_outbound_order(order_id: int, db: AsyncSession, user_id: int):
    order = await get_order_or_404(order_id, db)
    if order.status != OrderStatus.PENDING:
        raise BizException(3001, "单据状态不允许审核")

    for item in order.items:
        part = await get_part(item.part_id, db)

        if part.track_by_item == 1:
            # 单件追踪：校验实例状态并改为已出库
            inv_item = await db.get(InventoryItem, item.inventory_item_id)
            if not inv_item or inv_item.status != InventoryItemStatus.IN_STOCK:
                raise BizException(2002, f"库存件 {inv_item.item_code} 不在库")

            inv_item.status = InventoryItemStatus.OUT
            inv_item.outbound_item_id = item.id
            inv_item.vehicle_id = order.vehicle_id
            inv_item.work_order_id = order.work_order_id
            inv_item.out_at = datetime.now()
            inv_item.updated_by = user_id

            inventory = await get_inventory(
                item.part_id, order.warehouse_id, inv_item.location_id, db
            )
            inventory.item_count -= 1
        else:
            inventory = await get_inventory(
                item.part_id, order.warehouse_id, item.location_id, db
            )

        # 校验并扣减数量
        if inventory.quantity < item.quantity:
            raise BizException(2001, f"配件 {part.part_name} 库存不足")

        before_qty = inventory.quantity
        inventory.quantity -= item.quantity
        inventory.last_out_at = datetime.now()

        # 写流水
        db.add(InventoryTransaction(
            part_id=item.part_id,
            inventory_item_id=item.inventory_item_id,
            warehouse_id=order.warehouse_id,
            location_id=item.location_id,
            biz_type="OUT",
            change_qty=-item.quantity,
            before_qty=before_qty,
            after_qty=inventory.quantity,
            unit_cost=inventory.avg_cost,
            ref_type="OUTBOUND",
            ref_id=order.id,
            ref_no=order.order_no,
            batch_no=item.batch_no,
            scan_code=item.scan_code,
            operator_id=user_id,
            created_by=user_id,
        ))

        # 关联工单领料
        if order.work_order_id:
            db.add(WorkOrderPart(
                work_order_id=order.work_order_id,
                outbound_item_id=item.id,
                part_id=item.part_id,
                quantity=item.quantity,
                cost=item.amount,
                created_by=user_id,
            ))

    order.status = OrderStatus.COMPLETED
    order.audit_user_id = user_id
    order.audit_at = datetime.now()
    order.outbound_at = datetime.now()
    await db.commit()
```

### 10.4 移动加权平均成本

```python
def calc_avg_cost(before_qty, before_avg, in_qty, in_price) -> Decimal:
    total_qty = before_qty + in_qty
    if total_qty == 0:
        return Decimal("0")
    return (before_qty * before_avg + in_qty * in_price) / total_qty
```

### 10.5 并发控制

- 库存扣减使用 `SELECT ... FOR UPDATE` 行锁
- 或使用乐观锁：`inventory` 加 `version` 字段
- 序列号用 Redis `INCR` 或数据库序列表 `FOR UPDATE`

## 十一、鉴权与权限

### 11.1 JWT 流程

1. 登录 → 校验密码 → 签发 token（payload 含 user_id、role、exp）
2. 前端每次请求带 `Authorization: Bearer <token>`
3. 后端依赖注入 `get_current_user` 解析 token
4. 权限校验依赖 `require_role(["admin", "keeper"])`

### 11.2 角色权限

| 角色 | 权限 |
|---|---|
| admin | 全部 |
| keeper | 入库、出库、盘点、调拨、库存查询、扫码 |
| purchaser | 入库、供应商、配件查询 |
| leader | 报表、审批、查询 |
| readonly | 只读 |

### 11.3 依赖注入示例

```python
# app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token 无效")
    user = await db.get(User, payload["sub"])
    if not user or user.status != 1:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已停用")
    return user

def require_role(roles: list[str]):
    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "无权限")
        return user
    return checker
```

## 十二、异常处理

```python
# app/core/exceptions.py
class BizException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

# app/main.py
@app.exception_handler(BizException)
async def biz_exception_handler(request, exc: BizException):
    return JSONResponse(
        status_code=200,
        content={"code": exc.code, "message": exc.message, "data": None},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.exception(exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )
```

## 十三、审计字段自动填充

用 SQLAlchemy 事件或 Service 层统一设置：

```python
# app/core/deps.py
async def get_current_user_id(user: User = Depends(get_current_user)) -> int:
    return user.id

# Service 层新增时
obj = Part(..., created_by=user_id)

# 更新时
obj.updated_by = user_id
```

或用 `before_insert` / `before_update` 事件统一处理：

```python
from sqlalchemy import event

@event.listens_for(Session, "before_flush")
def fill_audit_fields(session, flush_context, instances):
    user_id = session.info.get("current_user_id")
    for obj in session.new:
        if hasattr(obj, "created_by") and not obj.created_by:
            obj.created_by = user_id
    for obj in session.dirty:
        if