-- 设置会话时区为中国/上海 (东八区)
SET time_zone = '+08:00';

-- 创建数据库 Nexus，指定多语言中文字符集 utf8mb4 和排序规则 utf8mb4_unicode_ci
CREATE DATABASE IF NOT EXISTS `Nexus`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 切换到 Nexus 数据库
USE `Nexus`;

-- --------------------------------------------------------
-- 表结构定义
-- --------------------------------------------------------

-- 1. 创建配置项主表 config_items
CREATE TABLE IF NOT EXISTS `config_items` (
    `config_id` VARCHAR(8) NOT NULL COMMENT '配置项编号 (固定8位)',
    `category` VARCHAR(1) NOT NULL COMMENT '配置项大类 (1位字母或数字)',
    `abbr` VARCHAR(3) NOT NULL COMMENT '配置项简称 (3位字母或数字)',
    `seq` VARCHAR(4) NOT NULL COMMENT '配置项序号 (4位字母或数字)',
    `description` LONGTEXT COMMENT '配置项说明',
    `content` LONGTEXT COMMENT '配置项内容 (序列化后的JSON字符串)',
    `updated_at` DATETIME NOT NULL COMMENT '最后更新时间',
    `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '假删除标记 (0:正常, 1:已删除)',
    PRIMARY KEY (`config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配置参数主表';

-- 2. 创建配置项历史履历表 config_history
CREATE TABLE IF NOT EXISTS `config_history` (
    `id` INT AUTO_INCREMENT NOT NULL COMMENT '履历自增ID',
    `config_id` VARCHAR(8) NOT NULL COMMENT '关联的配置项编号',
    `description` LONGTEXT COMMENT '此版本的配置项说明',
    `content` LONGTEXT COMMENT '此版本的配置项内容 (JSON)',
    `updated_at` DATETIME NOT NULL COMMENT '此次变更/更新的时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配置参数历史履历表';

-- --------------------------------------------------------
-- 用户及权限配置
-- --------------------------------------------------------

-- 1. 创建数据库的管理员 nex_dbo (具备对数据库的全部权限)
CREATE USER IF NOT EXISTS 'nex_dbo'@'%' IDENTIFIED BY 'NexusDbo2026^';
GRANT ALL PRIVILEGES ON `Nexus`.* TO 'nex_dbo'@'%';

-- 2. 创建普通使用者 nex_reader (对数据库只有只读权限)
CREATE USER IF NOT EXISTS 'nex_reader'@'%' IDENTIFIED BY 'NexusReader2027&';
GRANT SELECT ON `Nexus`.* TO 'nex_reader'@'%';

-- 刷新系统权限列表以使更改立即生效
FLUSH PRIVILEGES;
