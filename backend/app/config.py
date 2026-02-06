from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库配置
    DB_HOST: str
    DB_PORT: int 
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    
    # API配置
    API_HOST: str 
    API_PORT: int 
    
    # JWT配置
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int 
    
    # 管理员注册码
    ADMIN_REGISTER_CODE: str 
    
    # 代码评测系统配置
    PYTHON_EXECUTABLE: str                  # Python 解释器路径
    GCC_EXECUTABLE: str                     # GCC 编译器路径
    GPP_EXECUTABLE: str                     # G++ 编译器路径
    JAVAC_EXECUTABLE: str                   # Java 编译器路径
    JAVA_EXECUTABLE: str                    # Java 运行时路径
    JUDGE_TEMP_DIR: str                     # 临时文件目录(空表示使用系统临时目录)
    JUDGE_DEFAULT_TIMEOUT: int              # 默认超时时间(秒)
    JUDGE_DEFAULT_MEMORY_LIMIT: int         # 默认内存限制(MB)
    JUDGE_MAX_WORKERS: int                  # 并发评测线程数
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
