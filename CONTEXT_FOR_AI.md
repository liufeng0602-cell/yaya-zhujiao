# 芽芽项目上下文（给 AI 读的）

## 项目路径

- 代码：`~/Downloads/yaya-browser-v3`
- 文档：`~/Downloads/yaya-browser-v3/acceptance-artifacts/`
- 生成输出：`/tmp/`

## 当前引擎文档版本（2026-05-14）

| 文档 | 版本 | 状态 |
|------|------|------|
| 08_STRATEGY_PACKS.md | v2.1.2 | 已审 |
| 09_EVENT_PROTOCOL.md | v2.0.7 | 权威，11 事件 |
| 10_DATA_MODEL.md | v2.1.2 | 已审 |
| 11_DIAGNOSIS_ENGINE.md | v2.4.1 | 已审 |
| 12_STRATEGY_ENGINE.md | 待升版 | 17 问题中 13 已修 |
| 13_PARENT_SUMMARY_RULES.md | — | 待审查 |
| 14_QUALITY_DASHBOARD.md | — | 待审查 |

## 验收预览页规范

- PC 宽度 max-width: 1100px
- KP 行：展开详情 / ✨ 生成个性化课堂 / 📝 AI测试题 / 🎯 考试真题
- 单元 📚 按钮 → 教材浏览器在 unit-bd 顶部
- HTML 由 gen_full_preview.py 生成到 /tmp/，HTTP serve
- 图片用 HTTP 相对路径 `/tb_g5s1/pNNN.png`（禁用 file://）
- 生成后必验：189 KP / 31 单元 / 0 个 file://
- 无 per-KP 教材按钮（用户明确拒绝）

## 教师用书 PDF 提取

偏移量（PDF 页码 = 内部页码 + 偏移）：
- 五上：+12
- 五下：+11
- 六上：+12（但 U6 可能例外）
- 六下：+12

**TOC 页码不可盲信**：实测发现五下 U6、六上 U6 的 TOC 页码与实际 PDF 位置不一致。找不到时用 wide-range 恢复（渲染 15-20 页 + batch OCR + grep "教学目标"）。

提取流程：
1. Phase 0：easyocr TOC 提取目录页码
2. Phase 1：根据 TOC 渲染目标页 + 批量 OCR
3. Phase 2：vision_analyze 精确抄录关键单元

## 学生用书 PDF

偏移量：PDF 页码 = 课本页码 + 5（四册通用）

## 策略引擎 12 号待修问题

问题 12：家长反馈权重映射未完整（需明确：helpful ×1.2 / accurate 不影响 / inaccurate 标记人工复核 / reobserve 不影响但降低 confidence 贡献）

问题 17：验收标准需补充（traced 消费逻辑 / excluded 超时降级 / 连续退出触发 / 强策略五条件缺一不可）

## 关键设计决策

- 诊断引擎 validationActions → 诊断引擎选验证题；recommendedStrategies → 策略引擎经 strategy_mapping.json 消费
- 策略引擎以 taxonomy→strategy_mapping 为权威路径，KnowledgeNode.strategyPacks 仅教研参考
- -999 统一空值标记，消费方跳过不参与加权
- Phase 1 溯源仅限 G5-G6 图覆盖范围（3 层）
- 全局权重 vs 个人权重独立计算不叠乘，全局 < 0.3 进教研复审
- 强策略同天限制：总次数 ≤ 2 次，不受种类限制
- 强策略定义（08 §7.1 五条件）：变式特训包 SP_G_C02、错因专项包 SP_G_C03
