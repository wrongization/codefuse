"""
数据库重置脚本
用于将数据库恢复到初始状态,并插入测试样例数据

使用方法：
    cd backend
    uv run python reset_database.py

警告：此脚本会删除所有数据！请谨慎使用！
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

# 设置工作目录为脚本所在目录
script_dir = Path(__file__).parent
os.chdir(script_dir)

# 添加项目根目录到路径
sys.path.insert(0, str(script_dir))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import engine, SessionLocal, Base
from app.models import (
    User,
    Problem,
    Contest,
    Submission,
    Message,
    ContestProblem,
    ContestUser,
    UserSubmission,
    MessageProblem,
    MessageRecipient,
    ProblemSubmission,
)
from app.auth import get_password_hash


def drop_all_tables():
    """删除所有表"""
    print("🗑️  正在删除所有表...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            Base.metadata.drop_all(bind=engine)
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            conn.commit()
        print("✅ 所有表已删除")
    except Exception as e:
        print(f"❌ 删除表时出错: {e}")


def create_all_tables():
    """创建所有表（包括评测系统表）"""
    print("📋 正在创建所有表...")
    Base.metadata.create_all(bind=engine)
    ensure_problem_submission_table()
    
    # 设置 problem 表的自增起始值为 10000
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE problem AUTO_INCREMENT = 10000"))
            conn.commit()
            print("  ✅ 已设置 problem 表 AUTO_INCREMENT 起始值为 10000")
    except Exception as e:
        print(f"  ⚠️  设置 problem AUTO_INCREMENT 时出错: {e}")
    
    print("✅ 所有表已创建")


def ensure_problem_submission_table():
    """确保题目-提交关系表存在且结构合规"""
    try:
        ProblemSubmission.__table__.create(bind=engine, checkfirst=True)
        print("  ✅ 已确保 problem_submission 表存在")
    except Exception as e:
        print(f"  ⚠️  创建 problem_submission 表时出错: {e}")


def hash_password(password: str) -> str:
    """加密密码"""
    return get_password_hash(password)


def insert_sample_data(db: Session):
    """插入样例数据"""
    print("📝 正在插入样例数据...")
    
    # 1. 创建用户
    print("  👤 创建用户...")
    users_data = [
        {"username": "张三", "password": "123456", "email": "zhangsan@example.com", "school": "北京大学", "rating": 1200, "role": "user"},
        {"username": "李四", "password": "123456", "email": "lisi@example.com", "school": "清华大学", "rating": 1500, "role": "user"},
        {"username": "王五", "password": "123456", "email": "wangwu@example.com", "school": "复旦大学", "rating": 1000, "role": "user"},
        {"username": "赵六", "password": "123456", "email": "zhaoliu@example.com", "school": "上海交通大学", "rating": 1300, "role": "user"},
        {"username": "钱七", "password": "123456", "email": "qianqi@example.com", "school": "浙江大学", "rating": 1100, "role": "user"},
        {"username": "admin", "password": "admin123", "email": "admin@codefuse.com", "school": "CodeFuse", "rating": 2000, "role": "admin"},
    ]
    
    users = []
    for user_data in users_data:
        user = User(
            username=user_data["username"],
            password=hash_password(user_data["password"]),
            email=user_data["email"],
            school=user_data["school"],
            rating=user_data["rating"],
            role=user_data["role"],
        )
        db.add(user)
        users.append(user)
    
    db.commit()
    print(f"  ✅ 创建了 {len(users)} 个用户")
    
    # 2. 创建题目
    print("  📚 创建题目...")
    problems_data = [
        # 从已结束比赛迁移过来的题目（原来是 ID 1,2,3，现在在题库中）
        {
            "title": "[已发布] 简单加法",
            "description": "计算两个整数的和\n\n本题来自：CodeFuse 新手赛",
            "input_format": "两个整数 a 和 b（-10^9 ≤ a, b ≤ 10^9）",
            "output_format": "输出 a + b 的结果",
            "sample_input": "1 2",
            "sample_output": "3",
            "time_limit": 1000,
            "memory_limit": 1024,
            "difficulty": "easy",
            "tags": "数学,基础",
            "test_cases": [
                {"input_data": "1 2", "output_data": "3", "score": 20, "is_sample": 1, "order": 0},
                {"input_data": "100 200", "output_data": "300", "score": 20, "is_sample": 0, "order": 1},
                {"input_data": "-5 10", "output_data": "5", "score": 20, "is_sample": 0, "order": 2},
                {"input_data": "0 0", "output_data": "0", "score": 20, "is_sample": 0, "order": 3},
                {"input_data": "999999999 1", "output_data": "1000000000", "score": 20, "is_sample": 0, "order": 4},
            ],
        },
        {
            "title": "[已发布] 字符串反转",
            "description": "反转一个字符串\n\n本题来自：CodeFuse 新手赛",
            "input_format": "一个字符串（长度不超过1000）",
            "output_format": "输出反转后的字符串",
            "sample_input": "hello",
            "sample_output": "olleh",
            "time_limit": 1000,
            "memory_limit": 1024,
            "difficulty": "easy",
            "tags": "字符串,基础",
            "test_cases": [
                {"input_data": "hello", "output_data": "olleh", "score": 25, "is_sample": 1, "order": 0},
                {"input_data": "world", "output_data": "dlrow", "score": 25, "is_sample": 0, "order": 1},
                {"input_data": "a", "output_data": "a", "score": 25, "is_sample": 0, "order": 2},
                {"input_data": "racecar", "output_data": "racecar", "score": 25, "is_sample": 0, "order": 3},
            ],
        },
        {
            "title": "[已发布] 数组最大值",
            "description": "找出数组中的最大值\n\n本题来自：CodeFuse 新手赛",
            "input_format": "第一行包含整数n（1≤n≤1000），第二行包含n个整数",
            "output_format": "输出数组中的最大值",
            "sample_input": "5\n3 7 2 9 1",
            "sample_output": "9",
            "time_limit": 1000,
            "memory_limit": 1024,
            "difficulty": "easy",
            "tags": "数组,基础",
            "test_cases": [
                {"input_data": "5\n3 7 2 9 1", "output_data": "9", "score": 25, "is_sample": 1, "order": 0},
                {"input_data": "1\n42", "output_data": "42", "score": 25, "is_sample": 0, "order": 1},
                {"input_data": "4\n-5 -2 -8 -1", "output_data": "-1", "score": 25, "is_sample": 0, "order": 2},
                {"input_data": "3\n100 100 100", "output_data": "100", "score": 25, "is_sample": 0, "order": 3},
            ],
        },
        # 原有的题库题目
        {
            "title": "两数之和",
            "description": "给定一个整数数组 nums 和一个目标值 target，请你在该数组中找出和为目标值的那两个整数，并返回它们的数组下标。",
            "input_format": "第一行包含一个整数 n (2 ≤ n ≤ 10^4)，表示数组长度。\n第二行包含 n 个整数，表示数组元素。\n第三行包含一个整数 target，表示目标值。",
            "output_format": "输出两个整数，表示两个数的下标（从0开始），用空格分隔。",
            "sample_input": "4\n2 7 11 15\n9",
            "sample_output": "0 1",
            "time_limit": 1000,
            "memory_limit": 1024,
            "difficulty": "easy",
            "tags": "数组,哈希表",
            "test_cases": [
                {"input_data": "4\n2 7 11 15\n9", "output_data": "0 1", "score": 20, "is_sample": 1, "order": 0},
                {"input_data": "5\n3 2 4 1 5\n6", "output_data": "1 2", "score": 20, "is_sample": 0, "order": 1},
                {"input_data": "3\n3 3 6\n6", "output_data": "0 1", "score": 20, "is_sample": 0, "order": 2},
                {"input_data": "4\n-1 0 1 2\n1", "output_data": "1 2", "score": 20, "is_sample": 0, "order": 3},
                {"input_data": "2\n1 5\n6", "output_data": "0 1", "score": 20, "is_sample": 0, "order": 4},
            ],
        },
        {
            "title": "回文数",
            "description": "判断一个整数是否是回文数。回文数是指正序（从左向右）和倒序（从右向左）读都是一样的整数。",
            "input_format": "一个整数 x (-2^31 ≤ x ≤ 2^31 - 1)",
            "output_format": "如果是回文数输出 true，否则输出 false",
            "sample_input": "121",
            "sample_output": "true",
            "time_limit": 1000,
            "memory_limit": 1024,
            "difficulty": "easy",
            "tags": "数学",
            "test_cases": [
                {"input_data": "121", "output_data": "true", "score": 20, "is_sample": 1, "order": 0},
                {"input_data": "-121", "output_data": "false", "score": 20, "is_sample": 0, "order": 1},
                {"input_data": "10", "output_data": "false", "score": 20, "is_sample": 0, "order": 2},
                {"input_data": "1221", "output_data": "true", "score": 20, "is_sample": 0, "order": 3},
                {"input_data": "0", "output_data": "true", "score": 20, "is_sample": 0, "order": 4},
            ],
        },
        # 中等题目
        {
            "title": "最长回文子串",
            "description": "给你一个字符串 s，找到 s 中最长的回文子串。",
            "input_format": "一个字符串 s (1 ≤ length ≤ 1000)",
            "output_format": "输出最长的回文子串",
            "sample_input": "babad",
            "sample_output": "bab",
            "time_limit": 2000,
            "memory_limit": 2048,
            "difficulty": "medium",
            "tags": "字符串,动态规划",
            "test_cases": [
                {"input_data": "babad", "output_data": "bab", "score": 25, "is_sample": 1, "order": 0},
                {"input_data": "cbbd", "output_data": "bb", "score": 25, "is_sample": 0, "order": 1},
                {"input_data": "a", "output_data": "a", "score": 25, "is_sample": 0, "order": 2},
                {"input_data": "abcba", "output_data": "abcba", "score": 25, "is_sample": 0, "order": 3},
            ],
        },
        {
            "title": "三数之和",
            "description": "给你一个包含 n 个整数的数组 nums，判断 nums 中是否存在三个元素 a，b，c ，使得 a + b + c = 0 ？请你找出所有和为 0 且不重复的三元组。",
            "input_format": "第一行包含一个整数 n (3 ≤ n ≤ 3000)\n第二行包含 n 个整数",
            "output_format": "输出所有满足条件的三元组，每行一个，用空格分隔",
            "sample_input": "6\n-1 0 1 2 -1 -4",
            "sample_output": "-1 -1 2\n-1 0 1",
            "time_limit": 200,
            "memory_limit": 1024,
            "difficulty": "medium",
            "tags": "数组,双指针",
            "test_cases": [
                {"input_data": "6\n-1 0 1 2 -1 -4", "output_data": "-1 -1 2\n-1 0 1", "score": 25, "is_sample": 1, "order": 0},
                {"input_data": "3\n0 0 0", "output_data": "0 0 0", "score": 25, "is_sample": 0, "order": 1},
                {"input_data": "3\n1 2 3", "output_data": "", "score": 25, "is_sample": 0, "order": 2},
                {"input_data": "5\n-2 0 1 1 2", "output_data": "-2 0 2\n-2 1 1", "score": 25, "is_sample": 0, "order": 3},
            ],
        },
        {
            "title": "无重复字符的最长子串",
            "description": "给定一个字符串 s ，请你找出其中不含有重复字符的最长子串的长度。",
            "input_format": "一个字符串 s (0 ≤ length ≤ 5×10^4)",
            "output_format": "输出最长不重复子串的长度",
            "sample_input": "abcabcbb",
            "sample_output": "3",
            "time_limit": 150,
            "memory_limit": 21024,
            "difficulty": "medium",
            "tags": "字符串,滑动窗口",
            "test_cases": [
                {"input_data": "abcabcbb", "output_data": "3", "score": 20, "is_sample": 1, "order": 0},
                {"input_data": "bbbbb", "output_data": "1", "score": 20, "is_sample": 0, "order": 1},
                {"input_data": "pwwkew", "output_data": "3", "score": 20, "is_sample": 0, "order": 2},
                {"input_data": "", "output_data": "0", "score": 20, "is_sample": 0, "order": 3},
                {"input_data": "abcdef", "output_data": "6", "score": 20, "is_sample": 0, "order": 4},
            ],
        },
        # 困难题目
        {
            "title": "正则表达式匹配",
            "description": "给你一个字符串 s 和一个字符规律 p，请你来实现一个支持 '.' 和 '*' 的正则表达式匹配。\n'.' 匹配任意单个字符\n'*' 匹配零个或多个前面的那一个元素",
            "input_format": "两行字符串，第一行是字符串 s，第二行是模式 p",
            "output_format": "如果匹配成功输出 true，否则输出 false",
            "sample_input": "aa\na*",
            "sample_output": "true",
            "time_limit": 3000,
            "memory_limit": 1024,
            "difficulty": "hard",
            "tags": "字符串,动态规划,递归",
            "test_cases": [
                {"input_data": "aa\na*", "output_data": "true", "score": 25, "is_sample": 1, "order": 0},
                {"input_data": "ab\n.*", "output_data": "true", "score": 25, "is_sample": 0, "order": 1},
                {"input_data": "aab\nc*a*b", "output_data": "true", "score": 25, "is_sample": 0, "order": 2},
                {"input_data": "mississippi\nmis*is*ip*.", "output_data": "true", "score": 25, "is_sample": 0, "order": 3},
            ],
        },
        {
            "title": "最长有效括号",
            "description": "给你一个只包含 '(' 和 ')' 的字符串，找出最长有效（格式正确且连续）括号子串的长度。",
            "input_format": "一个字符串 s (0 ≤ length ≤ 3×10^4)",
            "output_format": "输出最长有效括号子串的长度",
            "sample_input": "(()",
            "sample_output": "2",
            "time_limit": 200,
            "memory_limit": 1024,
            "difficulty": "hard",
            "tags": "字符串,动态规划,栈",
            "test_cases": [
                {"input_data": "(()", "output_data": "2", "score": 25, "is_sample": 1, "order": 0},
                {"input_data": ")()())", "output_data": "4", "score": 25, "is_sample": 0, "order": 1},
                {"input_data": "", "output_data": "0", "score": 25, "is_sample": 0, "order": 2},
                {"input_data": "()(())", "output_data": "6", "score": 25, "is_sample": 0, "order": 3},
            ],
        },
        {
            "title": "接雨水",
            "description": "给定 n 个非负整数表示每个宽度为 1 的柱子的高度图，计算按此排列的柱子，下雨之后能接多少雨水。",
            "input_format": "第一行包含一个整数 n (0 ≤ n ≤ 2×10^4)\n第二行包含 n 个非负整数，表示高度",
            "output_format": "输出能接的雨水总量",
            "sample_input": "12\n0 1 0 2 1 0 1 3 2 1 2 1",
            "sample_output": "6",
            "time_limit": 2000,
            "memory_limit": 1024,
            "difficulty": "hard",
            "tags": "数组,双指针,栈",
            "test_cases": [
                {"input_data": "12\n0 1 0 2 1 0 1 3 2 1 2 1", "output_data": "6", "score": 25, "is_sample": 1, "order": 0},
                {"input_data": "6\n4 2 0 3 2 5", "output_data": "9", "score": 25, "is_sample": 0, "order": 1},
                {"input_data": "1\n5", "output_data": "0", "score": 25, "is_sample": 0, "order": 2},
                {"input_data": "5\n1 2 3 4 5", "output_data": "0", "score": 25, "is_sample": 0, "order": 3},
            ],
        },
    ]
    
    problems = []
    for i, problem_data in enumerate(problems_data):
        problem = Problem(
            title=problem_data["title"],
            description=problem_data["description"],
            input_format=problem_data["input_format"],
            output_format=problem_data["output_format"],
            sample_input=problem_data["sample_input"],
            sample_output=problem_data["sample_output"],
            time_limit=problem_data["time_limit"],
            memory_limit=problem_data["memory_limit"],
            difficulty=problem_data["difficulty"],
            tags=problem_data["tags"],
            test_cases=problem_data.get("test_cases", []),  # 添加测试点数据
            creator_id=users[5].user_id,  # admin创建（admin是第6个用户）
            visible=True,  # 可见题目，ID从10000开始
        )
        db.add(problem)
        problems.append(problem)
    
    db.commit()
    print(f"  ✅ 创建了 {len(problems)} 道题库题目（包含 3 道从已结束比赛迁移的题目）")
    
    # 创建保留题目（仅用于未结束的比赛）
    print("  🔒 创建保留ID题目（用于进行中和未开始的比赛）...")
    # 注意：ID 1, 2, 3 的题目已经在 contests[0] 结束时被 auto_publish 迁移并删除
    # 所以这里只创建仍在使用的保留题目（ID 4, 5）
    invisible_problems_data = [
        {
            "title": "[比赛] 斐波那契数列",
            "description": "计算斐波那契数列的第n项（F(0)=0, F(1)=1, F(n)=F(n-1)+F(n-2)）",
            "input_format": "一个整数n（0≤n≤30）",
            "output_format": "输出F(n)的值",
            "sample_input": "10",
            "sample_output": "55",
            "time_limit": 1000,
            "memory_limit": 1024,
            "difficulty": "medium",
            "tags": "动态规划,递归",
            "test_cases": [
                {"input_data": "10", "output_data": "55", "score": 20, "is_sample": 1, "order": 0},
                {"input_data": "0", "output_data": "0", "score": 20, "is_sample": 0, "order": 1},
                {"input_data": "1", "output_data": "1", "score": 20, "is_sample": 0, "order": 2},
                {"input_data": "20", "output_data": "6765", "score": 20, "is_sample": 0, "order": 3},
                {"input_data": "30", "output_data": "832040", "score": 20, "is_sample": 0, "order": 4},
            ],
        },
        {
            "title": "[比赛] 质数判断",
            "description": "判断一个数是否为质数",
            "input_format": "一个整数n（2≤n≤10^6）",
            "output_format": "如果是质数输出YES，否则输出NO",
            "sample_input": "17",
            "sample_output": "YES",
            "time_limit": 1000,
            "memory_limit": 1024,
            "difficulty": "medium",
            "tags": "数学,质数",
            "test_cases": [
                {"input_data": "17", "output_data": "YES", "score": 20, "is_sample": 1, "order": 0},
                {"input_data": "2", "output_data": "YES", "score": 20, "is_sample": 0, "order": 1},
                {"input_data": "4", "output_data": "NO", "score": 20, "is_sample": 0, "order": 2},
                {"input_data": "97", "output_data": "YES", "score": 20, "is_sample": 0, "order": 3},
                {"input_data": "100", "output_data": "NO", "score": 20, "is_sample": 0, "order": 4},
            ],
        },
    ]
    
    invisible_problems = []
    # 手动分配保留ID，从4开始（1,2,3已经被迁移删除）
    for idx, inv_data in enumerate(invisible_problems_data, start=4):
        inv_problem = Problem(
            problem_id=idx,  # 手动指定ID：4, 5（ID 1,2,3 已被 auto_publish 删除）
            title=inv_data["title"],
            description=inv_data["description"],
            input_format=inv_data["input_format"],
            output_format=inv_data["output_format"],
            sample_input=inv_data["sample_input"],
            sample_output=inv_data["sample_output"],
            time_limit=inv_data["time_limit"],
            memory_limit=inv_data["memory_limit"],
            difficulty=inv_data["difficulty"],
            tags=inv_data["tags"],
            test_cases=inv_data.get("test_cases", []),
            creator_id=users[5].user_id,  # admin创建
            visible=True,  # 保留ID的题目也设为可见
        )
        db.add(inv_problem)
        invisible_problems.append(inv_problem)
    
    db.commit()
    print(f"  ✅ 创建了 {len(invisible_problems)} 道保留ID题目（ID 4-{3+len(invisible_problems)}，用于进行中和未开始的比赛）")
    
    # 3. 创建比赛
    print("  🏆 创建比赛...")
    # 使用当前时间动态计算比赛时间，确保三种状态
    now = datetime.now()
    contests_data = [
        {
            "title": "CodeFuse 新手赛",
            "description": "适合编程新手的入门比赛\n\n本场比赛已结束，现已开放为练习模式。",
            "start_time": now - timedelta(days=10),  # 10天前开始
            "end_time": now - timedelta(days=9),     # 9天前结束（已结束 > 1天）
            "problems_published": True,  # 已自动发布题目到题库
        },
        {
            "title": "CodeFuse 月赛 - 11月",
            "description": "CodeFuse 11月份月度编程比赛\n\n本场比赛正在进行中，欢迎参加！",
            "start_time": now - timedelta(hours=2),  # 2小时前开始
            "end_time": now + timedelta(hours=2),    # 2小时后结束（正在进行中）
            "problems_published": False,
        },
        {
            "title": "算法竞赛模拟赛",
            "description": "模拟 ACM 竞赛风格的练习赛\n\n本场比赛尚未开始，敬请期待。",
            "start_time": now + timedelta(days=7),   # 7天后开始
            "end_time": now + timedelta(days=8),     # 8天后结束（未开始）
            "problems_published": False,
        },
    ]
    
    contests = []
    for contest_data in contests_data:
        contest = Contest(
            title=contest_data["title"],
            description=contest_data["description"],
            start_time=contest_data["start_time"],
            end_time=contest_data["end_time"],
            creator_id=users[5].user_id,  # admin创建（admin是第6个用户）
            problems_published=contest_data.get("problems_published", False)  # 根据数据设置
        )
        db.add(contest)
        contests.append(contest)
    
    db.commit()
    print(f"  ✅ 创建了 {len(contests)} 场比赛")
    
    # 4. 添加比赛题目
    print("  🔗 关联比赛和题目...")
    # 新手赛（已结束，练习模式）
    # 注意：由于比赛已结束且 problems_published=True，原 ID 1,2,3 的保留题目已被 auto_publish 迁移
    # 迁移后的题目现在是 problems[0], problems[1], problems[2]（ID>=10000）
    # 迁移后的题目仍然保留在比赛关联中，指向新的 ID
    db.add(ContestProblem(contest_id=contests[0].contest_id, problem_id=problems[0].problem_id))  # 简单加法（已迁移到题库）
    db.add(ContestProblem(contest_id=contests[0].contest_id, problem_id=problems[1].problem_id))  # 字符串反转（已迁移到题库）
    db.add(ContestProblem(contest_id=contests[0].contest_id, problem_id=problems[2].problem_id))  # 数组最大值（已迁移到题库）
    db.add(ContestProblem(contest_id=contests[0].contest_id, problem_id=problems[3].problem_id))  # 两数之和（题库题目）
    db.add(ContestProblem(contest_id=contests[0].contest_id, problem_id=problems[4].problem_id))  # 回文数（题库题目）
    
    # 月赛（正在进行中）
    # 包含题库题目和保留题目的混合
    db.add(ContestProblem(contest_id=contests[1].contest_id, problem_id=problems[4].problem_id))  # 回文数 (ID>=10000)
    db.add(ContestProblem(contest_id=contests[1].contest_id, problem_id=problems[5].problem_id))  # 最长回文子串 (ID>=10000)
    db.add(ContestProblem(contest_id=contests[1].contest_id, problem_id=problems[6].problem_id))  # 三数之和 (ID>=10000)
    db.add(ContestProblem(contest_id=contests[1].contest_id, problem_id=invisible_problems[0].problem_id))  # 斐波那契 (ID=4 保留)
    db.add(ContestProblem(contest_id=contests[1].contest_id, problem_id=problems[8].problem_id))  # 正则表达式匹配 (ID>=10000)
    
    # 算法竞赛模拟赛（未开始）
    # 包含题库题目和保留题目的混合
    db.add(ContestProblem(contest_id=contests[2].contest_id, problem_id=invisible_problems[1].problem_id))  # 质数判断 (ID=5 保留)
    db.add(ContestProblem(contest_id=contests[2].contest_id, problem_id=problems[7].problem_id))  # 无重复字符的最长子串 (ID>=10000)
    db.add(ContestProblem(contest_id=contests[2].contest_id, problem_id=problems[8].problem_id))  # 正则表达式匹配 (ID>=10000)
    db.add(ContestProblem(contest_id=contests[2].contest_id, problem_id=problems[9].problem_id))  # 最长有效括号 (ID>=10000)
    db.add(ContestProblem(contest_id=contests[2].contest_id, problem_id=problems[10].problem_id))  # 接雨水 (ID>=10000)
    
    db.commit()
    print("  ✅ 比赛题目关联完成")
    
    # 5. 用户参加比赛
    print("  👥 用户报名比赛...")
    # 所有用户参加新手赛
    for i in range(5):
        db.add(ContestUser(contest_id=contests[0].contest_id, user_id=users[i].user_id))
    
    # 部分用户参加月赛
    db.add(ContestUser(contest_id=contests[1].contest_id, user_id=users[0].user_id))  # 张三
    db.add(ContestUser(contest_id=contests[1].contest_id, user_id=users[1].user_id))  # 李四
    db.add(ContestUser(contest_id=contests[1].contest_id, user_id=users[3].user_id))  # 赵六
    
    # 少数高手参加模拟赛
    db.add(ContestUser(contest_id=contests[2].contest_id, user_id=users[1].user_id))  # 李四
    db.add(ContestUser(contest_id=contests[2].contest_id, user_id=users[4].user_id))  # 钱七
    
    db.commit()
    print("  ✅ 用户报名完成")
    
    # 6. 创建提交记录
    print("  📤 创建示例提交...")
    submissions_data = [
        # 张三的提交（题库提交）
        {
            "user": users[0],
            "problem": problems[3],  # 两数之和（原题库题目）
            "contest": None,
            "code": 'def two_sum(nums, target):\n    d = {}\n    for i, n in enumerate(nums):\n        if target - n in d:\n            return [d[target - n], i]\n        d[n] = i',
            "language": "python",
            "status": "accepted",
            "exec_time": 45,
            "exec_memory": 14336,
        },
        {
            "user": users[0],
            "problem": problems[4],  # 回文数（原题库题目）
            "contest": None,
            "code": 'def is_palindrome(x):\n    return str(x) == str(x)[::-1]',
            "language": "python",
            "status": "accepted",
            "exec_time": 32,
            "exec_memory": 13824,
        },
        {
            "user": users[0],
            "problem": problems[5],  # 最长回文子串
            "contest": None,
            "code": 'def longest_palindrome(s):\n    # 中心扩展法\n    pass',
            "language": "python",
            "status": "wrong_answer",
            "exec_time": 0,
            "exec_memory": 0,
        },
        # 李四的提交（正在进行的比赛 contests[1] 的提交）
        {
            "user": users[1],
            "problem": problems[4],  # 回文数
            "contest": contests[1],
            "code": 'def is_palindrome(x):\n    return str(x) == str(x)[::-1]',
            "language": "python",
            "status": "accepted",
            "exec_time": 30,
            "exec_memory": 13500,
        },
        {
            "user": users[1],
            "problem": problems[5],  # 最长回文子串
            "contest": contests[1],
            "code": 'def longest_palindrome(s):\n    # 动态规划\n    return "bab"',
            "language": "python",
            "status": "accepted",
            "exec_time": 120,
            "exec_memory": 15000,
        },
        {
            "user": users[1],
            "problem": problems[6],  # 三数之和
            "contest": contests[1],
            "code": 'def three_sum(nums):\n    nums.sort()\n    result = []\n    # 双指针算法\n    return result',
            "language": "python",
            "status": "accepted",
            "exec_time": 156,
            "exec_memory": 16384,
        },
        # 王五的提交（题库提交）
        {
            "user": users[2],
            "problem": problems[4],  # 回文数
            "contest": None,
            "code": 'def is_palindrome(x):\n    if x < 0:\n        return False\n    return True',
            "language": "python",
            "status": "wrong_answer",
            "exec_time": 0,
            "exec_memory": 0,
        },
        {
            "user": users[2],
            "problem": problems[0],  # 简单加法（从比赛迁移来的）
            "contest": None,
            "code": 'a, b = map(int, input().split())\nprint(a + b)',
            "language": "python",
            "status": "accepted",
            "exec_time": 25,
            "exec_memory": 13000,
        },
        # 赵六的提交（正在进行的比赛 contests[1] 的提交）
        {
            "user": users[3],
            "problem": problems[4],  # 回文数
            "contest": contests[1],
            "code": 'def is_palindrome(x):\n    s = str(x)\n    return s == s[::-1]',
            "language": "python",
            "status": "accepted",
            "exec_time": 35,
            "exec_memory": 14000,
        },
        {
            "user": users[3],
            "problem": problems[5],  # 最长回文子串
            "contest": None,
            "code": 'def longest_palindrome(s):\n    dp = [[False] * len(s) for _ in range(len(s))]\n    # 动态规划\n    return ""',
            "language": "python",
            "status": "accepted",
            "exec_time": 234,
            "exec_memory": 18432,
        },
        # 钱七的提交（题库提交）
        {
            "user": users[4],
            "problem": problems[7],  # 无重复字符的最长子串
            "contest": None,
            "code": 'def length_of_longest_substring(s):\n    from collections import defaultdict\n    d = defaultdict(int)\n    # 滑动窗口\n    return 0',
            "language": "python",
            "status": "runtime_error",
            "exec_time": 0,
            "exec_memory": 0,
        },
        {
            "user": users[4],
            "problem": problems[1],  # 字符串反转（从比赛迁移来的）
            "contest": None,
            "code": 's = input()\nprint(s[::-1])',
            "language": "python",
            "status": "accepted",
            "exec_time": 28,
            "exec_memory": 13568,
        },
    ]
    
    # 自动根据每个提交对应题目的 test_cases 生成评测结果，保证条目数量和内容一致。
    # 规则：
    #  - 若 submission.status == 'accepted'，则为该题所有测试点都标记为 accepted，actual_output 等于 expected_output，score 使用 test_case 中的 score。
    #  - 若 submission.status == 'wrong_answer'，则将前 N-1 个测试点标记为 accepted（并给分），最后一个标记为 wrong_answer（得分 0）。
    #  - 若 submission.status == 'runtime_error'，则第一个测试点标记为 runtime_error（得分 0），其他标记为 accepted（如有）。
    #  - time_used / memory_used 使用合理的示例值。
    judge_results_map = {}
    for i, sub in enumerate(submissions_data):
        problem = sub["problem"]
        tcs = problem.test_cases or []
        results = []
        if not isinstance(tcs, list) or len(tcs) == 0:
            # 如果题目没有测试点，跳过（保持 None）
            judge_results_map[i] = None
            continue

        if sub.get("status") == "accepted":
            for idx, tc in enumerate(tcs):
                results.append({
                    "test_case_index": idx,
                    "status": "accepted",
                    "time_used": 10 + idx * 2,
                    "memory_used": 13000 + idx * 256,
                    "score": int(tc.get("score", 0)),
                    "input_data": tc.get("input_data", ""),
                    "expected_output": tc.get("output_data", ""),
                    "actual_output": tc.get("output_data", ""),
                    "error_message": None,
                })
        elif sub.get("status") == "wrong_answer":
            # 前面通过，最后一个不通过
            for idx, tc in enumerate(tcs):
                if idx < len(tcs) - 1:
                    results.append({
                        "test_case_index": idx,
                        "status": "accepted",
                        "time_used": 8 + idx * 2,
                        "memory_used": 12000 + idx * 128,
                        "score": int(tc.get("score", 0)),
                        "input_data": tc.get("input_data", ""),
                        "expected_output": tc.get("output_data", ""),
                        "actual_output": tc.get("output_data", ""),
                        "error_message": None,
                    })
                else:
                    results.append({
                        "test_case_index": idx,
                        "status": "wrong_answer",
                        "time_used": 0,
                        "memory_used": 0,
                        "score": 0,
                        "input_data": tc.get("input_data", ""),
                        "expected_output": tc.get("output_data", ""),
                        "actual_output": "",
                        "error_message": "实际输出和期望输出不符合",
                    })
        elif sub.get("status") == "runtime_error":
            for idx, tc in enumerate(tcs):
                if idx == 0:
                    results.append({
                        "test_case_index": idx,
                        "status": "runtime_error",
                        "time_used": 0,
                        "memory_used": 0,
                        "score": 0,
                        "input_data": tc.get("input_data", ""),
                        "expected_output": tc.get("output_data", ""),
                        "actual_output": "",
                        "error_message": "运行时错误: IndexError",
                    })
                else:
                    results.append({
                        "test_case_index": idx,
                        "status": "accepted",
                        "time_used": 15 + idx * 3,
                        "memory_used": 14000 + idx * 200,
                        "score": int(tc.get("score", 0)),
                        "input_data": tc.get("input_data", ""),
                        "expected_output": tc.get("output_data", ""),
                        "actual_output": tc.get("output_data", ""),
                        "error_message": None,
                    })
        else:
            # 其它状态默认按 accepted 处理（保守策略）
            for idx, tc in enumerate(tcs):
                results.append({
                    "test_case_index": idx,
                    "status": "accepted",
                    "time_used": 12,
                    "memory_used": 13000,
                    "score": int(tc.get("score", 0)),
                    "input_data": tc.get("input_data", ""),
                    "expected_output": tc.get("output_data", ""),
                    "actual_output": tc.get("output_data", ""),
                    "error_message": None,
                })

        judge_results_map[i] = results
    
    # 创建提交记录并关联评测结果
    submissions = []
    judge_result_count = 0
    for idx, sub_data in enumerate(submissions_data):
        # 获取该提交的评测结果（如果有）
        judge_results = judge_results_map.get(idx, None)
        
        submission = Submission(
            problem_id=sub_data["problem"].problem_id,
            contest_id=sub_data["contest"].contest_id if sub_data["contest"] else None,
            code=sub_data["code"],
            language=sub_data["language"],
            status=sub_data["status"],
            exec_time=sub_data["exec_time"],
            exec_memory=sub_data["exec_memory"],
            judge_results=judge_results  # 将评测结果作为 JSON 存储
        )
        db.add(submission)
        db.flush()
        
        # 添加用户-提交关联
        db.add(UserSubmission(user_id=sub_data["user"].user_id, submission_id=submission.submission_id))
        submissions.append(submission)
        
        # 统计评测结果数量
        if judge_results:
            judge_result_count += len(judge_results)
    
    db.commit()
    print(f"  ✅ 创建了 {len(submissions)} 条提交记录（包含 {judge_result_count} 条评测结果详情）")
    
    # 7. 创建消息（题目讨论和私信）
    print("  💬 创建消息和讨论...")
    messages_data = [
        # 题目讨论帖
        {
            "title": "两数之和的时间复杂度问题",
            "content": "请问使用哈希表的方法时间复杂度是多少？我看到很多题解说是 O(n)，但是不太理解为什么。\n\n另外，如果数组中有重复元素的话，这个方法还适用吗？希望大佬们能帮忙解答一下！",
            "creator": users[0],  # 张三
            "message_type": "topic",
            "problem": problems[0],
        },
        {
            "title": "回文数的优化方法",
            "content": "不转换成字符串有更好的方法吗？\n\n我目前的做法是先把数字转成字符串，然后判断是否和反转后的字符串相等。但感觉这样有点投机取巧，有没有纯数学的解法？\n\n另外负数的处理需要特别注意吗？",
            "creator": users[2],  # 王五
            "message_type": "topic",
            "problem": problems[1],
        },
        {
            "title": "最长回文子串的动态规划解法",
            "content": "有人能详细讲解一下 DP 的状态转移方程吗？\n\n我理解 dp[i][j] 表示从 i 到 j 的子串是否是回文串，但是状态转移的时候总是想不清楚。\n\n是先判断 s[i] == s[j]，然后再看 dp[i+1][j-1] 吗？\n\n求大神指点迷津！",
            "creator": users[1],  # 李四
            "message_type": "topic",
            "problem": problems[5],  # 最长回文子串
        },
        {
            "title": "三数之和去重问题讨论",
            "content": "这道题最难的地方就是去重了吧？\n\n我用的是先排序，然后在遍历的时候跳过重复元素。但是提交之后发现还是有重复的结果。\n\n有没有人遇到过类似的问题？能分享一下你们的去重策略吗？",
            "creator": users[3],  # 赵六
            "message_type": "topic",
            "problem": problems[6],  # 三数之和
        },
        {
            "title": "滑动窗口的精髓",
            "content": "做无重复字符最长子串这题的时候，感觉滑动窗口真的很巧妙！\n\n关键是要理解什么时候移动左指针，什么时候移动右指针。\n\n我的理解是：右指针一直往前走，遇到重复字符的时候，左指针移动到重复字符的下一个位置。\n\n这样理解对吗？欢迎大家讨论！",
            "creator": users[0],  # 张三
            "message_type": "topic",
            "problem": problems[7],  # 无重复字符的最长子串
        },
        {
            "title": "正则表达式匹配好难啊",
            "content": "这道题感觉是 hard 难度中最难的之一了...\n\n光是理解题意就花了很长时间，'*' 匹配零个或多个前面的元素，这个怎么用递归或者 DP 来实现呢？\n\n有没有大佬能画个图解释一下思路？实在是理解不了...",
            "creator": users[4],  # 钱七
            "message_type": "topic",
            "problem": problems[8],  # 正则表达式匹配
        },
        {
            "title": "括号匹配的栈解法分享",
            "content": "最长有效括号这道题，我用栈解决的！\n\n思路是维护一个栈来存储索引，遇到 '(' 就入栈，遇到 ')' 就尝试匹配。\n\n关键是要在栈底预先放一个 -1 作为基准位置，这样计算长度的时候就很方便了。\n\n有兴趣的同学可以试试这个思路！",
            "creator": users[1],  # 李四
            "message_type": "topic",
            "problem": problems[9],  # 最长有效括号
        },
        {
            "title": "接雨水的双指针解法真优雅",
            "content": "刚学会了接雨水的双指针解法，太优雅了！\n\n核心思想是：从两端向中间移动，每次移动较矮的那一边。\n\n因为能接多少水取决于较短的那块板子，这个想法真的很巧妙。\n\n比用栈或者动态规划的方法都要简洁，强烈推荐！",
            "creator": users[3],  # 赵六
            "message_type": "topic",
            "problem": problems[10],  # 接雨水
        },
        {
            "title": "Python 的语法糖真好用",
            "content": "用 Python 刷题真的很爽，特别是处理字符串和列表的时候。\n\n比如 [::-1] 反转，enumerate() 遍历索引和值，zip() 打包...\n\n虽然面试的时候可能要用 C++ 或 Java，但是平时练习用 Python 真的效率很高！\n\n大家觉得呢？",
            "creator": users[2],  # 王五
            "message_type": "topic",
            "problem": problems[3],  # 两数之和
        },
        {
            "title": "关于测试用例的边界条件",
            "content": "做题的时候发现很多坑都在边界条件上...\n\n空数组、单个元素、负数、零、超大数...\n\n建议大家提交之前自己先想想各种边界情况，能避免很多 Wrong Answer。\n\n有没有人总结过常见的边界条件？可以分享一下吗？",
            "creator": users[4],  # 钱七
            "message_type": "topic",
            "problem": problems[4],  # 回文数
        },
        
        # 私信消息
        {
            "title": "关于新手赛的报名问题",
            "content": "管理员你好！\n\n我看到了新手赛的通知，想报名参加，但是不太清楚具体的规则。\n\n请问：\n1. 比赛时长是多久？\n2. 可以中途退出吗？\n3. 比赛期间能查看题解吗？\n4. 评分机制是怎样的？\n\n希望能得到回复，谢谢！",
            "creator": users[4],  # 钱七
            "message_type": "private",
            "problem": None,
            "recipient": users[5],  # 发给管理员
        },
        # 以下私信都是在好友之间发送（符合好友约束）
        {
            "title": "代码求助：回文数判断",
            "content": "李四你好！\n\n我看到你 AC 了回文数这道题，能帮我看看我的代码哪里有问题吗？\n\n```python\ndef is_palindrome(x):\n    if x < 0:\n        return False\n    return True\n```\n\n我这样写为什么只能通过第二个测试点，其他都是 Wrong Answer？\n\n麻烦了！",
            "creator": users[0],  # 张三
            "message_type": "private",
            "problem": None,
            "recipient": users[1],  # 发给李四（张三↔李四是好友）
        },
        {
            "title": "组队练习邀请",
            "content": "王五，最近刷题进度怎么样？\n\n我打算每天晚上 8 点到 10 点固定刷题时间，要不要一起？\n\n可以互相讨论题目，遇到不会的一起研究，这样效率更高！\n\n有兴趣的话回复我一下！",
            "creator": users[0],  # 张三
            "message_type": "private",
            "problem": None,
            "recipient": users[2],  # 发给王五（张三↔王五是好友）
        },
        {
            "title": "感谢你的题解！",
            "content": "李四你好！\n\n我看到你在接雨水题目下的讨论帖，双指针的思路真的帮到我了！\n\n之前我一直卡在这道题上，看了你的解释之后终于理解了。\n\n今天成功 AC 了，特地来感谢你！\n\n希望以后能多多交流！",
            "creator": users[3],  # 赵六
            "message_type": "private",
            "problem": None,
            "recipient": users[1],  # 发给李四（赵六↔李四是好友）
        },
        {
            "title": "Python技巧分享",
            "content": "张三你好！\n\n我最近发现了一个很有用的 Python 技巧：可以用 zip() 函数同时遍历多个列表。\n\n比如：\n```python\nfor a, b in zip(list1, list2):\n    print(a, b)\n```\n\n这样在处理配对数据的时候特别方便，分享给你！",
            "creator": users[2],  # 王五
            "message_type": "private",
            "problem": None,
            "recipient": users[0],  # 发给张三（王五↔张三是好友）
        },
        {
            "title": "比赛经验请教",
            "content": "赵六你好！\n\n看到你参加了很多比赛，rating 也挺高的。\n\n能分享一下比赛的经验吗？比如：\n- 怎么分配时间？\n- 遇到不会的题是跳过还是死磕？\n- 怎么练习才能提高比赛能力？\n\n作为新手很迷茫，希望能得到指点！",
            "creator": users[1],  # 李四
            "message_type": "private",
            "problem": None,
            "recipient": users[3],  # 发给赵六（李四↔赵六是好友）
        },
    ]
    
    # 为消息添加不同的创建时间，使其更真实
    for i, msg_data in enumerate(messages_data):
        # 消息在过去 30 天内随机分布
        days_ago = 30 - (i * 2)  # 越早的消息离现在越远
        hours_ago = (i * 3) % 24  # 添加小时偏移
        created_time = now - timedelta(days=days_ago, hours=hours_ago)
        
        message = Message(
            title=msg_data["title"],
            content=msg_data["content"],
            creator_id=msg_data["creator"].user_id,
            message_type=msg_data["message_type"],
            created_at=created_time,
        )
        db.add(message)
        db.flush()
        
        # 如果是讨论帖，关联题目
        if msg_data["message_type"] == "topic" and msg_data.get("problem"):
            db.add(MessageProblem(message_id=message.message_id, problem_id=msg_data["problem"].problem_id))
        
        # 如果是私信，添加接收者
        if msg_data["message_type"] == "private" and "recipient" in msg_data:
            db.add(MessageRecipient(message_id=message.message_id, recipient_user_id=msg_data["recipient"].user_id))
    
    db.commit()
    print(f"  ✅ 创建了 {len(messages_data)} 条消息（{sum(1 for m in messages_data if m['message_type'] == 'topic')} 条讨论帖，{sum(1 for m in messages_data if m['message_type'] == 'private')} 条私信）")
    
    # ========== 9. 创建好友关系 ==========
    print("\n9️⃣  创建好友关系...")
    from app.models import Friendship
    
    friendships_data = [
        # 张三和李四是好友
        {
            "user": users[0],  # 张三
            "friend": users[1],  # 李四
            "status": "accepted",
        },
        {
            "user": users[1],  # 李四
            "friend": users[0],  # 张三
            "status": "accepted",
        },
        # 张三和王五是好友
        {
            "user": users[0],  # 张三
            "friend": users[2],  # 王五
            "status": "accepted",
        },
        {
            "user": users[2],  # 王五
            "friend": users[0],  # 张三
            "status": "accepted",
        },
        # 李四和赵六是好友
        {
            "user": users[1],  # 李四
            "friend": users[3],  # 赵六
            "status": "accepted",
        },
        {
            "user": users[3],  # 赵六
            "friend": users[1],  # 李四
            "status": "accepted",
        },
        # 钱七向张三发送好友请求（待处理）
        {
            "user": users[4],  # 钱七
            "friend": users[0],  # 张三
            "status": "pending",
        },
        # 王五向李四发送好友请求（待处理）
        {
            "user": users[2],  # 王五
            "friend": users[1],  # 李四
            "status": "pending",
        },
        # 张三屏蔽了某个用户（假设屏蔽用户ID 99，示例）
        # 可以后续添加更多真实用户后再测试屏蔽功能
    ]
    
    for friendship_data in friendships_data:
        friendship = Friendship(
            user_id=friendship_data["user"].user_id,
            friend_id=friendship_data["friend"].user_id,
            status=friendship_data["status"],
        )
        db.add(friendship)
    
    db.commit()
    print(f"  ✅ 创建了 {len(friendships_data)} 条好友关系")
    accepted_count = sum(1 for f in friendships_data if f['status'] == 'accepted')
    pending_count = sum(1 for f in friendships_data if f['status'] == 'pending')
    print(f"     - {accepted_count // 2} 对好友关系（双向 {accepted_count} 条记录）")
    print(f"     - {pending_count} 条待处理的好友请求")
    
    print("✅ 样例数据插入完成！")


def print_summary(db: Session):
    """打印数据库摘要"""
    print("\n" + "="*50)
    print("📊 数据库重置完成！当前数据统计：")
    print("="*50)
    print(f"  👤 用户数量: {db.query(User).count()}")
    print(f"  📚 题目数量: {db.query(Problem).count()}")
    # 测试点数据现在存储在 problem 表的 test_cases JSON 字段中
    problems_with_test_cases = db.query(Problem).filter(Problem.test_cases != None).count()
    print(f"  🧪 包含测试点的题目: {problems_with_test_cases}/{db.query(Problem).count()}")
    print(f"  🏆 比赛数量: {db.query(Contest).count()}")
    print(f"  📤 提交数量: {db.query(Submission).count()}")
    # 评测结果现在存储在 submission 表的 judge_results JSON 字段中
    submissions_with_results = db.query(Submission).filter(Submission.judge_results != None).count()
    print(f"  🔍 包含评测结果的提交: {submissions_with_results}/{db.query(Submission).count()}")
    print(f"  💬 消息数量: {db.query(Message).count()}")
    
    from app.models import Friendship
    print(f"  👥 好友关系: {db.query(Friendship).filter(Friendship.status == 'accepted').count() // 2} 对好友")
    print(f"  📬 好友请求: {db.query(Friendship).filter(Friendship.status == 'pending').count()} 条待处理")
    print("="*50)
    print("\n📋 测试账号信息：")
    print("="*50)
    users = db.query(User).all()
    for user in users:
        password = "admin123" if user.role == "admin" else "123456"
        print(f"  用户名: {user.username:10s} | 密码: {password:10s} | 角色: {user.role}")
    print("="*50)
    print("\n💡 提示：")
    print("  1. 请使用上述账号登录系统")
    print("  2. 'Hello World' 题目已配置测试用例，可以测试评测功能")
    print("  3. 其他题目需要手动添加测试用例")
    print("="*50 + "\n")


def main():
    """主函数"""
    print("\n" + "="*50)
    print("⚠️  数据库重置脚本")
    print("="*50)
    print("警告：此操作将删除所有现有数据！")
    print("="*50)
    
    # 确认操作
    confirm = input("\n是否继续？(yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ 操作已取消")
        return
    
    try:
        # 1. 删除所有表
        drop_all_tables()
        
        # 2.删除头像文件夹及其内容
        if os.path.exists("./uploads/avatars"):
            shutil.rmtree("./uploads/avatars")
            print("✅ 头像文件夹已删除")
        
        # 3. 重新创建所有表
        create_all_tables()
        
        # 4. 插入样例数据
        db = SessionLocal()
        try:
            insert_sample_data(db)
            print_summary(db)
        finally:
            db.close()
        
        print("🎉 数据库重置成功！")
        
    except Exception as e:
        print(f"\n❌ 错误：{str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
