"""
好友关系路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db, execute_query, execute_insert, execute_update, fetch_one
from app.schemas import FriendshipCreate, FriendshipResponse, FriendshipWithUser, UserBrief
from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/friendships", tags=["friendships"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def send_friend_request(
    friendship: FriendshipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送好友请求"""
    # 不能添加自己为好友
    if friendship.friend_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="不能添加自己为好友")
    
    # 检查目标用户是否存在
    friend_sql = "SELECT user_id FROM user WHERE user_id = :user_id"
    friend = fetch_one(db, friend_sql, {"user_id": friendship.friend_id})
    if not friend:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查是否已经存在好友关系
    existing_sql = """
        SELECT * FROM friendship 
        WHERE user_id = :user_id AND friend_id = :friend_id
    """
    existing = fetch_one(db, existing_sql, {
        "user_id": current_user.user_id,
        "friend_id": friendship.friend_id
    })
    
    if existing:
        if existing['status'] == 'pending':
            raise HTTPException(status_code=400, detail="已发送过好友请求，请等待对方处理")
        elif existing['status'] == 'accepted':
            raise HTTPException(status_code=400, detail="已经是好友关系")
        elif existing['status'] == 'blocked':
            raise HTTPException(status_code=400, detail="无法添加该用户为好友")
        elif existing['status'] == 'rejected':
            # 如果之前被拒绝，允许重新发送请求
            update_sql = """
                UPDATE friendship 
                SET status = 'pending', updated_at = :updated_at
                WHERE friendship_id = :friendship_id
            """
            execute_update(db, update_sql, {
                "updated_at": datetime.utcnow(),
                "friendship_id": existing['friendship_id']
            })
            return fetch_one(db, "SELECT * FROM friendship WHERE friendship_id = :friendship_id",
                           {"friendship_id": existing['friendship_id']})
    
    # 检查对方是否屏蔽了自己
    blocked_sql = """
        SELECT 1 FROM friendship 
        WHERE user_id = :friend_id AND friend_id = :user_id AND status = 'blocked'
        LIMIT 1
    """
    blocked = fetch_one(db, blocked_sql, {
        "friend_id": friendship.friend_id,
        "user_id": current_user.user_id
    })
    
    if blocked:
        raise HTTPException(status_code=400, detail="无法添加该用户为好友")
    
    # 创建好友请求
    insert_sql = """
        INSERT INTO friendship (user_id, friend_id, status, created_at, updated_at)
        VALUES (:user_id, :friend_id, :status, :created_at, :updated_at)
    """
    friendship_id = execute_insert(db, insert_sql, {
        "user_id": current_user.user_id,
        "friend_id": friendship.friend_id,
        "status": 'pending',
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    # 返回创建的好友请求
    select_sql = "SELECT * FROM friendship WHERE friendship_id = :friendship_id"
    return fetch_one(db, select_sql, {"friendship_id": friendship_id})


@router.get("/requests", response_model=List[dict])
def get_friend_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取收到的好友请求列表"""
    # 获取收到的好友请求及发送者信息
    sql = """
        SELECT 
            f.*,
            u.user_id as sender_user_id,
            u.username as sender_username,
            u.avatar as sender_avatar
        FROM friendship f
        INNER JOIN user u ON f.user_id = u.user_id
        WHERE f.friend_id = :user_id AND f.status = 'pending'
    """
    requests = execute_query(db, sql, {"user_id": current_user.user_id})
    
    # 构造响应
    result = []
    for req in requests:
        result.append({
            "friendship_id": req['friendship_id'],
            "user_id": req['user_id'],
            "friend_id": req['friend_id'],
            "status": req['status'],
            "created_at": req['created_at'],
            "updated_at": req['updated_at'],
            "user": {
                "user_id": req['sender_user_id'],
                "username": req['sender_username'],
                "avatar": req['sender_avatar']
            },
            "friend": None
        })
    
    return result


@router.get("/sent", response_model=List[dict])
def get_sent_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取发送的好友请求列表"""
    # 获取发送的好友请求及接收者信息
    sql = """
        SELECT 
            f.*,
            u.user_id as friend_user_id,
            u.username as friend_username,
            u.avatar as friend_avatar
        FROM friendship f
        INNER JOIN user u ON f.friend_id = u.user_id
        WHERE f.user_id = :user_id AND f.status = 'pending'
    """
    requests = execute_query(db, sql, {"user_id": current_user.user_id})
    
    # 构造响应
    result = []
    for req in requests:
        result.append({
            "friendship_id": req['friendship_id'],
            "user_id": req['user_id'],
            "friend_id": req['friend_id'],
            "status": req['status'],
            "created_at": req['created_at'],
            "updated_at": req['updated_at'],
            "user": None,
            "friend": {
                "user_id": req['friend_user_id'],
                "username": req['friend_username'],
                "avatar": req['friend_avatar']
            }
        })
    
    return result


@router.get("/", response_model=List[dict])
def get_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取好友列表（已接受的好友）"""
    # 获取好友列表及好友信息
    sql = """
        SELECT 
            f.*,
            u.user_id as friend_user_id,
            u.username as friend_username,
            u.avatar as friend_avatar
        FROM friendship f
        INNER JOIN user u ON f.friend_id = u.user_id
        WHERE f.user_id = :user_id AND f.status = 'accepted'
    """
    friendships = execute_query(db, sql, {"user_id": current_user.user_id})
    
    # 构造响应
    result = []
    for friendship in friendships:
        result.append({
            "friendship_id": friendship['friendship_id'],
            "user_id": friendship['user_id'],
            "friend_id": friendship['friend_id'],
            "status": friendship['status'],
            "created_at": friendship['created_at'],
            "updated_at": friendship['updated_at'],
            "user": None,
            "friend": {
                "user_id": friendship['friend_user_id'],
                "username": friendship['friend_username'],
                "avatar": friendship['friend_avatar']
            }
        })
    
    return result


@router.get("/blocked", response_model=List[dict])
def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取黑名单"""
    # 获取黑名单及用户信息
    sql = """
        SELECT 
            f.*,
            u.user_id as friend_user_id,
            u.username as friend_username,
            u.avatar as friend_avatar
        FROM friendship f
        INNER JOIN user u ON f.friend_id = u.user_id
        WHERE f.user_id = :user_id AND f.status = 'blocked'
    """
    blocked = execute_query(db, sql, {"user_id": current_user.user_id})
    
    # 构造响应
    result = []
    for friendship in blocked:
        result.append({
            "friendship_id": friendship['friendship_id'],
            "user_id": friendship['user_id'],
            "friend_id": friendship['friend_id'],
            "status": friendship['status'],
            "created_at": friendship['created_at'],
            "updated_at": friendship['updated_at'],
            "user": None,
            "friend": {
                "user_id": friendship['friend_user_id'],
                "username": friendship['friend_username'],
                "avatar": friendship['friend_avatar']
            }
        })
    
    return result


@router.put("/{friendship_id}/accept", response_model=dict)
def accept_friend_request(
    friendship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """接受好友请求"""
    # 查找好友请求
    check_sql = """
        SELECT * FROM friendship 
        WHERE friendship_id = :friendship_id 
          AND friend_id = :user_id 
          AND status = 'pending'
    """
    friendship = fetch_one(db, check_sql, {
        "friendship_id": friendship_id,
        "user_id": current_user.user_id
    })
    
    if not friendship:
        raise HTTPException(status_code=404, detail="好友请求不存在或已处理")
    
    # 更新为已接受
    update_sql = """
        UPDATE friendship 
        SET status = 'accepted', updated_at = :updated_at
        WHERE friendship_id = :friendship_id
    """
    execute_update(db, update_sql, {
        "updated_at": datetime.utcnow(),
        "friendship_id": friendship_id
    })
    
    # 检查是否已有反向好友关系
    reverse_sql = """
        SELECT * FROM friendship 
        WHERE user_id = :user_id AND friend_id = :friend_id
    """
    reverse_friendship = fetch_one(db, reverse_sql, {
        "user_id": current_user.user_id,
        "friend_id": friendship['user_id']
    })
    
    if reverse_friendship:
        # 更新反向关系为已接受
        update_reverse_sql = """
            UPDATE friendship 
            SET status = 'accepted', updated_at = :updated_at
            WHERE friendship_id = :friendship_id
        """
        execute_update(db, update_reverse_sql, {
            "updated_at": datetime.utcnow(),
            "friendship_id": reverse_friendship['friendship_id']
        })
    else:
        # 创建反向好友关系
        insert_reverse_sql = """
            INSERT INTO friendship (user_id, friend_id, status, created_at, updated_at)
            VALUES (:user_id, :friend_id, :status, :created_at, :updated_at)
        """
        execute_insert(db, insert_reverse_sql, {
            "user_id": current_user.user_id,
            "friend_id": friendship['user_id'],
            "status": 'accepted',
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    # 返回更新后的好友请求
    return fetch_one(db, "SELECT * FROM friendship WHERE friendship_id = :friendship_id",
                    {"friendship_id": friendship_id})


@router.put("/{friendship_id}/reject", response_model=dict)
def reject_friend_request(
    friendship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """拒绝好友请求"""
    # 查找好友请求
    check_sql = """
        SELECT * FROM friendship 
        WHERE friendship_id = :friendship_id 
          AND friend_id = :user_id 
          AND status = 'pending'
    """
    friendship = fetch_one(db, check_sql, {
        "friendship_id": friendship_id,
        "user_id": current_user.user_id
    })
    
    if not friendship:
        raise HTTPException(status_code=404, detail="好友请求不存在或已处理")
    
    # 更新为已拒绝
    update_sql = """
        UPDATE friendship 
        SET status = 'rejected', updated_at = :updated_at
        WHERE friendship_id = :friendship_id
    """
    execute_update(db, update_sql, {
        "updated_at": datetime.utcnow(),
        "friendship_id": friendship_id
    })
    
    # 返回更新后的好友请求
    return fetch_one(db, "SELECT * FROM friendship WHERE friendship_id = :friendship_id",
                    {"friendship_id": friendship_id})


@router.delete("/{friendship_id}")
def delete_friend(
    friendship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除好友关系"""
    # 查找好友关系
    check_sql = """
        SELECT * FROM friendship 
        WHERE friendship_id = :friendship_id AND user_id = :user_id
    """
    friendship = fetch_one(db, check_sql, {
        "friendship_id": friendship_id,
        "user_id": current_user.user_id
    })
    
    if not friendship:
        raise HTTPException(status_code=404, detail="好友关系不存在")
    
    friend_id = friendship['friend_id']
    
    # 删除双向好友关系（无论什么状态）
    # 删除当前用户的关系
    delete_sql = "DELETE FROM friendship WHERE friendship_id = :friendship_id"
    execute_update(db, delete_sql, {"friendship_id": friendship_id})
    
    # 删除对方的关系（如果存在）
    delete_reverse_sql = """
        DELETE FROM friendship 
        WHERE user_id = :friend_id AND friend_id = :user_id
    """
    rows_affected = execute_update(db, delete_reverse_sql, {
        "friend_id": friend_id,
        "user_id": current_user.user_id
    })
    
    if rows_affected > 0:
        return {"message": "好友关系已删除（双向）"}
    else:
        return {"message": "好友关系已删除"}


@router.post("/block/{user_id}")
def block_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """直接屏蔽某个用户（通过user_id）"""
    # 不能屏蔽自己
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="不能屏蔽自己")
    
    # 检查目标用户是否存在
    user_sql = "SELECT user_id FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查是否已经存在关系
    existing_sql = """
        SELECT * FROM friendship 
        WHERE user_id = :user_id AND friend_id = :friend_id
    """
    existing = fetch_one(db, existing_sql, {
        "user_id": current_user.user_id,
        "friend_id": user_id
    })
    
    if existing:
        if existing['status'] == 'blocked':
            raise HTTPException(status_code=400, detail="已经屏蔽该用户")
        
        # 更新为已屏蔽
        update_sql = """
            UPDATE friendship 
            SET status = 'blocked', updated_at = :updated_at
            WHERE friendship_id = :friendship_id
        """
        execute_update(db, update_sql, {
            "updated_at": datetime.utcnow(),
            "friendship_id": existing['friendship_id']
        })
        
        return {
            "message": "用户已屏蔽",
            "friendship_id": existing['friendship_id']
        }
    else:
        # 创建屏蔽关系
        insert_sql = """
            INSERT INTO friendship (user_id, friend_id, status, created_at, updated_at)
            VALUES (:user_id, :friend_id, :status, :created_at, :updated_at)
        """
        friendship_id = execute_insert(db, insert_sql, {
            "user_id": current_user.user_id,
            "friend_id": user_id,
            "status": 'blocked',
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        return {
            "message": "用户已屏蔽",
            "friendship_id": friendship_id
        }


@router.put("/{friendship_id}/block")
def block_user(
    friendship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """屏蔽用户（通过friendship_id）"""
    # 查找关系
    check_sql = """
        SELECT * FROM friendship 
        WHERE friendship_id = :friendship_id AND user_id = :user_id
    """
    friendship = fetch_one(db, check_sql, {
        "friendship_id": friendship_id,
        "user_id": current_user.user_id
    })
    
    if not friendship:
        raise HTTPException(status_code=404, detail="关系不存在")
    
    # 更新为已屏蔽
    update_sql = """
        UPDATE friendship 
        SET status = 'blocked', updated_at = :updated_at
        WHERE friendship_id = :friendship_id
    """
    execute_update(db, update_sql, {
        "updated_at": datetime.utcnow(),
        "friendship_id": friendship_id
    })
    
    return {"message": "用户已屏蔽"}


@router.put("/{friendship_id}/unblock")
def unblock_user(
    friendship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消屏蔽用户"""
    # 查找屏蔽关系
    check_sql = """
        SELECT * FROM friendship 
        WHERE friendship_id = :friendship_id 
          AND user_id = :user_id 
          AND status = 'blocked'
    """
    friendship = fetch_one(db, check_sql, {
        "friendship_id": friendship_id,
        "user_id": current_user.user_id
    })
    
    if not friendship:
        raise HTTPException(status_code=404, detail="屏蔽关系不存在")
    
    friend_id = friendship['friend_id']
    
    # 检查对方是否也有指向我的好友关系（双向好友）
    reverse_sql = """
        SELECT * FROM friendship 
        WHERE user_id = :friend_id 
          AND friend_id = :user_id 
          AND status = 'accepted'
    """
    reverse_friendship = fetch_one(db, reverse_sql, {
        "friend_id": friend_id,
        "user_id": current_user.user_id
    })
    
    if reverse_friendship:
        # 对方还保持着好友关系，恢复为accepted（好友）
        update_sql = """
            UPDATE friendship 
            SET status = 'accepted', updated_at = :updated_at
            WHERE friendship_id = :friendship_id
        """
        execute_update(db, update_sql, {
            "updated_at": datetime.utcnow(),
            "friendship_id": friendship_id
        })
        return {"message": "已取消屏蔽，好友关系已恢复"}
    else:
        # 没有双向好友关系，直接删除屏蔽记录
        delete_sql = "DELETE FROM friendship WHERE friendship_id = :friendship_id"
        execute_update(db, delete_sql, {"friendship_id": friendship_id})
        return {"message": "已取消屏蔽"}
