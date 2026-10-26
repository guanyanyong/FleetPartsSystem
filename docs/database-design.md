# 车队配件库存管理系统 - 数据库设计文档

## 一、系统概述

车队配件库存管理系统，支持多仓库、多车型、配件单件追踪、扫码出入库、维修工单领料、盘点调拨等功能。

- 数据库：MySQL 8.0
- 字符集：utf8mb4
- 排序规则：utf8mb4_general_ci
- 表数量：25 张

## 二、命名规范

- 表名：小写下划线，如 `inventory_item`
- 字段名：小写下划线，如 `created_at`
- 主键：`id` BIGINT AUTO_INCREMENT
- 外键：`xxx_id` BIGINT
- 时间：DATETIME
- 金额：DECIMAL(14,2)
- 数量：DECIMAL(12,2)
- 单价/成本：DECIMAL(12,4)
- 逻辑删除：`is_deleted` TINYINT，0正常 1删除
- 业务状态：`status` TINYINT

## 三、审计字段规范

除 `inventory_transaction` 和 `operation_log` 两张只读表外，所有表统一包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| created_by | BIGINT | 创建人ID |
| created_at | DATETIME | 创建时间，默认 CURRENT_TIMESTAMP |
| updated_by | BIGINT | 更新人ID |
| updated_at | DATETIME | 更新时间，ON UPDATE CURRENT_TIMESTAMP |
| is_deleted | TINYINT | 0正常 1删除，默认 0 |

`inventory_transaction` 和 `operation_log` 只保留 `created_by`、`created_at`。

## 四、表结构详细设计

### 1. 用户表 `sys_user`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | 主键 |
| username | VARCHAR(50) | 否 | | 登录名，唯一 |
| password_hash | VARCHAR(255) | 否 | | 密码哈希 |
| real_name | VARCHAR(50) | 是 | NULL | 姓名 |
| phone | VARCHAR(20) | 是 | NULL | 电话 |
| role | VARCHAR(20) | 否 | 'readonly' | 角色：admin/keeper/purchaser/leader/readonly |
| default_warehouse_id | BIGINT | 是 | NULL | 默认仓库ID |
| status | TINYINT | 否 | 1 | 1启用 0停用 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | ON UPDATE CURRENT_TIMESTAMP |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_username(username)`

---

### 2. 车型表 `vehicle_model`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| brand | VARCHAR(50) | 否 | | 品牌 |
| model_name | VARCHAR(100) | 否 | | 型号 |
| tonnage | VARCHAR(20) | 是 | NULL | 吨位/座位 |
| remark | VARCHAR(255) | 是 | NULL | |
| status | TINYINT | 否 | 1 | 1启用 0停用 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

---

### 3. 车辆表 `vehicle`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| plate_no | VARCHAR(20) | 否 | | 车牌号，唯一 |
| model_id | BIGINT | 是 | NULL | 车型ID |
| vin | VARCHAR(50) | 是 | NULL | 车架号 |
| engine_no | VARCHAR(50) | 是 | NULL | 发动机号 |
| purchase_date | DATE | 是 | NULL | 购置日期 |
| department | VARCHAR(50) | 是 | NULL | 所属车队/部门 |
| status | TINYINT | 否 | 1 | 1在用 2维修 3停用 4报废 |
| mileage | INT | 是 | 0 | 当前里程 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_plate_no(plate_no)`、`idx_model(model_id)`

---

### 4. 配件分类表 `part_category`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| name | VARCHAR(50) | 否 | | 分类名 |
| parent_id | BIGINT | 是 | NULL | 父分类ID |
| sort | INT | 是 | 0 | 排序 |
| status | TINYINT | 否 | 1 | 1启用 0停用 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

---

### 5. 配件表 `part`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| part_code | VARCHAR(50) | 否 | | 配件业务编码，唯一 |
| part_name | VARCHAR(100) | 否 | | 配件名称 |
| category_id | BIGINT | 是 | NULL | 分类ID |
| spec | VARCHAR(100) | 是 | NULL | 规格型号 |
| brand | VARCHAR(50) | 是 | NULL | 品牌 |
| unit | VARCHAR(20) | 否 | '个' | 基本单位 |
| is_general | TINYINT | 否 | 0 | 是否通用件 |
| safety_stock | DECIMAL(12,2) | 是 | 0 | 安全库存 |
| max_stock | DECIMAL(12,2) | 是 | 0 | 最高库存 |
| shelf_life_days | INT | 是 | 0 | 保质期天数，0为无 |
| track_by_item | TINYINT | 否 | 0 | 是否按件追踪，1是则入库逐件生成二维码 |
| scan_enabled | TINYINT | 否 | 1 | 是否允许扫码出库 |
| remark | VARCHAR(255) | 是 | NULL | |
| status | TINYINT | 否 | 1 | 1启用 0停用 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_part_code(part_code)`、`idx_category(category_id)`、`idx_track(track_by_item)`

---

### 6. 配件车型适配表 `part_vehicle_model`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| part_id | BIGINT | 否 | | 配件ID |
| model_id | BIGINT | 否 | | 车型ID |
| remark | VARCHAR(100) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_part_model(part_id, model_id)`

---

### 7. 配件单位换算表 `part_unit_conversion`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| part_id | BIGINT | 否 | | 配件ID |
| from_unit | VARCHAR(20) | 否 | | 源单位 |
| to_unit | VARCHAR(20) | 否 | | 目标单位 |
| rate | DECIMAL(12,4) | 否 | | 换算率 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`idx_part(part_id)`

---

### 8. 供应商表 `supplier`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| name | VARCHAR(100) | 否 | | 供应商名称 |
| contact | VARCHAR(50) | 是 | NULL | 联系人 |
| phone | VARCHAR(20) | 是 | NULL | 电话 |
| address | VARCHAR(255) | 是 | NULL | 地址 |
| main_category | VARCHAR(100) | 是 | NULL | 主营品类 |
| payment_term | VARCHAR(50) | 是 | NULL | 账期 |
| status | TINYINT | 否 | 1 | 1合作 0停用 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

---

### 9. 仓库表 `warehouse`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| name | VARCHAR(50) | 否 | | 仓库名 |
| address | VARCHAR(255) | 是 | NULL | 地址 |
| keeper_id | BIGINT | 是 | NULL | 负责人ID |
| status | TINYINT | 否 | 1 | 1启用 0停用 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

---

### 10. 库位表 `warehouse_location`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| warehouse_id | BIGINT | 否 | | 仓库ID |
| location_code | VARCHAR(50) | 否 | | 库位编码 |
| location_qrcode | VARCHAR(255) | 是 | NULL | 库位二维码内容 |
| remark | VARCHAR(100) | 是 | NULL | |
| status | TINYINT | 否 | 1 | 1启用 0停用 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_warehouse_location(warehouse_id, location_code)`

---

### 11. 库存表 `inventory`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| part_id | BIGINT | 否 | | 配件ID |
| warehouse_id | BIGINT | 否 | | 仓库ID |
| location_id | BIGINT | 是 | NULL | 库位ID |
| quantity | DECIMAL(12,2) | 否 | 0 | 当前数量（汇总） |
| item_count | INT | 否 | 0 | 在库实例数 |
| locked_qty | DECIMAL(12,2) | 否 | 0 | 锁定数量 |
| avg_cost | DECIMAL(12,4) | 否 | 0 | 移动加权平均成本 |
| last_in_at | DATETIME | 是 | NULL | 最后入库时间 |
| last_out_at | DATETIME | 是 | NULL | 最后出库时间 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_part_warehouse_location(part_id, warehouse_id, location_id)`

> 注意：MySQL 唯一索引对 `NULL` 不去重，`location_id IS NULL`（仓库级库存）时
> 该索引无法阻止重复行。审核入库时按 `part_id` 升序对 `part` 行加 `FOR UPDATE`
> 锁，把「查询 + 创建库存行」串行化；`uk_item_code` 冲突由服务层回滚重试兜底。

---

### 12. 库存件实例表 `inventory_item`（核心新增表）

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| item_code | VARCHAR(50) | 否 | | 库存件唯一编码，唯一 |
| qrcode | VARCHAR(255) | 否 | | 二维码内容，唯一 |
| qrcode_image | VARCHAR(255) | 是 | NULL | 二维码图片路径 |
| part_id | BIGINT | 否 | | 所属配件ID |
| warehouse_id | BIGINT | 否 | | 当前仓库ID |
| location_id | BIGINT | 是 | NULL | 当前库位ID |
| batch_no | VARCHAR(50) | 是 | NULL | 批次号 |
| serial_no | VARCHAR(100) | 是 | NULL | 序列号/出厂编号 |
| production_date | DATE | 是 | NULL | 生产日期 |
| expire_date | DATE | 是 | NULL | 到期日期 |
| unit_cost | DECIMAL(12,4) | 否 | 0 | 该件入库成本 |
| status | TINYINT | 否 | 1 | 1在库 2锁定 3已出库 4已报废 5已盘亏 |
| inbound_item_id | BIGINT | 是 | NULL | 来源入库明细ID |
| outbound_item_id | BIGINT | 是 | NULL | 出库明细ID |
| vehicle_id | BIGINT | 是 | NULL | 装到哪台车 |
| work_order_id | BIGINT | 是 | NULL | 关联维修工单 |
| in_at | DATETIME | 是 | NULL | 入库时间 |
| out_at | DATETIME | 是 | NULL | 出库时间 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：
- `uk_item_code(item_code)`
- `uk_qrcode(qrcode)`
- `idx_part_status(part_id, status)`
- `idx_warehouse_location(warehouse_id, location_id)`
- `idx_vehicle(vehicle_id)`
- `idx_batch(batch_no)`

---

### 13. 库存流水表 `inventory_transaction`（只读）

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| part_id | BIGINT | 否 | | 配件ID |
| inventory_item_id | BIGINT | 是 | NULL | 库存件实例ID |
| warehouse_id | BIGINT | 否 | | 仓库ID |
| location_id | BIGINT | 是 | NULL | 库位ID |
| biz_type | VARCHAR(20) | 否 | | IN/OUT/TRANSFER_IN/TRANSFER_OUT/ADJUST_IN/ADJUST_OUT |
| change_qty | DECIMAL(12,2) | 否 | | 变动数量 |
| before_qty | DECIMAL(12,2) | 否 | | 变动前数量 |
| after_qty | DECIMAL(12,2) | 否 | | 变动后数量 |
| unit_cost | DECIMAL(12,4) | 是 | NULL | 单位成本 |
| ref_type | VARCHAR(20) | 否 | | INBOUND/OUTBOUND/TRANSFER/STOCKTAKE |
| ref_id | BIGINT | 是 | NULL | 关联单据ID |
| ref_no | VARCHAR(50) | 是 | NULL | 关联单号 |
| batch_no | VARCHAR(50) | 是 | NULL | 批次号 |
| scan_code | VARCHAR(100) | 是 | NULL | 扫码原始编码 |
| operator_id | BIGINT | 是 | NULL | 操作人ID |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |

索引：`idx_part_warehouse_time(part_id, warehouse_id, created_at)`、`idx_ref(ref_type, ref_id)`、`idx_item(inventory_item_id)`

---

### 14. 入库单主表 `inbound_order`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_no | VARCHAR(50) | 否 | | 入库单号，唯一 |
| supplier_id | BIGINT | 是 | NULL | 供应商ID |
| warehouse_id | BIGINT | 否 | | 入库仓库ID |
| inbound_type | VARCHAR(20) | 否 | 'PURCHASE' | PURCHASE/RETURN/TRANSFER/ADJUST |
| total_amount | DECIMAL(14,2) | 是 | 0 | 总金额 |
| status | TINYINT | 否 | 1 | 1草稿 2待审 3已入库 4作废 |
| operator_id | BIGINT | 是 | NULL | 经办人ID |
| audit_user_id | BIGINT | 是 | NULL | 审核人ID |
| audit_at | DATETIME | 是 | NULL | 审核时间 |
| inbound_at | DATETIME | 是 | NULL | 入库时间 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_order_no(order_no)`、`idx_status(status)`

---

### 15. 入库单明细表 `inbound_order_item`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_id | BIGINT | 否 | | 入库单ID |
| part_id | BIGINT | 否 | | 配件ID |
| quantity | DECIMAL(12,2) | 否 | | 数量 |
| unit | VARCHAR(20) | 是 | NULL | 单位 |
| unit_price | DECIMAL(12,4) | 否 | 0 | 单价 |
| amount | DECIMAL(14,2) | 是 | 0 | 金额 |
| batch_no | VARCHAR(50) | 是 | NULL | 批次号 |
| production_date | DATE | 是 | NULL | 生产日期 |
| expire_date | DATE | 是 | NULL | 到期日期 |
| location_id | BIGINT | 是 | NULL | 库位ID |
| track_by_item | TINYINT | 否 | 0 | 是否逐件追踪 |
| generate_item_qty | INT | 是 | 0 | 本次生成实例数量 |
| generated | TINYINT | 否 | 0 | 是否已生成实例 |
| scan_code | VARCHAR(100) | 是 | NULL | 扫码原始编码 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`idx_order(order_id)`、`idx_part(part_id)`

---

### 16. 出库单主表 `outbound_order`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_no | VARCHAR(50) | 否 | | 出库单号，唯一 |
| warehouse_id | BIGINT | 否 | | 出库仓库ID |
| outbound_type | VARCHAR(20) | 否 | 'REPAIR' | REPAIR/SALE/RETURN/TRANSFER/SCRAP |
| vehicle_id | BIGINT | 是 | NULL | 关联车辆ID |
| work_order_id | BIGINT | 是 | NULL | 关联维修工单ID |
| receiver_id | BIGINT | 是 | NULL | 领用人ID |
| total_amount | DECIMAL(14,2) | 是 | 0 | 总金额 |
| status | TINYINT | 否 | 1 | 1草稿 2待审 3已出库 4作废 |
| scan_mode | TINYINT | 否 | 0 | 是否扫码模式 |
| scanner_id | BIGINT | 是 | NULL | 扫码操作人ID |
| operator_id | BIGINT | 是 | NULL | 经办人ID |
| audit_user_id | BIGINT | 是 | NULL | 审核人ID |
| audit_at | DATETIME | 是 | NULL | 审核时间 |
| outbound_at | DATETIME | 是 | NULL | 出库时间 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_order_no(order_no)`、`idx_status(status)`、`idx_vehicle(vehicle_id)`

---

### 17. 出库单明细表 `outbound_order_item`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_id | BIGINT | 否 | | 出库单ID |
| part_id | BIGINT | 否 | | 配件ID |
| inventory_item_id | BIGINT | 是 | NULL | 库存件实例ID |
| quantity | DECIMAL(12,2) | 否 | | 数量 |
| unit | VARCHAR(20) | 是 | NULL | 单位 |
| unit_cost | DECIMAL(12,4) | 是 | 0 | 单位成本 |
| amount | DECIMAL(14,2) | 是 | 0 | 金额 |
| batch_no | VARCHAR(50) | 是 | NULL | 批次号 |
| location_id | BIGINT | 是 | NULL | 库位ID |
| scan_code | VARCHAR(100) | 是 | NULL | 扫码原始编码 |
| scan_type | VARCHAR(20) | 是 | NULL | BARCODE/QRCODE/MANUAL |
| scan_at | DATETIME | 是 | NULL | 扫码时间 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`idx_order(order_id)`、`idx_part(part_id)`、`idx_inventory_item(inventory_item_id)`、`idx_scan_code(scan_code)`

---

### 18. 调拨单主表 `transfer_order`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_no | VARCHAR(50) | 否 | | 调拨单号，唯一 |
| from_warehouse_id | BIGINT | 否 | | 调出仓库ID |
| to_warehouse_id | BIGINT | 否 | | 调入仓库ID |
| status | TINYINT | 否 | 1 | 1草稿 2待审 3已调出 4已调入 5作废 |
| operator_id | BIGINT | 是 | NULL | 经办人ID |
| audit_user_id | BIGINT | 是 | NULL | 审核人ID |
| transfer_at | DATETIME | 是 | NULL | 调拨时间 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_order_no(order_no)`

---

### 19. 调拨单明细表 `transfer_order_item`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_id | BIGINT | 否 | | 调拨单ID |
| part_id | BIGINT | 否 | | 配件ID |
| inventory_item_id | BIGINT | 是 | NULL | 库存件实例ID |
| quantity | DECIMAL(12,2) | 否 | | 数量 |
| from_location_id | BIGINT | 是 | NULL | 调出库位ID |
| to_location_id | BIGINT | 是 | NULL | 调入库位ID |
| batch_no | VARCHAR(50) | 是 | NULL | 批次号 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`idx_order(order_id)`、`idx_part(part_id)`

---

### 20. 盘点单主表 `stocktake_order`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_no | VARCHAR(50) | 否 | | 盘点单号，唯一 |
| warehouse_id | BIGINT | 否 | | 盘点仓库ID |
| status | TINYINT | 否 | 1 | 1草稿 2盘点中 3已完成 4作废 |
| operator_id | BIGINT | 是 | NULL | 盘点人ID |
| audit_user_id | BIGINT | 是 | NULL | 审核人ID |
| stocktake_at | DATETIME | 是 | NULL | 盘点时间 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_order_no(order_no)`

---

### 21. 盘点单明细表 `stocktake_order_item`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_id | BIGINT | 否 | | 盘点单ID |
| part_id | BIGINT | 否 | | 配件ID |
| inventory_item_id | BIGINT | 是 | NULL | 库存件实例ID |
| location_id | BIGINT | 是 | NULL | 库位ID |
| book_qty | DECIMAL(12,2) | 是 | 0 | 账面数量 |
| actual_qty | DECIMAL(12,2) | 是 | 0 | 实盘数量 |
| diff_qty | DECIMAL(12,2) | 是 | 0 | 差异数量 |
| scan_code | VARCHAR(100) | 是 | NULL | 扫码原始编码 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`idx_order(order_id)`、`idx_part(part_id)`

---

### 22. 维修工单表 `work_order`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| order_no | VARCHAR(50) | 否 | | 工单号，唯一 |
| vehicle_id | BIGINT | 否 | | 车辆ID |
| repair_type | VARCHAR(20) | 否 | 'REPAIR' | MAINTENANCE/REPAIR/ACCIDENT |
| description | TEXT | 是 | NULL | 故障描述 |
| repair_man_id | BIGINT | 是 | NULL | 维修负责人ID |
| in_at | DATETIME | 是 | NULL | 进厂时间 |
| out_at | DATETIME | 是 | NULL | 出厂时间 |
| status | TINYINT | 否 | 1 | 1待修 2维修中 3已完工 4已结算 |
| total_parts_cost | DECIMAL(14,2) | 是 | 0 | 配件总成本 |
| total_labor_cost | DECIMAL(14,2) | 是 | 0 | 工时费 |
| remark | VARCHAR(255) | 是 | NULL | |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`uk_order_no(order_no)`、`idx_vehicle(vehicle_id)`、`idx_status(status)`

---

### 23. 工单领料关联表 `work_order_part`

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| work_order_id | BIGINT | 否 | | 工单ID |
| outbound_item_id | BIGINT | 是 | NULL | 出库明细ID |
| part_id | BIGINT | 否 | | 配件ID |
| quantity | DECIMAL(12,2) | 是 | 0 | 数量 |
| cost | DECIMAL(14,2) | 是 | 0 | 成本 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

索引：`idx_work_order(work_order_id)`、`idx_outbound_item(outbound_item_id)`

---

### 24. 库存预警表 `stock_alert`（可选）

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| part_id | BIGINT | 否 | | 配件ID |
| warehouse_id | BIGINT | 否 | | 仓库ID |
| alert_type | VARCHAR(20) | 否 | | LOW/HIGH/EXPIRING |
| current_qty | DECIMAL(12,2) | 是 | 0 | 当前数量 |
| threshold | DECIMAL(12,2) | 是 | 0 | 阈值 |
| status | TINYINT | 否 | 1 | 1未处理 2已处理 |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |
| updated_by | BIGINT | 是 | NULL | |
| updated_at | DATETIME | 是 | NULL | |
| is_deleted | TINYINT | 否 | 0 | |

---

### 25. 操作日志表 `operation_log`（只读）

| 字段 | 类型 | 允许空 | 默认值 | 说明 |
|---|---|---|---|---|
| id | BIGINT PK AUTO | 否 | | |
| user_id | BIGINT | 是 | NULL | 操作人ID |
| module | VARCHAR(50) | 是 | NULL | 模块 |
| action | VARCHAR(50) | 是 | NULL | 动作 |
| ref_type | VARCHAR(20) | 是 | NULL | 关联类型 |
| ref_id | BIGINT | 是 | NULL | 关联ID |
| scan_code | VARCHAR(100) | 是 | NULL | 扫码原始编码 |
| content | TEXT | 是 | NULL | 内容 |
| ip | VARCHAR(50) | 是 | NULL | IP |
| created_by | BIGINT | 是 | NULL | |
| created_at | DATETIME | 否 | CURRENT_TIMESTAMP | |

索引：`idx_user_time(user_id, created_at)`、`idx_ref(ref_type, ref_id)`

---

## 五、表关系说明

### 主数据关系
- `vehicle_model` 1:N `vehicle`
- `vehicle_model` N:M `part`（通过 `part_vehicle_model`）
- `part_category` 1:N `part`
- `warehouse` 1:N `warehouse_location`
- `warehouse` 1:N `inventory`
- `warehouse` 1:N `inventory_item`

### 库存关系
- `part` 1:N `inventory`（按仓库+库位汇总）
- `part` 1:N `inventory_item`（单件实例）
- `inventory_item` 1:N `inventory_transaction`（单件流水）

### 单据关系
- `inbound_order` 1:N `inbound_order_item`
- `inbound_order_item` 1:N `inventory_item`（逐件追踪时生成）
- `outbound_order` 1:N `outbound_order_item`
- `outbound_order_item` 1:1 `inventory_item`（扫码出库时关联）
- `transfer_order` 1:N `transfer_order_item`
- `stocktake_order` 1:N `stocktake_order_item`
- `work_order` 1:N `work_order_part`
- `outbound_order_item` 1:N `work_order_part`

### 扫码关系
- `inventory_item.qrcode` 唯一，扫码入口
- `outbound_order_item.inventory_item_id` 关联实例
- `inventory_transaction.inventory_item_id` 记录单件变动

---

## 六、关键业务规则

### 1. 入库生成实例规则
- 入库单审核通过时触发
- 若 `part.track_by_item = 1`：
  - 按 `inbound_order_item.quantity` 循环生成 N 条 `inventory_item`
  - 每条生成唯一 `item_code` 和 `qrcode`
  - 更新 `inbound_order_item.generate_item_qty` 和 `generated = 1`
  - 更新 `inventory.item_count += N`
- 若 `part.track_by_item = 0`：
  - 只更新 `inventory.quantity`
  - 不生成实例

### 2. 扫码出库规则
- 扫码得到 `qrcode` 内容
- 查 `inventory_item`，校验 `status = 1`（在库）
- 若 `status != 1`，提示"该件已出库/锁定/报废，不能出库"
- 追加出库明细，写入 `inventory_item_id`
- 出库单提交时：
  - `inventory_item.status = 3`（已出库）
  - 回填 `outbound_item_id`、`vehicle_id`、`out_at`
  - 写 `inventory_transaction`（biz_type=OUT）
  - 更新 `inventory.quantity -= 1`、`item_count -= 1`

### 3. 库存一致性校验
- 定期任务：`inventory.item_count == count(inventory_item where status=1 and part_id=? and warehouse_id=?)`
- 不一致则告警

### 4. 状态机

**入库单**：1草稿 → 2待审 → 3已入库 → 4作废
**出库单**：1草稿 → 2待审 → 3已出库 → 4作废
**调拨单**：1草稿 → 2待审 → 3已调出 → 4已调入 → 5作废
**盘点单**：1草稿 → 2盘点中 → 3已完成 → 4作废
**库存件实例**：1在库 → 2锁定 → 3已出库；1在库 → 4已报废；1在库 → 5已盘亏
**维修工单**：1待修 → 2维修中 → 3已完工 → 4已结算

### 5. 二维码编码规则

**库存件编码 `item_code`**：
```
IT + yyyyMMdd + 6位流水
例：IT20261022000001
```

**二维码内容 `qrcode`**：
```
直接等于 item_code
例：IT20261022000001
```

**入库单号**：`IN + yyyyMMdd + 6位流水`
**出库单号**：`OUT + yyyyMMdd + 6位流水`
**调拨单号**：`TR + yyyyMMdd + 6位流水`
**盘点单号**：`ST + yyyyMMdd + 6位流水`
**维修工单号**：`WO + yyyyMMdd + 6位流水`

---

## 七、扫码接口设计

### 扫码查询库存件
```
GET /api/inventory-item/scan?code=IT20261022000001
```

响应：
```json
{
  "code": 200,
  "message": "success",
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

异常响应：
```json
{
  "code": 400,
  "message": "该件已出库，不能重复出库",
  "data": null
}
```

---

## 八、审计字段自动填充规则

所有写操作由后端框架自动填充：
- `created_by`：当前登录用户ID
- `created_at`：当前时间
- `updated_by`：当前登录用户ID
- `updated_at`：当前时间
- `is_deleted`：默认 0

只读表 `inventory_transaction`、`operation_log` 只填充 `created_by`、`created_at`。

---

## 九、建表顺序（有外键依赖）

1. sys_user
2. vehicle_model
3. vehicle
4. part_category
5. part
6. part_vehicle_model
7. part_unit_conversion
8. supplier
9. warehouse
10. warehouse_location
11. inventory
12. inventory_item
13. inventory_transaction
14. inbound_order
15. inbound_order_item
16. outbound_order
17. outbound_order_item
18. transfer_order
19. transfer_order_item
20. stocktake_order
21. stocktake_order_item
22. work_order
23. work_order_part
24. stock_alert
25. operation_log

> 实际建表时外键可选，建议应用层保证一致性，DDL 不加物理外键，避免维护麻烦。

---

## 十、开发优先级建议

### 第一阶段（核心）
- sys_user、part、warehouse、warehouse_location、inventory、inventory_item
- inbound_order、inbound_order_item
- outbound_order、outbound_order_item
- inventory_transaction

### 第二阶段（业务闭环）
- vehicle_model、vehicle、part_vehicle_model
- supplier、part_unit_conversion
- work_order、work_order_part

### 第三阶段（扩展）
- transfer_order、transfer_order_item
- stocktake_order、stocktake_order_item
- stock_alert、operation_log

---

## 十一、给 DeepSeek 的建表 SQL 生成提示

```
请根据以上 database-design.md 文档，生成 MySQL 8.0 的完整建表 SQL 文件 schema.sql，要求：
1. 每张表带 COMMENT 注释
2. 每个字段带 COMMENT 注释
3. 包含所有索引（唯一索引、普通索引）
4. 不加物理外键，由应用层保证
5. 字符集 utf8mb4，排序 utf8mb4_general_ci
6. 审计字段带 DEFAULT CURRENT_TIMESTAMP 和 ON UPDATE CURRENT_TIMESTAMP
7. 按文档中的建表顺序输出
8. 最后输出初始化数据：一个 admin 用户、一个默认仓库、一个默认库位
```