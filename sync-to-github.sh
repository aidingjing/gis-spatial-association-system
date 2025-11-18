#!/bin/bash

# GitHub Epic同步脚本 - GIS空间关联分析系统
# 使用方法: ./sync-to-github.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 开始GitHub同步 - GIS空间关联分析系统${NC}"

# 检查是否为Git仓库
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ 当前目录不是Git仓库${NC}"
    echo -e "${YELLOW}请先初始化Git仓库：${NC}"
    echo "git init"
    echo "git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    exit 1
fi

# 检查GitHub CLI
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ 未安装GitHub CLI (gh)${NC}"
    echo -e "${YELLOW}请安装GitHub CLI：${NC}"
    echo "macOS: brew install gh"
    echo "Ubuntu: sudo apt install gh"
    echo "其他: https://cli.github.com/"
    exit 1
fi

# 检查GitHub登录状态
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ 未登录GitHub CLI${NC}"
    echo -e "${YELLOW}请先登录：${NC}"
    echo "gh auth login"
    exit 1
fi

# 获取仓库信息
remote_url=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$remote_url" ]]; then
    echo -e "${RED}❌ 未设置Git远程仓库${NC}"
    echo -e "${YELLOW}请设置远程仓库：${NC}"
    echo "git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    exit 1
fi

# 检查是否为CCPM模板仓库
if [[ "$remote_url" == *"automazeio/ccpm"* ]] || [[ "$remote_url" == *"automazeio/ccpm.git"* ]]; then
    echo -e "${RED}❌ 错误：您正在尝试与CCPM模板仓库同步！${NC}"
    echo ""
    echo "这个仓库（automazeio/ccpm）是供他人使用的模板。"
    echo "您不应该在此创建问题或PR。"
    echo ""
    echo "解决方法："
    echo "1. 将此仓库fork到您自己的GitHub账户"
    echo "2. 更新远程仓库："
    echo "   git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    echo ""
    echo -e "${YELLOW}当前远程仓库：${NC}$remote_url"
    exit 1
fi

REPO=$(echo "$remote_url" | sed 's|.*github.com[:/]||' | sed 's|\.git$||')
echo -e "${GREEN}📋 目标仓库：${NC}$REPO"

# 检查epic是否存在
if [[ ! -f ".claude/epics/gis-spatial-association-system/epic.md" ]]; then
    echo -e "${RED}❌ Epic文件不存在${NC}"
    echo "请先运行: /pm:prd-parse gis-spatial-association-system"
    exit 1
fi

# 统计任务文件
task_count=$(ls .claude/epics/gis-spatial-association-system/[0-9][0-9][0-9].md 2>/dev/null | wc -l)
if [[ $task_count -eq 0 ]]; then
    echo -e "${RED}❌ 未找到任务文件${NC}"
    echo "请先运行: /pm:epic-decompose gis-spatial-association-system"
    exit 1
fi

echo -e "${GREEN}📊 找到 $task_count 个任务文件${NC}"

# 检查gh-sub-issue扩展
if gh extension list | grep -q "yahsan2/gh-sub-issue"; then
    use_subissues=true
    echo -e "${GREEN}✅ 使用gh-sub-issue扩展${NC}"
else
    use_subissues=false
    echo -e "${YELLOW}⚠️ gh-sub-issue未安装，使用fallback模式${NC}"
fi

# 1. 准备Epic内容
echo -e "${BLUE}📝 准备Epic内容...${NC}"

# 提取epic内容（去除frontmatter）
sed '1,/^---$/d; 1,/^---$/d' .claude/epics/gis-spatial-association-system/epic.md > /tmp/epic-body-raw.md

# 处理Tasks Created部分，替换为Stats
awk '
/^## Tasks Created/ {
    in_tasks=1
    next
}
/^## / && in_tasks {
    in_tasks=0
    if (total_tasks) {
        print "## Stats"
        print ""
        print "Total tasks: " total_tasks
        print "Parallel tasks: " parallel_tasks " (can be worked on simultaneously)"
        print "Sequential tasks: " sequential_tasks " (have dependencies)"
        if (total_effort) print "Estimated total effort: " total_effort " hours"
        print ""
    }
}
/^Total tasks:/ && in_tasks { total_tasks = $3; next }
/^Parallel tasks:/ && in_tasks { parallel_tasks = $3; next }
/^Sequential tasks:/ && in_tasks { sequential_tasks = $3; next }
/^Estimated total effort:/ && in_tasks {
    sub(/^Estimated total effort: /, "")
    total_effort = $0
    next
}
!in_tasks { print }
END {
    if (in_tasks && total_tasks) {
        print "## Stats"
        print ""
        print "Total tasks: " total_tasks
        print "Parallel tasks: " parallel_tasks " (can be worked on simultaneously)"
        print "Sequential tasks: " sequential_tasks " (have dependencies)"
        if (total_effort) print "Estimated total effort: " total_effort
    }
}
' /tmp/epic-body-raw.md > /tmp/epic-body.md

# 确定epic类型
if grep -qi "bug\|fix\|issue\|problem\|error" /tmp/epic-body.md; then
    epic_type="bug"
else
    epic_type="feature"
fi

echo -e "${GREEN}🏷️ Epic类型：${NC}$epic_type"

# 2. 创建Epic Issue
echo -e "${BLUE}🎯 创建Epic Issue...${NC}"

epic_number=$(gh issue create \
    --repo "$REPO" \
    --title "Epic: gis-spatial-association-system" \
    --body-file /tmp/epic-body.md \
    --label "epic,epic:gis-spatial-association-system,$epic_type" \
    --json number -q .number)

echo -e "${GREEN}✅ Epic创建成功：${NC}#$epic_number"

# 3. 创建任务子问题
echo -e "${BLUE}📋 创建 $task_count 个任务子问题...${NC}"

# 创建临时目录存储映射
mkdir -p /tmp/task-mapping
echo "" > /tmp/task-mapping.txt

# 根据任务数量决定创建策略
if [[ $task_count -lt 5 ]]; then
    # 小批量顺序创建
    echo -e "${BLUE}🔄 顺序创建任务...${NC}"

    for task_file in .claude/epics/gis-spatial-association-system/[0-9][0-9][0-9].md; do
        [[ -f "$task_file" ]] || continue

        # 提取任务名称
        task_name=$(grep '^name:' "$task_file" | sed 's/^name: *//')

        # 去除frontmatter
        sed '1,/^---$/d; 1,/^---$/d' "$task_file" > /tmp/task-body.md

        # 创建子问题
        if [[ "$use_subissues" == true ]]; then
            task_number=$(gh sub-issue create \
                --parent "$epic_number" \
                --title "$task_name" \
                --body-file /tmp/task-body.md \
                --label "task,epic:gis-spatial-association-system" \
                --json number -q .number)
        else
            task_number=$(gh issue create \
                --repo "$REPO" \
                --title "$task_name" \
                --body-file /tmp/task-body.md \
                --label "task,epic:gis-spatial-association-system" \
                --json number -q .number)
        fi

        # 记录映射
        echo "$task_file:$task_number" >> /tmp/task-mapping.txt
        echo -e "${GREEN}  ✅ 创建任务 #$task_number: ${NC}$task_name"

        # 短暂延迟避免API限制
        sleep 0.5
    done
else
    # 大批量并行创建 - 使用Task工具
    echo -e "${BLUE}⚡ 并行创建任务...${NC}"

    # 这里应该调用Task工具进行并行创建
    # 由于脚本环境限制，我们使用顺序创建作为fallback
    for task_file in .claude/epics/gis-spatial-association-system/[0-9][0-9][0-9].md; do
        [[ -f "$task_file" ]] || continue

        task_name=$(grep '^name:' "$task_file" | sed 's/^name: *//')
        sed '1,/^---$/d; 1,/^---$/d' "$task_file" > /tmp/task-body.md

        if [[ "$use_subissues" == true ]]; then
            task_number=$(gh sub-issue create \
                --parent "$epic_number" \
                --title "$task_name" \
                --body-file /tmp/task-body.md \
                --label "task,epic:gis-spatial-association-system" \
                --json number -q .number)
        else
            task_number=$(gh issue create \
                --repo "$REPO" \
                --title "$task_name" \
                --body-file /tmp/task-body.md \
                --label "task,epic:gis-spatial-association-system" \
                --json number -q .number)
        fi

        echo "$task_file:$task_number" >> /tmp/task-mapping.txt
        echo -e "${GREEN}  ✅ 创建任务 #$task_number: ${NC}$task_name"
        sleep 0.5
    done
fi

# 4. 重命名文件并更新引用
echo -e "${BLUE}🔄 重命名文件并更新引用...${NC}"

# 构建ID映射
> /tmp/id-mapping.txt
while IFS=: read -r task_file task_number; do
    old_num=$(basename "$task_file" .md)
    echo "$old_num:$task_number" >> /tmp/id-mapping.txt
done < /tmp/task-mapping.txt

# 处理每个任务文件
while IFS=: read -r task_file task_number; do
    new_name="$(dirname "$task_file")/${task_number}.md"

    # 读取内容
    content=$(cat "$task_file")

    # 更新depends_on和conflicts_with引用
    while IFS=: read -r old_num new_num; do
        content=$(echo "$content" | sed "s/\b$old_num\b/$new_num/g")
    done < /tmp/id-mapping.txt

    # 写入新文件
    echo "$content" > "$new_name"

    # 删除旧文件
    [[ "$task_file" != "$new_name" ]] && rm "$task_file"

    # 更新frontmatter中的github和updated字段
    repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
    github_url="https://github.com/$repo/issues/$task_number"
    current_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    sed -i.bak "/^github:/c\github: $github_url" "$new_name"
    sed -i.bak "/^updated:/c\updated: $current_date" "$new_name"
    rm "${new_name}.bak"

    echo -e "${GREEN}  ✅ 重命名: ${NC}$(basename $task_file) → $task_number.md"
done < /tmp/task-mapping.txt

# 5. 更新Epic文件
echo -e "${BLUE}📝 更新Epic文件...${NC}"

repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
epic_url="https://github.com/$repo/issues/$epic_number"
current_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 更新Epic frontmatter
sed -i.bak "/^github:/c\github: $epic_url" .claude/epics/gis-spatial-association-system/epic.md
sed -i.bak "/^updated:/c\updated: $current_date" .claude/epics/gis-spatial-association-system/epic.md
rm .claude/epics/gis-spatial-association-system/epic.md.bak

# 创建更新后的Tasks Created section
cat > /tmp/tasks-section.md << 'EOF'
## Tasks Created
EOF

# 添加任务列表
for task_file in .claude/epics/gis-spatial-association-system/[0-9]*.md; do
    [[ -f "$task_file" ]] || continue

    issue_num=$(basename "$task_file" .md)
    task_name=$(grep '^name:' "$task_file" | sed 's/^name: *//')
    parallel=$(grep '^parallel:' "$task_file" | sed 's/^parallel: *//')

    echo "- [ ] #${issue_num} - ${task_name} (parallel: ${parallel})" >> /tmp/tasks-section.md
done

# 添加统计信息
total_count=$(ls .claude/epics/gis-spatial-association-system/[0-9]*.md 2>/dev/null | wc -l)
parallel_count=$(grep -l '^parallel: true' .claude/epics/gis-spatial-association-system/[0-9]*.md 2>/dev/null | wc -l)
sequential_count=$((total_count - parallel_count))

cat >> /tmp/tasks-section.md << EOF

Total tasks: ${total_count}
Parallel tasks: ${parallel_count}
Sequential tasks: ${sequential_count}
EOF

# 更新Epic文件中的Tasks Created section
cp .claude/epics/gis-spatial-association-system/epic.md .claude/epics/gis-spatial-association-system/epic.md.backup

awk '
/^## Tasks Created/ {
    skip=1
    while ((getline line < "/tmp/tasks-section.md") > 0) print line
    close("/tmp/tasks-section.md")
}
/^## / && !/^## Tasks Created/ { skip=0 }
!skip && !/^## Tasks Created/ { print }
' .claude/epics/gis-spatial-association-system/epic.md.backup > .claude/epics/gis-spatial-association-system/epic.md

rm .claude/epics/gis-spatial-association-system/epic.md.backup

# 6. 创建映射文件
echo -e "${BLUE}📋 创建GitHub映射文件...${NC}"

cat > .claude/epics/gis-spatial-association-system/github-mapping.md << EOF
# GitHub Issue Mapping

Epic: #${epic_number} - https://github.com/${repo}/issues/${epic_number}

Tasks:
EOF

# 添加任务映射
for task_file in .claude/epics/gis-spatial-association-system/[0-9]*.md; do
    [[ -f "$task_file" ]] || continue

    issue_num=$(basename "$task_file" .md)
    task_name=$(grep '^name:' "$task_file" | sed 's/^name: *//')

    echo "- #${issue_num}: ${task_name} - https://github.com/${repo}/issues/${issue_num}" >> .claude/epics/gis-spatial-association-system/github-mapping.md
done

echo "" >> .claude/epics/gis-spatial-association-system/github-mapping.md
echo "Synced: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> .claude/epics/gis-spatial-association-system/github-mapping.md

# 7. 创建Worktree（如果支持）
echo -e "${BLUE}🌳 创建开发Worktree...${NC}"

# 确保main分支是最新的
git checkout main
git pull origin main 2>/dev/null || echo "跳过pull（远程仓库可能不存在）"

# 创建worktree
if git worktree add ../epic-gis-spatial-association-system -b epic/gis-spatial-association-system 2>/dev/null; then
    echo -e "${GREEN}✅ Worktree创建成功：${NC}../epic-gis-spatial-association-system"
else
    echo -e "${YELLOW}⚠️ Worktree创建失败，可能分支已存在${NC}"
fi

# 8. 提交所有更改
echo -e "${BLUE}💾 提交本地更改...${NC}"

git add .claude/epics/gis-spatial-association-system/
git add sync-to-github.sh

git commit -m "🚀 Sync epic gis-spatial-association-system to GitHub

- Epic: #${epic_number}
- Tasks: ${task_count} sub-issues created
- Files renamed: 001.md → ${issue_num}.md format
- References updated: depends_on/conflicts_with now use issue IDs
- Worktree created for development

Co-authored-by: Claude Code <claude@anthropic.com>"

# 9. 清理临时文件
rm -f /tmp/epic-body*.md /tmp/task-body.md /tmp/tasks-section.md

# 10. 完成报告
echo ""
echo -e "${GREEN}🎉 GitHub同步完成！${NC}"
echo ""
echo -e "${BLUE}📊 同步统计：${NC}"
echo -e "  Epic: ${GREEN}#${epic_number} - ${NC}https://github.com/${repo}/issues/${epic_number}"
echo -e "  Tasks: ${GREEN}${task_count} 个子问题已创建${NC}"
echo -e "  Labels: ${YELLOW}epic, task, epic:gis-spatial-association-system${NC}"
echo -e "  Files: ${YELLOW}任务文件已重命名为GitHub Issue ID格式${NC}"
echo -e "  Worktree: ${YELLOW}../epic-gis-spatial-association-system${NC}"
echo ""
echo -e "${BLUE}🔗 下一步操作：${NC}"
echo -e "  - 开始并行执行: ${GREEN}/pm:epic-start gis-spatial-association-system${NC}"
echo -e "  - 或处理单个问题: ${GREEN}/pm:issue-start ${issue_num}${NC}"
echo -e "  - 查看Epic: ${BLUE}https://github.com/${repo}/issues/${epic_number}${NC}"
echo -e "  - 推送到远程: ${BLUE}git push origin main && git push origin epic/gis-spatial-association-system${NC}"
echo ""
echo -e "${GREEN}✨ Happy coding! 🚀${NC}"