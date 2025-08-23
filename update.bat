@echo off
chcp 65001 >nul
echo 🚀 开始同步更新...

REM 检查Git状态
echo 📋 检查当前修改状态...
git status

echo.
set /p commit_message=📝 请输入本次更新的描述: 

REM 如果没有输入，使用默认信息
if "%commit_message%"=="" (
    for /f "tokens=1-4 delims=/ " %%i in ('date /t') do set mydate=%%i-%%j-%%k
    for /f "tokens=1-2 delims=: " %%i in ('time /t') do set mytime=%%i:%%j
    set commit_message=📈 常规更新: %mydate% %mytime%
)

REM 添加所有更改
echo 📦 添加修改的文件...
git add .

REM 检查是否有更改
git diff-index --quiet HEAD
if %errorlevel% neq 0 (
    REM 提交更改
    echo 💾 提交更改...
    git commit -m "%commit_message%"
    
    REM 推送到GitHub
    echo ⬆️  推送到GitHub...
    git push origin main
    
    if %errorlevel% equ 0 (
        echo.
        echo ✅ 更新完成!
        echo 🔄 GitHub已更新，Streamlit Cloud将在1-2分钟内自动重新部署
        echo 🌐 请稍后刷新您的在线应用查看更新
        echo.
        echo 📊 查看部署状态:
        echo    - Streamlit Cloud: https://share.streamlit.io
        pause
    ) else (
        echo ❌ 推送失败，请检查网络连接或权限
        pause
    )
) else (
    echo ℹ️  没有检测到文件更改
    pause
)