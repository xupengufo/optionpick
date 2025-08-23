#!/bin/bash
# 美股期权工具快速更新脚本

echo "🚀 开始同步更新..."

# 检查Git状态
echo "📋 检查当前修改状态..."
git status

# 用户输入提交信息
echo ""
echo "📝 请输入本次更新的描述:"
read -p "更新说明: " commit_message

# 如果没有输入，使用默认信息
if [ -z "$commit_message" ]; then
    commit_message="📈 常规更新: $(date +'%Y-%m-%d %H:%M')"
fi

# 添加所有更改
echo "📦 添加修改的文件..."
git add .

# 检查是否有更改
if [ -z "$(git status --porcelain)" ]; then
    echo "ℹ️  没有检测到文件更改"
    exit 0
fi

# 提交更改
echo "💾 提交更改..."
git commit -m "$commit_message"

# 推送到GitHub
echo "⬆️  推送到GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 更新完成!"
    echo "🔄 GitHub已更新，Streamlit Cloud将在1-2分钟内自动重新部署"
    echo "🌐 请稍后刷新您的在线应用查看更新"
    echo ""
    echo "📊 查看部署状态:"
    echo "   - GitHub Actions: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/actions"
    echo "   - Streamlit Cloud: https://share.streamlit.io"
else
    echo "❌ 推送失败，请检查网络连接或权限"
fi