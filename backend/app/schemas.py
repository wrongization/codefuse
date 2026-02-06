from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    school: Optional[str] = None
    role: str = 'user'


class UserCreate(UserBase):
    password: str
    admin_code: Optional[str] = None  # 管理员注册码（可选）


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    school: Optional[str] = None
    password: Optional[str] = None
    current_password: Optional[str] = None  # 修改密码时需要提供当前密码


class UserResponse(UserBase):
    user_id: int
    rating: int
    created_at: datetime
    avatar: Optional[str] = None
    
    class Config:
        from_attributes = True


# Problem Schemas
class ProblemBase(BaseModel):
    title: str
    description: str
    input_format: str
    output_format: str
    sample_input: str
    sample_output: str
    time_limit: int
    memory_limit: int
    difficulty: str
    tags: Optional[str] = None
    visible: Optional[bool] = True  # 是否对普通用户可见


class ProblemCreate(ProblemBase):
    test_cases: Optional[List['TestCaseData']] = None


class ProblemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    sample_input: Optional[str] = None
    sample_output: Optional[str] = None
    time_limit: Optional[int] = None
    memory_limit: Optional[int] = None
    difficulty: Optional[str] = None
    tags: Optional[str] = None
    visible: Optional[bool] = None
    test_cases: Optional[List['TestCaseData']] = None


class ProblemResponse(ProblemBase):
    problem_id: int
    creator_id: int
    visible: bool
    test_cases: Optional[List['TestCaseData']] = None
    
    class Config:
        from_attributes = True


# 简化的题目信息（用于提交记录等场景）
class ProblemBrief(BaseModel):
    problem_id: int
    title: str
    difficulty: str
    tags: Optional[str] = None
    
    class Config:
        from_attributes = True


# Contest Schemas
class ContestBase(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: datetime


class ContestCreate(ContestBase):
    pass


class ContestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ContestResponse(ContestBase):
    contest_id: int
    creator_id: int
    
    class Config:
        from_attributes = True


# Message Schemas
class MessageBase(BaseModel):
    title: Optional[str] = None
    content: str
    message_type: str  # 'topic' or 'private'


class MessageCreate(MessageBase):
    problem_id: Optional[int] = None  # for topic messages
    recipient_ids: Optional[List[int]] = None  # for private messages


class MessageResponse(MessageBase):
    message_id: int
    creator_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Submission Schemas
class SubmissionBase(BaseModel):
    problem_id: int
    contest_id: Optional[int] = None
    code: str
    language: str


class SubmissionCreate(SubmissionBase):
    # 可选的同步提交用户列表（user_id 列表）
    sync_with: Optional[List[int]] = None


class SubmissionUpdate(BaseModel):
    status: Optional[str] = None
    exec_time: Optional[int] = None
    exec_memory: Optional[int] = None


class SubmissionResponse(SubmissionBase):
    submission_id: int
    status: str
    exec_time: int
    exec_memory: int
    submitted_at: datetime
    user: Optional['UserResponse'] = None
    problem: Optional['ProblemBrief'] = None
    
    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Activity Log Schemas
class ActivityLogResponse(BaseModel):
    log_id: int
    user_id: Optional[int]
    action_type: str
    entity_type: str
    entity_id: Optional[int]
    description: str
    created_at: datetime
    username: Optional[str] = None  # 用户名（方便前端显示）
    
    class Config:
        from_attributes = True


# Test Case Data (embedded in Problem as JSON)
class TestCaseData(BaseModel):
    """测试点数据结构（作为题目的 JSON 属性）"""
    id: Optional[str] = None  # 稳定 ID（UUID 字符串），便于在数组中唯一标识测试点
    input_data: str
    output_data: str
    score: int = 10
    is_sample: int = 0  # 0=隐藏, 1=样例
    order: int = 0


# 独立的 TestCase CRUD Schemas（用于 /api/test-cases 路由）
class TestCaseCreate(BaseModel):
    problem_id: int
    id: Optional[str] = None
    input_data: str
    output_data: str
    score: int = 10
    is_sample: int = 0
    order: int = 0


class TestCaseUpdate(BaseModel):
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    score: Optional[int] = None
    is_sample: Optional[int] = None
    order: Optional[int] = None


class TestCaseResponse(BaseModel):
    test_case_id: int
    id: Optional[str] = None
    problem_id: int
    input_data: str
    output_data: str
    score: int
    is_sample: int
    order: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Judge Result Schemas (评测结果作为提交的属性，以 JSON 格式存储)
class JudgeResultResponse(BaseModel):
    test_case_index: int  # 测试点索引
    status: str
    time_used: Optional[int]
    memory_used: Optional[int]
    score: int
    error_message: Optional[str]
    input: Optional[str] = None  # 仅管理员可见
    expected_output: Optional[str] = None  # 仅管理员可见
    actual_output: Optional[str] = None  # 仅管理员可见
    
    class Config:
        from_attributes = True


# Submission with detailed judge results
class SubmissionDetailResponse(SubmissionResponse):
    judge_results: List[JudgeResultResponse] = []
    total_score: int = 0
    
    class Config:
        from_attributes = True


# Message Schemas
class MessageCreate(BaseModel):
    """创建消息（私信或讨论）"""
    title: Optional[str] = None  # 标题（讨论时可选，私信时可选）
    content: str  # 内容
    message_type: str  # 'private' 或 'topic'
    recipient_ids: Optional[List[int]] = None  # 私信接收者ID列表
    problem_id: Optional[int] = None  # 题目讨论的题目ID


class MessageUpdate(BaseModel):
    """更新消息（标题和内容）"""
    title: Optional[str] = None
    content: str


class MessageResponse(BaseModel):
    message_id: int
    title: Optional[str]
    content: str
    creator_id: int
    message_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserBrief(BaseModel):
    """用户简要信息"""
    user_id: int
    username: str
    avatar: Optional[str] = None


class ProblemBriefForMessage(BaseModel):
    """题目简要信息"""
    problem_id: int
    title: str


class MessageListResponse(BaseModel):
    """消息列表响应（包含创建者和接收者/题目信息）"""
    message_id: int
    title: Optional[str]
    content: str
    message_type: str
    created_at: datetime
    creator: Optional[UserBrief]
    recipients: Optional[List[UserBrief]] = None  # 私信接收者
    problem: Optional[ProblemBriefForMessage] = None  # 题目讨论关联的题目


# Friendship Schemas
class FriendshipBase(BaseModel):
    """好友关系基础模型"""
    pass


class FriendshipCreate(FriendshipBase):
    """创建好友请求"""
    friend_id: int


class FriendshipResponse(BaseModel):
    """好友关系响应"""
    friendship_id: int
    user_id: int
    friend_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FriendshipWithUser(BaseModel):
    """好友关系（包含用户信息）"""
    friendship_id: int
    user_id: int
    friend_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    user: Optional[UserBrief]  # 发起者信息
    friend: Optional[UserBrief]  # 好友信息
    
    class Config:
        from_attributes = True
