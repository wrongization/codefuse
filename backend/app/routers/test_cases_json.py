"""
测试用例管理路由（JSON 模式）

直接读写 `problem.test_cases` JSON 字段。前端在 JSON 模式下可将数组索引作为
`test_case_id` 进行引用。实现包含：单个创建、批量创建、查询（含隐藏/样例过滤）、更新和删除。
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Any

from app.database import get_db, execute_update, fetch_one, execute_query
from app.schemas import TestCaseCreate, TestCaseUpdate, TestCaseData
import uuid
import logging
from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/test-cases", tags=["test-cases"])

logger = logging.getLogger("app.test_cases")


def _load_problem_test_cases_json(db, problem_id: int):
    logger.debug("_load_problem_test_cases_json called for problem_id=%s", problem_id)
    p = fetch_one(db, "SELECT test_cases, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    if p is None:
        return None
    tcs = p.get('test_cases')
    if isinstance(tcs, str):
        try:
            import json as _json
            tcs = _json.loads(tcs)
        except Exception:
            tcs = []
    if not isinstance(tcs, list):
        tcs = []
    normalized = []
    for idx, tc in enumerate(tcs):
        if not isinstance(tc, dict):
            tc = {}
        normalized.append({
            'test_case_id': idx,
            'id': tc.get('id'),
            'input_data': tc.get('input_data',''),
            'output_data': tc.get('output_data',''),
            'score': tc.get('score', 10),
            'is_sample': tc.get('is_sample', 0),
            'order': tc.get('order', idx)
        })
    return normalized


def _save_problem_test_cases_json(db, problem_id: int, tcs: list):
    import json as _json
    logger.info("_save_problem_test_cases_json: saving %d test cases for problem_id=%s", len(tcs), problem_id)
    simple = []
    for tc in tcs:
        # ensure each test case has a stable id
        tc_id = tc.get('id') or getattr(tc, 'id', None) or str(uuid.uuid4())
        simple.append({
            'id': tc_id,
            'input_data': tc.get('input_data',''),
            'output_data': tc.get('output_data',''),
            'score': int(tc.get('score', 10)),
            'is_sample': int(tc.get('is_sample', 0)),
            'order': int(tc.get('order', 0))
        })
    update_sql = "UPDATE problem SET test_cases = :test_cases WHERE problem_id = :problem_id"
    execute_update(db, update_sql, {"test_cases": _json.dumps(simple), "problem_id": problem_id})
    logger.debug("_save_problem_test_cases_json: saved test_cases for problem_id=%s", problem_id)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_test_case(
    test_case: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": test_case.problem_id})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员或题目创建者可以添加测试用例")

    tcs = _load_problem_test_cases_json(db, test_case.problem_id) or []
    existing_score = sum(tc.get('score',0) for tc in tcs)
    if existing_score + int(test_case.score) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"测试点分数总和不能超过100分，当前已有{existing_score}分，添加{test_case.score}分后将超出限制")

    new = {
        'id': test_case.id or str(uuid.uuid4()),
        'input_data': test_case.input_data,
        'output_data': test_case.output_data,
        'score': int(test_case.score),
        'is_sample': int(test_case.is_sample),
        'order': int(test_case.order)
    }
    tcs.append(new)
    _save_problem_test_cases_json(db, test_case.problem_id, tcs)
    return {**new, 'test_case_id': len(tcs)-1}


@router.post("/batch", response_model=List[dict])
def batch_create_test_cases(
    test_cases: List[TestCaseCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量向 problem.test_cases 中追加测试点（所有 test_cases 必须属于同一题目）"""
    if not test_cases:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="测试用例列表不能为空")
    problem_ids = set(tc.problem_id for tc in test_cases)
    if len(problem_ids) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="批量创建的测试用例必须属于同一题目")
    problem_id = test_cases[0].problem_id
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员或题目创建者可以添加测试用例")
    tcs = _load_problem_test_cases_json(db, problem_id) or []
    existing_score = sum(tc.get('score',0) for tc in tcs)
    # test_cases here are Pydantic models; access attributes
    new_score = sum(int(getattr(tc, 'score', 0)) for tc in test_cases)
    if existing_score + new_score > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"测试点分数总和不能超过100分，当前已有{existing_score}分，批量添加{new_score}分后将超出限制")
    start_index = len(tcs)
    new_items = []
    for i, tc in enumerate(test_cases):
        item = {
            'id': getattr(tc, 'id', None) or str(uuid.uuid4()),
            'input_data': tc.input_data,
            'output_data': tc.output_data,
            'score': int(tc.score),
            'is_sample': int(tc.is_sample),
            'order': int(tc.order)
        }
        tcs.append(item)
        new_items.append({**item, 'test_case_id': start_index + i})
    _save_problem_test_cases_json(db, problem_id, tcs)
    return new_items


@router.get("/problem/{problem_id}", response_model=List[dict])
def get_problem_test_cases(
    problem_id: int,
    include_hidden: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if include_hidden:
        if current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员或题目创建者可以查看隐藏测试用例")

    all_tcs = _load_problem_test_cases_json(db, problem_id) or []
    if include_hidden:
        return all_tcs
    return [tc for tc in all_tcs if tc.get('is_sample') == 1]


@router.put("/sync", response_model=List[dict])
async def sync_test_cases(
    request: Request,
    problem_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """原子化地用前端提供的完整测试点数组替换 problem.test_cases。
    前端应当将最终的 test_cases 数组整体发送过来（body 为数组），并在查询参数中提供 problem_id。
    这样避免了索引移动导致的删除/更新错位问题。
    """
    if problem_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON 模式下请提供 problem_id")
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员或题目创建者可以修改测试用例")

    # 验证并归一化输入的 test_cases
    # 支持更宽松的输入格式：前端发送数组或对象数组（元素为 dict），也容错处理 pydantic 验证错误并给出更友好的 400
    simple_list = []
    total_score = 0
    # 读取原始请求体并解析为 JSON（容错处理）
    try:
        test_cases = await request.json()
    except Exception as e:
        logger.exception("sync_test_cases: failed to parse request.json: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法解析请求体为 JSON")
    if not isinstance(test_cases, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体应为测试点数组 (JSON 数组)")
    logger.info("sync_test_cases: user=%s, problem_id=%s, incoming_count=%d", getattr(current_user, 'username', None), problem_id, len(test_cases))
    for idx, raw_tc in enumerate(test_cases):
        # 尝试把每个元素转换为 TestCaseData（兼容 pydantic v1/v2）
        try:
            if isinstance(raw_tc, TestCaseData):
                tc_obj = raw_tc
            else:
                # prefer model_validate if available (pydantic v2), else instantiate
                if hasattr(TestCaseData, 'model_validate'):
                    tc_obj = TestCaseData.model_validate(raw_tc)
                else:
                    tc_obj = TestCaseData(**raw_tc)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"测试点格式错误 (index={idx}): {str(e)}")
        score = int(getattr(tc_obj, 'score', 0) or 0)
        total_score += score
        simple_list.append({
            'id': getattr(tc_obj, 'id', None),
            'input_data': getattr(tc_obj, 'input_data', ''),
            'output_data': getattr(tc_obj, 'output_data', ''),
            'score': score,
            'is_sample': int(getattr(tc_obj, 'is_sample', 0) or 0),
            'order': int(getattr(tc_obj, 'order', idx) if getattr(tc_obj, 'order', None) is not None else idx)
        })

    if total_score > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"测试点分数总和不能超过100分，总和为{total_score}")
    logger.info("sync_test_cases: validated total_score=%s for problem_id=%s", total_score, problem_id)

    # 保存并返回包含 test_case_id（索引）的数组
    try:
        _save_problem_test_cases_json(db, problem_id, simple_list)
    except Exception as e:
        logger.exception("sync_test_cases: failed to save test cases for problem_id=%s: %s", problem_id, e)
        raise
    normalized = []
    for idx, tc in enumerate(simple_list):
        normalized.append({**tc, 'test_case_id': idx})
# duplicate sync implementation removed (moved earlier to avoid path-param capture)
    return normalized


@router.get("/{test_case_id}", response_model=dict)
def get_test_case(
    test_case_id: int,
    problem_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if problem_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON 模式下请提供 problem_id 查询参数")
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    tcs = _load_problem_test_cases_json(db, problem_id) or []
    idx = test_case_id
    if idx < 0 or idx >= len(tcs):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="测试用例不存在")
    tc = tcs[idx]
    if tc.get('is_sample',0) == 0 and current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看隐藏测试用例")
    return tc


@router.get('/by-id/{tc_uuid}', response_model=dict)
def get_test_case_by_uuid(
    tc_uuid: str,
    problem_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if problem_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON 模式下请提供 problem_id 查询参数")
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    tcs = _load_problem_test_cases_json(db, problem_id) or []
    for tc in tcs:
        if tc.get('id') == tc_uuid:
            if tc.get('is_sample',0) == 0 and current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看隐藏测试用例")
            return tc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='测试用例不存在')


@router.put("/{test_case_id}", response_model=dict)
def update_test_case(
    test_case_id: int,
    test_case_update: TestCaseUpdate,
    problem_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if problem_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON 模式下请提供 problem_id")
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员或题目创建者可以修改测试用例")
    tcs = _load_problem_test_cases_json(db, problem_id) or []
    idx = test_case_id
    if idx < 0 or idx >= len(tcs):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="测试用例不存在")
    update_data = test_case_update.model_dump(exclude_unset=True)
    if 'score' in update_data:
        existing_score = sum(tc.get('score',0) for i,tc in enumerate(tcs) if i != idx)
        if existing_score + int(update_data['score']) > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"测试点分数总和不能超过100分，更新后总分将超出限制")
    for k, v in update_data.items():
        if k in ['input_data','output_data','score','is_sample','order']:
            tcs[idx][k] = v
    _save_problem_test_cases_json(db, problem_id, tcs)
    return tcs[idx]


@router.put('/id/{tc_uuid}', response_model=dict)
def update_test_case_by_uuid(
    tc_uuid: str,
    test_case_update: TestCaseUpdate,
    problem_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if problem_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON 模式下请提供 problem_id")
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": problem_id})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员或题目创建者可以修改测试用例")
    tcs = _load_problem_test_cases_json(db, problem_id) or []
    found = None
    for idx, tc in enumerate(tcs):
        if tc.get('id') == tc_uuid:
            found = idx
            break
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='测试用例不存在')
    idx = found
    update_data = test_case_update.model_dump(exclude_unset=True)
    if 'score' in update_data:
        existing_score = sum(tc.get('score',0) for i,tc in enumerate(tcs) if i != idx)
        if existing_score + int(update_data['score']) > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"测试点分数总和不能超过100分，更新后总分将超出限制")
    for k, v in update_data.items():
        if k in ['input_data','output_data','score','is_sample','order']:
            tcs[idx][k] = v
    _save_problem_test_cases_json(db, problem_id, tcs)
    return tcs[idx]


@router.delete("/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(
    test_case_id: int,
    problem_id: Optional[int] = None,
    problem_id_body: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 支持两种方式提供 problem_id：query 参数或请求体（兼容某些客户端不方便传 query 的情况）
    pid = problem_id if problem_id is not None else problem_id_body
    # 如果仍未提供 problem_id，尝试在所有题目中查找第一个包含该索引的题目（宽容回退）
    if pid is None:
        matches = []
        # 一次性读取 problem_id 和 creator_id，尽量减少额外查询
        rows = execute_query(db, "SELECT problem_id, creator_id FROM problem WHERE test_cases IS NOT NULL")
        for r in rows:
            pid_candidate = r.get('problem_id')
            try:
                tcs = _load_problem_test_cases_json(db, pid_candidate) or []
            except Exception:
                tcs = []
            if isinstance(tcs, list) and test_case_id >= 0 and test_case_id < len(tcs):
                matches.append({
                    'problem_id': pid_candidate,
                    'creator_id': r.get('creator_id')
                })
        logger.debug("delete_test_case: candidates for index %s -> %s", test_case_id, [m['problem_id'] for m in matches])
        if len(matches) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未提供 problem_id，且未找到包含该索引的题目。请在请求中添加 problem_id 参数")

        # 如果有多个匹配，优先选择当前用户有权限管理的题目（即创建者为当前用户）。
        if len(matches) > 1:
            manageable = []
            for m in matches:
                if current_user.role == 'admin' or m.get('creator_id') == current_user.user_id:
                    manageable.append(m['problem_id'])
            # 如果恰好有一个可管理的题目，采用该题目
            if len(manageable) == 1:
                pid = manageable[0]
            else:
                # 如果没有可管理的题目或可管理题目仍然多个，返回歧义错误，要求客户端指定 problem_id
                candidate_ids = [m['problem_id'] for m in matches]
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"多个题目包含该测试点索引，请在请求中明确指定 problem_id。候选: {candidate_ids}")
        else:
            pid = matches[0]['problem_id']
    logger.info("delete_test_case: resolved problem_id=%s for index %s by user=%s", pid, test_case_id, getattr(current_user, 'username', None))
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": pid})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员或题目创建者可以删除测试用例")
    tcs = _load_problem_test_cases_json(db, pid) or []
    idx = test_case_id
    if idx < 0 or idx >= len(tcs):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="测试用例不存在")
    tcs.pop(idx)
    _save_problem_test_cases_json(db, pid, tcs)
    return None


@router.delete('/id/{tc_uuid}', status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case_by_uuid(
    tc_uuid: str,
    problem_id: Optional[int] = None,
    problem_id_body: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pid = problem_id if problem_id is not None else problem_id_body
    if pid is None:
        # try to find unique candidate where tc_uuid exists
        rows = execute_query(db, "SELECT problem_id, creator_id FROM problem WHERE test_cases IS NOT NULL")
        matches = []
        for r in rows:
            try:
                tcs = _load_problem_test_cases_json(db, r['problem_id']) or []
            except Exception:
                tcs = []
            for tc in tcs:
                if tc.get('id') == tc_uuid:
                    matches.append({'problem_id': r['problem_id'], 'creator_id': r.get('creator_id')})
                    break
        logger.debug("delete_test_case_by_uuid: candidates for uuid %s -> %s", tc_uuid, [m['problem_id'] for m in matches])
        if len(matches) == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='测试用例不存在')
        if len(matches) > 1:
            manageable = [m['problem_id'] for m in matches if current_user.role == 'admin' or m.get('creator_id') == current_user.user_id]
            if len(manageable) == 1:
                pid = manageable[0]
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"多个题目包含该测试点，请在请求中明确指定 problem_id。候选: {[m['problem_id'] for m in matches]}")
        else:
            pid = matches[0]['problem_id']
    logger.info("delete_test_case_by_uuid: resolved problem_id=%s for uuid=%s by user=%s", pid, tc_uuid, getattr(current_user, 'username', None))
    problem = fetch_one(db, "SELECT problem_id, creator_id FROM problem WHERE problem_id = :problem_id", {"problem_id": pid})
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    if current_user.role != 'admin' and problem['creator_id'] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有管理员或题目创建者可以删除测试用例")
    tcs = _load_problem_test_cases_json(db, pid) or []
    found = None
    for idx, tc in enumerate(tcs):
        if tc.get('id') == tc_uuid:
            found = idx
            break
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='测试用例不存在')
    tcs.pop(found)
    _save_problem_test_cases_json(db, pid, tcs)
    return None
