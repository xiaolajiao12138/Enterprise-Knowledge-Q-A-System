@echo off
chcp 65001 >nul
title 企业内部知识问答平台 (RAG) 一键启动服务

echo =====================================================================
echo           【企业内部知识问答平台 (RAG)】一键启动程序
echo =====================================================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

:: 查找可用 Python 路径
set PYTHON_CMD=python
if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
)

echo [1/4] 正在检查并初始化数据库与默认管理员账号...
"%PYTHON_CMD%" backend\init_db.py
if errorlevel 1 (
    echo [警告] 数据库初始化检测异常，尝试继续启动...
)

echo.
echo [2/4] 正在启动后端 FastAPI 服务 (http://127.0.0.1:8000)...
start "企业知识问答-后端服务" cmd /k "cd /d %SCRIPT_DIR%backend && ^"%PYTHON_CMD%^" run.py"

:: 等待后端端口初始化
timeout /t 3 /nobreak >nul

echo.
echo [3/4] 正在启动前端 Vue3 服务 (http://127.0.0.1:3000)...
start "企业知识问答-前端服务" cmd /k "cd /d %SCRIPT_DIR%frontend && npm run dev"

:: 等待前端服务初始化
timeout /t 3 /nobreak >nul

echo.
echo [4/4] 正在启动浏览器访问系统...
start http://localhost:3000

echo.
echo =====================================================================
echo 系统已成功启动！
echo.
echo 前端访问地址: http://localhost:3000
echo 后端接口文档: http://127.0.0.1:8000/docs
echo.
echo 默认体验账号:
echo   - 系统管理员: admin   / admin123  (拥有全部上传、管理与系统配置权限)
echo   - 普通员工:   staff   / staff123  (仅问答与查看历史，无上传删除权限)
echo.
echo 请保留弹出的前后端服务黑框运行，关闭黑框即可停止服务。
echo =====================================================================
pause
