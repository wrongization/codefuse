from typing import Optional, Tuple
import json
import time
from datetime import datetime

from app.database import SessionLocal, execute_update, fetch_one
from app.judge_engine import JudgeEngine


def run_submission_judge(submission_id: int, db=None):
    """Run judge for a submission. If db is None, creates its own SessionLocal and closes it.

    This function contains the core logic previously inside `judge_submission` so it can be
    executed either synchronously (with a provided db session) or asynchronously in a worker
    thread (where it will create its own db session).
    """
    created_session = False
    if db is None:
        db = SessionLocal()
        created_session = True

    try:
        # 获取提交记录
        sub_sql = "SELECT * FROM submission WHERE submission_id = :submission_id"
        submission = fetch_one(db, sub_sql, {"submission_id": submission_id})
        if not submission:
            raise ValueError("提交记录不存在")

        # 获取题目信息
        prob_sql = "SELECT * FROM problem WHERE problem_id = :problem_id"
        problem = fetch_one(db, prob_sql, {"problem_id": submission['problem_id']})
        if not problem:
            raise ValueError("题目不存在")

        # 获取测试点
        test_cases = json.loads(problem['test_cases']) if problem.get('test_cases') else []

        if not test_cases:
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

        # 初始化评测引擎
        judge_engine = JudgeEngine()

        total_score = 0
        max_time = 0
        max_memory = 0
        final_status = 'accepted'
        judge_results_list = []

        try:
            for idx, test_case in enumerate(test_cases):
                status_result, time_used, memory_used, error_msg, actual_output = judge_engine.judge(
                    code=submission['code'],
                    language=submission['language'],
                    input_data=test_case.get('input_data', ''),
                    expected_output=test_case.get('output_data', ''),
                    time_limit=problem.get('time_limit'),
                    memory_limit=problem.get('memory_limit')
                )

                score = test_case.get('score', 10) if status_result == 'accepted' else 0
                total_score += score
                max_time = max(max_time, time_used)
                max_memory = max(max_memory, memory_used)

                judge_result = {
                    "test_case_index": idx,
                    "status": status_result,
                    "time_used": time_used,
                    "memory_used": memory_used,
                    "score": score,
                    "error_message": error_msg,
                    "input_data": test_case.get('input_data', ''),
                    "expected_output": test_case.get('output_data', ''),
                    "actual_output": actual_output
                }
                judge_results_list.append(judge_result)

                if status_result != 'accepted' and final_status == 'accepted':
                    final_status = status_result

            # 所有测试点完成后写回数据库
            judge_results_json = json.dumps(judge_results_list)
            update_sql = """
                UPDATE submission 
                SET status = :status, exec_time = :exec_time, exec_memory = :exec_memory, judge_results = :judge_results
                WHERE submission_id = :submission_id
            """
            execute_update(db, update_sql, {
                "status": final_status,
                "exec_time": max_time,
                "exec_memory": max_memory,
                "judge_results": judge_results_json,
                "submission_id": submission_id
            })
        except Exception as e:
            # 若出现未捕获异常，确保不会把提交一直留在 judging 状态，记录为 system_error
            try:
                error_result = [{
                    "test_case_index": -1,
                    "status": "system_error",
                    "time_used": 0,
                    "memory_used": 0,
                    "score": 0,
                    "error_message": str(e),
                    "input_data": "",
                    "expected_output": "",
                    "actual_output": ""
                }]
                execute_update(db, """
                    UPDATE submission 
                    SET status = :status, exec_time = :exec_time, exec_memory = :exec_memory, judge_results = :judge_results
                    WHERE submission_id = :submission_id
                """, {
                    "status": 'system_error',
                    "exec_time": max_time,
                    "exec_memory": max_memory,
                    "judge_results": json.dumps(error_result),
                    "submission_id": submission_id
                })
            except Exception:
                pass
            # 不抛出异常以免线程池日志混乱；已将状态更新到 DB
            return

    finally:
        if created_session:
            try:
                db.close()
            except Exception:
                pass
