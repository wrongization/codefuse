from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from typing import List, Dict, Any, Optional

settings = get_settings()

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,  # 开发环境打印SQL
    pool_pre_ping=True,
    pool_recycle=3600,
    # 增加连接超时/读写超时，改善与 MySQL 之间不稳定网络导致的连接丢失问题
    connect_args={
        # 连接超时（秒）
        'connect_timeout': 10,
        # 读/写超时 (部分 MySQL 驱动支持)
        'read_timeout': 60,
        'write_timeout': 60,
    },
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类（仅用于模型定义和建表）
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_query(db, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    执行查询SQL语句并返回结果
    
    Args:
        db: 数据库会话
        query: SQL查询语句
        params: 参数字典（用于参数化查询，防止SQL注入）
    
    Returns:
        查询结果列表，每行是一个字典
    """
    result = db.execute(text(query), params or {})
    # 将结果转换为字典列表
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def execute_update(db, query: str, params: Dict[str, Any] = None) -> int:
    """
    执行INSERT/UPDATE/DELETE等修改语句
    
    Args:
        db: 数据库会话
        query: SQL语句
        params: 参数字典
    
    Returns:
        受影响的行数
    """
    result = db.execute(text(query), params or {})
    db.commit()
    return result.rowcount


def execute_insert(db, query: str, params: Dict[str, Any] = None) -> int:
    """
    执行INSERT语句并返回新插入行的ID
    
    Args:
        db: 数据库会话
        query: INSERT SQL语句
        params: 参数字典
    
    Returns:
        新插入行的自增ID
    """
    result = db.execute(text(query), params or {})
    db.commit()
    return result.lastrowid


def fetch_one(db, query: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    执行查询并返回单行结果
    
    Args:
        db: 数据库会话
        query: SQL查询语句
        params: 参数字典
    
    Returns:
        单行结果字典，如果没有结果则返回None
    """
    result = db.execute(text(query), params or {})
    row = result.fetchone()
    if row:
        columns = result.keys()
        return dict(zip(columns, row))
    return None
