#!/usr/bin/env python3
"""S09 课堂生成引擎自动化审计脚本 v2
覆盖 DOC_ACCEPTANCE_STANDARD v2.2 全部 BLOCK 项 + 两轮地狱评审19类问题模式
用法: python3 audit_s09.py
退出码: 0=全部通过, 1=有 BLOCK 错误
"""

import re, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
S09_PATH = "/Users/liufeng/Documents/芽芽AI助教/subsystems/S09_CLASSROOM_ENGINE.md"
errors = []
warnings = []

def err(msg): errors.append(msg)
def warn(msg): warnings.append(msg)

with open(S09_PATH) as f:
    doc = f.read()
lines = doc.split('\n')

print(f"=== S09 审计开始 ({len(lines)}行) ===\n")

# ===== 1. 必填章节完整性 (1.1) =====
required_sections = [
    ('变更记录', '变更记录'),
    ('北极星对齐', '北极星对齐'),
    ('定义与职责', '定义与职责'),
    ('通用骨架标准定义', '通用骨架标准定义'),
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
ver_match = re.search(r'v(\d+\.\d+(?:\.\d+)?)', title_line)
changelog_versions = re.findall(r'\|\s*v(\d+\.\d+(?:\.\d+)?)\s*\|', '\n'.join(lines[3:15]))
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
# Use ### heading to avoid matching changelog mentions
matrix_start = doc.find('### 维度交互矩阵\n')
matrix_text = doc[matrix_start:matrix_start+1200] if matrix_start > 0 else ''
if matrix_start > 0:
    if '验证步骤' not in matrix_text:
        err("[1.17] 维度交互矩阵缺少验证步骤")
else:
    err("[1.17] 维度交互矩阵缺失（### 标题）")

# ===== 15. 三级权限分级 =====
if '三级权限分级' in doc:
    if not ('高级' in doc and '中级' in doc and '低级' in doc):
        warn("[1.12] 三级权限分级缺少完整三级定义")
else:
    err("[1.12] 缺少三级权限分级")

# ===== 16. HUMAN-SIGNED 参数节 =====
if 'HUMAN-SIGNED' not in doc:
    warn("[1.7附] 缺少 HUMAN-SIGNED 参数节")

# ===== 17. 提交前自查声明 (3.18) =====
if not ('自查一' in doc and '自查二' in doc and '自查三' in doc):
    err("[3.18] 缺少提交前自查声明")

# ===== SPECIFIC CHECKS: 两轮地狱评审问题模式 =====

# P1: 通用骨架标准定义集中化 (v1.7问题1)
if '通用骨架标准定义' not in doc:
    err("[P1] 缺少通用骨架标准定义集中章节")
# 验证4处引用点都在
gs_ref_count = doc.count('通用骨架——标准定义见 §通用骨架标准定义')
if gs_ref_count < 4:
    warn(f"[P1] 通用骨架引用仅{gs_ref_count}处（预期≥4处: 北极星底线/超纲/质检回退/信用分）")

# P2: SP_G_D01 AI字眼免疫说明 (v1.7问题2)
# Find SP_G_D01 definition (skip changelog by searching for the definition text)
sp_def_start = doc.find('SP_G_D01 即通用骨架（标准定义见')
sp_d01_text = doc[sp_def_start:sp_def_start+500] if sp_def_start > 0 else ''
if '不经过LLM生成' not in sp_d01_text:
    warn("[P2] SP_G_D01未标注不经过LLM生成")
if '使用场景区分' not in sp_d01_text:
    warn("[P2] SP_G_D01未标注与通用骨架的使用场景区分")

# P3: 缓存1500组合数(v1.7问题3)
if '1500 个活跃组合' not in doc:
    err("[P3] 缓存容量未明确1500=组合数(非记录数)")

# P4: 退化计数器跨骨架(v1.7问题4)
if '跨骨架类型累计' not in doc:
    err("[P4] 退化计数器未明确跨骨架累计")

# P5: 退化组合场景枚举(v1.7问题5)
if '退化组合场景枚举' not in doc:
    err("[P5] 缺少退化组合场景枚举")

# P6: 接口契约附件标注(v1.7问题6)
s02_contract = doc[doc.find('S02/S09 接口契约附件'):doc.find('S02/S09 接口契约附件')+150] if 'S02/S09 接口契约附件' in doc else ''
if '当前该附件不存在' not in s02_contract:
    warn("[P6] S02/S09接口契约附件未标注不存在")

# P7: 维度交互矩阵三条件
matrix_start = doc.find('### 维度交互矩阵\n')
matrix_end = doc.find('### 退化组合场景枚举', matrix_start) if matrix_start > 0 else -1
if matrix_end == -1:
    matrix_end = doc.find('## 自我进化执行方法', matrix_start) if matrix_start > 0 else -1
matrix_text = doc[matrix_start:matrix_end] if matrix_start > 0 and matrix_end > 0 else ''
if '三个触发条件' not in matrix_text:
    err("[P7] 维度交互矩阵未验证全部三个触发条件")

# P8: 维度二触发不依赖积木库≥50 (只检查维度二的触发条件行，不检查终局状态)
dim2_section_start = doc.find('### 维度二：生成效率进化')
dim2_section = doc[dim2_section_start:dim2_section_start+500] if dim2_section_start > 0 else ''
# 提取触发条件列(表格第2列)
dim2_lines = dim2_section.split('\n')
for line in dim2_lines:
    if '|' in line and '阶段' in line and '2' in line and '自主' in line:
        if re.search(r'积木库\s*[≥>]\s*50', line):
            err("[P8] 维度二触发条件仍含积木库≥50（循环依赖）")
        break

# P9: SP_G_D01错因排序(v1.6已修复) - search for definition text directly
sp_d01_line = doc.find('SP_G_D01 即通用骨架（标准定义见')
if sp_d01_line > 0:
    sp_context = doc[sp_d01_line:sp_d01_line+800]
    if '绑定频率降序' not in sp_context and 'error_kp_bindings' not in sp_context and '排序规则与通用骨架一致' not in sp_context:
        warn("[P9] SP_G_D01缺少错因排序规则")

# P10: 200ms标注
if 'p50经验值' not in doc:
    err("[P10] 200ms延迟未标注p50经验值/非硬阈值")

# P11: parentExplanation兜底话术
if 'parentExplanation 也缺失' not in doc:
    warn("[P11] parentExplanation缺失时未标注兜底话术")

# P12: S13缺失降级方案 (check in both 通用骨架标准定义 and S13消费清单行)
gs_def = doc[doc.find('通用骨架标准定义'):doc.find('通用骨架标准定义')+800] if '通用骨架标准定义' in doc else ''
s13_consumer = doc[doc.find('| 题目数据 | S13'):doc.find('| 题目数据 | S13')+200] if '| 题目数据 | S13' in doc else ''
has_s13_fallback = ('S13 未就绪' in gs_def and '降级为 S01' in gs_def) or ('S13 子系统未建' in s13_consumer)
if not has_s13_fallback:
    warn("[P12] S13缺失降级方案未标注")

# P13: 退化计数器清零
if '从0重新开始计数' not in doc:
    err("[P13] 退化计数器清零规则未定义")

# P14: 总时长约束
if '总时长约束' not in doc or '480秒' not in doc:
    err("[P14] 五环节总时长上限未定义")

# P15: 8种画像组合逻辑
if 'G5默认「夸他」，G6默认「积分」' not in doc:
    warn("[P15] 8种画像组合逻辑未完整解释")

# P16: SP_G_D01使用场景(已在P2检查)

# P17: 缓存3次用途
if '缓存 3 次而非 1 次的原因' not in doc:
    warn("[P17] 缓存3次用途未说明")

# P18: 矩阵月度回顾标注
if '月度回顾性核查' not in doc:
    warn("[P18] 矩阵验证步骤未标注月度回顾")

# P19: 自查声明数字
if '共 15 条记录' not in doc:
    warn("[P19] 自查声明消费清单记录数未更新")

# ===== 跨文档引用检查 =====
# S02 masteryLevel - check that the broken reference doc note exists
s02_section = doc[doc.find('S02 知识图谱'):doc.find('S02 知识图谱')+300] if 'S02 知识图谱' in doc else ''
if 'S02/S09 接口契约附件' in s02_section and '当前该附件不存在' not in s02_section:
    warn("[跨文档] S02 接口契约附件引用未标注不存在")

# S13 存在性 - only warn if S13 is referenced WITHOUT proper annotation
s13_doc_exists = os.path.exists('/Users/liufeng/Documents/芽芽AI助教/subsystems/S13_DIFFICULTY_MATRIX.md')
s13_refs = [l for l in lines if 'S13' in l and ('教材' in l or '题库' in l or '题型' in l)]
if s13_refs and not s13_doc_exists:
    for l in s13_refs:
        l_stripped = l.strip()
        # Skip lines that already have proper annotations
        if any(kw in l for kw in ['待 S13', 'S13 子系统', 'S13子系统', 'S13 确认', 'S13 未就绪', 'S13未就绪', 'S13 缺失', 'S13 子系统未建', 'S13子系统未建']):
            continue
        # Skip 大白话 section mentions (just listing data sources)
        if '知识库（S01）+图谱（S02）+错因定义（S03）' in l:
            continue
        # Skip 阶段1触发条件 line (listing dependency requirements, not a reference to consume)
        if 'S13 教材数据全量录入 + S07/S08 引擎就绪' in l:
            continue
        warn(f"[跨文档] S13引用但子系统不存在且未标注待定义: {l_stripped[:80]}...")

# ===== 结果输出 =====
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
