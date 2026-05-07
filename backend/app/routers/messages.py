from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db, execute_query, execute_insert, execute_update, fetch_one
from app.schemas import MessageCreate, MessageUpdate, MessageResponse, MessageListResponse

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_message(
    message: MessageCreate,
    creator_id: int,
    db: Session = Depends(get_db)
):
    """
    创建消息（私信或讨论）
    
    - message_type='private': 私信，需要提供recipient_ids
    - message_type='topic': 题目讨论，需要提供problem_id
    """
    # 验证消息类型
    if message.message_type not in ['private', 'topic']:
        raise HTTPException(status_code=400, detail="消息类型必须是 'private' 或 'topic'")
    
    # 验证创建者存在
    creator_sql = "SELECT user_id FROM user WHERE user_id = :user_id"
    creator = fetch_one(db, creator_sql, {"user_id": creator_id})
    if not creator:
        raise HTTPException(status_code=404, detail="创建者不存在")
    
    # 如果是私信，先验证所有接收者（在创建消息之前）
    if message.message_type == 'private':
        if not message.recipient_ids or len(message.recipient_ids) == 0:
            raise HTTPException(status_code=400, detail="私信必须指定至少一个接收者")
        
        for recipient_id in message.recipient_ids:
            # 验证接收者存在
            recipient_sql = "SELECT user_id FROM user WHERE user_id = :user_id"
            recipient = fetch_one(db, recipient_sql, {"user_id": recipient_id})
            if not recipient:
                raise HTTPException(status_code=404, detail=f"接收者 {recipient_id} 不存在")
            
            # 检查是否被对方屏蔽
            blocked_sql = """
                SELECT 1 FROM friendship 
                WHERE user_id = :recipient_id AND friend_id = :creator_id AND status = 'blocked'
                LIMIT 1
            """
            blocked = fetch_one(db, blocked_sql, {
                "creator_id": creator_id,
                "recipient_id": recipient_id
            })
            
            if blocked:
                raise HTTPException(
                    status_code=403, 
                    detail="该好友屏蔽了你"
                )
            
            # 验证好友关系（只有互为好友才能发送私信）
            friendship_sql = """
                SELECT 1 FROM friendship 
                WHERE (
                    (user_id = :creator_id AND friend_id = :recipient_id AND status = 'accepted')
                    OR
                    (user_id = :recipient_id AND friend_id = :creator_id AND status = 'accepted')
                )
                LIMIT 1
            """
            friendship = fetch_one(db, friendship_sql, {
                "creator_id": creator_id,
                "recipient_id": recipient_id
            })
            
            if not friendship:
                raise HTTPException(
                    status_code=403, 
                    detail=f"只能向好友发送私信，用户 {recipient_id} 不是您的好友"
                )
    
    # 验证通过后，创建消息
    insert_msg_sql = """
        INSERT INTO message (title, content, creator_id, message_type, created_at)
        VALUES (:title, :content, :creator_id, :message_type, :created_at)
    """
    message_id = execute_insert(db, insert_msg_sql, {
        "title": message.title,
        "content": message.content,
        "creator_id": creator_id,
        "message_type": message.message_type,
        "created_at": datetime.utcnow()
    })
    
    # 如果是私信，添加接收者关联
    if message.message_type == 'private':
        for recipient_id in message.recipient_ids:
            # 添加接收者关联
            insert_recipient_sql = """
                INSERT INTO message_recipient (message_id, recipient_user_id)
                VALUES (:message_id, :recipient_user_id)
            """
            execute_insert(db, insert_recipient_sql, {
                "message_id": message_id,
                "recipient_user_id": recipient_id
            })
    
    # 如果是题目讨论，添加题目关联
    elif message.message_type == 'topic':
        if not message.problem_id:
            raise HTTPException(status_code=400, detail="题目讨论必须指定题目ID")
        
        # 验证题目存在
        problem_sql = "SELECT problem_id FROM problem WHERE problem_id = :problem_id"
        problem = fetch_one(db, problem_sql, {"problem_id": message.problem_id})
        if not problem:
            raise HTTPException(status_code=404, detail="题目不存在")
        
        # 添加题目关联
        insert_prob_sql = """
            INSERT INTO message_problem (message_id, problem_id)
            VALUES (:message_id, :problem_id)
        """
        execute_insert(db, insert_prob_sql, {
            "message_id": message_id,
            "problem_id": message.problem_id
        })
    
    # 记录活动日志
    log_description = f"发送了私信给 {len(message.recipient_ids)} 个用户" if message.message_type == 'private' else f"在题目讨论区发表了主题《{message.title or '无标题'}》"
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": creator_id,
        "action_type": "create",
        "entity_type": "message",
        "entity_id": message_id,
        "description": log_description,
        "created_at": datetime.utcnow()
    })
    
    # 返回创建的消息
    select_sql = "SELECT * FROM message WHERE message_id = :message_id"
    return fetch_one(db, select_sql, {"message_id": message_id})


@router.get("/admin/all", response_model=List[dict])
def get_all_messages_admin(
    message_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """管理员获取所有消息（私信或讨论）"""
    # 构建SQL查询
    sql = "SELECT * FROM message WHERE 1=1"
    params = {}
    
    # 按消息类型筛选
    if message_type:
        sql += " AND message_type = :message_type"
        params["message_type"] = message_type
    
    # 搜索标题或内容
    if search:
        sql += " AND (title LIKE :search OR content LIKE :search)"
        params["search"] = f"%{search}%"
    
    sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = skip
    
    messages = execute_query(db, sql, params)
    
    # 构建响应
    result = []
    for msg in messages:
        # 获取发送者信息
        sender_sql = "SELECT user_id, username FROM user WHERE user_id = :user_id"
        sender = fetch_one(db, sender_sql, {"user_id": msg['creator_id']})
        
        # 获取接收者信息（如果是私信）
        recipients = []
        if msg['message_type'] == 'private':
            recipient_sql = """
                SELECT u.user_id, u.username
                FROM message_recipient mr
                INNER JOIN user u ON mr.recipient_user_id = u.user_id
                WHERE mr.message_id = :message_id
            """
            recipients = execute_query(db, recipient_sql, {"message_id": msg['message_id']})
        
        # 获取题目信息（如果是讨论）
        problem = None
        if msg['message_type'] == 'topic':
            problem_sql = """
                SELECT p.problem_id, p.title
                FROM message_problem mp
                INNER JOIN problem p ON mp.problem_id = p.problem_id
                WHERE mp.message_id = :message_id
            """
            problem = fetch_one(db, problem_sql, {"message_id": msg['message_id']})
        
        result.append({
            'message_id': msg['message_id'],
            'title': msg['title'],
            'content': msg['content'],
            'message_type': msg['message_type'],
            'created_at': msg['created_at'],
            'creator': sender,
            'recipients': recipients,
            'problem': problem
        })
    
    return result


@router.get("/available-recipients", response_model=List[dict])
def get_available_recipients(
    user_id: int,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取可以发送私信的用户列表（即当前用户的好友列表，排除已屏蔽的）
    支持搜索功能
    """
    # 查询所有好友（status = 'accepted'）
    sql = """
        SELECT DISTINCT u.user_id, u.username, u.school, u.avatar, u.rating
        FROM user u
        INNER JOIN friendship f ON (
            (f.user_id = :user_id AND f.friend_id = u.user_id AND f.status = 'accepted')
            OR
            (f.friend_id = :user_id AND f.user_id = u.user_id AND f.status = 'accepted')
        )
        WHERE u.user_id != :user_id
    """
    params = {"user_id": user_id}
    
    # 添加搜索条件
    if search:
        sql += " AND (u.username LIKE :search OR u.school LIKE :search)"
        params["search"] = f"%{search}%"
    
    sql += " ORDER BY u.username ASC"
    
    friends = execute_query(db, sql, params)
    return friends


@router.get("/private", response_model=List[dict])
def get_private_messages(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取用户的私信列表（作为发送者或接收者）"""
    # 获取用户相关的所有私信（发送或接收）
    sql = """
        SELECT DISTINCT m.*
        FROM message m
        LEFT JOIN message_recipient mr ON m.message_id = mr.message_id
        WHERE m.message_type = 'private'
          AND (m.creator_id = :user_id OR mr.recipient_user_id = :user_id)
        ORDER BY m.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    messages = execute_query(db, sql, {
        "user_id": user_id,
        "limit": limit,
        "offset": skip
    })
    
    # 构造响应
    result = []
    for msg in messages:
        # 获取创建者信息
        creator_sql = "SELECT user_id, username, avatar FROM user WHERE user_id = :user_id"
        creator = fetch_one(db, creator_sql, {"user_id": msg['creator_id']})
        
        # 获取接收者信息
        recipients_sql = """
            SELECT u.user_id, u.username, u.avatar
            FROM message_recipient mr
            INNER JOIN user u ON mr.recipient_user_id = u.user_id
            WHERE mr.message_id = :message_id
        """
        recipients = execute_query(db, recipients_sql, {"message_id": msg['message_id']})
        
        result.append({
            "message_id": msg['message_id'],
            "title": msg['title'],
            "content": msg['content'],
            "message_type": msg['message_type'],
            "created_at": msg['created_at'],
            "creator": creator,
            "recipients": recipients
        })
    
    return result


@router.get("/my-topics", response_model=List[dict])
def get_my_topics(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取用户发送的所有题目讨论"""
    # 验证用户存在
    user_sql = "SELECT user_id, username, avatar FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取用户发送的讨论
    messages_sql = """
        SELECT m.*, p.problem_id, p.title as problem_title
        FROM message m
        INNER JOIN message_problem mp ON m.message_id = mp.message_id
        INNER JOIN problem p ON mp.problem_id = p.problem_id
        WHERE m.creator_id = :user_id AND m.message_type = 'topic'
        ORDER BY m.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    messages = execute_query(db, messages_sql, {
        "user_id": user_id,
        "limit": limit,
        "offset": skip
    })
    
    # 构造响应
    result = []
    for msg in messages:
        result.append({
            "message_id": msg['message_id'],
            "title": msg['title'],
            "content": msg['content'],
            "message_type": msg['message_type'],
            "created_at": msg['created_at'],
            "creator": user,
            "problem": {
                "problem_id": msg['problem_id'],
                "title": msg['problem_title']
            } if msg.get('problem_id') else None
        })
    
    return result


@router.get("/topic/{problem_id}", response_model=List[dict])
def get_problem_discussions(
    problem_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取题目的讨论列表"""
    # 验证题目存在
    problem_sql = "SELECT problem_id, title FROM problem WHERE problem_id = :problem_id"
    problem = fetch_one(db, problem_sql, {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    # 获取讨论
    messages_sql = """
        SELECT m.*, u.user_id as creator_user_id, u.username as creator_username, u.avatar as creator_avatar
        FROM message m
        INNER JOIN message_problem mp ON m.message_id = mp.message_id
        INNER JOIN user u ON m.creator_id = u.user_id
        WHERE mp.problem_id = :problem_id AND m.message_type = 'topic'
        ORDER BY m.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    messages = execute_query(db, messages_sql, {
        "problem_id": problem_id,
        "limit": limit,
        "offset": skip
    })
    
    # 构造响应
    result = []
    for msg in messages:
        result.append({
            "message_id": msg['message_id'],
            "title": msg['title'],
            "content": msg['content'],
            "message_type": msg['message_type'],
            "created_at": msg['created_at'],
            "creator": {
                "user_id": msg['creator_user_id'],
                "username": msg['creator_username'],
                "avatar": msg['creator_avatar']
            },
            "problem": problem
        })
    
    return result


@router.get("/{message_id}", response_model=dict)
def get_message(message_id: int, db: Session = Depends(get_db)):
    """获取消息详情"""
    sql = "SELECT * FROM message WHERE message_id = :message_id"
    message = fetch_one(db, sql, {"message_id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    return message


@router.put("/{message_id}", response_model=dict)
def update_message(
    message_id: int,
    message_update: MessageUpdate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    更新消息（标题和内容）
    只有创建者或管理员可以编辑
    """
    # 获取消息
    msg_sql = "SELECT * FROM message WHERE message_id = :message_id"
    message = fetch_one(db, msg_sql, {"message_id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    # 验证权限
    user_sql = "SELECT role FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    is_creator = message['creator_id'] == user_id
    is_admin = user['role'] == 'admin'
    
    if not (is_creator or is_admin):
        raise HTTPException(status_code=403, detail="无权编辑此消息")
    
    # 更新消息
    update_sql = "UPDATE message SET "
    update_fields = []
    params = {"message_id": message_id}
    
    if message_update.title is not None:
        update_fields.append("title = :title")
        params["title"] = message_update.title
    
    update_fields.append("content = :content")
    params["content"] = message_update.content
    
    update_sql += ", ".join(update_fields) + " WHERE message_id = :message_id"
    execute_update(db, update_sql, params)
    
    # 获取更新后的标题
    updated_msg = fetch_one(db, "SELECT title FROM message WHERE message_id = :message_id", 
                           {"message_id": message_id})
    
    # 记录活动日志
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": user_id,
        "action_type": "update",
        "entity_type": "message",
        "entity_id": message_id,
        "description": f"编辑了消息《{updated_msg['title'] or '无标题'}》",
        "created_at": datetime.utcnow()
    })
    
    # 返回更新后的消息
    return fetch_one(db, "SELECT * FROM message WHERE message_id = :message_id", 
                    {"message_id": message_id})


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    删除消息
    - 创建者/管理员：完全删除消息
    - 接收者（私信）：只删除自己的接收记录，消息对该用户不可见
    """
    # 获取消息
    msg_sql = "SELECT * FROM message WHERE message_id = :message_id"
    message = fetch_one(db, msg_sql, {"message_id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    # 验证权限
    user_sql = "SELECT role FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 判断用户是否是接收者
    is_recipient_sql = """
        SELECT 1 FROM message_recipient 
        WHERE message_id = :message_id AND recipient_user_id = :user_id
        LIMIT 1
    """
    is_recipient = fetch_one(db, is_recipient_sql, {
        "message_id": message_id,
        "user_id": user_id
    }) is not None
    
    # 判断用户权限
    is_creator = message['creator_id'] == user_id
    is_admin = user['role'] == 'admin'
    
    if not (is_creator or is_admin or is_recipient):
        raise HTTPException(status_code=403, detail="无权删除此消息")
    
    # 如果是接收者但不是创建者/管理员，只删除接收记录
    if is_recipient and not (is_creator or is_admin):
        # 只删除该用户的接收记录
        delete_recipient_sql = """
            DELETE FROM message_recipient 
            WHERE message_id = :message_id AND recipient_user_id = :user_id
        """
        execute_update(db, delete_recipient_sql, {
            "message_id": message_id,
            "user_id": user_id
        })
        
        # 记录活动日志
        log_sql = """
            INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
            VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
        """
        execute_insert(db, log_sql, {
            "user_id": user_id,
            "action_type": "delete",
            "entity_type": "message_recipient",
            "entity_id": message_id,
            "description": f"删除了接收的私信《{message['title'] or '无标题'}》",
            "created_at": datetime.utcnow()
        })
        return None
    
    # 如果是创建者或管理员，完全删除消息
    # 删除关联数据
    delete_recipients_sql = "DELETE FROM message_recipient WHERE message_id = :message_id"
    execute_update(db, delete_recipients_sql, {"message_id": message_id})
    
    delete_problem_sql = "DELETE FROM message_problem WHERE message_id = :message_id"
    execute_update(db, delete_problem_sql, {"message_id": message_id})
    
    # 删除消息
    delete_msg_sql = "DELETE FROM message WHERE message_id = :message_id"
    execute_update(db, delete_msg_sql, {"message_id": message_id})
    
    # 记录活动日志
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": user_id,
        "action_type": "delete",
        "entity_type": "message",
        "entity_id": message_id,
        "description": f"删除了消息《{message['title'] or '无标题'}》",
        "created_at": datetime.utcnow()
    })
    
    return None
