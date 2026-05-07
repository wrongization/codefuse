from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "user"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)  # 存储哈希后的密码
    email = Column(String(255), nullable=False, unique=True)
    school = Column(String(255), nullable=True)
    rating = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    role = Column(String(50), default='user', nullable=False)  # 'user' or 'admin'
    avatar = Column(String(255), nullable=True)  # 用户头像URL
    
    # 关系
    created_problems = relationship("Problem", back_populates="creator", foreign_keys="Problem.creator_id")
    created_contests = relationship("Contest", back_populates="creator", foreign_keys="Contest.creator_id")
    created_messages = relationship("Message", back_populates="creator")
    user_submissions = relationship("UserSubmission", back_populates="user")
    contest_users = relationship("ContestUser", back_populates="user")
    received_messages = relationship("MessageRecipient", back_populates="recipient_user")


class Problem(Base):
    """题目表"""
    __tablename__ = "problem"
    
    problem_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    input_format = Column(Text, nullable=False)
    output_format = Column(Text, nullable=False)
    sample_input = Column(Text, nullable=False)
    sample_output = Column(Text, nullable=False)
    time_limit = Column(Integer, nullable=False)  # 毫秒
    memory_limit = Column(Integer, nullable=False)  # KB
    difficulty = Column(String(50), nullable=False)  # 'easy', 'medium', 'hard'
    tags = Column(String(255), nullable=True)
    creator_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    test_cases = Column(JSON, nullable=True)  # 测试用例（JSON数组）
    visible = Column(Boolean, nullable=False, default=True)  # 是否对普通用户可见（id<10000为保留题，默认不可见）
    
    # 关系
    creator = relationship("User", back_populates="created_problems", foreign_keys=[creator_id])
    submissions = relationship("Submission", back_populates="problem")
    contest_problems = relationship("ContestProblem", back_populates="problem")
    problem_messages = relationship("MessageProblem", back_populates="problem")
    problem_submissions = relationship("ProblemSubmission", back_populates="problem")
    # 测试用例现在存储在 `test_cases` JSON 字段中，故不再维护独立的 TestCase 表关系


class Contest(Base):
    """比赛表"""
    __tablename__ = "contest"
    
    contest_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    creator_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    problems_published = Column(Boolean, default=False, nullable=False)  # 题目是否已发布到公开题库
    
    # 关系
    creator = relationship("User", back_populates="created_contests", foreign_keys=[creator_id])
    contest_problems = relationship("ContestProblem", back_populates="contest")
    contest_users = relationship("ContestUser", back_populates="contest")


class Message(Base):
    """消息表"""
    __tablename__ = "message"
    
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    creator_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    message_type = Column(String(50), nullable=False)  # 'topic' or 'private'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系
    creator = relationship("User", back_populates="created_messages")
    message_problems = relationship("MessageProblem", back_populates="message")
    message_recipients = relationship("MessageRecipient", back_populates="message")


class Submission(Base):
    """提交记录表"""
    __tablename__ = "submission"
    
    submission_id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey('problem.problem_id'), nullable=False)
    contest_id = Column(Integer, ForeignKey('contest.contest_id'), nullable=True)
    code = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)  # 'python', 'cpp', 'java', etc.
    status = Column(String(50), nullable=False)  # 'accepted', 'wrong_answer', 'time_limit_exceeded', etc.
    exec_time = Column(Integer, nullable=False)  # 毫秒
    exec_memory = Column(Integer, nullable=False)  # KB
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    judge_results = Column(JSON, nullable=True)  # 评测结果（JSON数组），每个测试点一个结果对象
    
    # 关系
    problem = relationship("Problem", back_populates="submissions")
    user_submissions = relationship("UserSubmission", back_populates="submission", cascade="all, delete-orphan")
    problem_submissions = relationship("ProblemSubmission", back_populates="submission", cascade="all, delete-orphan")


# 联系表

class ContestProblem(Base):
    """比赛-题目联系表"""
    __tablename__ = "contest_problem"
    
    contest_id = Column(Integer, ForeignKey('contest.contest_id'), primary_key=True)
    problem_id = Column(Integer, ForeignKey('problem.problem_id'), primary_key=True)
    
    # 关系
    contest = relationship("Contest", back_populates="contest_problems")
    problem = relationship("Problem", back_populates="contest_problems")


class ContestUser(Base):
    """比赛-用户联系表"""
    __tablename__ = "contest_user"
    
    contest_id = Column(Integer, ForeignKey('contest.contest_id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'), primary_key=True)
    
    # 关系
    contest = relationship("Contest", back_populates="contest_users")
    user = relationship("User", back_populates="contest_users")


class MessageProblem(Base):
    """消息-题目联系表"""
    __tablename__ = "message_problem"
    
    message_id = Column(Integer, ForeignKey('message.message_id'), primary_key=True)
    problem_id = Column(Integer, ForeignKey('problem.problem_id'), primary_key=True)
    
    # 关系
    message = relationship("Message", back_populates="message_problems")
    problem = relationship("Problem", back_populates="problem_messages")


class MessageRecipient(Base):
    """消息-接收者联系表"""
    __tablename__ = "message_recipient"
    
    message_id = Column(Integer, ForeignKey('message.message_id'), primary_key=True)
    recipient_user_id = Column(Integer, ForeignKey('user.user_id'), primary_key=True)
    
    # 关系
    message = relationship("Message", back_populates="message_recipients")
    recipient_user = relationship("User", back_populates="received_messages")


class ProblemSubmission(Base):
    """题目-提交联系表"""
    __tablename__ = "problem_submission"
    
    problem_id = Column(Integer, ForeignKey('problem.problem_id', ondelete='CASCADE'), primary_key=True)
    submission_id = Column(Integer, ForeignKey('submission.submission_id', ondelete='CASCADE'), primary_key=True)
    
    # 关系
    problem = relationship("Problem", back_populates="problem_submissions")
    submission = relationship("Submission", back_populates="problem_submissions")


class UserSubmission(Base):
    """用户-提交联系表"""
    __tablename__ = "user_submission"
    
    user_id = Column(Integer, ForeignKey('user.user_id'), primary_key=True)
    submission_id = Column(Integer, ForeignKey('submission.submission_id'), primary_key=True)
    
    # 关系
    user = relationship("User", back_populates="user_submissions")
    submission = relationship("Submission", back_populates="user_submissions")


class Friendship(Base):
    """好友关系表"""
    __tablename__ = "friendship"
    
    friendship_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)  # 发起者
    friend_id = Column(Integer, ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)  # 接收者
    status = Column(SQLEnum('pending', 'accepted', 'rejected', 'blocked', name='friendship_status'), 
                   default='pending', nullable=False)  # 好友状态
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # 申请时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # 更新时间
    
    # 关系
    user = relationship("User", foreign_keys=[user_id], backref="friendships_sent")
    friend = relationship("User", foreign_keys=[friend_id], backref="friendships_received")


class ActivityLog(Base):
    """活动日志表"""
    __tablename__ = "activity_log"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.user_id'), nullable=True)  # 执行操作的用户
    action_type = Column(String(50), nullable=False)  # create, update, delete, submit
    entity_type = Column(String(50), nullable=False)  # user, problem, contest, submission
    entity_id = Column(Integer, nullable=True)  # 被操作实体的ID
    description = Column(Text, nullable=False)  # 操作描述
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系
    user = relationship("User")

# NOTE: TestCase model removed. Test cases are stored inside Problem.test_cases (JSON).
