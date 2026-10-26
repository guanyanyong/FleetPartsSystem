-- ============================================================
-- 车队配件库存管理系统 - MySQL 5.7 建表脚本
-- 数据库：FleetParts
-- 字符集：utf8mb4 / utf8mb4_unicode_ci
-- 表数量：25 张
-- 说明：不加物理外键，由应用层保证一致性
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 创建数据库
-- ----------------------------
CREATE DATABASE IF NOT EXISTS `FleetParts`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `FleetParts`;

-- ============================================================
-- 1. 用户表 sys_user
-- ============================================================
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username` VARCHAR(50) NOT NULL COMMENT '登录名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `real_name` VARCHAR(50) DEFAULT NULL COMMENT '姓名',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '电话',
  `role` VARCHAR(20) NOT NULL DEFAULT 'readonly' COMMENT '角色：admin/keeper/purchaser/leader/readonly',
  `default_warehouse_id` BIGINT DEFAULT NULL COMMENT '默认仓库ID',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_role` (`role`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================================
-- 2. 车型表 vehicle_model
-- ============================================================
DROP TABLE IF EXISTS `vehicle_model`;
CREATE TABLE `vehicle_model` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `brand` VARCHAR(50) NOT NULL COMMENT '品牌',
  `model_name` VARCHAR(100) NOT NULL COMMENT '型号',
  `tonnage` VARCHAR(20) DEFAULT NULL COMMENT '吨位/座位',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_brand` (`brand`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='车型表';

-- ============================================================
-- 3. 车辆表 vehicle
-- ============================================================
DROP TABLE IF EXISTS `vehicle`;
CREATE TABLE `vehicle` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `plate_no` VARCHAR(20) NOT NULL COMMENT '车牌号',
  `model_id` BIGINT DEFAULT NULL COMMENT '车型ID',
  `vin` VARCHAR(50) DEFAULT NULL COMMENT '车架号',
  `engine_no` VARCHAR(50) DEFAULT NULL COMMENT '发动机号',
  `purchase_date` DATE DEFAULT NULL COMMENT '购置日期',
  `department` VARCHAR(50) DEFAULT NULL COMMENT '所属车队/部门',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1在用 2维修 3停用 4报废',
  `mileage` INT DEFAULT 0 COMMENT '当前里程',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_plate_no` (`plate_no`),
  KEY `idx_model` (`model_id`),
  KEY `idx_status` (`status`),
  KEY `idx_department` (`department`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='车辆表';

-- ============================================================
-- 4. 配件分类表 part_category
-- ============================================================
DROP TABLE IF EXISTS `part_category`;
CREATE TABLE `part_category` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(50) NOT NULL COMMENT '分类名',
  `parent_id` BIGINT DEFAULT NULL COMMENT '父分类ID',
  `sort` INT DEFAULT 0 COMMENT '排序',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_parent` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配件分类表';

-- ============================================================
-- 5. 配件表 part
-- ============================================================
DROP TABLE IF EXISTS `part`;
CREATE TABLE `part` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `part_code` VARCHAR(50) NOT NULL COMMENT '配件业务编码',
  `part_name` VARCHAR(100) NOT NULL COMMENT '配件名称',
  `category_id` BIGINT DEFAULT NULL COMMENT '分类ID',
  `spec` VARCHAR(100) DEFAULT NULL COMMENT '规格型号',
  `brand` VARCHAR(50) DEFAULT NULL COMMENT '品牌',
  `unit` VARCHAR(20) NOT NULL DEFAULT '个' COMMENT '基本单位',
  `is_general` TINYINT NOT NULL DEFAULT 0 COMMENT '是否通用件 1是 0否',
  `safety_stock` DECIMAL(12,2) DEFAULT 0.00 COMMENT '安全库存',
  `max_stock` DECIMAL(12,2) DEFAULT 0.00 COMMENT '最高库存',
  `shelf_life_days` INT DEFAULT 0 COMMENT '保质期天数，0为无',
  `track_by_item` TINYINT NOT NULL DEFAULT 0 COMMENT '是否按件追踪，1是则入库逐件生成二维码',
  `scan_enabled` TINYINT NOT NULL DEFAULT 1 COMMENT '是否允许扫码出库',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_part_code` (`part_code`),
  KEY `idx_category` (`category_id`),
  KEY `idx_track` (`track_by_item`),
  KEY `idx_status` (`status`),
  KEY `idx_part_name` (`part_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配件表';

-- ============================================================
-- 6. 配件车型适配表 part_vehicle_model
-- ============================================================
DROP TABLE IF EXISTS `part_vehicle_model`;
CREATE TABLE `part_vehicle_model` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `model_id` BIGINT NOT NULL COMMENT '车型ID',
  `remark` VARCHAR(100) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_part_model` (`part_id`, `model_id`),
  KEY `idx_model` (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配件车型适配表';

-- ============================================================
-- 7. 配件单位换算表 part_unit_conversion
-- ============================================================
DROP TABLE IF EXISTS `part_unit_conversion`;
CREATE TABLE `part_unit_conversion` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `from_unit` VARCHAR(20) NOT NULL COMMENT '源单位',
  `to_unit` VARCHAR(20) NOT NULL COMMENT '目标单位',
  `rate` DECIMAL(12,4) NOT NULL COMMENT '换算率',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_part` (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配件单位换算表';

-- ============================================================
-- 8. 供应商表 supplier
-- ============================================================
DROP TABLE IF EXISTS `supplier`;
CREATE TABLE `supplier` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(100) NOT NULL COMMENT '供应商名称',
  `contact` VARCHAR(50) DEFAULT NULL COMMENT '联系人',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '电话',
  `address` VARCHAR(255) DEFAULT NULL COMMENT '地址',
  `main_category` VARCHAR(100) DEFAULT NULL COMMENT '主营品类',
  `payment_term` VARCHAR(50) DEFAULT NULL COMMENT '账期',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1合作 0停用',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_name` (`name`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供应商表';

-- ============================================================
-- 9. 仓库表 warehouse
-- ============================================================
DROP TABLE IF EXISTS `warehouse`;
CREATE TABLE `warehouse` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(50) NOT NULL COMMENT '仓库名',
  `address` VARCHAR(255) DEFAULT NULL COMMENT '地址',
  `keeper_id` BIGINT DEFAULT NULL COMMENT '负责人ID',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_name` (`name`),
  KEY `idx_keeper` (`keeper_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仓库表';

-- ============================================================
-- 10. 库位表 warehouse_location
-- ============================================================
DROP TABLE IF EXISTS `warehouse_location`;
CREATE TABLE `warehouse_location` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `warehouse_id` BIGINT NOT NULL COMMENT '仓库ID',
  `location_code` VARCHAR(50) NOT NULL COMMENT '库位编码',
  `location_qrcode` VARCHAR(255) DEFAULT NULL COMMENT '库位二维码内容',
  `remark` VARCHAR(100) DEFAULT NULL COMMENT '备注',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_warehouse_location` (`warehouse_id`, `location_code`),
  KEY `idx_warehouse` (`warehouse_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='库位表';

-- ============================================================
-- 11. 库存表 inventory
-- ============================================================
DROP TABLE IF EXISTS `inventory`;
CREATE TABLE `inventory` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `warehouse_id` BIGINT NOT NULL COMMENT '仓库ID',
  `location_id` BIGINT DEFAULT NULL COMMENT '库位ID',
  `quantity` DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '当前数量（汇总）',
  `item_count` INT NOT NULL DEFAULT 0 COMMENT '在库实例数',
  `locked_qty` DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '锁定数量',
  `avg_cost` DECIMAL(12,4) NOT NULL DEFAULT 0.0000 COMMENT '移动加权平均成本',
  `last_in_at` DATETIME DEFAULT NULL COMMENT '最后入库时间',
  `last_out_at` DATETIME DEFAULT NULL COMMENT '最后出库时间',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_part_warehouse_location` (`part_id`, `warehouse_id`, `location_id`),
  KEY `idx_warehouse` (`warehouse_id`),
  KEY `idx_location` (`location_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='库存表';

-- ============================================================
-- 12. 库存件实例表 inventory_item
-- ============================================================
DROP TABLE IF EXISTS `inventory_item`;
CREATE TABLE `inventory_item` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `item_code` VARCHAR(50) NOT NULL COMMENT '库存件唯一编码',
  `qrcode` VARCHAR(255) NOT NULL COMMENT '二维码内容',
  `qrcode_image` VARCHAR(255) DEFAULT NULL COMMENT '二维码图片路径',
  `part_id` BIGINT NOT NULL COMMENT '所属配件ID',
  `warehouse_id` BIGINT NOT NULL COMMENT '当前仓库ID',
  `location_id` BIGINT DEFAULT NULL COMMENT '当前库位ID',
  `batch_no` VARCHAR(50) DEFAULT NULL COMMENT '批次号',
  `serial_no` VARCHAR(100) DEFAULT NULL COMMENT '序列号/出厂编号',
  `production_date` DATE DEFAULT NULL COMMENT '生产日期',
  `expire_date` DATE DEFAULT NULL COMMENT '到期日期',
  `unit_cost` DECIMAL(12,4) NOT NULL DEFAULT 0.0000 COMMENT '该件入库成本',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1在库 2锁定 3已出库 4已报废 5已盘亏',
  `inbound_item_id` BIGINT DEFAULT NULL COMMENT '来源入库明细ID',
  `outbound_item_id` BIGINT DEFAULT NULL COMMENT '出库明细ID',
  `vehicle_id` BIGINT DEFAULT NULL COMMENT '装到哪台车',
  `work_order_id` BIGINT DEFAULT NULL COMMENT '关联维修工单',
  `in_at` DATETIME DEFAULT NULL COMMENT '入库时间',
  `out_at` DATETIME DEFAULT NULL COMMENT '出库时间',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_item_code` (`item_code`),
  UNIQUE KEY `uk_qrcode` (`qrcode`),
  KEY `idx_part_status` (`part_id`, `status`),
  KEY `idx_warehouse_location` (`warehouse_id`, `location_id`),
  KEY `idx_vehicle` (`vehicle_id`),
  KEY `idx_work_order` (`work_order_id`),
  KEY `idx_batch` (`batch_no`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='库存件实例表';

-- ============================================================
-- 13. 库存流水表 inventory_transaction（只读）
-- ============================================================
DROP TABLE IF EXISTS `inventory_transaction`;
CREATE TABLE `inventory_transaction` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `inventory_item_id` BIGINT DEFAULT NULL COMMENT '库存件实例ID',
  `warehouse_id` BIGINT NOT NULL COMMENT '仓库ID',
  `location_id` BIGINT DEFAULT NULL COMMENT '库位ID',
  `biz_type` VARCHAR(20) NOT NULL COMMENT 'IN/OUT/TRANSFER_IN/TRANSFER_OUT/ADJUST_IN/ADJUST_OUT',
  `change_qty` DECIMAL(12,2) NOT NULL COMMENT '变动数量',
  `before_qty` DECIMAL(12,2) NOT NULL COMMENT '变动前数量',
  `after_qty` DECIMAL(12,2) NOT NULL COMMENT '变动后数量',
  `unit_cost` DECIMAL(12,4) DEFAULT NULL COMMENT '单位成本',
  `ref_type` VARCHAR(20) NOT NULL COMMENT 'INBOUND/OUTBOUND/TRANSFER/STOCKTAKE',
  `ref_id` BIGINT DEFAULT NULL COMMENT '关联单据ID',
  `ref_no` VARCHAR(50) DEFAULT NULL COMMENT '关联单号',
  `batch_no` VARCHAR(50) DEFAULT NULL COMMENT '批次号',
  `scan_code` VARCHAR(100) DEFAULT NULL COMMENT '扫码原始编码',
  `operator_id` BIGINT DEFAULT NULL COMMENT '操作人ID',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_part_warehouse_time` (`part_id`, `warehouse_id`, `created_at`),
  KEY `idx_ref` (`ref_type`, `ref_id`),
  KEY `idx_item` (`inventory_item_id`),
  KEY `idx_biz_type` (`biz_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='库存流水表';

-- ============================================================
-- 14. 入库单主表 inbound_order
-- ============================================================
DROP TABLE IF EXISTS `inbound_order`;
CREATE TABLE `inbound_order` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_no` VARCHAR(50) NOT NULL COMMENT '入库单号',
  `supplier_id` BIGINT DEFAULT NULL COMMENT '供应商ID',
  `warehouse_id` BIGINT NOT NULL COMMENT '入库仓库ID',
  `inbound_type` VARCHAR(20) NOT NULL DEFAULT 'PURCHASE' COMMENT 'PURCHASE/RETURN/TRANSFER/ADJUST',
  `total_amount` DECIMAL(14,2) DEFAULT 0.00 COMMENT '总金额',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1草稿 2待审 3已入库 4作废',
  `operator_id` BIGINT DEFAULT NULL COMMENT '经办人ID',
  `audit_user_id` BIGINT DEFAULT NULL COMMENT '审核人ID',
  `audit_at` DATETIME DEFAULT NULL COMMENT '审核时间',
  `inbound_at` DATETIME DEFAULT NULL COMMENT '入库时间',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_status` (`status`),
  KEY `idx_supplier` (`supplier_id`),
  KEY `idx_warehouse` (`warehouse_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='入库单主表';

-- ============================================================
-- 15. 入库单明细表 inbound_order_item
-- ============================================================
DROP TABLE IF EXISTS `inbound_order_item`;
CREATE TABLE `inbound_order_item` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_id` BIGINT NOT NULL COMMENT '入库单ID',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `quantity` DECIMAL(12,2) NOT NULL COMMENT '数量',
  `unit` VARCHAR(20) DEFAULT NULL COMMENT '单位',
  `unit_price` DECIMAL(12,4) NOT NULL DEFAULT 0.0000 COMMENT '单价',
  `amount` DECIMAL(14,2) DEFAULT 0.00 COMMENT '金额',
  `batch_no` VARCHAR(50) DEFAULT NULL COMMENT '批次号',
  `production_date` DATE DEFAULT NULL COMMENT '生产日期',
  `expire_date` DATE DEFAULT NULL COMMENT '到期日期',
  `location_id` BIGINT DEFAULT NULL COMMENT '库位ID',
  `track_by_item` TINYINT NOT NULL DEFAULT 0 COMMENT '是否逐件追踪',
  `generate_item_qty` INT DEFAULT 0 COMMENT '本次生成实例数量',
  `generated` TINYINT NOT NULL DEFAULT 0 COMMENT '是否已生成实例',
  `scan_code` VARCHAR(100) DEFAULT NULL COMMENT '扫码原始编码',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_order` (`order_id`),
  KEY `idx_part` (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='入库单明细表';

-- ============================================================
-- 16. 出库单主表 outbound_order
-- ============================================================
DROP TABLE IF EXISTS `outbound_order`;
CREATE TABLE `outbound_order` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_no` VARCHAR(50) NOT NULL COMMENT '出库单号',
  `warehouse_id` BIGINT NOT NULL COMMENT '出库仓库ID',
  `outbound_type` VARCHAR(20) NOT NULL DEFAULT 'REPAIR' COMMENT 'REPAIR/SALE/RETURN/TRANSFER/SCRAP',
  `vehicle_id` BIGINT DEFAULT NULL COMMENT '关联车辆ID',
  `work_order_id` BIGINT DEFAULT NULL COMMENT '关联维修工单ID',
  `receiver_id` BIGINT DEFAULT NULL COMMENT '领用人ID',
  `total_amount` DECIMAL(14,2) DEFAULT 0.00 COMMENT '总金额',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1草稿 2待审 3已出库 4作废',
  `scan_mode` TINYINT NOT NULL DEFAULT 0 COMMENT '是否扫码模式',
  `scanner_id` BIGINT DEFAULT NULL COMMENT '扫码操作人ID',
  `operator_id` BIGINT DEFAULT NULL COMMENT '经办人ID',
  `audit_user_id` BIGINT DEFAULT NULL COMMENT '审核人ID',
  `audit_at` DATETIME DEFAULT NULL COMMENT '审核时间',
  `outbound_at` DATETIME DEFAULT NULL COMMENT '出库时间',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_status` (`status`),
  KEY `idx_vehicle` (`vehicle_id`),
  KEY `idx_work_order` (`work_order_id`),
  KEY `idx_warehouse` (`warehouse_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='出库单主表';

-- ============================================================
-- 17. 出库单明细表 outbound_order_item
-- ============================================================
DROP TABLE IF EXISTS `outbound_order_item`;
CREATE TABLE `outbound_order_item` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_id` BIGINT NOT NULL COMMENT '出库单ID',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `inventory_item_id` BIGINT DEFAULT NULL COMMENT '库存件实例ID',
  `quantity` DECIMAL(12,2) NOT NULL COMMENT '数量',
  `unit` VARCHAR(20) DEFAULT NULL COMMENT '单位',
  `unit_cost` DECIMAL(12,4) DEFAULT 0.0000 COMMENT '单位成本',
  `amount` DECIMAL(14,2) DEFAULT 0.00 COMMENT '金额',
  `batch_no` VARCHAR(50) DEFAULT NULL COMMENT '批次号',
  `location_id` BIGINT DEFAULT NULL COMMENT '库位ID',
  `scan_code` VARCHAR(100) DEFAULT NULL COMMENT '扫码原始编码',
  `scan_type` VARCHAR(20) DEFAULT NULL COMMENT 'BARCODE/QRCODE/MANUAL',
  `scan_at` DATETIME DEFAULT NULL COMMENT '扫码时间',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_order` (`order_id`),
  KEY `idx_part` (`part_id`),
  KEY `idx_inventory_item` (`inventory_item_id`),
  KEY `idx_scan_code` (`scan_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='出库单明细表';

-- ============================================================
-- 18. 调拨单主表 transfer_order
-- ============================================================
DROP TABLE IF EXISTS `transfer_order`;
CREATE TABLE `transfer_order` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_no` VARCHAR(50) NOT NULL COMMENT '调拨单号',
  `from_warehouse_id` BIGINT NOT NULL COMMENT '调出仓库ID',
  `to_warehouse_id` BIGINT NOT NULL COMMENT '调入仓库ID',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1草稿 2待审 3已调出 4已调入 5作废',
  `operator_id` BIGINT DEFAULT NULL COMMENT '经办人ID',
  `audit_user_id` BIGINT DEFAULT NULL COMMENT '审核人ID',
  `transfer_at` DATETIME DEFAULT NULL COMMENT '调拨时间',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_status` (`status`),
  KEY `idx_from_warehouse` (`from_warehouse_id`),
  KEY `idx_to_warehouse` (`to_warehouse_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='调拨单主表';

-- ============================================================
-- 19. 调拨单明细表 transfer_order_item
-- ============================================================
DROP TABLE IF EXISTS `transfer_order_item`;
CREATE TABLE `transfer_order_item` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_id` BIGINT NOT NULL COMMENT '调拨单ID',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `inventory_item_id` BIGINT DEFAULT NULL COMMENT '库存件实例ID',
  `quantity` DECIMAL(12,2) NOT NULL COMMENT '数量',
  `from_location_id` BIGINT DEFAULT NULL COMMENT '调出库位ID',
  `to_location_id` BIGINT DEFAULT NULL COMMENT '调入库位ID',
  `batch_no` VARCHAR(50) DEFAULT NULL COMMENT '批次号',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_order` (`order_id`),
  KEY `idx_part` (`part_id`),
  KEY `idx_inventory_item` (`inventory_item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='调拨单明细表';

-- ============================================================
-- 20. 盘点单主表 stocktake_order
-- ============================================================
DROP TABLE IF EXISTS `stocktake_order`;
CREATE TABLE `stocktake_order` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_no` VARCHAR(50) NOT NULL COMMENT '盘点单号',
  `warehouse_id` BIGINT NOT NULL COMMENT '盘点仓库ID',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1草稿 2盘点中 3已完成 4作废',
  `operator_id` BIGINT DEFAULT NULL COMMENT '盘点人ID',
  `audit_user_id` BIGINT DEFAULT NULL COMMENT '审核人ID',
  `stocktake_at` DATETIME DEFAULT NULL COMMENT '盘点时间',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_status` (`status`),
  KEY `idx_warehouse` (`warehouse_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='盘点单主表';

-- ============================================================
-- 21. 盘点单明细表 stocktake_order_item
-- ============================================================
DROP TABLE IF EXISTS `stocktake_order_item`;
CREATE TABLE `stocktake_order_item` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_id` BIGINT NOT NULL COMMENT '盘点单ID',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `inventory_item_id` BIGINT DEFAULT NULL COMMENT '库存件实例ID',
  `location_id` BIGINT DEFAULT NULL COMMENT '库位ID',
  `book_qty` DECIMAL(12,2) DEFAULT 0.00 COMMENT '账面数量',
  `actual_qty` DECIMAL(12,2) DEFAULT 0.00 COMMENT '实盘数量',
  `diff_qty` DECIMAL(12,2) DEFAULT 0.00 COMMENT '差异数量',
  `scan_code` VARCHAR(100) DEFAULT NULL COMMENT '扫码原始编码',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_order` (`order_id`),
  KEY `idx_part` (`part_id`),
  KEY `idx_inventory_item` (`inventory_item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='盘点单明细表';

-- ============================================================
-- 22. 维修工单表 work_order
-- ============================================================
DROP TABLE IF EXISTS `work_order`;
CREATE TABLE `work_order` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_no` VARCHAR(50) NOT NULL COMMENT '工单号',
  `vehicle_id` BIGINT NOT NULL COMMENT '车辆ID',
  `repair_type` VARCHAR(20) NOT NULL DEFAULT 'REPAIR' COMMENT 'MAINTENANCE/REPAIR/ACCIDENT',
  `description` TEXT COMMENT '故障描述',
  `repair_man_id` BIGINT DEFAULT NULL COMMENT '维修负责人ID',
  `in_at` DATETIME DEFAULT NULL COMMENT '进厂时间',
  `out_at` DATETIME DEFAULT NULL COMMENT '出厂时间',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1待修 2维修中 3已完工 4已结算',
  `total_parts_cost` DECIMAL(14,2) DEFAULT 0.00 COMMENT '配件总成本',
  `total_labor_cost` DECIMAL(14,2) DEFAULT 0.00 COMMENT '工时费',
  `remark` VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_vehicle` (`vehicle_id`),
  KEY `idx_status` (`status`),
  KEY `idx_repair_man` (`repair_man_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='维修工单表';

-- ============================================================
-- 23. 工单领料关联表 work_order_part
-- ============================================================
DROP TABLE IF EXISTS `work_order_part`;
CREATE TABLE `work_order_part` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `work_order_id` BIGINT NOT NULL COMMENT '工单ID',
  `outbound_item_id` BIGINT DEFAULT NULL COMMENT '出库明细ID',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `quantity` DECIMAL(12,2) DEFAULT 0.00 COMMENT '数量',
  `cost` DECIMAL(14,2) DEFAULT 0.00 COMMENT '成本',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_work_order` (`work_order_id`),
  KEY `idx_outbound_item` (`outbound_item_id`),
  KEY `idx_part` (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工单领料关联表';

-- ============================================================
-- 24. 库存预警表 stock_alert
-- ============================================================
DROP TABLE IF EXISTS `stock_alert`;
CREATE TABLE `stock_alert` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `part_id` BIGINT NOT NULL COMMENT '配件ID',
  `warehouse_id` BIGINT NOT NULL COMMENT '仓库ID',
  `alert_type` VARCHAR(20) NOT NULL COMMENT 'LOW/HIGH/EXPIRING',
  `current_qty` DECIMAL(12,2) DEFAULT 0.00 COMMENT '当前数量',
  `threshold` DECIMAL(12,2) DEFAULT 0.00 COMMENT '阈值',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '1未处理 2已处理',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT NOT NULL DEFAULT 0 COMMENT '0正常 1删除',
  PRIMARY KEY (`id`),
  KEY `idx_part_warehouse` (`part_id`, `warehouse_id`),
  KEY `idx_alert_type` (`alert_type`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='库存预警表';

-- ============================================================
-- 25. 操作日志表 operation_log（只读）
-- ============================================================
DROP TABLE IF EXISTS `operation_log`;
CREATE TABLE `operation_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` BIGINT DEFAULT NULL COMMENT '操作人ID',
  `module` VARCHAR(50) DEFAULT NULL COMMENT '模块',
  `action` VARCHAR(50) DEFAULT NULL COMMENT '动作',
  `ref_type` VARCHAR(20) DEFAULT NULL COMMENT '关联类型',
  `ref_id` BIGINT DEFAULT NULL COMMENT '关联ID',
  `scan_code` VARCHAR(100) DEFAULT NULL COMMENT '扫码原始编码',
  `content` TEXT COMMENT '内容',
  `ip` VARCHAR(50) DEFAULT NULL COMMENT 'IP',
  `created_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_time` (`user_id`, `created_at`),
  KEY `idx_ref` (`ref_type`, `ref_id`),
  KEY `idx_module` (`module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

SET FOREIGN_KEY_CHECKS = 1;


