from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.database import engine, Base
from app.routers import users, problems, submissions, contests, activity_logs, messages, friendships, test_cases_json
from app.config import get_settings
from datetime import datetime

settings = get_settings()

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title="CodeFuse API",
    description="CodeFuse 编程学习系统 API",
    version="1.0.0"
)

# 创建uploads目录
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
(uploads_dir / "avatars").mkdir(exist_ok=True)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vue开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(users.router)
app.include_router(problems.router)
app.include_router(submissions.router)
app.include_router(contests.router)
app.include_router(activity_logs.router)
app.include_router(messages.router)
app.include_router(friendships.router)
app.include_router(test_cases_json.router)

# 挂载静态文件目录（必须在路由注册之后，避免被路由覆盖）
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="uploads")





@app.get("/")
def root():
    """根路径"""
    return {
        "message": "欢迎使用 CodeFuse API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
