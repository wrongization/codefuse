from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db, execute_query, execute_insert, fetch_one
from app.schemas import ActivityLogResponse

router = APIRouter(prefix="/api/activity-logs", tags=["activity-logs"])


@router.get("/", response_model=List[dict])
def get_activity_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取活动日志列表"""
    # 使用LEFT JOIN获取日志及用户名
    sql = """
        SELECT 
            al.log_id,
            al.user_id,
            al.action_type,
            al.entity_type,
            al.entity_id,
            al.description,
            al.created_at,
            u.username
        FROM activity_log al
        LEFT JOIN user u ON al.user_id = u.user_id
        ORDER BY al.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    logs = execute_query(db, sql, {
        "limit": limit,
        "offset": skip
    })
    
    return logs


def create_activity_log(
    db: Session,
    user_id: int,
    action_type: str,
    entity_type: str,
    entity_id: int,
    description: str
):
    """创建活动日志的辅助函数"""
    insert_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    log_id = execute_insert(db, insert_sql, {
        "user_id": user_id,
        "action_type": action_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "description": description,
        "created_at": datetime.utcnow()
    })
    
    # 返回创建的日志
    select_sql = "SELECT * FROM activity_log WHERE log_id = :log_id"
    return fetch_one(db, select_sql, {"log_id": log_id})
