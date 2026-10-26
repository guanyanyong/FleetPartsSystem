"""
数据库连接模块
使用 PyMySQL 连接 MySQL 数据库
"""
import pymysql
from pymysql.cursors import DictCursor

# 数据库连接配置
DB_CONFIG = {
    "host": "sh-cdb-om3hqg2y.sql.tencentcdb.com",
    "port": 23159,
    "user": "root",
    "password": "ABcd1234",
    "database": "FleetParts",
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": True,
}
