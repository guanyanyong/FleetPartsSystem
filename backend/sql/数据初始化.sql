

-- ============================================================
-- 初始化数据
-- ============================================================
USE `FleetParts`;

-- 默认管理员（密码：admin123）
-- 下面的哈希由后端 passlib(bcrypt) 生成，不要手写占位串；
-- 需要更换密码时用 app.core.security.hash_password("新密码") 生成后替换。
INSERT INTO `sys_user` (`username`, `password_hash`, `real_name`, `role`, `status`, `created_at`)
VALUES (
  'admin',
  '$2b$12$yQFRNvW9Dq2X74U97CvM/OraDYVwLheWuf95m594jPPWaFt7FaktC',
  '管理员',
  'admin',
  1,
  NOW()
)
ON DUPLICATE KEY UPDATE `updated_at` = NOW();
-- 注意：命中重复键时只刷新 updated_at，不会重置已有账号密码（避免误改线上密码）

-- 默认仓库
INSERT INTO `warehouse` (`name`, `address`, `status`, `created_at`)
VALUES ('主仓', '车队维修厂', 1, NOW());

-- 默认库位
INSERT INTO `warehouse_location` (`warehouse_id`, `location_code`, `remark`, `status`, `created_at`)
SELECT id, 'A-01-01', '默认库位', 1, NOW() FROM `warehouse` WHERE `name` = '主仓'
ON DUPLICATE KEY UPDATE `updated_at` = NOW();

-- 默认配件分类
INSERT INTO `part_category` (`name`, `parent_id`, `sort`, `status`, `created_at`)
VALUES
  ('机油', NULL, 1, 1, NOW()),
  ('滤芯', NULL, 2, 1, NOW()),
  ('刹车', NULL, 3, 1, NOW()),
  ('轮胎', NULL, 4, 1, NOW()),
  ('电器', NULL, 5, 1, NOW())
ON DUPLICATE KEY UPDATE `updated_at` = NOW();

select *
from sys_user;