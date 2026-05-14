# Hermes Memory 完整内容

生成时间：2026-05-14 21:36
总占用：1,853 / 2,200 字符（84%）
条目数：9

---

## 1. Hermes MCP
> Hermes MCP serve 需要 Python 包 `mcp`。该包不在 Hermes 默认 venv 中，需手动安装：`~/.hermes/hermes-agent/venv/bin/python -m pip install mcp`。缺少时 Cursor 连接 Hermes MCP 会报 Error。

## 2. Hermes 配置
> Hermes yaya profile 已配置 DeepSeek 为默认模型（deepseek-chat / deepseek-v4-pro），provider 名为 deepseek，API 地址 https://api.deepseek.com/v1。辅助视觉模型用 doubao-seed-2.0-pro（volcengine-agent-plan provider）。API Server 在 http://127.0.0.1:8643/v1 提供 OpenAI 兼容接口，model 名 "yaya"。

## 3. 验收预览页
> 验收预览页：PC宽度max-width:1100px。KP行展开详情/课堂/AI测试/真题。单元📚按钮→教材浏览器在unit-bd顶部。HTML由gen_full_preview.py→/tmp/，HTTP serve，图片用HTTP相对路径(/tb_g5s1/pNNN.png)。生成后必验189KP/31单元/0个file://。

## 4. 教参提取
> teachingGoal=教参原文，teachingGoalSource=来源标注。textbookPage={source,unit,pageStart,pageEnd,lesson}。教参PDF二阶段提取：easyocr TOC→vision_analyze抄录。五上偏移+12、五下+11、六上+12(但U6在p171非TOC说163)、六下+12。TOC页码不可盲信。

## 5. 诊断引擎
> 诊断引擎协议v1.2定稿→`acceptance-artifacts/11_DIAGNOSIS_ENGINE.md`。四步诊断：初筛→匹配→验证→溯源。溯源最大3层。冷启动用数据阈值(30/120节点)非日历时间。验证逻辑：做错×1.15、做对不变、连错3道确诊。输出分parentSummary(short/full)和teacherNote。

## 6. 版本管理
> 版本管理要求：变更记录的"日期"列必须精确到分钟（格式 YYYY-MM-DD HH:MM），不能只写到日期。同时标题行的版本号必须与最新的变更记录条目一致。

## 7. GitHub
> GitHub 全通：gh CLI 已登录 liufeng0602-cell，仓库 yaya-zhujiao，代码在 ~/Downloads/yaya-browser-v3，git 凭据已配 gh auth setup-git。Hermes 可直接提交/PR。

## 8. 数据规范总集（合并了原来的字段名+六维+9铁规3条）
> 芽芽项目数据规范总集：(1)字段名：知识点名=name非knowledgeName、学期=book非semester、无knowledgeType；错因在error_taxonomy.json的l1_universal/l2_math_specific；绑定数组key=bindings；levels用levels数组。(2)图谱六维：prerequisites/next/questionTypes/commonErrors/strategyPacks/masteryRule。(3)9铁规：R1-levelScore禁手、R2-三文件对账、R3-字段区分度、R4-错因全引用、R5-必填完整、R6-级别一致、R7-A≥3绑定、R8-双向边对称、R9-题库全覆盖。门禁data_quality_gate.py。(4)术语：parentExplanation非parentSafeExplanation；错因/errorCode非错误/errorType。

## 9. 交叉审计7铁律（单条最大，619字符）
> 交叉审计7铁律（2026-05-14教训）：T1-写版本时间前必须跑date命令，禁止拍脑袋；T2-引用外部字段名前grep数据文件确认存在（如parentExplanation非parentSafeExplanation）；T3-patch前read_file全文防重复行；T4-交叉引用章节号前打开目标文档确认；T5-引用09号事件编号以09_EVENT_PROTOCOL.md当前版本为准；T6-接口表覆盖所有有数据依赖的引擎文档；T7-术语统一：错因/errorCode非错误/errorType。
