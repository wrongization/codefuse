from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db, execute_query, execute_insert, execute_update, fetch_one, SessionLocal
from app.schemas import (
    SubmissionCreate, SubmissionResponse, SubmissionUpdate, 
    SubmissionDetailResponse, JudgeResultResponse
)
from app.judge_worker import submit_submission_judge
from app.judge_runner import run_submission_judge

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def ensure_problem_submission_table(db: Session):
    """确保 problem_submission 联系表存在。"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS problem_submission (
            problem_id INT NOT NULL,
            submission_id INT NOT NULL,
            PRIMARY KEY (problem_id, submission_id),
            INDEX idx_problem_submission_submission (submission_id),
            CONSTRAINT fk_problem_submission_problem FOREIGN KEY (problem_id)
                REFERENCES problem(problem_id) ON DELETE CASCADE,
            CONSTRAINT fk_problem_submission_submission FOREIGN KEY (submission_id)
                REFERENCES submission(submission_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    # 使用 execute_update 以便兼容 DDL（返回值可忽略）
    execute_update(db, create_sql, {})


def link_problem_submission(db: Session, problem_id: int, submission_id: int):
    """为提交建立题目-提交关系，重复插入自动忽略。"""
    try:
        ensure_problem_submission_table(db)
        link_sql = """
            INSERT IGNORE INTO problem_submission (problem_id, submission_id)
            VALUES (:problem_id, :submission_id)
        """
        execute_update(db, link_sql, {"problem_id": problem_id, "submission_id": submission_id})
    except Exception as e:
        # 不中断主流程，但记录日志便于排查
        print(f"[problem_submission] link failed for problem {problem_id}, submission {submission_id}: {e}")


def backfill_problem_submission(db: Session, problem_id: int):
    """当关系表缺失记录时，从 submission 表回填 problem_submission。"""
    ensure_problem_submission_table(db)
    has_link = fetch_one(db, "SELECT 1 FROM problem_submission WHERE problem_id = :problem_id LIMIT 1", {"problem_id": problem_id})
    if has_link:
        return
    # 回退到遍历 submission 表，并将缺失的映射补齐
    existing_submissions = execute_query(db, "SELECT submission_id FROM submission WHERE problem_id = :problem_id", {"problem_id": problem_id})
    for sub in existing_submissions:
        try:
            link_problem_submission(db, problem_id, sub["submission_id"])
        except Exception as e:
            print(f"[problem_submission] backfill failed for submission {sub['submission_id']}: {e}")


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_submission(
    submission: SubmissionCreate, 
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """创建提交记录并自动评测"""
    # 检查题目是否存在（原生SQL）
    check_sql = "SELECT problem_id, title FROM problem WHERE problem_id = :problem_id"
    problem = fetch_one(db, check_sql, {"problem_id": submission.problem_id})
    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    # 如果指定了同步提交的用户，先验证权限与约束
    sync_with = submission.sync_with or []
    if sync_with:
        # 确保提交者和每个同步用户是已接受的好友关系
        for collab_id in sync_with:
            # 不能同步给自己
            if collab_id == user_id:
                raise HTTPException(status_code=400, detail="不能将提交同步给自己")
            friend_check_sql = """
                SELECT 1 FROM friendship
                WHERE ((user_id = :user_id AND friend_id = :collab_id)
                       OR (user_id = :collab_id AND friend_id = :user_id))
                  AND status = 'accepted' LIMIT 1
            """
            is_friend = fetch_one(db, friend_check_sql, {"user_id": user_id, "collab_id": collab_id})
            if not is_friend:
                raise HTTPException(status_code=400, detail=f"用户 {collab_id} 不是你的好友，无法同步提交")
        # 如果是比赛题目，确保每个同步用户也报名了该比赛
        if submission.contest_id:
            for collab_id in sync_with:
                cu_check_sql = "SELECT 1 FROM contest_user WHERE contest_id = :contest_id AND user_id = :user_id LIMIT 1"
                in_contest = fetch_one(db, cu_check_sql, {"contest_id": submission.contest_id, "user_id": collab_id})
                if not in_contest:
                    raise HTTPException(status_code=400, detail=f"用户 {collab_id} 未报名该比赛，无法同步提交")
    
    # 创建初始提交记录（状态为 judging）
    insert_sql = """
        INSERT INTO submission (
            problem_id, contest_id, code, language, status, exec_time, exec_memory, submitted_at
        ) VALUES (
            :problem_id, :contest_id, :code, :language, :status, :exec_time, :exec_memory, :submitted_at
        )
    """
    submission_id = execute_insert(db, insert_sql, {
        "problem_id": submission.problem_id,
        "contest_id": submission.contest_id,
        "code": submission.code,
        "language": submission.language,
        "status": 'judging',
        "exec_time": 0,
        "exec_memory": 0,
        "submitted_at": datetime.utcnow()
    })

    # 记录题目-提交关系
    link_problem_submission(db, submission.problem_id, submission_id)
    
    # 创建用户-提交关联
    user_sub_sql = """
        INSERT INTO user_submission (user_id, submission_id)
        VALUES (:user_id, :submission_id)
    """
    execute_insert(db, user_sub_sql, {
        "user_id": user_id,
        "submission_id": submission_id
    })

    # 为同步用户创建完全相同的提交记录（如果有）
    created_collab_submissions = []
    if sync_with:
        for collab_id in sync_with:
            collab_sub_id = execute_insert(db, insert_sql, {
                "problem_id": submission.problem_id,
                "contest_id": submission.contest_id,
                "code": submission.code,
                "language": submission.language,
                "status": 'judging',
                "exec_time": 0,
                "exec_memory": 0,
                "submitted_at": datetime.utcnow()
            })
            execute_insert(db, user_sub_sql, {
                "user_id": collab_id,
                "submission_id": collab_sub_id
            })
            link_problem_submission(db, submission.problem_id, collab_sub_id)
            created_collab_submissions.append((collab_id, collab_sub_id))
    
    # 开始评测：先评测发起者提交，再评测同步的提交（如果有）
    try:
        # 将主提交也改为异步：提交到线程池并立即返回（submission.status 已为 'judging'）
        background_tasks.add_task(_background_judge, submission_id)
        # 将协作用户的评测异步化，减少 HTTP 响应延迟
        for collab_id, collab_sub_id in created_collab_submissions:
            # 使用 BackgroundTasks 触发将任务提交到线程池（非阻塞）
            background_tasks.add_task(_background_judge, collab_sub_id)
    except Exception as e:
        # 评测失败，更新状态
        update_sql = """
            UPDATE submission 
            SET status = :status, exec_time = :exec_time, exec_memory = :exec_memory
            WHERE submission_id = :submission_id
        """
        execute_update(db, update_sql, {
            "status": 'system_error',
            "exec_time": 0,
            "exec_memory": 0,
            "submission_id": submission_id
        })
        raise HTTPException(
            status_code=500,
            detail=f"评测失败: {str(e)}"
        )
    
    # 记录活动日志：主提交与每个协作提交都记录为各自用户的提交行为
    user_sql = "SELECT username FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    username = user['username'] if user else "未知用户"

    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": user_id,
        "action_type": "submit",
        "entity_type": "submission",
        "entity_id": submission_id,
        "description": f"用户 {username} 提交了题目《{problem['title']}》",
        "created_at": datetime.utcnow()
    })
    # 记录协作用户的提交日志（同时说明是由谁同步）
    for collab_id, collab_sub_id in created_collab_submissions:
        collab_user = fetch_one(db, user_sql, {"user_id": collab_id})
        collab_username = collab_user['username'] if collab_user else f"用户#{collab_id}"
        execute_insert(db, log_sql, {
            "user_id": collab_id,
            "action_type": "submit",
            "entity_type": "submission",
            "entity_id": collab_sub_id,
            "description": f"用户 {collab_username} 由 {username} 同步提交了题目《{problem['title']}》",
            "created_at": datetime.utcnow()
        })
    
    # 返回创建的提交记录及 task id（这里使用 submission_id 作为 task id）
    select_sql = "SELECT * FROM submission WHERE submission_id = :submission_id"
    db_submission = fetch_one(db, select_sql, {"submission_id": submission_id})
    return {"submission": db_submission, "task_id": submission_id}


@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_submission_from_file(
    file: UploadFile = File(...),
    problem_id: int = Form(...),
    language: str = Form(...),
    contest_id: Optional[int] = Form(None),
    user_id: int = Form(...),
    sync_with: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """从本地文件上传代码并创建提交"""
    # 检查题目是否存在
    check_sql = "SELECT problem_id, title FROM problem WHERE problem_id = :problem_id"
    problem = fetch_one(db, check_sql, {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    # 验证语言
    supported_languages = ['c', 'cpp', 'python', 'java']
    if language.lower() not in supported_languages:
        raise HTTPException(status_code=400, detail=f"不支持的语言: {language}")
    
    # 读取文件内容
    try:
        content = await file.read()
        code = content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取文件失败: {str(e)}")
    
    # 验证代码不为空
    if not code.strip():
        raise HTTPException(status_code=400, detail="代码内容不能为空")

    # 解析并验证 sync_with（如果有）——前端会以 JSON 字符串传递列表
    try:
        sync_list = json.loads(sync_with) if sync_with else []
        if not isinstance(sync_list, list):
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="sync_with 参数格式不正确，应为 JSON 数组")
    # 验证好友关系和比赛报名（和 create_submission 中相同的约束）
    if sync_list:
        for collab_id in sync_list:
            if collab_id == user_id:
                raise HTTPException(status_code=400, detail="不能将提交同步给自己")
            friend_check_sql = """
                SELECT 1 FROM friendship
                WHERE ((user_id = :user_id AND friend_id = :collab_id)
                       OR (user_id = :collab_id AND friend_id = :user_id))
                  AND status = 'accepted' LIMIT 1
            """
            is_friend = fetch_one(db, friend_check_sql, {"user_id": user_id, "collab_id": collab_id})
            if not is_friend:
                raise HTTPException(status_code=400, detail=f"用户 {collab_id} 不是你的好友，无法同步提交")
        if contest_id:
            for collab_id in sync_list:
                cu_check_sql = "SELECT 1 FROM contest_user WHERE contest_id = :contest_id AND user_id = :user_id LIMIT 1"
                in_contest = fetch_one(db, cu_check_sql, {"contest_id": contest_id, "user_id": collab_id})
                if not in_contest:
                    raise HTTPException(status_code=400, detail=f"用户 {collab_id} 未报名该比赛，无法同步提交")
    
    # 创建提交记录
    insert_sql = """
        INSERT INTO submission (
            problem_id, contest_id, code, language, status, exec_time, exec_memory, submitted_at
        ) VALUES (
            :problem_id, :contest_id, :code, :language, :status, :exec_time, :exec_memory, :submitted_at
        )
    """
    submission_id = execute_insert(db, insert_sql, {
        "problem_id": problem_id,
        "contest_id": contest_id,
        "code": code,
        "language": language,
        "status": 'judging',
        "exec_time": 0,
        "exec_memory": 0,
        "submitted_at": datetime.utcnow()
    })

    # 记录题目-提交关系
    link_problem_submission(db, problem_id, submission_id)
    
    # 创建用户-提交关联
    user_sub_sql = """
        INSERT INTO user_submission (user_id, submission_id)
        VALUES (:user_id, :submission_id)
    """
    execute_insert(db, user_sub_sql, {
        "user_id": user_id,
        "submission_id": submission_id
    })

    # 为同步用户创建提交并关联
    created_collab_submissions = []
    if sync_list:
        for collab_id in sync_list:
            collab_sub_id = execute_insert(db, insert_sql, {
                "problem_id": problem_id,
                "contest_id": contest_id,
                "code": code,
                "language": language,
                "status": 'judging',
                "exec_time": 0,
                "exec_memory": 0,
                "submitted_at": datetime.utcnow()
            })
            execute_insert(db, user_sub_sql, {
                "user_id": collab_id,
                "submission_id": collab_sub_id
            })
            link_problem_submission(db, problem_id, collab_sub_id)
            created_collab_submissions.append((collab_id, collab_sub_id))
    
    # 开始评测
    try:
        # 将主提交改为异步：提交到线程池并立即返回
        if background_tasks is not None:
            background_tasks.add_task(_background_judge, submission_id)
        else:
            # 兼容没有 BackgroundTasks 的调用方式，直接提交到线程池
            submit_submission_judge(submission_id)

        # 协作提交异步评测
        if background_tasks is not None:
            for collab_id, collab_sub_id in created_collab_submissions:
                background_tasks.add_task(_background_judge, collab_sub_id)
        else:
            for collab_id, collab_sub_id in created_collab_submissions:
                try:
                    submit_submission_judge(collab_sub_id)
                except Exception as e:
                    print(f"协作用户 {collab_id} 的评测任务提交失败: {e}")
    except Exception as e:
        # 评测失败，更新状态
        update_sql = """
            UPDATE submission 
            SET status = :status, exec_time = :exec_time, exec_memory = :exec_memory
            WHERE submission_id = :submission_id
        """
        execute_update(db, update_sql, {
            "status": 'system_error',
            "exec_time": 0,
            "exec_memory": 0,
            "submission_id": submission_id
        })
        raise HTTPException(
            status_code=500,
            detail=f"评测失败: {str(e)}"
        )
    
    # 记录活动日志
    user_sql = "SELECT username FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    username = user['username'] if user else "未知用户"
    
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": user_id,
        "action_type": "submit",
        "entity_type": "submission",
        "entity_id": submission_id,
        "description": f"用户 {username} 通过文件上传提交了题目《{problem['title']}》",
        "created_at": datetime.utcnow()
    })
    
    # 返回创建的提交记录及 task id（使用 submission_id 作为 task id）
    select_sql = "SELECT * FROM submission WHERE submission_id = :submission_id"
    db_submission = fetch_one(db, select_sql, {"submission_id": submission_id})
    return {"submission": db_submission, "task_id": submission_id}


def judge_submission(submission_id: int, db: Session):
    """
    评测提交
    
    Args:
        submission_id: 提交ID
        db: 数据库会话
    """
    # 获取提交记录（原生SQL）
    sub_sql = "SELECT * FROM submission WHERE submission_id = :submission_id"
    submission = fetch_one(db, sub_sql, {"submission_id": submission_id})
    if not submission:
        raise ValueError("提交记录不存在")
    
    # 获取题目信息
    prob_sql = "SELECT * FROM problem WHERE problem_id = :problem_id"
    problem = fetch_one(db, prob_sql, {"problem_id": submission['problem_id']})
    if not problem:
        raise ValueError("题目不存在")
    
    # 获取测试点（从 JSON 字段）
    test_cases = json.loads(problem['test_cases']) if problem['test_cases'] else []
    
    if not test_cases:
        # 没有测试用例，直接标记为 accepted（兼容旧题目）
        update_sql = """
            UPDATE submission 
            SET status = :status, exec_time = :exec_time, exec_memory = :exec_memory
            WHERE submission_id = :submission_id
        """
        execute_update(db, update_sql, {
            "status": 'accepted',
            "exec_time": 0,
            "exec_memory": 0,
            "submission_id": submission_id
        })
        return
    
    # 调用共享的评测 runner（使用当前请求提供的 db 会话同步运行）
    run_submission_judge(submission_id, db=db)


def _background_judge(submission_id: int):
    """Background wrapper used with FastAPI BackgroundTasks.

    This function will enqueue the actual judging work into the global thread pool so
    multiple submissions can be judged concurrently. It returns immediately after
    scheduling the task. Any exceptions inside worker threads are captured by the
    ThreadPoolExecutor and printed there.
    """
    try:
        future = submit_submission_judge(submission_id)
        # Optionally attach a callback to log exceptions
        def _cb(f):
            try:
                _ = f.result()
            except Exception as e:
                print(f"Background judge task for submission {submission_id} failed: {e}")
        future.add_done_callback(_cb)
    except Exception as e:
        print(f"Failed to submit background judge for submission {submission_id}: {e}")


@router.get('/worker_stats', response_model=dict)
def get_worker_stats():
    """Return statistics about the judge thread pool (running/pending/max_workers)."""
    try:
        from app.judge_worker import get_stats
        return get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/", response_model=List[dict])
def get_submissions(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    problem_id: Optional[int] = None,
    contest_id: Optional[int] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    sort_by: str = "submitted_at",  # submitted_at, exec_time, exec_memory
    order: str = "desc",  # asc, desc
    db: Session = Depends(get_db)
):
    """
    获取提交记录列表（支持筛选、排序）
    
    - contest_id: 如果指定，只返回该比赛的提交；如果为 None，返回所有提交
    - 传递 contest_id=-1 可以专门筛选题库（非比赛）的提交
    """
    params = {"limit": limit, "offset": skip}
    where_clauses = []

    use_problem_relation = problem_id is not None
    join_clause = """
        FROM submission s
        LEFT JOIN user_submission us ON s.submission_id = us.submission_id
        LEFT JOIN user u ON us.user_id = u.user_id
        LEFT JOIN problem p ON s.problem_id = p.problem_id
    """

    if use_problem_relation:
        try:
            backfill_problem_submission(db, problem_id)
            join_clause = """
                FROM problem_submission ps
                JOIN submission s ON ps.submission_id = s.submission_id
                LEFT JOIN user_submission us ON s.submission_id = us.submission_id
                LEFT JOIN user u ON us.user_id = u.user_id
                LEFT JOIN problem p ON s.problem_id = p.problem_id
            """
            where_clauses.append("ps.problem_id = :problem_id")
            params["problem_id"] = problem_id
        except Exception as e:
            # 兼容老数据或DDL失败时回退到 submission 表过滤
            print(f"[problem_submission] fallback to submission table: {e}")
            use_problem_relation = False

    # 用户筛选
    if user_id:
        where_clauses.append("u.user_id = :user_id")
        params["user_id"] = user_id

    # 题目筛选（仅当未使用联系表过滤时追加）
    if problem_id and not use_problem_relation:
        where_clauses.append("s.problem_id = :problem_id")
        params["problem_id"] = problem_id

    # 比赛筛选
    if contest_id is not None:
        if contest_id == -1:
            where_clauses.append("s.contest_id IS NULL")
        else:
            where_clauses.append("s.contest_id = :contest_id")
            params["contest_id"] = contest_id

    # 状态筛选
    if status:
        where_clauses.append("s.status = :status")
        params["status"] = status

    # 语言筛选
    if language:
        where_clauses.append("s.language = :language")
        params["language"] = language

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    sql = f"""
        SELECT 
            s.*,
            u.user_id as u_user_id,
            u.username,
            u.email,
            u.school,
            u.rating,
            u.role,
            u.created_at as u_created_at,
            p.problem_id as p_problem_id,
            p.title as problem_title,
            p.difficulty,
            p.tags
        {join_clause}
        WHERE {where_sql}
    """

    # 排序
    order_dir = "DESC" if order == "desc" else "ASC"
    if sort_by == "submitted_at":
        sql += f" ORDER BY s.submitted_at {order_dir}"
    elif sort_by == "exec_time":
        sql += f" ORDER BY s.exec_time {order_dir}"
    elif sort_by == "exec_memory":
        sql += f" ORDER BY s.exec_memory {order_dir}"

    # 分页
    sql += " LIMIT :limit OFFSET :offset"

    submissions = execute_query(db, sql, params)

    result = []
    for sub in submissions:
        submission_dict = {
            "submission_id": sub['submission_id'],
            "problem_id": sub['problem_id'],
            "contest_id": sub['contest_id'],
            "code": sub['code'],
            "language": sub['language'],
            "status": sub['status'],
            "exec_time": sub['exec_time'],
            "exec_memory": sub['exec_memory'],
            "submitted_at": sub['submitted_at'],
            "user": {
                "user_id": sub['u_user_id'],
                "username": sub['username'],
                "email": sub['email'],
                "school": sub['school'],
                "rating": sub['rating'],
                "role": sub['role'],
                "created_at": sub['u_created_at']
            } if sub['u_user_id'] else None,
            "problem": {
                "problem_id": sub['p_problem_id'],
                "title": sub['problem_title'],
                "difficulty": sub['difficulty'],
                "tags": sub['tags']
            } if sub['p_problem_id'] else None
        }
        result.append(submission_dict)

    return result


@router.get("/{submission_id}", response_model=dict)
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    """获取单个提交记录"""
    sql = "SELECT * FROM submission WHERE submission_id = :submission_id"
    submission = fetch_one(db, sql, {"submission_id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    return submission


@router.get("/{submission_id}/detail", response_model=dict)
def get_submission_detail(
    submission_id: int, 
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取提交记录的详细评测结果
    
    - 管理员可以看到输入数据、期望输出和实际输出
    - 普通用户只能看到状态、时间、内存、分数和错误信息
    """
    # 获取提交记录
    sub_sql = "SELECT * FROM submission WHERE submission_id = :submission_id"
    submission = fetch_one(db, sub_sql, {"submission_id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    
    # 获取评测结果（从 JSON 字段）
    judge_results = json.loads(submission['judge_results']) if submission['judge_results'] else []
    
    # 计算总分
    total_score = sum(result.get('score', 0) for result in judge_results)
    
    # 获取用户和题目信息
    user_sub_sql = "SELECT user_id FROM user_submission WHERE submission_id = :submission_id"
    user_submission = fetch_one(db, user_sub_sql, {"submission_id": submission_id})
    
    user = None
    if user_submission:
        user_sql = "SELECT * FROM user WHERE user_id = :user_id"
        user = fetch_one(db, user_sql, {"user_id": user_submission['user_id']})
    
    prob_sql = "SELECT * FROM problem WHERE problem_id = :problem_id"
    problem = fetch_one(db, prob_sql, {"problem_id": submission['problem_id']})
    
    # 判断当前请求用户是否为管理员
    is_admin = False
    if user_id:
        current_user_sql = "SELECT role FROM user WHERE user_id = :user_id"
        current_user = fetch_one(db, current_user_sql, {"user_id": user_id})
        is_admin = current_user and current_user['role'] == 'admin'
    
    # 构造响应
    result = {
        "submission_id": submission['submission_id'],
        "problem_id": submission['problem_id'],
        "contest_id": submission['contest_id'],
        "code": submission['code'],
        "language": submission['language'],
        "status": submission['status'],
        "exec_time": submission['exec_time'],
        "exec_memory": submission['exec_memory'],
        "submitted_at": submission['submitted_at'],
        "user": {
            "user_id": user['user_id'],
            "username": user['username'],
            "email": user['email'],
            "school": user['school'],
            "rating": user['rating'],
            "role": user['role'],
            "created_at": user['created_at']
        } if user else None,
        "problem": {
            "problem_id": problem['problem_id'],
            "title": problem['title'],
            "difficulty": problem['difficulty'],
            "tags": problem['tags']
        } if problem else None,
        "judge_results": [
            {
                "test_case_index": jr.get('test_case_index'),
                "status": jr.get('status'),
                "time_used": jr.get('time_used'),
                "memory_used": jr.get('memory_used'),
                "score": jr.get('score'),
                "error_message": jr.get('error_message'),
                # 只有管理员才能看到输入、期望输出和实际输出
                "input": jr.get('input_data') if is_admin else None,
                "expected_output": jr.get('expected_output') if is_admin else None,
                "actual_output": jr.get('actual_output') if is_admin else None,
            } for jr in judge_results
        ],
        "total_score": total_score
    }
    
    return result


@router.post("/{submission_id}/rejudge", response_model=dict)
def rejudge_submission(submission_id: int, user_id: int, db: Session = Depends(get_db)):
    """重新评测提交（仅管理员）"""
    # 检查管理员权限
    user_sql = "SELECT role FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可以重测提交")
    
    # 检查提交是否存在
    check_sql = "SELECT submission_id FROM submission WHERE submission_id = :submission_id"
    submission = fetch_one(db, check_sql, {"submission_id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    
    # 清空旧的评测结果并更新状态
    clear_sql = """
        UPDATE submission 
        SET judge_results = NULL, status = :status
        WHERE submission_id = :submission_id
    """
    execute_update(db, clear_sql, {
        "status": 'judging',
        "submission_id": submission_id
    })
    
    try:
        judge_submission(submission_id, db)
    except Exception as e:
        error_sql = "UPDATE submission SET status = :status WHERE submission_id = :submission_id"
        execute_update(db, error_sql, {
            "status": 'system_error',
            "submission_id": submission_id
        })
        raise HTTPException(
            status_code=500,
            detail=f"重新评测失败: {str(e)}"
        )
    
    # 返回更新后的提交记录
    result_sql = "SELECT * FROM submission WHERE submission_id = :submission_id"
    return fetch_one(db, result_sql, {"submission_id": submission_id})


@router.post("/rejudge_bulk", response_model=dict)
def rejudge_bulk(submission_ids: dict, user_id: int, background_tasks: BackgroundTasks = None, db: Session = Depends(get_db)):
    """批量重测提交（仅管理员）

    请求体示例: {"submission_ids": [1,2,3]}
    """
    # 校验管理员权限
    user_sql = "SELECT role FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可以批量重测提交")

    ids = submission_ids.get('submission_ids') if isinstance(submission_ids, dict) else None
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="请求体必须包含 submission_ids 列表")

    processed = []
    for sid in ids:
        # 检查提交是否存在
        check_sql = "SELECT submission_id FROM submission WHERE submission_id = :submission_id"
        submission = fetch_one(db, check_sql, {"submission_id": sid})
        if not submission:
            continue
        # 清空旧的评测结果并标记为 judging
        clear_sql = """
            UPDATE submission
            SET judge_results = NULL, status = :status
            WHERE submission_id = :submission_id
        """
        execute_update(db, clear_sql, {"status": 'judging', "submission_id": sid})
        # 若有 background_tasks，则异步评测；否则同步评测
        if background_tasks is not None:
            background_tasks.add_task(_background_judge, sid)
        else:
            try:
                judge_submission(sid, db)
            except Exception as e:
                # 将状态置为 system_error
                execute_update(db, "UPDATE submission SET status = :status WHERE submission_id = :submission_id", {
                    "status": 'system_error', "submission_id": sid
                })
        processed.append(sid)

    return {"processed_count": len(processed), "processed_ids": processed}


@router.put("/{submission_id}", response_model=dict)
def update_submission(
    submission_id: int,
    submission_update: SubmissionUpdate,
    db: Session = Depends(get_db)
):
    """更新提交记录（管理员）"""
    # 检查提交是否存在并获取原状态
    check_sql = "SELECT status, problem_id FROM submission WHERE submission_id = :submission_id"
    db_submission = fetch_one(db, check_sql, {"submission_id": submission_id})
    if not db_submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    
    old_status = db_submission['status']
    problem_id = db_submission['problem_id']
    
    # 构建更新SQL
    update_data = submission_update.model_dump(exclude_unset=True)
    if not update_data:
        return fetch_one(db, "SELECT * FROM submission WHERE submission_id = :submission_id", 
                        {"submission_id": submission_id})
    
    # 处理judge_results（如果有）
    if 'judge_results' in update_data and update_data['judge_results'] is not None:
        update_data['judge_results'] = json.dumps(update_data['judge_results'])
    
    update_fields = []
    params = {"submission_id": submission_id}
    
    for field, value in update_data.items():
        update_fields.append(f"{field} = :{field}")
        params[field] = value
    
    if update_fields:
        update_sql = f"UPDATE submission SET {', '.join(update_fields)} WHERE submission_id = :submission_id"
        execute_update(db, update_sql, params)
    
    # 获取更新后的状态
    new_status_sql = "SELECT status FROM submission WHERE submission_id = :submission_id"
    updated_submission = fetch_one(db, new_status_sql, {"submission_id": submission_id})
    new_status = updated_submission['status']
    
    # 如果状态从非 accepted 变为 accepted，需要更新用户 rating
    if old_status != 'accepted' and new_status == 'accepted':
        # 获取提交用户
        user_sub_sql = "SELECT user_id FROM user_submission WHERE submission_id = :submission_id"
        user_submission = fetch_one(db, user_sub_sql, {"submission_id": submission_id})
        
        if user_submission:
            user_id_val = user_submission['user_id']
            
            # 检查用户是否之前通过过这道题
            count_sql = """
                SELECT COUNT(*) as cnt
                FROM submission s
                INNER JOIN user_submission us ON s.submission_id = us.submission_id
                WHERE us.user_id = :user_id
                  AND s.problem_id = :problem_id
                  AND s.status = 'accepted'
                  AND s.submission_id != :submission_id
            """
            accepted_result = fetch_one(db, count_sql, {
                "user_id": user_id_val,
                "problem_id": problem_id,
                "submission_id": submission_id
            })
            accepted_count = accepted_result['cnt']
            
            # 如果是第一次通过，增加 rating
            if accepted_count == 0:
                prob_sql = "SELECT difficulty FROM problem WHERE problem_id = :problem_id"
                problem = fetch_one(db, prob_sql, {"problem_id": problem_id})
                if problem:
                    # 根据难度增加不同的 rating
                    rating_increase = {'easy': 10, 'medium': 20, 'hard': 30}.get(problem['difficulty'], 10)
                    rating_sql = "UPDATE user SET rating = rating + :increase WHERE user_id = :user_id"
                    execute_update(db, rating_sql, {
                        "increase": rating_increase,
                        "user_id": user_id_val
                    })
    
    # 返回更新后的提交记录
    return fetch_one(db, "SELECT * FROM submission WHERE submission_id = :submission_id", 
                    {"submission_id": submission_id})


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    submission_id: int,
    user_id: int,  # 添加执行删除的管理员ID
    db: Session = Depends(get_db)
):
    """删除提交记录（管理员）"""
    # 检查提交是否存在
    check_sql = "SELECT problem_id FROM submission WHERE submission_id = :submission_id"
    db_submission = fetch_one(db, check_sql, {"submission_id": submission_id})
    if not db_submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    
    # 获取题目信息用于日志
    prob_sql = "SELECT title FROM problem WHERE problem_id = :problem_id"
    problem = fetch_one(db, prob_sql, {"problem_id": db_submission['problem_id']})
    problem_title = problem['title'] if problem else f"题目#{db_submission['problem_id']}"
    
    # 记录活动日志
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": user_id,
        "action_type": "delete",
        "entity_type": "submission",
        "entity_id": submission_id,
        "description": f"管理员删除了提交记录 #{submission_id}（题目：{problem_title}）",
        "created_at": datetime.utcnow()
    })
    
    # 删除 user_submission 关联记录
    delete_user_sub_sql = "DELETE FROM user_submission WHERE submission_id = :submission_id"
    execute_update(db, delete_user_sub_sql, {"submission_id": submission_id})

    # 删除题目-提交关联记录（兼容级联缺失的历史数据）
    try:
        execute_update(db, "DELETE FROM problem_submission WHERE submission_id = :submission_id", {"submission_id": submission_id})
    except Exception as e:
        print(f"[problem_submission] delete link failed for submission {submission_id}: {e}")
    
    # 删除提交记录（评测结果作为 JSON 字段，会自动删除）
    delete_sql = "DELETE FROM submission WHERE submission_id = :submission_id"
    execute_update(db, delete_sql, {"submission_id": submission_id})
    
    return None
