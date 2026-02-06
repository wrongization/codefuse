from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db, execute_query, execute_insert, execute_update, fetch_one
from app.schemas import ProblemCreate, ProblemResponse, ProblemUpdate

router = APIRouter(prefix="/api/problems", tags=["problems"])

# 保留ID的最大值（id < 10000 为保留题目ID）
RESERVED_MAX_ID = 10000


def allocate_reserved_problem_id(db: Session) -> int:
    """为不可见题目分配保留ID（1-9999）"""
    # 找到所有已使用的保留ID（原生SQL）
    sql = "SELECT problem_id FROM problem WHERE problem_id < :max_id"
    used_problems = execute_query(db, sql, {"max_id": RESERVED_MAX_ID})
    used_ids = {p['problem_id'] for p in used_problems}
    
    # 找到最小的可用ID
    for i in range(1, RESERVED_MAX_ID):
        if i not in used_ids:
            return i
    
    raise HTTPException(status_code=500, detail="无可用保留题目ID（1-9999已用完）")


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_problem(problem: ProblemCreate, creator_id: int, db: Session = Depends(get_db)):
    """
    创建题目
    
    - visible=False: 创建比赛专用题目，手动分配保留ID（1-9999）
    - visible=True: 创建公开题目，自动分配ID（>=10000）
    
    比赛结束后，保留ID的题目可通过发布接口迁移到公开区（ID>=10000）
    """
    is_visible = problem.visible if problem.visible is not None else True
    
    # 处理test_cases（如果有）
    test_cases_json = json.dumps(problem.test_cases) if problem.test_cases else None
    
    if not is_visible:
        # 为比赛专用题目手动分配保留ID（1-9999）
        reserved_id = allocate_reserved_problem_id(db)
        insert_sql = """
            INSERT INTO problem (
                problem_id, title, description, input_format, output_format,
                sample_input, sample_output, time_limit, memory_limit,
                difficulty, tags, creator_id, test_cases, visible
            ) VALUES (
                :problem_id, :title, :description, :input_format, :output_format,
                :sample_input, :sample_output, :time_limit, :memory_limit,
                :difficulty, :tags, :creator_id, :test_cases, :visible
            )
        """
        problem_id = reserved_id
        execute_insert(db, insert_sql, {
            "problem_id": reserved_id,
            "title": problem.title,
            "description": problem.description,
            "input_format": problem.input_format,
            "output_format": problem.output_format,
            "sample_input": problem.sample_input,
            "sample_output": problem.sample_output,
            "time_limit": problem.time_limit,
            "memory_limit": problem.memory_limit,
            "difficulty": problem.difficulty,
            "tags": problem.tags,
            "creator_id": creator_id,
            "test_cases": test_cases_json,
            "visible": False
        })
    else:
        # 公开题目使用自动递增ID（>=10000）
        insert_sql = """
            INSERT INTO problem (
                title, description, input_format, output_format,
                sample_input, sample_output, time_limit, memory_limit,
                difficulty, tags, creator_id, test_cases, visible
            ) VALUES (
                :title, :description, :input_format, :output_format,
                :sample_input, :sample_output, :time_limit, :memory_limit,
                :difficulty, :tags, :creator_id, :test_cases, :visible
            )
        """
        problem_id = execute_insert(db, insert_sql, {
            "title": problem.title,
            "description": problem.description,
            "input_format": problem.input_format,
            "output_format": problem.output_format,
            "sample_input": problem.sample_input,
            "sample_output": problem.sample_output,
            "time_limit": problem.time_limit,
            "memory_limit": problem.memory_limit,
            "difficulty": problem.difficulty,
            "tags": problem.tags,
            "creator_id": creator_id,
            "test_cases": test_cases_json,
            "visible": True
        })
    
    # 记录活动日志（原生SQL）
    log_desc = f"创建了新题目《{problem.title}》{'（比赛专用，ID=' + str(problem_id) + '）' if not is_visible else ''}"
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": creator_id,
        "action_type": "create",
        "entity_type": "problem",
        "entity_id": problem_id,
        "description": log_desc,
        "created_at": datetime.utcnow()
    })
    
    # 查询刚创建的题目返回（原生SQL）
    select_sql = "SELECT * FROM problem WHERE problem_id = :problem_id"
    db_problem = fetch_one(db, select_sql, {"problem_id": problem_id})
    # 如果存在 test_case 表，则用 test_case 表的数据覆盖或补充 problem.test_cases 字段，保证一致性
    try:
        tc_sql = "SELECT * FROM test_case WHERE problem_id = :problem_id ORDER BY `order`"
        tcs = execute_query(db, tc_sql, {"problem_id": problem_id})
        if tcs:
            db_problem['test_cases'] = tcs
        else:
            # 如果没有独立的 test_case，则保留 problem.test_cases（可能为 JSON 字符串）
            if isinstance(db_problem.get('test_cases'), str):
                import json as _json
                try:
                    db_problem['test_cases'] = _json.loads(db_problem['test_cases'])
                except:
                    db_problem['test_cases'] = []
    except Exception:
        # 若 test_case 表不存在或查询失败，尝试解析 problem.test_cases 字段（兼容旧数据）
        if isinstance(db_problem.get('test_cases'), str):
            import json as _json
            try:
                db_problem['test_cases'] = _json.loads(db_problem['test_cases'])
            except:
                db_problem['test_cases'] = []

    return db_problem


@router.get("/", response_model=List[dict])
def get_problems(
    skip: int = 0, 
    limit: int = 100, 
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    tags: Optional[str] = None,
    sort_by: Optional[str] = None,  # problem_id, title, difficulty, is_solved
    sort_order: Optional[str] = None,  # asc, desc
    user_id: Optional[int] = None,  # 用户ID，用于查询通过状态
    db: Session = Depends(get_db)
):
    """获取题目列表（支持搜索、筛选、排序）"""
    # 权限过滤：非管理员只能看到公开题库的题目（ID>=10000）
    is_admin = False
    if user_id:
        user_sql = "SELECT role FROM user WHERE user_id = :user_id"
        user = fetch_one(db, user_sql, {"user_id": user_id})
        is_admin = user and user['role'] == 'admin'
    
    # 构建SQL查询
    sql = "SELECT * FROM problem WHERE 1=1"
    params = {}
    
    # 权限过滤
    if not is_admin:
        sql += " AND problem_id >= :reserved_max_id"
        params["reserved_max_id"] = RESERVED_MAX_ID
    
    # 难度筛选
    if difficulty:
        sql += " AND difficulty = :difficulty"
        params["difficulty"] = difficulty
    
    # 搜索（仅搜索标题）
    if search:
        sql += " AND title LIKE :search"
        params["search"] = f"%{search}%"
    
    # 标签筛选（支持多标签，逗号分隔）
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        for idx, tag in enumerate(tag_list):
            sql += f" AND tags LIKE :tag{idx}"
            params[f"tag{idx}"] = f"%{tag}%"
    
    # 排序（不包括is_solved）
    if sort_by and sort_by != "is_solved":
        order = "DESC" if sort_order == "desc" else "ASC"
        if sort_by == "problem_id":
            sql += f" ORDER BY problem_id {order}"
        elif sort_by == "title":
            sql += f" ORDER BY title {order}"
        elif sort_by == "difficulty":
            sql += f" ORDER BY difficulty {order}"
    
    # 分页
    sql += " LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = skip
    
    problems = execute_query(db, sql, params)
    
    # 如果提供了user_id，查询每道题的通过状态
    result = []
    for problem in problems:
        problem_dict = dict(problem)
        problem_dict["is_solved"] = False
        
        if user_id:
            # 查询用户是否通过了这道题（只统计题库中的提交，不包括比赛提交）
            solved_sql = """
                SELECT s.submission_id 
                FROM submission s
                INNER JOIN user_submission us ON s.submission_id = us.submission_id
                WHERE us.user_id = :user_id 
                  AND s.problem_id = :problem_id
                  AND s.contest_id IS NULL
                  AND s.status = 'accepted'
                LIMIT 1
            """
            solved = fetch_one(db, solved_sql, {
                "user_id": user_id,
                "problem_id": problem['problem_id']
            })
            problem_dict["is_solved"] = solved is not None
        
        result.append(problem_dict)
    
    # 如果需要按is_solved排序，在Python中进行排序
    if sort_by == "is_solved" and sort_order:
        result.sort(key=lambda x: x["is_solved"], reverse=(sort_order == "desc"))
    
    return result


@router.get("/{problem_id}", response_model=dict)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    """获取单个题目"""
    sql = "SELECT * FROM problem WHERE problem_id = :problem_id"
    problem = fetch_one(db, sql, {"problem_id": problem_id})
    
    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    # 为返回的数据附加 test_case 表中的测试点（若存在），优先使用 test_case 表
    try:
        tc_sql = "SELECT * FROM test_case WHERE problem_id = :problem_id ORDER BY `order`"
        tcs = execute_query(db, tc_sql, {"problem_id": problem_id})
        if tcs:
            problem['test_cases'] = tcs
        else:
            # 兼容旧版：如果 problem.test_cases 是字符串则解析
            if isinstance(problem.get('test_cases'), str):
                try:
                    import json as _json
                    problem['test_cases'] = _json.loads(problem['test_cases'])
                except:
                    problem['test_cases'] = []
    except Exception:
        if isinstance(problem.get('test_cases'), str):
            try:
                import json as _json
                problem['test_cases'] = _json.loads(problem['test_cases'])
            except:
                problem['test_cases'] = []

    return problem


@router.put("/{problem_id}", response_model=dict)
def update_problem(
    problem_id: int, 
    problem_update: ProblemUpdate,
    user_id: int,  # 添加操作用户ID
    db: Session = Depends(get_db)
):
    """更新题目"""
    # 查询题目是否存在
    check_sql = "SELECT title FROM problem WHERE problem_id = :problem_id"
    db_problem = fetch_one(db, check_sql, {"problem_id": problem_id})
    if not db_problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    # 构建更新SQL
    update_data = problem_update.dict(exclude_unset=True)
    if not update_data:
        return fetch_one(db, "SELECT * FROM problem WHERE problem_id = :problem_id", 
                        {"problem_id": problem_id})
    
    # 处理test_cases
    if 'test_cases' in update_data and update_data['test_cases'] is not None:
        update_data['test_cases'] = json.dumps(update_data['test_cases'])
    
    update_fields = []
    params = {"problem_id": problem_id}
    
    for field, value in update_data.items():
        update_fields.append(f"{field} = :{field}")
        params[field] = value
    
    if update_fields:
        update_sql = f"UPDATE problem SET {', '.join(update_fields)} WHERE problem_id = :problem_id"
        execute_update(db, update_sql, params)
    
    # 获取更新后的题目标题用于日志
    updated_problem = fetch_one(db, "SELECT title FROM problem WHERE problem_id = :problem_id", 
                                {"problem_id": problem_id})
    
    # 记录活动日志（原生SQL）
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": user_id,
        "action_type": "update",
        "entity_type": "problem",
        "entity_id": problem_id,
        "description": f"更新了题目《{updated_problem['title']}》",
        "created_at": datetime.utcnow()
    })
    
    # 返回更新后的题目
    updated = fetch_one(db, "SELECT * FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    # 同样附加 test_case 表的数据（优先）
    try:
        tc_sql = "SELECT * FROM test_case WHERE problem_id = :problem_id ORDER BY `order`"
        tcs = execute_query(db, tc_sql, {"problem_id": problem_id})
        if tcs:
            updated['test_cases'] = tcs
        else:
            if isinstance(updated.get('test_cases'), str):
                import json as _json
                try:
                    updated['test_cases'] = _json.loads(updated['test_cases'])
                except:
                    updated['test_cases'] = []
    except Exception:
        if isinstance(updated.get('test_cases'), str):
            import json as _json
            try:
                updated['test_cases'] = _json.loads(updated['test_cases'])
            except:
                updated['test_cases'] = []

    return updated


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem(problem_id: int, user_id: int, db: Session = Depends(get_db)):
    """删除题目（管理员）- 级联删除所有相关数据"""
    # 查询题目是否存在
    check_sql = "SELECT title FROM problem WHERE problem_id = :problem_id"
    db_problem = fetch_one(db, check_sql, {"problem_id": problem_id})
    if not db_problem:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    problem_title = db_problem['title']
    
    # 级联删除相关数据（按照外键依赖顺序，先删除子表，再删除父表）
    # 1. 获取该题目的所有提交记录ID
    get_submissions_sql = "SELECT submission_id FROM submission WHERE problem_id = :problem_id"
    submissions = execute_query(db, get_submissions_sql, {"problem_id": problem_id})
    submission_ids = [s['submission_id'] for s in submissions]
    
    if submission_ids:
        # 1.1 删除 user_submission（子表）
        ids_str = ','.join(map(str, submission_ids))
        delete_user_submission_sql = f"DELETE FROM user_submission WHERE submission_id IN ({ids_str})"
        execute_update(db, delete_user_submission_sql, {})
    
    # 1.2 删除 submission（现在可以安全删除）
    delete_submissions_sql = "DELETE FROM submission WHERE problem_id = :problem_id"
    execute_update(db, delete_submissions_sql, {"problem_id": problem_id})
    
    # 2. 删除比赛题目关联
    delete_contest_problem_sql = "DELETE FROM contest_problem WHERE problem_id = :problem_id"
    execute_update(db, delete_contest_problem_sql, {"problem_id": problem_id})
    
    # 3. 删除消息题目关联
    delete_message_problem_sql = "DELETE FROM message_problem WHERE problem_id = :problem_id"
    execute_update(db, delete_message_problem_sql, {"problem_id": problem_id})

    # 3.1 删除题目-提交关联
    try:
        delete_problem_submission_sql = "DELETE FROM problem_submission WHERE problem_id = :problem_id"
        execute_update(db, delete_problem_submission_sql, {"problem_id": problem_id})
    except Exception as e:
        print(f"[problem_submission] delete links failed for problem {problem_id}: {e}")
    
    # 4. 删除测试用例（如果有test_case表）
    try:
        delete_test_cases_sql = "DELETE FROM test_case WHERE problem_id = :problem_id"
        execute_update(db, delete_test_cases_sql, {"problem_id": problem_id})
    except:
        pass  # 如果test_case表不存在则忽略
    
    # 5. 删除题目本身
    delete_problem_sql = "DELETE FROM problem WHERE problem_id = :problem_id"
    execute_update(db, delete_problem_sql, {"problem_id": problem_id})
    
    # 6. 记录活动日志
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": user_id,
        "action_type": "delete",
        "entity_type": "problem",
        "entity_id": problem_id,
        "description": f"删除了题目《{problem_title}》",
        "created_at": datetime.utcnow()
    })
    
    return None
