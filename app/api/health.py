"""
Health Check 엔드포인트 - 서비스 상태 확인용
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import psutil
import os
from app.database import get_db_session
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """기본 Health Check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "stock-analyzer"
    }

@router.get("/detailed")
async def detailed_health_check():
    """상세 Health Check - 시스템 리소스 및 데이터베이스 상태 포함"""
    try:
        # 시스템 리소스 확인
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        
        # 데이터베이스 연결 확인
        db_status = "unknown"
        try:
            with get_db_session() as session:
                result = session.execute(text("SELECT 1"))
                if result.fetchone():
                    db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "stock-analyzer",
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory_info.total,
                    "used": memory_info.used,
                    "percent": memory_info.percent
                },
                "disk": {
                    "total": disk_info.total,
                    "used": disk_info.used,
                    "percent": (disk_info.used / disk_info.total) * 100
                }
            },
            "database": {
                "status": db_status
            },
            "environment": {
                "python_version": os.sys.version,
                "timezone": os.environ.get("TZ", "Unknown")
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/ready")
async def readiness_check():
    """Readiness Check - 서비스가 요청을 받을 준비가 되었는지 확인"""
    try:
        # 필수 환경 변수 확인
        required_env_vars = [
            "DATABASE_URL",
            "KIS_APP_KEY", 
            "KIS_SECRET_KEY"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise HTTPException(
                status_code=503, 
                detail=f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        
        # 데이터베이스 연결 확인
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "message": "Service is ready to accept requests"
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")

@router.get("/live")
async def liveness_check():
    """Liveness Check - 서비스가 살아있는지 확인"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime": datetime.now().isoformat()  # 실제로는 시작 시간부터 계산
    }
