#!/usr/bin/env python3
"""S09 课堂生成引擎自动化审计脚本 v3
覆盖 DOC_ACCEPTANCE_STANDARD v2.2 全部 BLOCK 项 + 三轮地狱评审所有问题模式
v3: 适配 v1.8 结构变更(降级策略独立章节/维度二后移/信用分单分制)
用法: python3 audit_s09.py
退出码: 0=全部通过, 1=有 BLOCK 错误
"""

import re, sys, os

S09_PATH = "/Users/liufeng/Documents/芽芽AI助教/subsystems/S09_CLASSROOM_ENGINE.md"
errors = []
warnings = []

def err(msg): errors.append(msg)
def warn(msg): warnings.append(msg)

with open(S09_PATH) as f:
    doc = f.read()
lines = doc.split('\n')

print(f"=== S09 审计 v3 ({len(lines)}行) ===\n")

# ===== 1. 必填章节完整性 (1.1) =====
required_sections = [
    ('变更记录', '变更记录'),
    ('北极星对齐', '北极星对齐'),
    ('定义与职责', '定义与职责'),
    ('降级策略', '降级策略'),
    ('核心设计', '核心设计'),
    ('它还不会什么', '它还不会什么'),
    ('设计演化推理链', '设计演化推理链'),
    ('自我进化路线图', '自我进化路线图'),
    ('退化组合场景枚举', '退化组合场景枚举'),
    ('自我进化执行方法', '自我进化执行方法'),
    ('消费关系清单', '消费关系清单'),
    ('不可修改边界', '不可修改边界'),
    ('大白话', '大白话'),
    ('提交前自查', '提交前自查声明'),
]
for name, pattern in required_sections:
    if pattern not in doc:
        err(f"[1.1] 缺少必填章节: {name}")

# ===== 2. 版本号一致性 (1.2) =====
title_line = lines[0]
ver_match = re.search(r'v(\d+\.\d+(?:\d+\.\d+)?)', title_line)
changelog_versions = re.findall(r'\|\s*v(\d+\.\d+(?:\d+\.\d+)?)\s*\|', '\n'.join(lines[3:15]))
if ver_match and changelog_versions:
    if ver_match.group(1) != changelog_versions[0]:
        err(f"[1.2] 标题版本 {ver_match.group(1)} ≠ 变更记录最新版本 {changelog_versions[0]}")

# ===== 3. AI-MUTABLE 标注完整性 (1.4) =====
ai_mutable_count = doc.count('AI-MUTABLE')
print(f"  AI-MUTABLE标注数: {ai_mutable_count}")

# ===== 4. 消费清单7列完整 (1.5) =====
if '| 本系统的元素 | 被消费方 | 消费方式 | 故障类型 | 严重等级 | 检测方式 | 链路类型 |' not in doc:
    err("[1.5] 消费清单缺少完整7列表头")

# ===== 5. 大白话10类 (1.6) =====
plain_lang_cats = ['系统职责定义', '核心设计', '自我进化路线图', '不可修改边界', '接口约定',
                   '自我进化执行方法', '异常进化处置', '应急熔断', '进化信用分', '内容与代码进化分离']
for cat in plain_lang_cats:
    if cat not in doc:
        warn(f"[1.6] 大白话缺类: {cat}")

# ===== 6. 不可修改边界7类 (1.7) =====
immutable_cats = ['外界法规定义', '全局外键', '通信协议', '学生原始数据', '质量门禁', '北极星底线', 'Shareable']
for cat in immutable_cats:
    if cat not in doc:
        err(f"[1.7] 不可修改边界缺类: {cat}")

# ===== 7. 间接修改表 (1.8) =====
if '间接修改边界量化表' not in doc and '间接修改' not in doc:
    err("[1.8] 缺少间接修改边界量化表")

# ===== 8. 越界告警 (1.9) =====
if '越界告警' not in doc:
    err("[1.9] 缺少越界告警分级处置")

# ===== 9. 北极星对齐 (1.10) =====
if not ('底线信号' in doc and '负信号' in doc and '正信号' in doc):
    err("[1.10] 北极星三层信号不完整")

# ===== 10. 进化路线图七要素 (1.11) =====
if '| 阶段 | 触发条件 | 系统能力 | 人工角色 | 终局状态 | 退化降级规则 |' not in doc:
    err("[1.11] 进化路线图缺少标准6列表头")

# ===== 11. 五类角色+五步流程+信用分 (1.12) =====
roles = ['芽芽自己', 'AI 编程工具', '产品经理', '教研人员', '审查员']
for role in roles:
    if role not in doc:
        warn(f"[1.12] 角色权限台账缺角色: {role}")
if '影子模式' not in doc or 'A/B' not in doc:
    err("[1.12] 缺少五步执行流程")

# ===== 12. 安全执行管道 (1.13) =====
if not ('影子模式' in doc and 'A/B 测试' in doc and '全量上线' in doc):
    err("[1.13] 安全执行管道三层不完整")

# ===== 13. 内容与代码进化分离 (1.15) =====
if not ('内容进化' in doc and '代码进化' in doc and '混合进化' in doc):
    err("[1.15] 内容与代码进化分离不完整或缺失")

# ===== 14. 维度交互矩阵 (1.17) =====
matrix_start = doc.find('### 维度交互矩阵')
matrix_text = doc[matrix_start:matrix_start+1200] if matrix_start > 0 else ''
if matrix_start > 0:
    if '验证步骤' not in matrix_text:
        err("[1.17] 维度交互矩阵缺少验证步骤")
else:
    err("[1.17] 维度交互矩阵缺失")

# ===== 15. 三级权限分级 =====
if '三级权限分级' not in doc:
    err("[1.12] 缺少三级权限分级")
elif not ('高级' in doc and '中级' in doc and '低级' in doc):
    warn("[1.12] 三级权限分级缺少完整三级定义")

# ===== 16. HUMAN-SIGNED =====
if 'HUMAN-SIGNED' not in doc:
    warn("[1.7附] 缺少 HUMAN-SIGNED 参数节")

# ===== 17. 提交前自查声明 =====
if not ('自查一' in doc and '自查二' in doc and '自查三' in doc):
    err("[3.18] 缺少提交前自查声明")

# ===================================================================
# v1.6-v1.7 SPECIFIC CHECKS
# ===================================================================

# P3: 缓存容量
if '1500 个活跃组合' not in doc:
    err("[P3] 缓存容量未明确")
if '服务端内存' not in doc:
    warn("[P3] 缓存未标注服务端位置")
if '13.5MB' in doc and '浏览器' not in doc:
    warn("[P3] 缓存标注了服务端但未提醒不可放前端")

# P4: 退化计数器跨骨架
if '跨骨架类型累计' not in doc:
    err("[P4] 退化计数器未明确跨骨架累计")

# P5: 退化组合枚举
if '退化组合场景枚举' not in doc:
    err("[P5] 缺少退化组合场景枚举")

# P6: S02接口契约
s02_contract = doc[doc.find('S02/S09 接口契约附件'):doc.find('S02/S09 接口契约附件')+200] if 'S02/S09 接口契约附件' in doc else ''
if '内联' not in s02_contract and '替代方案' not in s02_contract:
    warn("[P6] S02接口契约附件未标注替代方案")

# P7: 维度交互矩阵三条件(已在1.17检查)

# P8: 维度二 Phase 3 后移标记
dim2_title = doc.find('### 维度二：生成效率进化')
if dim2_title > 0:
    dim2_line = lines[doc[:dim2_title].count('\n')]
    if 'Phase 3' not in dim2_line and 'Phase 3' not in doc[dim2_title:dim2_title+200]:
        warn("[P8] 维度二未标注Phase 3后移")

# P9: SP_G_D01错因排序 — L3 defers to L2
# Check if L3 explicitly has sorting, or references L2 which has it
l3_start = doc.find('### L3 有感知降级') if '### L3 有感知降级' in doc else -1
l2_start = doc.find('### L2 无感知降级')
l2_text = doc[l2_start:l2_start+800] if l2_start > 0 else ''
l3_text = doc[l3_start:l3_start+800] if l3_start > 0 else ''
has_sort_l2 = 'error_kp_bindings' in l2_text or '绑定频率降序' in l2_text
has_sort_l3 = 'error_kp_bindings' in l3_text or '绑定频率降序' in l3_text
l3_refs_l2 = '通用骨架' in l3_text and '完全相同' in l3_text
if not has_sort_l3 and not (has_sort_l2 and l3_refs_l2):
    warn("[P9] SP_G_D01(L3)缺少错因排序规则且未引用L2")

# P10: 200ms
if '本地压测' not in doc:
    warn("[P10] 200ms p50未标注数据来源(本地压测)")

# P11: parentExplanation兜底
if 'parentExplanation 也缺失' not in doc:
    warn("[P11] parentExplanation缺失时未标注兜底话术")

# P12: S13降级
l2_start = doc.find('### L2 无感知降级')
l2_text = doc[l2_start:l2_start+800] if l2_start > 0 else ''
s13_consumer = doc[doc.find('| 题目数据 | S13'):doc.find('| 题目数据 | S13')+200] if '| 题目数据 | S13' in doc else ''
if 'S13 子系统未建' not in (l2_text + s13_consumer):
    warn("[P12] S13缺失降级方案未标注")

# P13: 计数器清零
if '从0重新开始计数' not in doc:
    err("[P13] 退化计数器清零规则未定义")

# P14: 总时长 → v1.8改为690
if '690 秒' not in doc:
    err("[P14] 总时长约束未更新为690秒")

# P15: 8种画像
if 'G5默认「夸他」，G6默认「积分」' not in doc:
    warn("[P15] 8种画像组合逻辑不完整")

# P17: 缓存3次
if '缓存 3 次而非 1 次的原因' not in doc:
    warn("[P17] 缓存3次用途未说明")

# P19: 自查声明数字(15条—已确认)

# ===================================================================
# v1.8 NEW CHECKS
# ===================================================================

# N1: 降级策略L0-L4表
if '| L0: 无降级' not in doc:
    err("[N1] 降级策略缺少L0-L4降级层级表")
elif '| L4:' not in doc:
    warn("[N1] 降级策略L4层级不完整")

# N2: SP_G_D01宕机场景
if 'S08_UNAVAILABLE' not in doc:
    warn("[N2] SP_G_D01缺少宕机errorCode")

# N3: 冷启动体验
if '冷启动体验标注' not in doc:
    warn("[N3] 缺少冷启动体验标注(前3次课堂反馈质量差异)")

# N4: 逐字段回退策略表
if '| 钩子字段 | 数据来源 | Phase1默认值 | Phase2回退条件 | Phase2回退值 |' not in doc:
    warn("[N4] 缺少逐字段回退策略表")

# N5: 种子积木手动标记
if '种子积木手动标记' not in doc:
    warn("[N5] 缺少种子积木手动标记入口")

# N6: 复习类统一模板
if '统一标准模板' not in doc:
    warn("[N6] 复习类未使用统一标准模板(仍为豁免)")

# N7: 信用分单分制
if '单分制' not in doc:
    warn("[N7] 信用分未简化为单分制")

# N8: 500ms移除
if '500ms超时' in doc:
    warn("[N8] 仍含500ms超时等待(应与异步推送冲突)")
if 'S09不主动查询S07' not in doc:
    warn("[N8] S07消费清单行未更新异步说明")

# N9: 矩阵纠正措施
if '纠正措施' not in doc:
    warn("[N9] 矩阵验证步骤缺少未通过时的纠正措施")

# N10: HTML注释格式
if '-- >' in doc:
    err("[N10] 仍含格式错误的HTML注释 '-- >'")

# ===== 跨文档引用检查 =====
# S02 masteryLevel
s02_section = doc[doc.find('S02 知识图谱'):doc.find('S02 知识图谱')+400] if 'S02 知识图谱' in doc else ''
if 'S02/S09 接口契约附件' in s02_section and '当前该附件不存在' not in s02_section:
    warn("[跨文档] S02 接口契约附件引用未标注不存在")

# S13 存在性
s13_refs = [l for l in lines if 'S13' in l and ('教材' in l or '题库' in l or '题型' in l)]
s13_doc_exists = os.path.exists('/Users/liufeng/Documents/芽芽AI助教/subsystems/S13_DIFFICULTY_MATRIX.md')
if s13_refs and not s13_doc_exists:
    for l in s13_refs:
        if any(kw in l for kw in ['待 S13', 'S13 子系统', 'S13子系统', 'S13 确认', 'S13 未就绪', 'S13未就绪', 'S13 缺失', 'S13 子系统未建', 'S13子系统未建']):
            continue
        if '知识库（S01）+图谱（S02）+错因定义（S03）' in l:
            continue
        if 'S13 教材数据全量录入 + S07/S08 引擎就绪' in l:
            continue
        warn(f"[跨文档] S13引用但子系统不存在且未标注待定义: {l.strip()[:80]}...")

# ===== 结果 =====
print(f"\n=== 审计结果 ===")
print(f"  BLOCK错误: {len(errors)}")
print(f"  WARN建议: {len(warnings)}")

if errors:
    print("\n🔴 BLOCK错误:")
    for e in errors:
        print(f"  - {e}")

if warnings:
    print("\n🟡 WARN建议:")
    for w in warnings:
        print(f"  - {w}")

if not errors and not warnings:
    print("✅ 全部通过！")

print(f"\n=== 完成 ===")
sys.exit(1 if errors else 0)
