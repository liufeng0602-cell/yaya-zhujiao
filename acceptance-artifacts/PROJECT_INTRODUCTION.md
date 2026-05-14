# 芽芽助教项目完整介绍

## 1. 项目一句话定义

**芽芽助教** 是一个面向 K12 学生的 AI 学习产品，目标是通过 AI 讲解、智能题库、错因诊断、学习画像、真课堂课件、TTS 朗读和家长反馈，构建一个能够长期陪伴学生成长、越用越懂孩子、越教越会教的自我进化 AI 教学系统。

它不是普通题库，也不是简单 AI 聊天讲题工具，而是一个围绕 **知识点 → 讲解 → 练习 → 错因 → 策略 → 课堂 → 成长记忆** 闭环构建的 AI 教学适配引擎。

---

## 2. 项目当前定位

芽芽助教当前处于 **本地可运行 MVP + 真课堂引擎增强阶段**。

当前已经完成：

- 小学知识点体系建设
- AI 讲解生成
- AI 题库预热
- 掌握度更新
- 错题本
- 教材 / 真题资源库
- 火山引擎 TTS
- 真课堂课件设计文档
- 前端课堂播放器
- Hermes Agent 工作流迁移
- 飞书机器人接入
- 方舟 Agent Plan 模型接入
- 自我进化 AI 教学适配引擎 PRD 拆分文档

项目未来目标是覆盖：

- 小学
- 初中
- 高中
- 多学科
- 多教材版本
- 多题型
- 个性化教学适配
- 家长端学习摘要
- K12 全学段 AI 教学闭环

---

## 3. 产品核心理念

芽芽助教的核心不是“让 AI 回答问题”，而是让 AI 在教学过程中持续理解学生：

- 孩子在哪个知识点卡住
- 是概念不懂，还是审题遗漏
- 是计算失误，还是题型不熟
- 哪种讲法对孩子更有效
- 哪种提示会造成依赖
- 孩子是否需要轻松一点，还是可以挑战一下
- 后续应该讲什么、练什么、复习什么

最终形成：

> 孩子用得越久，芽芽越懂他；芽芽教得越久，越知道怎么教他。

---

## 4. 项目核心模块

### 4.1 知识树系统

知识树是芽芽助教的基础。

当前已经录入并验证：

- 827 个知识点
- 覆盖小学 1–6 年级
- 包含数学、语文、英语
- 以知识点 code、年级、学科、章节、教材版本组织
- 前端已支持年级、学科、教材版本筛选
- 知识点详情页可进入 AI 讲解、教材、真题、课堂模式

知识树后续将升级为：

- 人教版小学数学 5–6 年级真实大纲优先
- A/B/C 知识点分级
- CoverageGate 覆盖门禁
- K12 全学段知识图谱
- 学科插件化结构

---

### 4.2 AI 讲解系统

AI 讲解系统用于为每个知识点生成儿童友好的结构化解释。

当前 AI 讲解固定为 7 个模块：

1. `oneLine`
2. `corePoints`
3. `whyItWorks`
4. `commonMistakes`
5. `example`
6. `summary`
7. `selfCheck`

重要约束：

- 顺序不能变
- 输出必须适合小学学生
- 不使用晦涩术语
- 不输出原始 JSON 给前端
- 支持非流式和 SSE 流式生成
- 流式输出是模块级 SSE，不是原始 token 流

相关接口：

- `POST /ai/explain`
- `POST /ai/explain/stream`
- `POST /ai/explain/save`
- `POST /ai/explain/rewrite`
- `POST /ai/explain/prewarm`
- `POST /ai/explain/prewarm-all`
- `POST /ai/explain/stats`
- `POST /ai/explain/assets`

当前状态：

- 827 个知识点已有 ExplainAsset
- 前端已支持 AI 讲解卡片
- 支持分段朗读
- 支持反馈按钮
- 支持动画短片入口
- 支持进入课堂模式

---

### 4.3 AI 题库系统

题库系统用于根据知识点生成测试题、练习题和推荐题。

当前已完成：

- `QuestionAsset`
- `QuestionWarmJob`
- `QuestionUsage`
- 全量 AI 题目预热
- 共 4115 道 ready 题目资产
- 每个知识点约 5 道题
- 支持基于掌握度推荐
- 支持作答后更新 mastery 和 wrongbook

相关接口：

- `POST /ai/questions`
- `POST /ai/questions/save`
- `POST /ai/questions/prewarm`
- `POST /ai/questions/stats`
- `POST /ai/questions/assets`
- `POST /ai/questions/recommend`

后续将升级为：

- 错因验证题
- 题型画像
- 策略包触发题
- 变式题
- 跨题型迁移训练
- 与自我进化教学引擎联动

---

### 4.4 掌握度系统

掌握度系统用于记录学生对知识点的学习状态。

当前支持：

- 作答后更新 mastery
- 错题后写入 wrongbook
- 看板页展示复习计划
- 薄弱点接口
- 错题摘要接口

相关接口：

- `GET /masteries/review-plan`
- `GET /masteries/weak-points`
- `POST /attempts/submit`
- `GET /wrongbook/summary/:userId`

后续将升级为：

- 知识点掌握度
- 题型掌握度
- 学科画像
- 当前掌握度复合模型
- 错因概率
- 策略效果反哺掌握度

---

### 4.5 错题本系统

错题本当前用于记录学生做错的题，并提供错题摘要。

当前能力：

- 作答提交时自动写入错题本
- 支持按用户查看错题摘要
- 支持标记 corrected
- 支持删除错题

后续将升级为：

- 错题原因假设
- 错因验证链路
- 错因概率变化
- 错题 → 验证题 → 策略包 → 成长记忆
- 不再只是错题记录，而是错因诊断入口

---

### 4.6 教材 / 真题资源库

项目已建立教材和真题资源基础。

当前已完成：

- `TextbookVersion` 表
- `ExamSource` 表
- 教材版本地图 256 行
- 真题来源地图 329 行
- 教材正文内容 827 行
- 教材 / 真题接口
- 前端知识卡片可查看教材和真题资源

相关接口：

- `POST /ai/materials/textbook`
- `POST /ai/materials/past-exam`

参考文件：

- `exports/reference/全国小学教材版本与真题来源清单.md`
- `exports/reference/全国小学教材版本与真题来源清单.json`

后续将升级为：

- 分页教材阅读器
- 题源索引
- 教材版本切换
- 与真实教材大纲绑定
- 与 CoverageGate 联动

---

### 4.7 TTS 朗读系统

当前已从浏览器 speechSynthesis 迁移到后端生成音频。

当前能力：

- 后端 `POST /ai/tts`
- 火山引擎 TTS 已接入
- 返回 MP3 base64
- 前端用 `HTMLAudioElement` 播放
- 支持分段朗读
- 支持暂停、继续、停止

当前火山音色：

- `zh-cn-female` → `BV001_V2_streaming`
- `zh-cn-male` → `BV002_streaming`

后续将用于：

- AI 讲解朗读
- 真课堂老师讲课
- AI 同学发言
- 课堂字幕同步
- 多角色语音

---

### 4.8 真课堂课件系统

真课堂是芽芽助教未来的重要差异化能力。

它不是普通文本卡片，而是 PPT 式、直播课式、动画优先的课堂系统。

当前已完成大量设计文档，位于：

`docs/classroom-engine/`

核心文档包括：

- `TRUE_CLASSROOM.md`
- `TRUE_CLASSROOM_MVP.md`
- `TRUE_CLASSROOM_CONTENT_SCHEMA.md`
- `TRUE_CLASSROOM_PROMPTS.md`
- `TRUE_CLASSROOM_EVENT_PROTOCOL.md`
- `TRUE_CLASSROOM_ROLES.md`
- `TRUE_CLASSROOM_UI_LAYOUT.md`
- `TRUE_CLASSROOM_CONTENT_QA.md`
- `TRUE_CLASSROOM_CONTENT_PIPELINE.md`
- `TRUE_CLASSROOM_PROMPT_EXAMPLES.md`
- `TRUE_CLASSROOM_PROMPT_TUNING.md`

当前课堂系统能力：

- `ClassroomPackage`
- `ClassroomTask`
- `ClassroomResponse`
- 课堂预热
- 课堂开始
- 课堂响应
- 课堂结束
- 前端课堂播放器
- `visualSpec` 动画渲染
- 老师字幕
- AI 同学气泡
- 策略式课堂场景
- 小数乘整数 demo 课件

相关接口：

- `POST /ai/classroom/prewarm`
- `POST /ai/classroom/start`
- `POST /ai/classroom/response`
- `POST /ai/classroom/finish`
- `GET /ai/classroom/replay/:lessonId`
- `POST /ai/explain/animation-script`

---

### 4.9 动画课件生成系统

当前已经有 DeepSeek-v4 动画脚本 prompt。

核心文件：

`src/modules/ai/prompts/explain-animation.prompt.ts`

输出结构包含：

- `keyText`
- `narration`
- `subtitle`
- `visualSpec`
- `elements`
- `anim`
- `x/y/w/h`
- `delayMs`
- `durationMs`

设计原则：

- 画面以图形、emoji、公式、短词为主
- 长句放在老师旁白和字幕中
- 板书不放整句
- 适配手机大小
- 教学区和字幕区分离
- 元素必须可前端直接渲染

后续将演进为：

- 课件批量生成
- 课件 QA
- 课件版本管理
- 豆包 / 方舟生图
- Seedance 视频
- 真课堂大规模内容生产

---

### 4.10 自我进化 AI 教学适配引擎

这是最近新增的长期核心系统规划。

文档已拆分到：

`docs/adaptive-engine/`

包含：

```text
00_INDEX.md
01_PRODUCT_VISION.md
02_DEVELOPMENT_ROADMAP.md
03_SYLLABUS_SOURCE_RULES.md
04_KNOWLEDGE_LEVELING.md
05_COVERAGE_GATE.md
06_KNOWLEDGE_GRAPH.md
07_ERROR_TAXONOMY.md
08_STRATEGY_PACKS.md
09_EVENT_PROTOCOL.md
10_DATA_MODEL.md
11_DIAGNOSIS_ENGINE.md
12_STRATEGY_ENGINE.md
13_PARENT_SUMMARY_RULES.md
14_QUALITY_DASHBOARD.md
```

这个系统的核心目标：

- 基于真实教材大纲
- 完整覆盖人教版小学数学 5–6 年级
- 建立 A/B/C 知识点分级
- 建立 CoverageGate
- 建立错因体系
- 建立策略包体系
- 建立行为事件协议
- 建立家长摘要规则
- 建立质量仪表盘
- 最终扩展到 K12 全学段、多学科

---

## 5. 技术架构

### 5.1 前端

前端目录：

`/Users/liufeng/Downloads/yaya-browser-v3/`

主要文件：

- `index.html`
- `app.js`
- `styles.css`
- `final-system.css`
- `voice-test.html`
- `design-preview-blackboard.html`
- `design-preview-live.html`
- `design-preview-core.css`

特点：

- 纯 HTML / JS / CSS
- 非 React/Vue
- 手机壳式页面
- 底部导航
- 知识树
- AI 讲解弹窗
- 看板
- 榜单
- 课堂模式
- TTS 播放
- 视觉课件渲染

启动方式：

```bash
cd /Users/liufeng/Downloads/yaya-browser-v3
python3 -m http.server 4173
```

访问：

```text
http://127.0.0.1:4173
```

---

### 5.2 后端

后端目录：

`/Users/liufeng/Library/Application Support/Genspark Claw/users/b53fc225-cf3a-4a61-859c-991d97d37ec2/workspace/`

技术栈：

- NestJS
- Prisma
- PostgreSQL
- TypeScript
- DeepSeek / 方舟兼容模型
- 火山引擎 TTS

启动方式：

```bash
cd "/Users/liufeng/Library/Application Support/Genspark Claw/users/b53fc225-cf3a-4a61-859c-991d97d37ec2/workspace"
PORT=3001 npm run start:dev
```

数据库：

```text
postgresql://kids:kids@localhost:5432/kids_learning_ai
```

健康检查：

```bash
curl http://localhost:3001/health
```

---

### 5.3 数据库核心表

当前已有或规划中的核心模型包括：

- `User`
- `StudentProfile`
- `Knowledge`
- `Content`
- `TextbookVersion`
- `ExamSource`
- `ExplainAsset`
- `ExplainWarmJob`
- `QuestionAsset`
- `QuestionWarmJob`
- `QuestionUsage`
- `Mastery`
- `Question`
- `Attempt`
- `WrongQuestion`
- `ClassroomPackage`
- `ClassroomTask`
- `ClassroomResponse`
- `Paper`
- `Report`
- `Leaderboard`

后续自我进化引擎将新增或扩展：

- `SubjectPlugin`
- `KnowledgeNode`
- `QuestionType`
- `ErrorTaxonomy`
- `StrategyPack`
- `BehaviorEvent`
- `ErrorDiagnosis`
- `StrategyEffect`
- `ParentSummary`
- `GrowthMemory`
- `CoverageReport`

---

## 6. 当前数据状态

截至当前交接阶段：

| 数据 | 数量 |
|---|---:|
| Knowledge | 827 |
| ExplainAsset | 827 |
| QuestionAsset | 4115 |
| ClassroomPackage | 4 |
| TextbookVersion | 256 |
| ExamSource | 329 |
| TextbookContent | 827 |

---

## 7. 当前关键文档

### 7.1 项目交接

`HANDOVER.md`

用途：

- 给接手者理解项目全貌
- 包含前端、后端、数据库、接口、已知问题、启动方式

---

### 7.2 Hermes 工作流

`YAYA_HERMES_WORKFLOW.md`

用途：

- 说明 `yaya` profile
- 说明 `yaya-workspace`
- 说明方舟模型
- 说明飞书 home channel
- 说明如何用 Hermes 继续开发芽芽项目

---

### 7.3 真课堂引擎文档

`docs/classroom-engine/`

用途：

- 课堂引擎长期设计
- 真课堂内容结构
- 课件 schema
- prompt
- UI
- QA
- pipeline
- 示例课件

---

### 7.4 自我进化教学适配引擎文档

`docs/adaptive-engine/`

用途：

- 新一代 AI 教学适配引擎设计
- K12 多学科长期架构
- 小学数学 5–6 首发规划
- CoverageGate
- 错因体系
- 策略包
- 行为事件协议
- 数据模型
- 家长摘要
- 质量看板

---

## 8. Hermes / 飞书 / 方舟工作流

当前项目已迁移到 Hermes 工作流。

### 8.1 Hermes Profile

Profile：

```text
yaya
```

专用入口：

```bash
yaya
```

项目工作区入口：

```bash
yaya-workspace
```

前端工作区入口：

```bash
yaya-frontend
```

---

### 8.2 方舟 Agent Plan

当前 Hermes 已配置：

- provider：`volcengine-agent-plan`
- model：`ark-code-latest`
- base_url：`https://ark.cn-beijing.volces.com/api/plan/v3`

---

### 8.3 飞书机器人

飞书已接入 Hermes。

home channel：

```text
oc_eec4b5efd0607fabb123f7248dbad474
```

当前状态：

- 飞书机器人已能回复
- Hermes gateway 已配置
- yaya gateway 已设置开机自启
- 飞书可用于后续远程协作开发

---

## 9. 当前已知重点问题

### 9.1 前端仍是单文件为主

当前核心逻辑主要集中在 `app.js`，后续应逐步模块化。

### 9.2 AI / Classroom 路由存在重叠

`ai.controller.ts` 和 `classroom.controller.ts` 都涉及 `/ai/classroom/*`，后续需要整理。

### 9.3 教材 / 真题仍需更强匹配

当前教材和真题资源是基础卡片展示，后续应升级为：

- 分页阅读
- 精准匹配
- 版本选择
- 题源检索

### 9.4 榜单仍是占位

Leaderboard 还未完全接真实业务。

### 9.5 自我进化引擎还未开发

目前已有完整规划和拆分文档，但尚未开始工程实现。

第一步应该是：

> 整理人教版小学数学 5–6 年级真实教材大纲。

---

## 10. 下一步最优先任务

## 10.1 启动 adaptive-engine 第一阶段

阅读：

```text
docs/adaptive-engine/00_INDEX.md
docs/adaptive-engine/03_SYLLABUS_SOURCE_RULES.md
docs/adaptive-engine/04_KNOWLEDGE_LEVELING.md
```

然后输出：

```text
primary_math_g5_g6_syllabus.md
primary_math_g5_g6_knowledge.json
```

目标：

- 找到人教版小学数学 5–6 年级完整教材目录
- 提取真实知识点
- 标明教材来源
- 为 A/B/C 分级做准备

---

## 10.2 后续紧接任务

1. 知识点 A/B/C 分级
2. CoverageGate 规则落地
3. 小学数学 5–6 知识图谱补全
4. 错因体系落地
5. 策略包体系落地
6. 行为事件协议实现
7. 错因诊断引擎
8. 策略调度引擎
9. 家长摘要
10. 质量仪表盘

---

## 11. 项目长期路线

### 第一阶段

人教版小学数学 5–6 年级完整覆盖。

### 第二阶段

小学语文 5–6 年级。

### 第三阶段

小学英语 5–6 年级。

### 第四阶段

小学数学 / 语文 / 英语 1–4 年级。

### 第五阶段

初中全学段、多学科。

### 第六阶段

高中全学段、多学科。

---

## 12. 项目最终愿景

芽芽助教最终要成为一个：

- 懂教材
- 懂知识点
- 懂错因
- 懂孩子
- 懂教学策略
- 懂家长表达
- 能长期记忆
- 能自我进化

的 K12 AI 学习伙伴。

最终目标不是“回答一道题”，而是：

> 陪孩子走完整个 K12 学习周期，并在这个过程中越来越知道如何帮助这个孩子学得更好。

---

## 13. 给 AI 工具的使用说明

如果要让 AI 工具继续开发本项目，应优先告诉它：

1. 先读 `PROJECT_INTRODUCTION.md`
2. 再读 `HANDOVER.md`
3. 如果做真课堂，读 `docs/classroom-engine/INDEX.md`
4. 如果做自我进化教学引擎，读 `docs/adaptive-engine/00_INDEX.md`
5. 当前最优先任务是人教版小学数学 5–6 年级教材大纲整理
6. 不要跳到初中、高中
7. 不要凭空生成知识点
8. 不要绕过 CoverageGate
9. 不要手动修改画像结论
10. 不要使用心理测评式语言

---

## 14. 最终总结

芽芽助教已经从一个 K12 AI 学习产品雏形，逐步演进为：

> **以 AI 讲解、AI 题库、真课堂课件、TTS 朗读、错因诊断、策略调度、成长记忆为核心的自我进化 AI 教学系统。**

当前项目已经具备继续开发的基础：

- 前端可运行
- 后端可运行
- 数据库已建立
- 知识点已录入
- AI 讲解可用
- 题库资产可用
- 课堂引擎已有原型
- Hermes 工作流已接入
- 飞书远程协作已打通
- 方舟 Agent Plan 已接入
- 自我进化教学引擎 PRD 已拆分

下一步不是继续讨论愿景，而是开始执行：

> **人教版小学数学 5–6 年级真实教材大纲整理。**
