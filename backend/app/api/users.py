from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, PasswordReset
from app.core.security import get_password_hash
from app.core.deps import get_current_admin
from app.core.logger import log_event

router = APIRouter(prefix="/users", tags=["用户管理(管理员)"])


@router.get("", response_model=List[UserResponse], summary="获取所有用户列表")
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员获取系统用户列表"""
    return db.query(User).order_by(User.id.asc()).all()


@router.post("", response_model=UserResponse, summary="新增用户")
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员创建新用户账号（普通员工或管理员）"""
    exist_user = db.query(User).filter(User.username == user_in.username).first()
    if exist_user:
        raise HTTPException(status_code=400, detail="该用户名已存在，请更换")

    if user_in.role not in ["admin", "employee"]:
        raise HTTPException(status_code=400, detail="无效的角色类型，仅支持 admin 或 employee")

    hashed_pw = get_password_hash(user_in.password)
    user = User(
        username=user_in.username,
        password_hash=hashed_pw,
        role=user_in.role,
        is_active=user_in.is_active
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_event(db, "USER", "INFO", f"管理员创建新用户: {user.username} (角色: {user.role})", operator=admin.username)
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户状态或角色")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员修改指定用户的角色或启用/禁用状态"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="指定用户不存在")

    # 防止管理员将自己禁用
    if user.id == admin.id and user_in.is_active is False:
        raise HTTPException(status_code=400, detail="不能禁用当前正在操作的管理员自身账号")

    if user_in.role is not None:
        if user_in.role not in ["admin", "employee"]:
            raise HTTPException(status_code=400, detail="无效的角色类型")
        user.role = user_in.role

    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    db.commit()
    db.refresh(user)
    log_event(db, "USER", "INFO", f"更新用户信息: {user.username} (active={user.is_active}, role={user.role})", operator=admin.username)
    return user


@router.post("/{user_id}/reset-password", summary="重置用户密码")
def reset_password(
    user_id: int,
    req: PasswordReset,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员重置某个用户的登录密码"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="指定用户不存在")

    user.password_hash = get_password_hash(req.new_password)
    db.commit()
    log_event(db, "USER", "INFO", f"重置用户密码: {user.username}", operator=admin.username)
    return {"message": f"用户 [{user.username}] 的密码已重置成功"}


@router.delete("/{user_id}", summary="删除用户")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员删除指定用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="指定用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前管理员自身账号")

    username = user.username
    db.delete(user)
    db.commit()
    log_event(db, "USER", "INFO", f"删除用户: {username}", operator=admin.username)
    return {"message": f"用户 [{username}] 已被删除"}
