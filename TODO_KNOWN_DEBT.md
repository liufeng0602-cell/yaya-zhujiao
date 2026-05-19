# TODO / Known Debt

## P1 — 闭源策略包

### value_range 规则在 PRD 和 Tech Doc 中重复
- `prd/l1/value_range`（`rules_prd.yaml`）和 `tech/l1/value_range_tech`（`rules_tech_doc.yaml`）检查逻辑相同：校验 PARAM 值是否在 glossary 约束范围内。
- 唯一差异：PRD 侧重业务术语（信用分、超时时间），Tech Doc 侧重技术参数（响应时间、请求速率）。
- 归属：glossary 自身已通过术语分类覆盖差异，规则本身不需要两份。
- 行动计划：后续抽为 `common/l1/value_range` 通用规则，两个 rules 文件共引用同一 id。
- 优先级：MVP 后可合并，不阻塞当前交付。

### `tech/l1/endpoint_naming` 的 check_type 语义错配
- 当前 `check_type: section_coverage`，但检查内容为"路径命名约定验证"。
- `section_coverage` checker 无法执行正则风格检查（小写、连字符、复数）。
- 后续需新增 `check_type: naming_convention` 或将此规则改为 L2（LLM 验证）。
- 优先级：MVP 阶段暂保留现状，规则不生效但不报错。

### security_consideration 依赖词表完整性
- `tech/l2/security_consideration` 使用 `trigger: on_term`，触发依赖 "认证方式"、"令牌过期时间" 是否出现在文档中。
- 如果文档使用同义词（如 "登录鉴权"、"token ttl"）而未使用标准术语，规则不会触发。
- 当前 MVP 阶段已加强 `term_refs` 覆盖面。后续可改为 `doc_flags` 驱动的显式声明模式。

## P2 — 开源框架

### StrategyPack.load() 实现在闭源方
- 开源框架的 `StrategyPack.load()` 为 `raise NotImplementedError`，docstring 描述了完整契约。
- 闭源策略包（`closed_source_pack/`）需覆写 `load()` 实现 prompts/ 扫描和规则解析。
- 已添加 `test_strategy_pack.py` 验证接口契约。

### test_e2e.py 状态名不匹配
- `test_e2e.py` 引用状态名 "needs_revision"，但 `kanban_ops` 使用 "revision"。
- 5 个 e2e 测试因此失败。Writer 门禁相关的 68 个测试全部通过。
- 优先级：低，不影响 Writer/Reviewer 核心流程。
