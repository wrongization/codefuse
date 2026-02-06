from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import math

from app.database import get_db, execute_query, execute_insert, execute_update, fetch_one
from app.schemas import ContestCreate, ContestResponse, ContestUpdate

router = APIRouter(prefix="/api/contests", tags=["contests"])


def auto_publish_contest_problems(contest_dict: dict, db: Session):
    """
    自动发布比赛题目到公开题库（比赛结束后）
    
    自动处理已结束但未发布题目的比赛：
    - 将 ID<10000 的保留题目迁移到 ID>=10000 的公开区
    - 更新所有相关提交记录和比赛题目关联
    - 删除原保留ID题目，释放ID供后续重用
    """
    # 检查比赛是否结束且题目未发布
    now = datetime.now()
    end_time = contest_dict['end_time']
    problems_published = contest_dict.get('problems_published', False)
    contest_id = contest_dict['contest_id']
    
    if end_time >= now or problems_published:
        return  # 比赛未结束或已发布，跳过
    
    # 获取比赛的所有题目
    cp_sql = "SELECT * FROM contest_problem WHERE contest_id = :contest_id"
    contest_problems = execute_query(db, cp_sql, {"contest_id": contest_id})
    # 在将提交转为题库提交之前先计算并更新等级分，避免后续将 contest_id 置空导致无法统计
    try:
        calculate_contest_ratings(contest_dict, db)
    except Exception as e:
        # 评分计算失败不应阻止题目发布流程，记录错误并继续
        print(f"auto_publish: calculate_contest_ratings failed for contest {contest_id}: {e}")
    
    published_count = 0
    converted_submissions_count = 0  # 记录转换为题库提交的数量
    
    for cp in contest_problems:
        prob_sql = "SELECT * FROM problem WHERE problem_id = :problem_id"
        problem = fetch_one(db, prob_sql, {"problem_id": cp['problem_id']})
        if not problem:
            continue
        
        # 处理ID<10000的保留题目（需要迁移）
        if problem['problem_id'] < 10000:
            old_id = problem['problem_id']
            
            # 准备标签（添加比赛来源标签，使用比赛标题）
            contest_tag = contest_dict['title']
            new_tags = problem['tags'] if problem['tags'] else ""
            if contest_tag not in new_tags:
                new_tags = f"{new_tags},{contest_tag}" if new_tags else contest_tag
            
            # 创建新题目（visible=True，将自动获得 ID>=10000）
            insert_prob_sql = """
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
            new_id = execute_insert(db, insert_prob_sql, {
                "title": problem['title'],
                "description": problem['description'],
                "input_format": problem['input_format'],
                "output_format": problem['output_format'],
                "sample_input": problem['sample_input'],
                "sample_output": problem['sample_output'],
                "time_limit": problem['time_limit'],
                "memory_limit": problem['memory_limit'],
                "difficulty": problem['difficulty'],
                "tags": new_tags,
                "creator_id": problem['creator_id'],
                "test_cases": problem['test_cases'],
                "visible": True
            })
            
            # 更新所有相关提交记录的 problem_id
            get_subs_sql = "SELECT * FROM submission WHERE problem_id = :problem_id"
            submissions = execute_query(db, get_subs_sql, {"problem_id": old_id})
            for submission in submissions:
                # 如果是比赛提交（contest_id 匹配当前比赛），转为题库提交
                if submission['contest_id'] == contest_id:
                    update_sub_sql = """
                        UPDATE submission 
                        SET problem_id = :new_id, contest_id = NULL
                        WHERE submission_id = :submission_id
                    """
                    execute_update(db, update_sub_sql, {
                        "new_id": new_id,
                        "submission_id": submission['submission_id']
                    })
                    converted_submissions_count += 1
                else:
                    update_sub_sql2 = """
                        UPDATE submission 
                        SET problem_id = :new_id
                        WHERE submission_id = :submission_id
                    """
                    execute_update(db, update_sub_sql2, {
                        "new_id": new_id,
                        "submission_id": submission['submission_id']
                    })
            
            # 更新比赛题目关联到新ID
            update_cp_sql = """
                UPDATE contest_problem 
                SET problem_id = :new_id
                WHERE contest_id = :contest_id AND problem_id = :old_id
            """
            execute_update(db, update_cp_sql, {
                "new_id": new_id,
                "contest_id": contest_id,
                "old_id": old_id
            })
            
            # 删除旧题目（释放保留ID）
            delete_prob_sql = "DELETE FROM problem WHERE problem_id = :problem_id"
            execute_update(db, delete_prob_sql, {"problem_id": old_id})
            
            published_count += 1
        
        # 处理ID>=10000的公开题目（无需迁移，但需将提交记录转为题库提交）
        else:
            update_subs_sql = """
                UPDATE submission 
                SET contest_id = NULL
                WHERE problem_id = :problem_id AND contest_id = :contest_id
            """
            affected = execute_update(db, update_subs_sql, {
                "problem_id": problem['problem_id'],
                "contest_id": contest_id
            })
            converted_submissions_count += affected
    
    # 标记比赛题目已发布
    if published_count > 0 or converted_submissions_count > 0:
        update_contest_sql = """
            UPDATE contest 
            SET problems_published = TRUE
            WHERE contest_id = :contest_id
        """
        execute_update(db, update_contest_sql, {"contest_id": contest_id})
        
        # 记录活动日志
        log_description = f"比赛《{contest_dict['title']}》结束"
        if published_count > 0:
            log_description += f"，自动发布 {published_count} 道题目到公开题库"
        if converted_submissions_count > 0:
            log_description += f"，{converted_submissions_count} 条提交记录转为题库提交"
        
        log_sql = """
            INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
            VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
        """
        execute_insert(db, log_sql, {
            "user_id": contest_dict['creator_id'],
            "action_type": "auto_publish",
            "entity_type": "contest",
            "entity_id": contest_id,
            "description": log_description,
            "created_at": datetime.utcnow()
        })
    
    # 注意：等级分已在题目发布前计算，避免在此重复计算


def calculate_contest_ratings(contest_dict: dict, db: Session):
    """
    计算比赛结束后的用户等级分

    修改规则：对于每位报名并参加比赛的用户，比赛结束后根据其在比赛中每道题目的得分增加等级分。
    每道题增加分数 = (该题得分 * 题目难度分) / 10
    难度分映射：简单(easy)=0.3，普通(medium)=0.5，困难(hard)=0.8

    注意：该规则按每道题目单独累加，不再要求用户必须完成所有题目。
    """
    contest_id = contest_dict['contest_id']
    
    # 获取比赛的所有题目
    cp_sql = "SELECT * FROM contest_problem WHERE contest_id = :contest_id"
    contest_problems = execute_query(db, cp_sql, {"contest_id": contest_id})
    
    if not contest_problems:
        return
    
    # 构建题目难度分映射
    difficulty_scores = {
        'easy': 0.3,
        'medium': 0.5,
        'hard': 0.8
    }
    
    # 获取所有参赛用户
    cu_sql = "SELECT * FROM contest_user WHERE contest_id = :contest_id"
    contest_users = execute_query(db, cu_sql, {"contest_id": contest_id})
    
    for cu in contest_users:
        user_id = cu['user_id']
        user_sql = "SELECT * FROM user WHERE user_id = :user_id"
        user = fetch_one(db, user_sql, {"user_id": user_id})
        if not user:
            continue

        # 使用浮点累加每题增分，再对总和取整，避免每题小数被截断导致总增分为0
        total_gain_float = 0.0

        for cp in contest_problems:
            prob_sql = "SELECT * FROM problem WHERE problem_id = :problem_id"
            problem = fetch_one(db, prob_sql, {"problem_id": cp['problem_id']})
            if not problem:
                continue

            # 查找用户在该比赛中对该题目的所有提交，选择得分最高的提交（按 judge_results 得分计算）
            subs_sql = """
                SELECT s.* 
                FROM submission s
                INNER JOIN user_submission us ON s.submission_id = us.submission_id
                WHERE us.user_id = :user_id
                  AND s.problem_id = :problem_id
                  AND s.contest_id = :contest_id
            """
            submissions = execute_query(db, subs_sql, {
                "user_id": user_id,
                "problem_id": cp['problem_id'],
                "contest_id": contest_id
            })

            if not submissions:
                continue

            # 对每次提交计算基于 judge_results 的得分，取最高分
            problem_score = 0
            for sub in submissions:
                jr = json.loads(sub['judge_results']) if sub.get('judge_results') else []
                score = 0
                for result in jr:
                    # 统计所有测试点的 score（不再仅统计 status=='Accepted'），
                    # 允许部分通过也能获得相应分数
                    if isinstance(result, dict):
                        score += result.get('score', 0)
                if score > problem_score:
                    problem_score = score

            if problem_score <= 0:
                continue

            difficulty_score = difficulty_scores.get(problem['difficulty'], 0.5)
            # 先计算浮点增分，后面对总和取整
            gain_float = (problem_score * difficulty_score) / 10.0
            total_gain_float += gain_float

        # 对总的浮点增分取整为整数增分（向下取整）
        total_gain = int(math.floor(total_gain_float))

        if total_gain > 0:
            # 幂等性检查：如果已经为该用户在本次比赛中记录过等级分更新，则跳过，避免重复加分
            check_log_sql = """
                SELECT 1 FROM activity_log
                WHERE action_type = 'rating_update' AND entity_type = 'contest' AND entity_id = :contest_id AND user_id = :user_id
                LIMIT 1
            """
            already = fetch_one(db, check_log_sql, {"contest_id": contest_id, "user_id": user_id})
            if already:
                continue

            rating_update_sql = """
                UPDATE user 
                SET rating = rating + :rating_gain
                WHERE user_id = :user_id
            """
            execute_update(db, rating_update_sql, {
                "rating_gain": int(total_gain),
                "user_id": user_id
            })

            # 记录活动日志
            log_sql = """
                INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
                VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
            """
            execute_insert(db, log_sql, {
                "user_id": user_id,
                "action_type": "rating_update",
                "entity_type": "contest",
                "entity_id": contest_id,
                "description": f"比赛《{contest_dict['title']}》结束，等级分 +{int(total_gain)}",
                "created_at": datetime.utcnow()
            })


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_contest(
    contest: ContestCreate,
    creator_id: int,
    db: Session = Depends(get_db)
):
    """创建比赛（管理员）"""
    insert_sql = """
        INSERT INTO contest (title, description, start_time, end_time, creator_id)
        VALUES (:title, :description, :start_time, :end_time, :creator_id)
    """
    contest_id = execute_insert(db, insert_sql, {
        "title": contest.title,
        "description": contest.description,
        "start_time": contest.start_time,
        "end_time": contest.end_time,
        "creator_id": creator_id
    })
    
    # 记录活动日志
    creator_sql = "SELECT username FROM user WHERE user_id = :user_id"
    creator = fetch_one(db, creator_sql, {"user_id": creator_id})
    creator_name = creator['username'] if creator else "管理员"
    
    log_sql = """
        INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
        VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
    """
    execute_insert(db, log_sql, {
        "user_id": creator_id,
        "action_type": "create",
        "entity_type": "contest",
        "entity_id": contest_id,
        "description": f"{creator_name} 创建了比赛《{contest.title}》",
        "created_at": datetime.utcnow()
    })
    
    # 返回创建的比赛
    select_sql = "SELECT * FROM contest WHERE contest_id = :contest_id"
    return fetch_one(db, select_sql, {"contest_id": contest_id})


@router.get("/", response_model=List[dict])
def get_contests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,  # upcoming, ongoing, finished
    search: Optional[str] = None,
    sort_by: str = "start_time",  # start_time, title
    order: str = "desc",  # asc, desc
    user_id: Optional[int] = None,  # 用于检查用户通过情况
    registered: Optional[str] = None,  # 报名状态筛选: true, false
    db: Session = Depends(get_db)
):
    """获取比赛列表"""
    # 构建SQL查询
    sql = "SELECT * FROM contest WHERE 1=1"
    params = {}
    
    # 搜索
    if search:
        sql += " AND title LIKE :search"
        params["search"] = f"%{search}%"
    
    # 按状态筛选
    now = datetime.now()
    if status == "upcoming":
        sql += " AND start_time > :now"
        params["now"] = now
    elif status == "ongoing":
        sql += " AND start_time <= :now AND end_time >= :now"
        params["now"] = now
    elif status == "finished":
        sql += " AND end_time < :now"
        params["now"] = now
    
    # 排序
    order_dir = "DESC" if order == "desc" else "ASC"
    if sort_by == "start_time":
        sql += f" ORDER BY start_time {order_dir}"
    elif sort_by == "title":
        sql += f" ORDER BY title {order_dir}"
    
    # 分页
    sql += " LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = skip
    
    contests = execute_query(db, sql, params)
    
    # 自动发布已结束比赛的题目
    for contest in contests:
        try:
            auto_publish_contest_problems(contest, db)
        except Exception as e:
            # 发布失败不影响列表查询，仅记录错误
            print(f"自动发布比赛 {contest['contest_id']} 题目失败: {e}")
    
    # 获取每个比赛的题目数和参赛人数
    result = []
    for contest in contests:
        # 计算状态
        if contest['start_time'] > now:
            contest_status = "upcoming"
        elif contest['end_time'] < now:
            contest_status = "finished"
        else:
            contest_status = "ongoing"
        
        # 获取题目数
        prob_count_sql = "SELECT COUNT(*) as cnt FROM contest_problem WHERE contest_id = :contest_id"
        prob_count_result = fetch_one(db, prob_count_sql, {"contest_id": contest['contest_id']})
        problem_count = prob_count_result['cnt']
        
        # 获取参赛人数
        part_count_sql = "SELECT COUNT(*) as cnt FROM contest_user WHERE contest_id = :contest_id"
        part_count_result = fetch_one(db, part_count_sql, {"contest_id": contest['contest_id']})
        participant_count = part_count_result['cnt']
        
        # 检查用户是否报名（通过 ContestUser 表判断）
        is_registered = False
        if user_id:
            reg_sql = """
                SELECT 1 FROM contest_user 
                WHERE contest_id = :contest_id AND user_id = :user_id
                LIMIT 1
            """
            is_registered = fetch_one(db, reg_sql, {
                "contest_id": contest['contest_id'],
                "user_id": user_id
            }) is not None
        
        # 根据报名状态筛选
        if registered is not None:
            if registered == "true" and not is_registered:
                continue
            elif registered == "false" and is_registered:
                continue
        
        # 检查用户通过情况（当且仅当所有题目被完成）
        is_passed = False
        if user_id and problem_count > 0:
            # 获取比赛的所有题目ID
            cp_ids_sql = "SELECT problem_id FROM contest_problem WHERE contest_id = :contest_id"
            contest_problem_ids = [cp['problem_id'] for cp in execute_query(db, cp_ids_sql, {
                "contest_id": contest['contest_id']
            })]
            
            # 检查用户是否通过了所有题目
            passed_count = 0
            for problem_id in contest_problem_ids:
                # 查询用户在该比赛中对该题目的提交
                accepted_sql = """
                    SELECT 1
                    FROM submission s
                    INNER JOIN user_submission us ON s.submission_id = us.submission_id
                    WHERE us.user_id = :user_id
                      AND s.problem_id = :problem_id
                      AND s.contest_id = :contest_id
                      AND s.status = 'Accepted'
                    LIMIT 1
                """
                accepted_submission = fetch_one(db, accepted_sql, {
                    "user_id": user_id,
                    "problem_id": problem_id,
                    "contest_id": contest['contest_id']
                })
                
                if accepted_submission:
                    passed_count += 1
            
            # 只有通过所有题目才算通过比赛
            is_passed = (passed_count == problem_count)
        
        result.append({
            "contest_id": contest['contest_id'],
            "title": contest['title'],
            "description": contest['description'],
            "start_time": contest['start_time'],
            "end_time": contest['end_time'],
            "creator_id": contest['creator_id'],
            "status": contest_status,
            "problem_count": problem_count,
            "participant_count": participant_count,
            "is_passed": is_passed,
            "is_registered": is_registered
        })
    
    return result


@router.get("/{contest_id}", response_model=dict)
def get_contest(
    contest_id: int,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    获取单个比赛详情
    - 只有报名用户在比赛时间内才能看到题目列表
    - 未报名或比赛时间外只能看到比赛基本信息
    """
    # 获取比赛
    contest_sql = "SELECT * FROM contest WHERE contest_id = :contest_id"
    contest = fetch_one(db, contest_sql, {"contest_id": contest_id})
    if not contest:
        raise HTTPException(status_code=404, detail="比赛不存在")
    
    # 计算状态（使用 naive datetime）
    now = datetime.now()
    if contest['start_time'] > now:
        contest_status = "upcoming"
    elif contest['end_time'] < now:
        contest_status = "finished"
    else:
        contest_status = "ongoing"
    
    # 检查用户是否报名
    is_registered = False
    if user_id:
        reg_sql = """
            SELECT 1 FROM contest_user 
            WHERE contest_id = :contest_id AND user_id = :user_id
            LIMIT 1
        """
        is_registered = fetch_one(db, reg_sql, {
            "contest_id": contest_id,
            "user_id": user_id
        }) is not None
    
    # 检查是否在比赛时间内
    is_during_contest = contest['start_time'] <= now <= contest['end_time']
    
    # 检查用户是否是管理员
    is_admin = False
    if user_id:
        user_sql = "SELECT role FROM user WHERE user_id = :user_id"
        user = fetch_one(db, user_sql, {"user_id": user_id})
        if user:
            is_admin = user['role'] == 'admin'
    
    # 判断是否可以查看题目
    is_practice_mode = contest_status == "finished"
    can_view_problems = is_admin or (is_registered and is_during_contest) or is_practice_mode
    
    problems = []
    if can_view_problems:
        # 获取比赛题目
        cp_sql = """
            SELECT p.problem_id, p.title, p.difficulty, p.tags
            FROM contest_problem cp
            INNER JOIN problem p ON cp.problem_id = p.problem_id
            WHERE cp.contest_id = :contest_id
        """
        problems = execute_query(db, cp_sql, {"contest_id": contest_id})
    
    # 获取参赛用户
    parts_sql = """
        SELECT u.user_id, u.username, u.rating, u.school
        FROM contest_user cu
        INNER JOIN user u ON cu.user_id = u.user_id
        WHERE cu.contest_id = :contest_id
    """
    participants = execute_query(db, parts_sql, {"contest_id": contest_id})
    
    return {
        "contest_id": contest['contest_id'],
        "title": contest['title'],
        "description": contest['description'],
        "start_time": contest['start_time'],
        "end_time": contest['end_time'],
        "creator_id": contest['creator_id'],
        "status": contest_status,
        "problems": problems,
        "participants": participants,
        "can_view_problems": can_view_problems,
        "is_registered": is_registered
    }


@router.put("/{contest_id}", response_model=dict)
def update_contest(
    contest_id: int,
    contest: ContestUpdate,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """更新比赛（管理员）"""
    # 检查比赛是否存在
    check_sql = "SELECT title FROM contest WHERE contest_id = :contest_id"
    db_contest = fetch_one(db, check_sql, {"contest_id": contest_id})
    if not db_contest:
        raise HTTPException(status_code=404, detail="比赛不存在")
    
    # 构建更新SQL
    update_data = contest.model_dump(exclude_unset=True)
    if not update_data:
        return fetch_one(db, "SELECT * FROM contest WHERE contest_id = :contest_id", 
                        {"contest_id": contest_id})
    
    update_fields = []
    params = {"contest_id": contest_id}
    
    for field, value in update_data.items():
        update_fields.append(f"{field} = :{field}")
        params[field] = value
    
    if update_fields:
        update_sql = f"UPDATE contest SET {', '.join(update_fields)} WHERE contest_id = :contest_id"
        execute_update(db, update_sql, params)
    
    # 获取更新后的比赛标题
    updated_contest = fetch_one(db, "SELECT title FROM contest WHERE contest_id = :contest_id", 
                                {"contest_id": contest_id})
    
    # 记录活动日志
    if user_id:
        user_sql = "SELECT username FROM user WHERE user_id = :user_id"
        user = fetch_one(db, user_sql, {"user_id": user_id})
        user_name = user['username'] if user else "管理员"
        
        log_sql = """
            INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
            VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
        """
        execute_insert(db, log_sql, {
            "user_id": user_id,
            "action_type": "update",
            "entity_type": "contest",
            "entity_id": contest_id,
            "description": f"{user_name} 更新了比赛《{updated_contest['title']}》",
            "created_at": datetime.utcnow()
        })
    
    # 返回更新后的比赛
    return fetch_one(db, "SELECT * FROM contest WHERE contest_id = :contest_id", 
                    {"contest_id": contest_id})


@router.delete("/{contest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contest(contest_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """删除比赛（管理员）"""
    # 检查比赛是否存在
    check_sql = "SELECT title FROM contest WHERE contest_id = :contest_id"
    db_contest = fetch_one(db, check_sql, {"contest_id": contest_id})
    if not db_contest:
        raise HTTPException(status_code=404, detail="比赛不存在")
    
    contest_title = db_contest['title']
    
    # 级联删除相关数据（按照外键依赖顺序）
    # 1. 获取该比赛的所有提交记录ID
    get_subs_sql = "SELECT submission_id FROM submission WHERE contest_id = :contest_id"
    submissions = execute_query(db, get_subs_sql, {"contest_id": contest_id})
    submission_ids = [s['submission_id'] for s in submissions]
    
    if submission_ids:
        # 2. 先删除 user_submission 关联记录（子表）
        ids_str = ','.join(map(str, submission_ids))
        delete_user_sub_sql = f"DELETE FROM user_submission WHERE submission_id IN ({ids_str})"
        execute_update(db, delete_user_sub_sql, {})
    
    # 3. 删除 submission 记录
    delete_subs_sql = "DELETE FROM submission WHERE contest_id = :contest_id"
    execute_update(db, delete_subs_sql, {"contest_id": contest_id})
    
    # 4. 删除相关的 contest_problem 和 contest_user 记录
    delete_cp_sql = "DELETE FROM contest_problem WHERE contest_id = :contest_id"
    execute_update(db, delete_cp_sql, {"contest_id": contest_id})
    
    delete_cu_sql = "DELETE FROM contest_user WHERE contest_id = :contest_id"
    execute_update(db, delete_cu_sql, {"contest_id": contest_id})
    
    # 5. 删除比赛
    delete_contest_sql = "DELETE FROM contest WHERE contest_id = :contest_id"
    execute_update(db, delete_contest_sql, {"contest_id": contest_id})
    
    # 6. 记录活动日志
    if user_id:
        user_sql = "SELECT username FROM user WHERE user_id = :user_id"
        user = fetch_one(db, user_sql, {"user_id": user_id})
        user_name = user['username'] if user else "管理员"
        
        log_sql = """
            INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
            VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
        """
        execute_insert(db, log_sql, {
            "user_id": user_id,
            "action_type": "delete",
            "entity_type": "contest",
            "entity_id": contest_id,
            "description": f"{user_name} 删除了比赛《{contest_title}》",
            "created_at": datetime.utcnow()
        })
    
    return None


@router.post("/{contest_id}/problems", status_code=status.HTTP_201_CREATED)
def add_problem_to_contest(
    contest_id: int,
    problem_id: int,
    db: Session = Depends(get_db)
):
    """为比赛添加题目（管理员）"""
    # 检查比赛是否存在
    contest_sql = "SELECT 1 FROM contest WHERE contest_id = :contest_id LIMIT 1"
    contest = fetch_one(db, contest_sql, {"contest_id": contest_id})
    if not contest:
        raise HTTPException(status_code=404, detail="比赛不存在")

    # 检查题目是否存在
    problem_sql = "SELECT 1 FROM problem WHERE problem_id = :problem_id LIMIT 1"
    problem = fetch_one(db, problem_sql, {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")

    # 检查是否已存在
    existing_sql = """
        SELECT 1 FROM contest_problem 
        WHERE contest_id = :contest_id AND problem_id = :problem_id
        LIMIT 1
    """
    existing = fetch_one(db, existing_sql, {
        "contest_id": contest_id,
        "problem_id": problem_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="题目已在比赛中")

    # 添加题目到比赛
    insert_sql = """
        INSERT INTO contest_problem (contest_id, problem_id)
        VALUES (:contest_id, :problem_id)
    """
    execute_insert(db, insert_sql, {
        "contest_id": contest_id,
        "problem_id": problem_id
    })
    
    return {"message": "添加成功"}


@router.delete("/{contest_id}/problems/{problem_id}")
def remove_problem_from_contest(
    contest_id: int,
    problem_id: int,
    db: Session = Depends(get_db)
):
    """从比赛中移除题目（管理员）"""
    # 检查题目是否在比赛中
    check_sql = """
        SELECT 1 FROM contest_problem 
        WHERE contest_id = :contest_id AND problem_id = :problem_id
        LIMIT 1
    """
    cp = fetch_one(db, check_sql, {
        "contest_id": contest_id,
        "problem_id": problem_id
    })
    if not cp:
        raise HTTPException(status_code=404, detail="题目未在比赛中")

    # 删除题目
    delete_sql = """
        DELETE FROM contest_problem 
        WHERE contest_id = :contest_id AND problem_id = :problem_id
    """
    execute_update(db, delete_sql, {
        "contest_id": contest_id,
        "problem_id": problem_id
    })
    
    return {"message": "移除成功"}


@router.post("/{contest_id}/register")
def register_contest(
    contest_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """报名参加比赛"""
    # 检查比赛是否存在
    contest_sql = "SELECT 1 FROM contest WHERE contest_id = :contest_id LIMIT 1"
    contest = fetch_one(db, contest_sql, {"contest_id": contest_id})
    if not contest:
        raise HTTPException(status_code=404, detail="比赛不存在")
    
    # 检查是否已经报名
    existing_sql = """
        SELECT 1 FROM contest_user 
        WHERE contest_id = :contest_id AND user_id = :user_id
        LIMIT 1
    """
    existing = fetch_one(db, existing_sql, {
        "contest_id": contest_id,
        "user_id": user_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="已经报名该比赛")
    
    # 创建报名记录
    insert_sql = """
        INSERT INTO contest_user (contest_id, user_id)
        VALUES (:contest_id, :user_id)
    """
    execute_insert(db, insert_sql, {
        "contest_id": contest_id,
        "user_id": user_id
    })
    
    return {"message": "报名成功"}


@router.delete("/{contest_id}/register/{user_id}")
def unregister_contest(
    contest_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """取消报名"""
    # 检查报名记录是否存在
    check_sql = """
        SELECT 1 FROM contest_user 
        WHERE contest_id = :contest_id AND user_id = :user_id
        LIMIT 1
    """
    contest_user = fetch_one(db, check_sql, {
        "contest_id": contest_id,
        "user_id": user_id
    })
    
    if not contest_user:
        raise HTTPException(status_code=404, detail="未找到报名记录")
    
    # 删除报名记录
    delete_sql = """
        DELETE FROM contest_user 
        WHERE contest_id = :contest_id AND user_id = :user_id
    """
    execute_update(db, delete_sql, {
        "contest_id": contest_id,
        "user_id": user_id
    })
    
    return {"message": "取消报名成功"}


@router.post("/{contest_id}/publish_invisible_problems")
def publish_invisible_problems(
    contest_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    比赛结束后发布不可见题目到公开题库（仅管理员）
    
    处理比赛中 ID<10000 的不可见题目：
    1. 创建新题目（visible=True，自动获得 ID>=10000）
    2. 复制所有题目数据，并添加比赛标签
    3. 更新所有相关提交记录到新题目ID
    4. 更新 contest_problem 引用到新题目
    5. 删除旧题目（释放 ID<10000 的保留ID供后续重用）
    """
    # 检查管理员权限
    user_sql = "SELECT role FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可以发布题目")
    
    # 检查比赛是否存在
    contest_sql = "SELECT * FROM contest WHERE contest_id = :contest_id"
    contest = fetch_one(db, contest_sql, {"contest_id": contest_id})
    if not contest:
        raise HTTPException(status_code=404, detail="比赛不存在")
    
    # 获取比赛的所有题目
    cp_sql = "SELECT * FROM contest_problem WHERE contest_id = :contest_id"
    contest_problems = execute_query(db, cp_sql, {"contest_id": contest_id})
    
    published = []
    
    for cp in contest_problems:
        prob_sql = "SELECT * FROM problem WHERE problem_id = :problem_id"
        problem = fetch_one(db, prob_sql, {"problem_id": cp['problem_id']})
        if not problem:
            continue
        
        # 只处理ID<10000的不可见题目
        if problem['problem_id'] < 10000:
            old_id = problem['problem_id']
            
            # 准备标签（添加比赛来源标签）
            contest_tag = contest['title']
            new_tags = problem['tags'] if problem['tags'] else ""
            if contest_tag not in new_tags:
                new_tags = f"{new_tags},{contest_tag}" if new_tags else contest_tag
            
            # 创建新题目（visible=True，将自动获得 ID>=10000）
            insert_prob_sql = """
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
            new_id = execute_insert(db, insert_prob_sql, {
                "title": problem['title'],
                "description": problem['description'],
                "input_format": problem['input_format'],
                "output_format": problem['output_format'],
                "sample_input": problem['sample_input'],
                "sample_output": problem['sample_output'],
                "time_limit": problem['time_limit'],
                "memory_limit": problem['memory_limit'],
                "difficulty": problem['difficulty'],
                "tags": new_tags,
                "creator_id": problem['creator_id'],
                "test_cases": problem['test_cases'],
                "visible": True
            })
            
            # 更新所有相关提交记录的 problem_id，并将比赛提交转为题库提交
            update_subs_sql = """
                UPDATE submission 
                SET problem_id = :new_id, contest_id = NULL
                WHERE problem_id = :old_id AND contest_id = :contest_id
            """
            execute_update(db, update_subs_sql, {
                "new_id": new_id,
                "old_id": old_id,
                "contest_id": contest_id
            })
            
            # 更新其他比赛提交的problem_id（不修改contest_id）
            update_other_subs_sql = """
                UPDATE submission 
                SET problem_id = :new_id
                WHERE problem_id = :old_id AND (contest_id IS NULL OR contest_id != :contest_id)
            """
            execute_update(db, update_other_subs_sql, {
                "new_id": new_id,
                "old_id": old_id,
                "contest_id": contest_id
            })
            
            # 更新比赛题目关联到新ID
            update_cp_sql = """
                UPDATE contest_problem 
                SET problem_id = :new_id
                WHERE contest_id = :contest_id AND problem_id = :old_id
            """
            execute_update(db, update_cp_sql, {
                "new_id": new_id,
                "contest_id": contest_id,
                "old_id": old_id
            })
            
            # 删除旧题目（释放保留ID 1-9999）
            delete_prob_sql = "DELETE FROM problem WHERE problem_id = :problem_id"
            execute_update(db, delete_prob_sql, {"problem_id": old_id})
            
            published.append({
                "old_id": old_id,
                "new_id": new_id,
                "title": problem['title']
            })
    
    # 标记比赛题目已发布
    if published:
        update_contest_sql = """
            UPDATE contest 
            SET problems_published = TRUE
            WHERE contest_id = :contest_id
        """
        execute_update(db, update_contest_sql, {"contest_id": contest_id})
        
        # 记录活动日志
        log_sql = """
            INSERT INTO activity_log (user_id, action_type, entity_type, entity_id, description, created_at)
            VALUES (:user_id, :action_type, :entity_type, :entity_id, :description, :created_at)
        """
        execute_insert(db, log_sql, {
            "user_id": user_id,
            "action_type": "publish",
            "entity_type": "contest",
            "entity_id": contest_id,
            "description": f"将比赛《{contest['title']}》中的 {len(published)} 道题目发布到公开题库（ID已从保留区迁移到>=10000）",
            "created_at": datetime.utcnow()
        })

        # 比赛发布后触发等级分与统计计算，确保报名用户的等级分与比赛参与统计得到更新
        try:
            calculate_contest_ratings(contest, db)
        except Exception as e:
            # 记录错误但不回滚发布操作
            print(f"发布比赛 {contest_id} 后计算等级分失败: {e}")
    
    return {
        "message": f"成功发布 {len(published)} 道题目到公开题库",
        "detail": f"题目ID已从保留区（<10000）迁移到公开区（>=10000），原保留ID已释放可重用",
        "published": published
    }


@router.post("/{contest_id}/finalize")
def finalize_contest(
    contest_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    比赛赛后收尾：发布不可见题目并计算等级分。

    仅管理员可调用该接口（通常由运维或调度器触发）。此接口是幂等的：
    - 发布操作会跳过已发布的题目
    - 等级分计算包含幂等检查，避免重复加分
    """
    # 权限检查
    user_sql = "SELECT role FROM user WHERE user_id = :user_id"
    user = fetch_one(db, user_sql, {"user_id": user_id})
    if not user or user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可以 finalize 比赛")

    contest_sql = "SELECT * FROM contest WHERE contest_id = :contest_id"
    contest = fetch_one(db, contest_sql, {"contest_id": contest_id})
    if not contest:
        raise HTTPException(status_code=404, detail="比赛不存在")

    # 1) 尝试发布不可见题目（函数内部会跳过已发布）
    try:
        auto_publish_contest_problems(contest, db)
    except Exception as e:
        print(f"finalize: auto publish failed for contest {contest_id}: {e}")

    # 2) 计算并更新等级分（calculate_contest_ratings 内部有幂等保护）
    try:
        calculate_contest_ratings(contest, db)
    except Exception as e:
        print(f"finalize: calculate_contest_ratings failed for contest {contest_id}: {e}")

    return {"message": "比赛已 finalize（发布题目并计算等级分，若有需要会在后台记录错误）"}
