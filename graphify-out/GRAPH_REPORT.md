# Graph Report - .  (2026-05-14)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 112 nodes · 186 edges · 15 communities (10 shown, 5 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]

## God Nodes (most connected - your core abstractions)
1. `api` - 11 edges
2. `renderClassroomPlayer()` - 8 edges
3. `bootstrap()` - 8 edges
4. `openKnowledgeDetail()` - 7 edges
5. `showToast()` - 7 edges
6. `switchTab()` - 7 edges
7. `renderExplainCard()` - 6 edges
8. `runClassroomScene()` - 6 edges
9. `speakText()` - 4 edges
10. `openAssistantView()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `refreshBackendStatus()` --calls--> `api`  [EXTRACTED]
  app.js → src/api/client.js
- `getPreferredClassroomLesson()` --calls--> `api`  [EXTRACTED]
  app.js → src/api/client.js
- `renderChapters()` --calls--> `api`  [EXTRACTED]
  app.js → src/api/client.js
- `speakText()` --calls--> `showToast()`  [EXTRACTED]
  app.js → src/app.js
- `switchTab()` --calls--> `loadLeaderboardPanel()`  [EXTRACTED]
  src/app.js → app.js

## Communities (15 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (16): appState, navIndicator, navItems, pageInits, pages, toastEl, topbarBadge, topbarMap (+8 more)

### Community 1 - "Community 1"
Cohesion: 0.1
Nodes (8): initBoardPage(), initHomePage(), syllabus, initKnowledgePage(), initLeaderboardPage(), leaderboardData, initPracticePage(), questions

### Community 2 - "Community 2"
Cohesion: 0.2
Nodes (12): api, showToast(), buildKnowledgeGraphic(), getPreferredClassroomLesson(), loadClassroomTtsAudio(), openAssistantView(), openKnowledgeDetail(), playExplainAnimation() (+4 more)

### Community 3 - "Community 3"
Cohesion: 0.18
Nodes (7): load(), initClassroomPage(), switchTab(), loadBoardPanel(), loadLeaderboardPanel(), loadPracticePanel(), renderChapters()

### Community 4 - "Community 4"
Cohesion: 0.32
Nodes (8): defaultClassmatesForScene(), fitClassroomCanvas(), normalizeClassroomQuiz(), normalizeClassroomScenes(), playClassroomAudio(), renderClassroomPlayer(), renderClassroomVisualSpec(), runClassroomScene()

### Community 5 - "Community 5"
Cohesion: 0.25
Nodes (7): setLoading(), setPageLoading(), bindNav(), bootstrap(), initDefaultVoice(), refreshBackendStatus(), setupCommonHandlers()

### Community 6 - "Community 6"
Cohesion: 0.29
Nodes (8): animateSectionText(), getVoicePresets(), isMostlyChinese(), renderExplainCard(), renderExplainSections(), sleep(), speakText(), stopSpeech()

### Community 7 - "Community 7"
Cohesion: 0.5
Nodes (5): emptyCard(), initAdminPage(), loadAdminData(), renderClassroomPanel(), renderLists()

### Community 8 - "Community 8"
Cohesion: 1.0
Nodes (3): Coverage Gate, Diagnosis Engine, Strategy Engine

### Community 9 - "Community 9"
Cohesion: 0.67
Nodes (3): collectForm(), readAiPayload(), readAiQuestionPayload()

## Knowledge Gaps
- **19 isolated node(s):** `explainState`, `_noopText`, `explainVoice`, `TTS_VOICE_MAP`, `demoClassroomLesson` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `loadBoardPanel()` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `api` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 5`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **What connects `explainState`, `_noopText`, `explainVoice` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._