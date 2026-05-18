#!/usr/bin/env python3
"""端到端流程测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kanban_ops import *

project = 'yaya-zhujiao'

# 1. 创建任务
tid = create_task(project, '测试 S01 文档审核',
                  file_path='projects/yaya-zhujiao/test_S01.md',
                  version='v1.0')
print(f'1. 创建任务: {tid}')

# 2. Writer claim: backlog -> drafting
update_task_status(project, tid, 'drafting', assigned_to='writer')
add_comment(project, tid, 'writer', '开始写作测试')
print('2. -> drafting')

# 3. 创建测试文件
os.makedirs('projects/yaya-zhujiao', exist_ok=True)
with open('projects/yaya-zhujiao/test_S01.md', 'w') as f:
    f.write('# 测试 S01 知识管理系统 v1.0\n\n')
    f.write('版本号: v1.0\n变更记录:\n- v1.0: 初始版本\n\n')
    f.write('## 1. 概述\n这是一个测试文档。\n\n')
    f.write('## 2. 数据模型\n| 字段 | 类型 | 说明 |\n|------|------|------|\n')
    f.write('| id | TEXT | 主键 |\n\n')
    f.write('## 3. 接口定义\n无\n\n')
    f.write('## 4. 状态机\nbacklog -> drafting -> awaiting_review\n\n')
    f.write('## 5. 部署步骤\nnpm install\n\n')
    f.write('## 6. 引用\n待 S99 定义\n')
print('3. 创建测试文件')

# 4. Writer 提交: drafting -> awaiting_review
update_task_status(project, tid, 'awaiting_review', commit_sha='test_sha_001')
add_comment(project, tid, 'writer', '自检声明: 写作完成')
print('4. -> awaiting_review')

# 5. Reviewer 审核
task = get_task(project, tid)
with open(task['file_path']) as f:
    content = f.read()

p0, p1, p2 = 0, 0, 0
if '待 S99 定义' in content:
    p1 += 1
    print(f'5. 审核发现: P1 - 待 S99 定义未闭合')

if p0 == 0 and p1 == 0:
    update_task_status(project, tid, 'approved')
    print(f'5. -> approved (P0=0 P1=0)')
else:
    increment_iteration(project, tid)
    update_task_status(project, tid, 'needs_revision')
    print(f'5. -> needs_revision (P0={p0} P1={p1})')

# 6. 验证
task = get_task(project, tid)
comments = get_comments(project, tid)
print(f'6. 最终: status={task["status"]}, comments={len(comments)}, iteration={task["iteration_count"]}')

# 7. needs_revision -> drafting (Writer 接手修改)
if task['status'] == 'needs_revision':
    update_task_status(project, tid, 'drafting', assigned_to='writer')
    add_comment(project, tid, 'writer', '开始修改（来自 needs_revision）')
    task = get_task(project, tid)
    assert task['status'] == 'drafting', f"应该进入 drafting, 实际 {task['status']}"
    print(f'7. needs_revision -> drafting ✓')

    # 修复后提交
    update_task_status(project, tid, 'awaiting_review')
    print(f'7. drafting -> awaiting_review ✓')

# 8. 第二轮审核通过
task = get_task(project, tid)
update_task_status(project, tid, 'approved')
task = get_task(project, tid)
assert task['status'] == 'approved'
print(f'8. -> approved ✓')

# 9. approved -> p2_clearing -> p2_cleared -> signed_off
update_task_status(project, tid, 'p2_clearing')
task = get_task(project, tid)
assert task['status'] == 'p2_clearing', f"应该进入 p2_clearing, 实际 {task['status']}"
print('9. -> p2_clearing ✓')

update_task_status(project, tid, 'p2_cleared')
task = get_task(project, tid)
assert task['status'] == 'p2_cleared'
print('9. -> p2_cleared ✓')

update_task_status(project, tid, 'signed_off')
task = get_task(project, tid)
assert task['status'] == 'signed_off'
print(f'9. -> signed_off ✓')

# 10. alert 验证
add_alert(project, '测试端到端通过')
alerts_dir = os.path.join(KANBAN_DIR, '.alerts')
alert_count = len([f for f in os.listdir(alerts_dir) if f.startswith(project)])
print(f'10. alert 文件数: {alert_count} ✓')

print('\n=== 端到端全部 10 项通过 ✓ ===')
