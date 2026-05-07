from datetime import datetime, timedelta
from typing import Optional
import hashlib
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import get_settings

settings = get_settings()

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


def _preprocess_password(password: str) -> bytes:
    """
    预处理密码：使用 SHA256 将任意长度的密码转换为固定长度
    这样可以绕过 bcrypt 的 72 字节限制
    返回 bytes 类型用于 bcrypt
    """
    return hashlib.sha256(password.encode('utf-8')).digest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # 先用 SHA256 预处理密码，再用 bcrypt 验证
    preprocessed = _preprocess_password(plain_password)
    return bcrypt.checkpw(preprocessed, hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    # 先用 SHA256 预处理密码，再用 bcrypt 加密
    preprocessed = _preprocess_password(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(preprocessed, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    """解码访问令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户（依赖注入）
    
    注意：此函数需要与 db: Session = Depends(get_db) 一起使用
    例如：
    def my_route(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        ...
    """
    from app.database import SessionLocal
    from app.models import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    username = decode_access_token(token)
    if username is None:
        raise credentials_exception
    
    # 创建临时数据库会话来验证用户
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception
        return user
    finally:
        db.close()
