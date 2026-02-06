from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import List, Optional
import os
import shutil
from pathlib import Path

from app.database import get_db, execute_query, execute_insert, execute_update, fetch_one
from app.schemas import UserCreate, UserResponse, LoginRequest, Token, UserUpdate
from app.auth import verify_password, get_password_hash, create_access_token, get_current_user
from app.config import get_settings

router = APIRouter(prefix="/api/users", tags=["users"])
settings = get_settings()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否存在（原生SQL）
    check_username_sql = "SELECT user_id FROM user WHERE username = :username"
    existing_user = fetch_one(db, check_username_sql, {"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 检查邮箱是否存在（原生SQL）
    check_email_sql = "SELECT user_id FROM user WHERE email = :email"
    existing_email = fetch_one(db, check_email_sql, {"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 确定用户角色：如果提供了正确的管理员注册码，则注册为管理员
    user_role = 'user'
    if user.admin_code:
        if user.admin_code == settings.ADMIN_REGISTER_CODE:
            user_role = 'admin'
        else:
            raise HTTPException(status_code=400, detail="管理员注册码错误")
    
    # 创建新用户（原生SQL INSERT）
    hashed_password = get_password_hash(user.password)
    insert_user_sql = """
        INSERT INTO user (username, password, email, school, rating, created_at, role)
        VALUES (:username, :password, :email, :school, :rating, :created_at, :role)
    """
    user_id = execute_insert(db, insert_user_sql, {
        "username": user.username,
        "password": hashed_password,
        "email": user.email,
        "school": user.school,
        "rating": 0,
        "created_at": datetime.utcnow(),
        "role": user_role
    })
    
    # 记录活动日志（原生SQL）
    insert_log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, insert_log_sql, {
        "user_id": user_id,
        "action_type": "create",
        "entity_type": "user",
        "entity_id": user_id,
        "description": f"用户 {user.username} 注册了账号",
        "created_at": datetime.utcnow()
    })
    
    # 查询刚创建的用户返回（原生SQL）
    select_user_sql = "SELECT * FROM user WHERE user_id = :user_id"
    db_user = fetch_one(db, select_user_sql, {"user_id": user_id})
    
    return db_user


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    # 查询用户（原生SQL）
    # 支持用户名或邮箱登录：如果输入中包含 '@' 则按邮箱查找，否则按用户名查找
    if '@' in login_data.username:
        select_user_sql = "SELECT * FROM user WHERE email = :identifier"
        user = fetch_one(db, select_user_sql, {"identifier": login_data.username})
    else:
        select_user_sql = "SELECT * FROM user WHERE username = :identifier"
        user = fetch_one(db, select_user_sql, {"identifier": login_data.username})
    
    if not user or not verify_password(login_data.password, user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username'], "role": user['role']}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user['user_id'],
        "username": user['username'],
        "role": user['role']
    }


@router.get("/me", response_model=dict)
def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前登录用户信息"""
    sql = "SELECT * FROM user WHERE user_id = :user_id"
    user = fetch_one(db, sql, {"user_id": current_user.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.get("/", response_model=List[dict])
def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[str] = None,
    sort_by: str = "created_at",  # created_at, username, rating
    order: str = "desc",  # asc, desc
    db: Session = Depends(get_db)
):
    """获取用户列表（支持搜索、筛选、排序）"""
    # 构建SQL查询
    sql = "SELECT * FROM user WHERE 1=1"
    params = {}
    
    # 搜索条件
    if search:
        sql += " AND (username LIKE :search OR email LIKE :search OR school LIKE :search)"
        params["search"] = f"%{search}%"
    
    # 角色筛选
    if role:
        sql += " AND role = :role"
        params["role"] = role
    
    # 排序
    if sort_by == "created_at":
        sql += f" ORDER BY created_at {order.upper()}"
    elif sort_by == "username":
        sql += f" ORDER BY username {order.upper()}"
    elif sort_by == "rating":
        sql += f" ORDER BY rating {order.upper()}"
    
    # 分页
    sql += " LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = skip
    
    users = execute_query(db, sql, params)
    return users


@router.get("/{user_id}", response_model=dict)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取单个用户信息"""
    sql = "SELECT * FROM user WHERE user_id = :user_id"
    user = fetch_one(db, sql, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, admin_id: Optional[int] = None, db: Session = Depends(get_db)):
    """删除用户（管理员）- 级联删除所有相关数据"""
    # 查询用户是否存在
    check_user_sql = "SELECT username, role FROM user WHERE user_id = :user_id"
    user = fetch_one(db, check_user_sql, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 防止删除管理员
    if user['role'] == 'admin':
        raise HTTPException(status_code=403, detail="不能删除管理员账户")
    
    username = user['username']
    
    # 级联删除相关数据（使用原生SQL）
    # 由于设置了外键级联删除，直接删除用户即可
    # 但为了更清晰，我们手动处理每个关联
    
    # 1. 获取用户的所有提交ID
    get_submissions_sql = """
        SELECT submission_id FROM user_submission WHERE user_id = :user_id
    """
    submission_ids = execute_query(db, get_submissions_sql, {"user_id": user_id})
    submission_id_list = [s['submission_id'] for s in submission_ids]
    
    # 2. 删除 user_submission 关联
    delete_user_submission_sql = "DELETE FROM user_submission WHERE user_id = :user_id"
    execute_update(db, delete_user_submission_sql, {"user_id": user_id})
    
    # 3. 删除 submission 记录
    if submission_id_list:
        # 将submission_id列表转换为字符串用于IN语句
        ids_str = ','.join(map(str, submission_id_list))
        delete_submissions_sql = f"DELETE FROM submission WHERE submission_id IN ({ids_str})"
        execute_update(db, delete_submissions_sql, {})
    
    # 4. 删除比赛参与记录
    delete_contest_user_sql = "DELETE FROM contest_user WHERE user_id = :user_id"
    execute_update(db, delete_contest_user_sql, {"user_id": user_id})
    
    # 5. 删除消息接收记录
    delete_message_recipient_sql = "DELETE FROM message_recipient WHERE recipient_user_id = :user_id"
    execute_update(db, delete_message_recipient_sql, {"user_id": user_id})
    
    # 6. 获取用户创建的消息ID
    get_messages_sql = "SELECT message_id FROM message WHERE creator_id = :user_id"
    message_ids = execute_query(db, get_messages_sql, {"user_id": user_id})
    message_id_list = [m['message_id'] for m in message_ids]
    
    # 7. 删除消息相关联
    if message_id_list:
        ids_str = ','.join(map(str, message_id_list))
        delete_message_problem_sql = f"DELETE FROM message_problem WHERE message_id IN ({ids_str})"
        execute_update(db, delete_message_problem_sql, {})
        
        delete_msg_recipient_sql = f"DELETE FROM message_recipient WHERE message_id IN ({ids_str})"
        execute_update(db, delete_msg_recipient_sql, {})
    
    # 8. 删除用户创建的消息
    delete_messages_sql = "DELETE FROM message WHERE creator_id = :user_id"
    execute_update(db, delete_messages_sql, {"user_id": user_id})
    
    # 9. 删除好友关系
    delete_friendships_sql = "DELETE FROM friendship WHERE user_id = :user_id OR friend_id = :user_id"
    execute_update(db, delete_friendships_sql, {"user_id": user_id})
    
    # 10. 删除活动日志（可选，保留用户的历史记录）
    # delete_activity_logs_sql = "DELETE FROM activity_log WHERE user_id = :user_id"
    # execute_update(db, delete_activity_logs_sql, {"user_id": user_id})
    
    # 11. 最后删除用户本身
    delete_user_sql = "DELETE FROM user WHERE user_id = :user_id"
    execute_update(db, delete_user_sql, {"user_id": user_id})
    
    # 12. 记录活动日志
    if admin_id:
        admin_sql = "SELECT username FROM user WHERE user_id = :admin_id"
        admin = fetch_one(db, admin_sql, {"admin_id": admin_id})
        admin_name = admin['username'] if admin else "管理员"
        
        log_sql = """
            INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
            VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
        """
        execute_insert(db, log_sql, {
            "user_id": admin_id,
            "action_type": "delete",
            "entity_type": "user",
            "entity_id": user_id,
            "description": f"{admin_name} 删除了用户 {username}",
            "created_at": datetime.utcnow()
        })
    
    return None


@router.put("/{user_id}", response_model=dict)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """更新用户信息"""
    # 查询用户是否存在
    check_user_sql = "SELECT * FROM user WHERE user_id = :user_id"
    user = fetch_one(db, check_user_sql, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    update_fields = []
    params = {"user_id": user_id}
    
    # 检查用户名是否被其他用户占用
    if user_update.username and user_update.username != user['username']:
        check_username_sql = "SELECT user_id FROM user WHERE username = :username AND user_id != :user_id"
        existing_user = fetch_one(db, check_username_sql, {"username": user_update.username, "user_id": user_id})
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")
        update_fields.append("username = :username")
        params["username"] = user_update.username
    
    # 检查邮箱是否被其他用户占用
    if user_update.email and user_update.email != user['email']:
        check_email_sql = "SELECT user_id FROM user WHERE email = :email AND user_id != :user_id"
        existing_user = fetch_one(db, check_email_sql, {"email": user_update.email, "user_id": user_id})
        if existing_user:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        update_fields.append("email = :email")
        params["email"] = user_update.email
    
    # 更新学校信息
    if user_update.school is not None:
        update_fields.append("school = :school")
        params["school"] = user_update.school
    
    # 如果要修改密码，需要验证当前密码
    if user_update.password and user_update.current_password:
        if not verify_password(user_update.current_password, user['password']):
            raise HTTPException(status_code=400, detail="当前密码错误")
        update_fields.append("password = :password")
        params["password"] = get_password_hash(user_update.password)
    
    # 执行更新
    if update_fields:
        update_sql = f"UPDATE user SET {', '.join(update_fields)} WHERE user_id = :user_id"
        execute_update(db, update_sql, params)
    
    # 返回更新后的用户信息
    updated_user = fetch_one(db, check_user_sql, {"user_id": user_id})
    return updated_user


@router.get("/{user_id}/stats", response_model=dict)
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    """
    返回用户相关统计：提交总数、通过题目数、参与比赛数
    """
    # 提交总数（通过 user_submission 关联表）
    subs_sql = "SELECT COUNT(*) as cnt FROM user_submission WHERE user_id = :user_id"
    subs_res = fetch_one(db, subs_sql, {"user_id": user_id})
    total_submissions = subs_res['cnt'] if subs_res else 0

    # 参与比赛数
    contest_sql = "SELECT COUNT(*) as cnt FROM contest_user WHERE user_id = :user_id"
    contest_res = fetch_one(db, contest_sql, {"user_id": user_id})
    contest_count = contest_res['cnt'] if contest_res else 0

    # 通过题目数：按 submission.status 为 Accepted 或 accepted 统计去重 problem_id
    solved_sql = """
        SELECT COUNT(DISTINCT s.problem_id) as cnt
        FROM submission s
        INNER JOIN user_submission us ON s.submission_id = us.submission_id
        WHERE us.user_id = :user_id AND (s.status = 'Accepted' OR s.status = 'accepted')
    """
    solved_res = fetch_one(db, solved_sql, {"user_id": user_id})
    solved_problems = solved_res['cnt'] if solved_res else 0

    return {
        "totalSubmissions": total_submissions,
        "solvedProblems": solved_problems,
        "contestCount": contest_count
    }


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传用户头像"""
    user_id = current_user.user_id
    
    # 查询用户
    check_user_sql = "SELECT avatar FROM user WHERE user_id = :user_id"
    user = fetch_one(db, check_user_sql, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证文件类型
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="只能上传图片文件")
    
    # 创建上传目录
    upload_dir = Path("uploads/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    file_extension = Path(file.filename).suffix
    new_filename = f"user_{user_id}{file_extension}"
    file_path = upload_dir / new_filename
    
    # 如果用户已有头像，删除旧文件
    if user['avatar']:
        old_file_path = Path(user['avatar'].lstrip("/"))
        if old_file_path.exists():
            try:
                old_file_path.unlink()
            except Exception as e:
                print(f"删除旧头像失败: {e}")
    
    # 保存文件
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 更新用户头像URL（原生SQL）
    avatar_url = f"/uploads/avatars/{new_filename}"
    update_avatar_sql = "UPDATE user SET avatar = :avatar WHERE user_id = :user_id"
    execute_update(db, update_avatar_sql, {"avatar": avatar_url, "user_id": user_id})
    
    return {"avatar_url": avatar_url, "message": "头像上传成功"}
