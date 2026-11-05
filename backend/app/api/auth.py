from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, Token, UserResponse
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.core.logger import log_event

router = APIRouter(prefix="/auth", tags=["认证模块"])


@router.post("/login", response_model=Token, summary="用户登录 (JSON 格式)")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户凭用户名与密码登录，成功返回访问 Token"""
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        log_event(db, "AUTH", "WARNING", f"用户登录失败: {request.username} 密码错误或不存在", operator=request.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或密码不正确"
        )
    if not user.is_active:
        log_event(db, "AUTH", "WARNING", f"禁用用户尝试登录: {request.username}", operator=request.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号已被系统管理员禁用"
        )

    access_token = create_access_token(subject=user.username)
    log_event(db, "AUTH", "INFO", f"用户登录成功: {user.username} (角色: {user.role})", operator=user.username)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/token", response_model=Token, summary="兼容 Swagger OAuth2 表单登录")
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """支持 Swagger UI Authorize 功能"""
    req = LoginRequest(username=form_data.username, password=form_data.password)
    return login(req, db)


@router.get("/me", response_model=UserResponse, summary="获取当前登录用户信息")
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前已登录用户的详细信息与角色"""
    return current_user


@router.post("/logout", summary="退出登录")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用户安全注销"""
    log_event(db, "AUTH", "INFO", f"用户退出登录: {current_user.username}", operator=current_user.username)
    return {"message": "已安全退出"}
