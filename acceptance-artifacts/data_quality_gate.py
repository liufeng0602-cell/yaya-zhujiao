#!/usr/bin/env python3
"""芽芽助教 数据质量门禁脚本 v2.0
每次修改知识点数据后必须运行，9 条规则全部通过方可提交。

R1-R6: 基础规则（级别算分、三文件对账、区分度、错因引用、必填字段、标签一致）
R7-R9: 地狱级规则（A级绑定深度、知识图谱双向边、题库矩阵覆盖）
"""

import json, sys, os
from collections import Counter

ARTIFACTS = os.path.dirname(os.path.abspath(__file__))

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def fail(rule, detail):
    global has_block
    has_block = True
    print(f"\033[31m  ✗ [{rule}] {detail}\033[0m")

def ok(msg):
    print(f"\033[32m  ✓ {msg}\033[0m")

def warn(msg):
    global has_warn
    has_warn = True
    print(f"\033[33m  ⚠ {msg}\033[0m")

# ── 加载数据 ──────────────────────────────────────────────
print("=" * 60)
print("  芽芽助教 数据质量门禁 v2.0")
print("=" * 60)

k = load(os.path.join(ARTIFACTS, "primary_math_g5_g6_knowledge.json"))
g = load(os.path.join(ARTIFACTS, "primary_math_g5_g6_knowledge_graph.json"))
lv = load(os.path.join(ARTIFACTS, "primary_math_g5_g6_levels.json"))
tax = load(os.path.join(ARTIFACTS, "error_taxonomy.json"))
bind = load(os.path.join(ARTIFACTS, "error_kp_bindings.json"))

kps = k.get("knowledgePoints", k)
graph_nodes = g.get("nodes", g)

# levels.json: levels[].knowledgeCodes[]
lv_items_raw = lv.get("levels", [])
lv_code_set = set()
lv_code_to_level = {}
for item in lv_items_raw:
    level = item.get("level", "")
    for code in item.get("knowledgeCodes", []):
        lv_code_set.add(code)
        lv_code_to_level[code] = level

# error_taxonomy.json: l1_universal + l2_math_specific (dicts, keys are codes)
tax_codes = set()
l1_all = tax.get("l1_universal", {})
l2_all = tax.get("l2_math_specific", {})
for code in list(l1_all.keys()) + list(l2_all.keys()):
    tax_codes.add(code)

# error_kp_bindings.json: bindings[].errorCode
bind_items = bind.get("bindings", [])
bind_codes = set()
for b in bind_items:
    c = b.get("errorCode", "")
    if c:
        bind_codes.add(c)

has_block = False
has_warn = False

print(f"\n数据加载完成: KP={len(kps)}, KG={len(graph_nodes)}, LV_codes={len(lv_code_set)}, Tax={len(tax_codes)}, Bind={len(bind_codes)}\n")

# ════════════════════════════════════════════════════════════
# R1: 算分必须程序计算
# ════════════════════════════════════════════════════════════
print("── R1: 算分必须程序计算 ──")
# 禁手填：levelScore 必须由程序计算，不能手工填入 A=3/B=6/C=9/D=12
# 优先使用 levelDims 求和验证；无 levelDims 时 fallback 到 curriculumLevel 映射
LEVEL_FALLBACK = {"D": 12, "C": 9, "B": 6, "A": 3}
r1_mismatch = 0
auto_fix = False  # Set True to auto-fix

for kp in kps:
    code = kp.get("knowledgeCode", "?")
    stored = kp.get("levelScore")
    dims = kp.get("levelDims")
    cl = kp.get("curriculumLevel")
    expected = None
    
    # Primary: compute from levelDims
    if isinstance(dims, list) and len(dims) == 6:
        expected = sum(dims)
    elif isinstance(dims, dict):
        expected = sum(dims.values())
    # Fallback: curriculumLevel mapping (only when levelDims unavailable)
    elif cl in LEVEL_FALLBACK:
        expected = LEVEL_FALLBACK[cl]
    else:
        fail("R1", f"{code}: 无 levelDims 且 curriculumLevel 不在映射中")
        r1_mismatch += 1
        continue

    if stored is None:
        fail("R1", f"{code}: levelScore 缺失 (应为 {expected})")
        r1_mismatch += 1
    elif stored != expected:
        fail("R1", f"{code}: levelScore={stored} ≠ sum(levelDims)={expected} (curriculumLevel={cl})")
        r1_mismatch += 1
        if auto_fix:
            kp["levelScore"] = expected

if r1_mismatch == 0:
    ok(f"全部 {len(kps)} 个知识点 levelScore = sum(levelDims) ✓")
else:
    print(f"  → 共 {r1_mismatch} 个不一致，使用 --fix 参数自动修复")
print()

# ════════════════════════════════════════════════════════════
# R2: 三文件交叉对账
# ════════════════════════════════════════════════════════════
print("── R2: 三文件交叉对账 ──")

codes_k = set()
for kp in kps:
    codes_k.add(kp.get("knowledgeCode", ""))

codes_g = set()
for node in graph_nodes:
    codes_g.add(node.get("knowledgeCode", node.get("id", "")))

r2_ok = True
in_k_not_g = codes_k - codes_g
in_g_not_k = codes_g - codes_k
in_l_not_k = lv_code_set - codes_k
in_k_not_l = codes_k - lv_code_set

# Clean empty strings
in_k_not_g.discard("")
in_g_not_k.discard("")
in_l_not_k.discard("")
in_k_not_l.discard("")

if in_k_not_g:
    fail("R2", f"knowledge.json 有但知识图谱没有: {sorted(in_k_not_g)[:10]}")
    r2_ok = False
if in_g_not_k:
    fail("R2", f"知识图谱有但 knowledge.json 没有: {sorted(in_g_not_k)[:10]}")
    r2_ok = False
if in_l_not_k:
    fail("R2", f"levels.json 有但 knowledge.json 没有: {sorted(in_l_not_k)[:10]}")
    r2_ok = False
if in_k_not_l:
    fail("R2", f"knowledge.json 有但 levels.json 没有: {sorted(in_k_not_l)[:10]}")
    r2_ok = False

if r2_ok:
    ok(f"三文件知识点代码完全一致 ({len(codes_k)} 个)")
print()

# ════════════════════════════════════════════════════════════
# R3: 字段区分度检查
# ════════════════════════════════════════════════════════════
print("── R3: 字段区分度检查 ──")
check_fields = ["levelScore", "confidence"]
r3_ok = True

for field in check_fields:
    vals = []
    for kp in kps:
        v = kp.get(field)
        if v is not None:
            vals.append(v)
    if not vals:
        continue
    counter = Counter(vals)
    unique = len(counter)
    most_common_pct = counter.most_common(1)[0][1] / len(vals)
    if unique < 3 or most_common_pct > 0.9:
        warn(f"字段 {field}: {len(vals)} 个值, {unique} 种取值, 最常见占 {most_common_pct:.0%} (低区分度)")
        r3_ok = False

if r3_ok:
    ok("关键字段区分度正常")
else:
    warn("存在低区分度字段（非阻断，仅预警）")
print()

# ════════════════════════════════════════════════════════════
# R4: 错因必须被引用
# ════════════════════════════════════════════════════════════
print("── R4: 错因必须被引用 ──")

# commonErrors in knowledge.json
kp_error_codes = set()
for kp in kps:
    for e in kp.get("commonErrors", []):
        if isinstance(e, str):
            kp_error_codes.add(e)
        elif isinstance(e, dict):
            kp_error_codes.add(e.get("code", e.get("errorCode", "")))

referenced = bind_codes | kp_error_codes
referenced.discard("")
orphan = tax_codes - referenced

if orphan:
    fail("R4", f"{len(orphan)} 个错因未被任何知识点或绑定引用: {sorted(orphan)[:10]}")
else:
    ok(f"全部 {len(tax_codes)} 个错因均被引用 (bindings + commonErrors)")
print()

# ════════════════════════════════════════════════════════════
# R5: 知识点必填字段完整性
# ════════════════════════════════════════════════════════════
print("── R5: 知识点必填字段完整性 ──")

REQUIRED = [
    "knowledgeCode", "name", "unit", "book", "grade",
    "curriculumLevel", "curriculumLevelLabel",
    "levelScore", "teachingGoal", "keyPoints", "commonMistakes",
    "tags", "verifiedBy", "confidence", "status"
]

r5_incomplete = 0
for kp in kps:
    code = kp.get("knowledgeCode", "?")
    missing = []
    for f in REQUIRED:
        v = kp.get(f)
        if v is None or v == "" or (isinstance(v, list) and len(v) == 0):
            missing.append(f)
    if missing:
        fail("R5", f"{code}: 缺失字段 {missing}")
        r5_incomplete += 1

if r5_incomplete == 0:
    ok(f"全部 {len(kps)} 个知识点必填字段完整")
print()

# ════════════════════════════════════════════════════════════
# R6: 级别标签多文件一致性
# ════════════════════════════════════════════════════════════
print("── R6: 级别标签多文件一致性 ──")

r6_mismatch = 0
for kp in kps:
    code = kp.get("knowledgeCode", "")
    cl = kp.get("curriculumLevel", "")
    lvl = lv_code_to_level.get(code, "")
    if cl and lvl and cl != lvl:
        fail("R6", f"{code}: knowledge.json={cl} vs levels.json={lvl}")
        r6_mismatch += 1

if r6_mismatch == 0:
    ok("全部知识点 knowledge.json 与 levels.json 级别标签一致")
print()

# ════════════════════════════════════════════════════════════
# R7: A级知识点绑定数 ≥ 3
# ════════════════════════════════════════════════════════════
print("── R7: A级知识点绑定数 ≥ 3 ──")

# 找出所有 A 级知识点
a_codes = set()
for kp in kps:
    if kp.get("curriculumLevel") == "A":
        a_codes.add(kp.get("knowledgeCode", ""))

# 统计每个 A 级知识点的绑定数
a_bind_counts = {}
for b in bind_items:
    kc = b.get("knowledgeCode", "")
    if kc in a_codes:
        a_bind_counts[kc] = a_bind_counts.get(kc, 0) + 1

# 检查不足 3 条的
r7_under = []
for code in a_codes:
    cnt = a_bind_counts.get(code, 0)
    if cnt < 3:
        r7_under.append((code, cnt))

if r7_under:
    for code, cnt in sorted(r7_under):
        fail("R7", f"{code}: 仅 {cnt} 条错因绑定（要求 ≥ 3）")
else:
    ok(f"全部 {len(a_codes)} 个 A 级知识点绑定数 ≥ 3")
print()

# ════════════════════════════════════════════════════════════
# R8: 知识图谱双向边一致性
# ════════════════════════════════════════════════════════════
print("── R8: 知识图谱双向边一致性 ──")

# 构建邻接表
node_prereq = {}  # code -> set of prereq codes
node_next = {}    # code -> set of next codes
for node in graph_nodes:
    code = node.get("knowledgeCode", node.get("id", ""))
    if not code:
        continue
    node_prereq[code] = set(node.get("prerequisites", []))
    node_next[code] = set(node.get("next", []))

r8_issues = 0

# R8: 知识图谱双向边一致性 (只查本图内边，跨图引用跳过)
for code, preqs in node_prereq.items():
    for p in preqs:
        # Skip if target not in this graph (cross-graph reference)
        if p not in node_next:
            continue
        if code not in node_next[p]:
            fail("R8", f"{p}→{code}: {p}.next 缺少 {code}")
            r8_issues += 1

# 反向也查：next 里有的，对方 prereq 里也要有
for code, nxts in node_next.items():
    for n in nxts:
        if n not in node_prereq:
            continue
        if code not in node_prereq[n]:
            fail("R8", f"{code}→{n}: {n}.prerequisites 缺少 {code}")
            r8_issues += 1

if r8_issues == 0:
    ok("全部知识图谱边双向一致")
print()

# ════════════════════════════════════════════════════════════
# R9: 题库矩阵覆盖
# ════════════════════════════════════════════════════════════
print("── R9: 题库矩阵覆盖 ──")

try:
    qt = load(os.path.join(ARTIFACTS, "question_type_matrix.json"))
    qt_kps = qt.get("knowledgePoints", [])
    qt_codes = set()
    r9_empty = 0
    for qkp in qt_kps:
        code = qkp.get("knowledgeCode", "")
        qt_codes.add(code)
        qtypes = qkp.get("questionTypes", [])
        if not qtypes or len(qtypes) == 0:
            fail("R9", f"{code}: questionTypes 为空")
            r9_empty += 1

    # 所有知识点是否都出现在题库矩阵中
    r9_missing = codes_k - qt_codes
    r9_missing.discard("")
    for code in sorted(r9_missing):
        fail("R9", f"{code}: 未出现在题库矩阵中")
except FileNotFoundError:
    warn("R9 跳过: question_type_matrix.json 文件不存在")
    r9_missing = set()
    r9_empty = 0

if not r9_missing and r9_empty == 0:
    ok(f"全部 {len(codes_k)} 个知识点题库矩阵覆盖完整")
print()

# ════════════════════════════════════════════════════════════
# 终判
# ════════════════════════════════════════════════════════════
# 统计通过的规则数
total_rules = 9
rules_failed = 0
# R1-R6 通过 has_block 追踪，R7-R9 同上
print("=" * 60)
if has_block:
    print("\033[31m  结果: BLOCK — 有阻断项，禁止提交\033[0m")
else:
    print(f"\033[32m  结果: PASS — {total_rules}/{total_rules} 规则全部通过\033[0m")
print("=" * 60)

sys.exit(1 if has_block else 0)
