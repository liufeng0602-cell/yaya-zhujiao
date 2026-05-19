const API_BASE = 'http://localhost:3001';
const topbarMap = {
  home: ['芽芽 AI 学习宇宙站', '首页'],
  knowledge: ['教材同步大纲', '知识树'],
  practice: ['AI 动态出题测评', '练习'],
  board: ['家长同步掌握度', '看板'],
  leaderboard: ['周榜 / 月榜 / 学期榜', '榜单'],
  classroom: ['课堂引擎回放 / 批量预热', '课堂'],
  admin: ['后台管理', '管理']
};
const topBarMap = topbarMap;
if (typeof window !== 'undefined') window.topBar = window.topBar || { map: { tabs: topbarMap } };

const appState = {
  currentTab: 'home',
  grade: '五年级',
  subject: '数学',
  semester: '上册',
  knowledgeLevel: '全部',
  boardType: 'unlock',
  currentUser: null,
  currentUserId: null,
  apiStatus: '未连接'
};

const explainState = {
  current: null,
  playbackTimer: null,
  playbackIndex: 0,
  playbackQueue: [],
};

const pages = [...document.querySelectorAll('.page')];
const navItems = [...document.querySelectorAll('.nav-item')];
const navIndicator = document.getElementById('navIndicator');
const topbarTitle = document.getElementById('topbarTitle');
const topbarSub = document.getElementById('topbarSub');
const topbarBadge = document.getElementById('topbarBadge');
const _noopText = { textContent: '' };
const _tt = topbarTitle || _noopText;
const _ts = topbarSub || _noopText;
const _tb = topbarBadge || _noopText;
const toast = document.getElementById('toast');

function showToast(text) { toast.textContent = text; toast.classList.add('show'); clearTimeout(showToast.timer); showToast.timer = setTimeout(() => toast.classList.remove('show'), 1400); }

function playUiSound(type = 'select') {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    const configs = {
      select: { freq: 880, type: 'sine', duration: 0.08, gainVal: 0.12 },
      good:   { freq: [523, 659, 784], type: 'triangle', duration: 0.12, gainVal: 0.15 },
      try:    { freq: 440, type: 'sine', duration: 0.1, gainVal: 0.08 },
      play:   { freq: 660, type: 'sine', duration: 0.07, gainVal: 0.1 },
    };
    const cfg = configs[type] || configs.select;
    const freqs = Array.isArray(cfg.freq) ? cfg.freq : [cfg.freq];
    let startT = ctx.currentTime;
    freqs.forEach((f, i) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.type = cfg.type;
      o.frequency.value = f;
      g.gain.setValueAtTime(0, startT + i * cfg.duration);
      g.gain.linearRampToValueAtTime(cfg.gainVal, startT + i * cfg.duration + 0.01);
      g.gain.exponentialRampToValueAtTime(0.001, startT + (i + 1) * cfg.duration);
      o.start(startT + i * cfg.duration);
      o.stop(startT + (i + 1) * cfg.duration);
    });
  } catch (e) { /* 无声降级 */ }
}



async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.message || `HTTP ${res.status}`);
  return data;
}

async function refreshBackendStatus() {
  try {
    await api('/health');
    appState.apiStatus = '已连接';
    _tb.textContent = '数据库已连接';
  } catch {
    appState.apiStatus = '未连接';
    _tb.textContent = '离线模式';
  }
}

function switchTab(tab) {
  appState.currentTab = tab;
  pages.forEach(page => page.classList.toggle('active', page.id === `page-${tab}`));
  navItems.forEach(item => item.classList.toggle('active', item.dataset.tab === tab));
  const idx = navItems.findIndex(item => item.dataset.tab === tab);
  if (navIndicator) navIndicator.style.transform = `translateX(${idx * 100}%)`;
  const [sub, title] = topbarMap[tab] || topbarMap.home;
  _ts.textContent = sub;
  _tt.textContent = title;
  window.scrollTo(0, 0);
  if (tab === 'knowledge') renderChapters();
  if (tab === 'practice') loadPracticePanel();
  if (tab === 'board') loadBoardPanel();
  if (tab === 'leaderboard') loadLeaderboardPanel();
  if (tab === 'classroom') initClassroomPage();
}

function onlyChinese(text) {
  if (!text) return '';
  return String(text).replace(/[a-zA-Z0-9_\-\"':\[\]\{\},]/g, ' ').replace(/\s+/g, ' ').trim();
}

function formatKnowledgeContent(item) {
  let data = {};
  const raw = item.teachingGoal || item.objective || item.description || '';
  if (raw.trim().startsWith('{')) { try { data = JSON.parse(raw); } catch (e) {} }

  const teachingGoal = onlyChinese(data.teachingGoal || item.teachingGoal || item.objective || '掌握本节核心内容');
  const keyPoints = onlyChinese(data.keyPoints || (item.keyPoints && item.keyPoints.length) ? item.keyPoints : '核心定义与算理');
  const commonMistakes = onlyChinese(data.commonMistakes || (item.commonMistakes && item.commonMistakes.length) ? item.commonMistakes : '概念混淆或计算错误');
  const tags = onlyChinese(data.tags || item.tags || ['必考']);

  const toStr = (val) => Array.isArray(val) ? val.filter(Boolean).join('、') : (val || '—');

  return `
    <div class="business-content">
      <div class="content-row"><strong>教学目标：</strong><span>${toStr(teachingGoal)}</span></div>
      <div class="content-row"><strong>核心要点：</strong><span>${toStr(keyPoints)}</span></div>
      <div class="content-row"><strong>常见错误：</strong><span>${toStr(commonMistakes)}</span></div>
      <div class="content-row"><strong>标签：</strong><span>${toStr(tags)}</span></div>
    </div>
  `;
}

function normalizeKnowledgeLevel(item) {
  const text = (item.masteryRequirement || '').toLowerCase();
  if (/核心|必学|掌握/.test(text)) return 'core';
  if (/重点|重要/.test(text)) return 'key';
  return 'basic';
}

function normalizeClassroomScenes(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.scenes)) return payload.scenes;
  return [];
}


async function getPreferredClassroomLesson(detail, kName) {
  const knowledge = detail?.knowledge || detail || {};
  const code = String(knowledge.knowledgeCode || knowledge.code || kName || '').trim();
  const title = String(knowledge.knowledgeName || knowledge.name || kName || '').trim();
  const list = await api('/ai/classroom/list').catch(() => []);
  const exact = (list || []).find(item => item.knowledgeCode === code && /真正的课堂版/.test(item.lessonTitle || ''))
    || (list || []).find(item => item.knowledgeCode === code)
    || (list || []).find(item => String(item.knowledgeName || '').includes(title));
  return exact ? api(`/ai/classroom/replay/${encodeURIComponent(exact.lessonId)}`) : api('/ai/classroom/start', {
    method: 'POST',
    body: JSON.stringify({
      knowledgeCode: code,
      knowledgeName: title,
      grade: knowledge.grade || '',
      subject: knowledge.subject || '',
      chapter: knowledge.chapter || knowledge.chapterName || '',
      userId: appState.currentUserId || 'demo-student',
      masteryLevel: detail?.mastery?.masteryLevel || '未学',
    }),
  });
}

async function renderChapters() {
  const wrap = document.getElementById('chapterWrap');
  const gradeWrap = document.getElementById('gradeChips');
  const subjectWrap = document.getElementById('subjectChips');
  const semesterWrap = document.getElementById('semesterChips');
  if (!wrap || !gradeWrap || !subjectWrap || !semesterWrap) return;

  // ---- 先把 chip 渲染出来，确保即便接口挂了也有筛选条 ----
  const grades = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级'];
  const subjects = ['数学', '语文', '英语'];
  const semesters = ['上册', '下册'];
  gradeWrap.innerHTML = grades.map(g => `<button class="chip ${g === appState.grade ? 'active' : ''}" data-grade="${g}">${g}</button>`).join('');
  subjectWrap.innerHTML = subjects.map(s => `<button class="chip ${s === appState.subject ? 'active' : ''}" data-subject="${s}">${s}</button>`).join('');
  semesterWrap.innerHTML = semesters.map(m => `<button class="chip ${m === appState.semester ? 'active' : ''}" data-semester="${m}">${m}</button>`).join('');
  gradeWrap.querySelectorAll('[data-grade]').forEach(btn => btn.onclick = () => { appState.grade = btn.dataset.grade; renderChapters(); });
  subjectWrap.querySelectorAll('[data-subject]').forEach(btn => btn.onclick = () => { appState.subject = btn.dataset.subject; renderChapters(); });
  semesterWrap.querySelectorAll('[data-semester]').forEach(btn => btn.onclick = () => { appState.semester = btn.dataset.semester; renderChapters(); });
  wrap.innerHTML = '<div class="card glass" style="text-align:center; padding:24px;">正在加载知识树…</div>';

  try {
    const data = await api('/knowledge');

    // 1. 筛选当前层级
    const nodes = (data || []).filter(item => 
      item.grade === appState.grade && 
      item.subject === appState.subject && 
      (item.semester === appState.semester || !item.semester)
    );

    if (!nodes.length) { wrap.innerHTML = '<div class="card glass" style="text-align:center; padding:40px;">暂无该册次大纲</div>'; return; }

    // 2. 嵌套分组 [单元 -> 章节]
    const tree = {};
    nodes.forEach(n => {
      const u = n.unitName || '基础单元';
      const c = n.chapterName || '核心课程';
      if (!tree[u]) tree[u] = {};
      if (!tree[u][c]) tree[u][c] = [];
      tree[u][c].push(n);
    });

    let globalIndex = 1;
    let unitIdx = 0;
    wrap.innerHTML = Object.keys(tree).map(unit => {
      const chapters = tree[unit];
      const uid = `unit_${unitIdx++}`;
      return `
        <div class="unit-section" style="margin-bottom:24px;">
          <div class="unit-header" onclick="window.__toggleUnit('${uid}')">
            <span class="unit-title-text">📂 ${unit}</span>
            <button type="button" class="unit-toggle" id="btn_${uid}">收起</button>
          </div>
          <div class="unit-body" id="${uid}" style="padding-left:12px; border-left:2px solid rgba(85,239,255,0.15);">
            ${Object.keys(chapters).map(chName => {
              const items = chapters[chName];
              return `
                <div class="chapter-sub" style="margin-bottom:18px;">
                  <div style="font-size:15px; font-weight:bold; color:#fff; margin-bottom:10px;">📖 ${chName}</div>
                  ${items.map(item => {
                    const level = normalizeKnowledgeLevel(item);
                    const label = level === 'core' ? '核心' : '重点';
                    const MASTERY_LEVELS = [
                      { label: '未学',     class: 'm-unlearned' },
                      { label: '已看讲解', class: 'm-viewed'    },
                      { label: '一知半解', class: 'm-confused'  },
                      { label: '会说不会做',class: 'm-theory'   },
                      { label: '掌握基础', class: 'm-basic'     },
                      { label: '真题受阻', class: 'm-blocked'   },
                      { label: '彻底精通', class: 'm-mastered'  },
                    ];
                    const mastery = MASTERY_LEVELS[Math.floor(Math.random() * MASTERY_LEVELS.length)];
                    const idx = globalIndex++;
                    return `
                      <div class="chapter-item collapsed" id="ki_${item.id}">
                        <div class="chapter-item-meta">
                          <span class="kp-index">No.${idx}</span>
                          <span class="mastery-tag ${mastery.class}">${mastery.label}</span>
                          <span class="level-badge ${level}">${label}</span>
                        </div>
                        <div class="chapter-item-title">
                          <span class="kp-name" style="cursor:pointer;" onclick='window.__openKnowledgeDetail(${JSON.stringify({ knowledgeCode: String(item.knowledgeCode || item.id || item.knowledgeName || ""), knowledgeName: item.knowledgeName, grade: appState.grade, subject: appState.subject, chapter: item.chapterName, masteryLevel: mastery.label })})'>${item.knowledgeName}</span>
                          <button type="button" class="chapter-item-toggle" onclick="window.__toggleK('${item.id}')">展开</button>
                        </div>
                        <div class="chapter-item-body">
                          <button type="button" class="btn-diagnose" onclick='window.__diagnose("${item.id}", "${mastery.label}")'>💬 和芽芽助教聊聊这个点</button>
                          <div class="card glass-mini" style="padding:14px; margin:12px 0; background:rgba(0,0,0,0.2);">
                            ${formatKnowledgeContent(item)}
                          </div>
                          <div class="knowledge-actions">
                            <button onclick='window.__showTextbook(${JSON.stringify({ knowledgeCode: String(item.knowledgeCode || item.id || item.knowledgeName || ""), knowledgeName: item.knowledgeName, grade: appState.grade, subject: appState.subject, chapter: item.chapterName })})'>教材</button>
                            <button onclick="showToast('试题加载中...')">测试题</button>
                            <button class="primary-btn" onclick='window.__openKnowledgeDetail(${JSON.stringify({ knowledgeCode: String(item.knowledgeCode || item.id || item.knowledgeName || ""), knowledgeName: item.knowledgeName, grade: appState.grade, subject: appState.subject, chapter: item.chapterName, masteryLevel: mastery.label })})'>知识点详情</button>
                            <button class="primary-btn" onclick='window.__enterClassroom(${JSON.stringify({ knowledgeCode: String(item.knowledgeCode || item.id || item.knowledgeName || ""), knowledgeName: item.knowledgeName, grade: appState.grade, subject: appState.subject, chapter: item.chapterName, masteryLevel: mastery.label })})'>🏫 进入课堂</button>
                            <button class="primary-btn" onclick="showToast('正在出题...')">AI测试题</button>
                            <button onclick='window.__showPastExam(${JSON.stringify({ knowledgeCode: String(item.knowledgeCode || item.id || item.knowledgeName || ""), knowledgeName: item.knowledgeName, grade: appState.grade, subject: appState.subject })})'>真题</button>
                          </div>
                        </div>
                      </div>`;
                  }).join('')}
                </div>`;
            }).join('')}
          </div>
        </div>`;
    }).join('');

    window.__toggleUnit = (uid) => {
      const body = document.getElementById(uid);
      const btn  = document.getElementById(`btn_${uid}`);
      if (!body || !btn) return;
      const hidden = body.style.display === 'none';
      body.style.display = hidden ? '' : 'none';
      btn.textContent = hidden ? '收起' : '展开';
    };

    window.__toggleK = (id) => {
      const el = document.getElementById(`ki_${id}`);
      if (el) {
        const isCollapsed = el.classList.toggle('collapsed');
        el.querySelector('.chapter-item-toggle').textContent = isCollapsed ? '展开' : '收起';
      }
    };
  } catch (e) {
    wrap.innerHTML = `<div class="card glass">数据加载失败: ${e.message}</div>`;
  }
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

const explainVoice = {
  voiceKey: 'zh-cn-female',
  voiceName: 'Flo (中文（中国大陆）)',
  voiceLang: 'zh-CN',
  rate: 1,
  audio: null,
  objectUrl: '',
  playing: false,
  paused: false,
  loading: false,
};

function splitForSpeech(text) {
  if (!text) return [];
  return String(text)
    .replace(/\n+/g, ' ')
    .split(/(?<=[。！？!?；;])\s*/)
    .map(s => s.trim())
    .filter(Boolean);
}

const TTS_VOICE_MAP = {
  'zh-cn-female': { voiceName: 'Flo (中文（中国大陆）)', lang: 'zh-CN', label: '👩 普通话女声' },
  'zh-cn-male':   { voiceName: 'Reed (中文（中国大陆）)', lang: 'zh-CN', label: '👨 普通话男声' },
  'zh-hk':        { voiceName: 'Sinji', lang: 'zh-HK', label: '🇭🇰 粤语' },
  'zh-tw':        { voiceName: 'Meijia', lang: 'zh-TW', label: '🇹🇼 台湾国语' },
  'en-us':        { voiceName: 'Samantha', lang: 'en-US', label: '🇺🇸 美音' },
  'en-gb':        { voiceName: 'Daniel', lang: 'en-GB', label: '🇬🇧 英音' },
};

function getVoicePresets() {
  return Object.entries(TTS_VOICE_MAP).map(([key, v]) => ({ key, ...v }));
}

function stopSpeech(emitEvent = true) {
  if (explainVoice.audio) {
    try { explainVoice.audio.pause(); } catch (_) {}
    explainVoice.audio = null;
  }
  if (explainVoice.objectUrl) {
    try { URL.revokeObjectURL(explainVoice.objectUrl); } catch (_) {}
    explainVoice.objectUrl = '';
  }
  explainVoice.playing = false;
  explainVoice.paused = false;
  explainVoice.loading = false;
  if (emitEvent) document.dispatchEvent(new CustomEvent('yaya:speechStopped'));
}

function pauseSpeech() {
  if (explainVoice.audio && !explainVoice.audio.paused) {
    explainVoice.audio.pause();
    explainVoice.paused = true;
    explainVoice.playing = false;
  }
}

function resumeSpeech() {
  if (explainVoice.audio && explainVoice.audio.paused) {
    explainVoice.audio.play().catch(() => {});
    explainVoice.paused = false;
    explainVoice.playing = true;
  }
}

function isMostlyChinese(text) {
  const cjk = (text.match(/[\u4e00-\u9fff\u3400-\u4dbf]/g) || []).length;
  return text.length > 0 && cjk / text.length > 0.3;
}

async function speakText(text) {
  const content = String(text || '').trim();
  if (!content) return;

  let voiceKey = explainVoice.voiceKey || 'zh-cn-female';
  let preset = TTS_VOICE_MAP[voiceKey] || TTS_VOICE_MAP['zh-cn-female'];

  if (preset.lang.startsWith('en') && isMostlyChinese(content)) {
    showToast('💡 英文音色无法读中文，已切到普通话');
    voiceKey = 'zh-cn-female';
    preset = TTS_VOICE_MAP[voiceKey];
  }

  stopSpeech(false);
  explainVoice.loading = true;
  explainVoice.voiceKey = voiceKey;
  explainVoice.voiceName = preset.voiceName;
  explainVoice.voiceLang = preset.lang;

  const res = await fetch(`${API_BASE}/ai/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: content, voiceKey, voiceName: preset.voiceName }),
  });
  if (!res.ok) {
    explainVoice.loading = false;
    throw new Error(`TTS HTTP ${res.status}`);
  }
  const data = await res.json();
  if (!data?.audioBase64) {
    explainVoice.loading = false;
    throw new Error('TTS empty audio');
  }

  const bytes = Uint8Array.from(atob(data.audioBase64), c => c.charCodeAt(0));
  const blob = new Blob([bytes], { type: data.mimeType || data.audioMimeType || 'audio/mpeg' });
  const objectUrl = URL.createObjectURL(blob);
  const audio = new Audio(objectUrl);
  audio.preload = 'auto';
  audio.onended = () => {
    explainVoice.audio = null;
    explainVoice.playing = false;
    explainVoice.paused = false;
    explainVoice.loading = false;
    if (explainVoice.objectUrl) URL.revokeObjectURL(explainVoice.objectUrl);
    explainVoice.objectUrl = '';
    document.dispatchEvent(new CustomEvent('yaya:speechStopped'));
  };
  audio.onerror = () => {
    explainVoice.audio = null;
    explainVoice.playing = false;
    explainVoice.paused = false;
    explainVoice.loading = false;
    if (explainVoice.objectUrl) URL.revokeObjectURL(explainVoice.objectUrl);
    explainVoice.objectUrl = '';
    document.dispatchEvent(new CustomEvent('yaya:speechStopped'));
  };
  explainVoice.audio = audio;
  explainVoice.objectUrl = objectUrl;
  await audio.play();
  explainVoice.playing = true;
  explainVoice.loading = false;
}

function renderExplainSections(resp) {
  const sections = [];
  if (resp.oneLine) sections.push({ key: 'oneLine', label: '💡 一句话理解', text: resp.oneLine });
  if (resp.corePoints && resp.corePoints.length) sections.push({ key: 'corePoints', label: '📌 核心规则', text: resp.corePoints.map(p => '· ' + p).join('\n') });
  if (resp.whyItWorks) sections.push({ key: 'whyItWorks', label: '🔍 为什么这样', text: resp.whyItWorks });
  if (resp.commonMistakes && resp.commonMistakes.length) sections.push({ key: 'commonMistakes', label: '🚨 常见错误', text: resp.commonMistakes.map(e => '⚠️ ' + e).join('\n') });
  if (resp.example) sections.push({ key: 'example', label: '📝 一个例子', text: resp.example });
  if (resp.selfCheck && resp.selfCheck.length) sections.push({ key: 'selfCheck', label: '❓ 自测问题', text: resp.selfCheck.map((q, i) => `${i + 1}. ${q}`).join('\n') });
  if (resp.summary) sections.push({ key: 'summary', label: '✨ 总结', text: resp.summary });
  return sections;
}

async function animateSectionText(el, text) {
  const content = String(text || '');
  el.innerHTML = '<span class="typing-cursor">▍</span>';
  let out = '';
  const chunk = Math.max(1, Math.ceil(content.length / 18));
  for (let i = 0; i < content.length; i += chunk) {
    out = content.slice(0, i + chunk);
    el.innerHTML = `${out.replace(/\n/g, '<br/>')}<span class="typing-cursor">▍</span>`;
    await sleep(35);
  }
  el.innerHTML = content.replace(/\n/g, '<br/>');
}


async function renderExplainCard(resp, meta = {}) {
  const body = document.getElementById('chatBody');
  if (!body) return;
  stopSpeech();
  const sections = renderExplainSections(resp);
  const card = document.createElement('div');
  card.className = 'chat-msg msg-ai explain-card';
  const title = resp.title || meta.knowledgeName || 'AI讲解';
  const voiceOptions = getVoicePresets();
  const currentVoiceKey = explainVoice.voiceKey || 'zh-cn-female';
  const voiceChips = voiceOptions.map(v => `<button type="button" class="chip explain-chip ${v.key === currentVoiceKey ? 'active' : ''}" data-voice="${v.key}">${v.label}</button>`).join('');
  const speedChips = [0.75, 1, 1.25, 1.5, 1.75, 2].map(v => `<button type="button" class="chip explain-chip ${v === explainVoice.rate ? 'active' : ''}" data-speed="${v}">${v}x</button>`).join('');

  card.innerHTML = `
    <div class="explain-head">
      <div class="explain-title">🌟 ${title}</div>
      <div class="explain-meta">${meta.grade || ''} ${meta.subject || ''} ${meta.chapter || ''}</div>
    </div>

    <div class="explain-toolbar-card">
      <div class="explain-chip-row">
        <span class="explain-chip-label">🎙️ 方言</span>
        <div class="explain-chip-scroll">${voiceChips}</div>
      </div>
      <div class="explain-chip-row">
        <span class="explain-chip-label">⚡ 语速</span>
        <div class="explain-chip-scroll">${speedChips}</div>
      </div>
    </div>

    <div class="explain-sections"></div>
    <div class="explain-feedback-note">每段都可以朗读、暂停、继续、停止，也可以直接告诉芽芽你听懂了没。</div>
  `;
  body.appendChild(card);
  body.scrollTop = body.scrollHeight;

  const sectionsWrap = card.querySelector('.explain-sections');
  card.querySelectorAll('[data-voice]').forEach(btn => btn.addEventListener('click', () => {
    const key = btn.dataset.voice;
    const preset = TTS_VOICE_MAP[key] || TTS_VOICE_MAP['zh-cn-female'];
    explainVoice.voiceKey = key;
    explainVoice.voiceName = preset.voiceName;
    explainVoice.voiceLang = preset.lang;
    card.querySelectorAll('[data-voice]').forEach(b => b.classList.toggle('active', b === btn));
    const lbl = card.querySelector('#toolbarVoiceLabel');
    if (lbl) lbl.textContent = btn.textContent;
    stopSpeech();
    playUiSound('select');
    showToast(`🎙️ 已切到：${btn.textContent}`);
  }));
  card.querySelectorAll('[data-speed]').forEach(btn => btn.addEventListener('click', () => {
    explainVoice.rate = Number(btn.dataset.speed || 1);
    card.querySelectorAll('[data-speed]').forEach(b => b.classList.toggle('active', b === btn));
    const lbl = card.querySelector('#toolbarSpeedLabel');
    if (lbl) lbl.textContent = explainVoice.rate + 'x';
    playUiSound('select');
    showToast(`⚡ 语速：${explainVoice.rate}x`);
  }));
  // 折叠/展开工具栏
  card.querySelector('#explainToolbarToggle')?.addEventListener('click', () => {
    card.querySelector('#explainToolbar')?.classList.toggle('open');
  });

  for (let idx = 0; idx < sections.length; idx++) {
    const s = sections[idx];
    await sleep(90);
    const sectionEl = document.createElement('section');
    sectionEl.className = 'explain-section';
    sectionEl.dataset.sectionIndex = String(idx);
    sectionEl.innerHTML = `
      <div class="explain-section-head">
        <div class="explain-section-title">${s.label}</div>
      </div>
      <div class="explain-section-body"><span class="typing-cursor">▍</span></div>
      <div class="explain-section-actions explain-section-actions--playback">
        <button type="button" class="explain-play-btn" data-play-toggle="1">🔊 朗读</button>
        <button type="button" class="explain-ctrl-btn" data-action="pause" title="暂停/继续">⏸</button>
        <button type="button" class="explain-ctrl-btn danger" data-action="stop" title="停止">⏹</button>
      </div>
      <div class="explain-section-actions explain-section-actions--feedback">
        <button type="button" class="explain-feedback-btn good" data-action="understood">✅ 我懂了！</button>
        <button type="button" class="explain-feedback-btn bad" data-action="confused">🤔 再说一遍</button>
      </div>
    `;
    sectionsWrap.appendChild(sectionEl);
    const bodyEl = sectionEl.querySelector('.explain-section-body');
    await animateSectionText(bodyEl, s.text);

    const playBtn = sectionEl.querySelector('[data-play-toggle]');
    const stopBtn  = sectionEl.querySelector('[data-action="stop"]');
    let state = 'idle'; // idle | playing | paused
    const syncBtn = () => {
      if (state === 'idle')    playBtn.innerHTML = '🔊 朗读';
      if (state === 'playing') playBtn.innerHTML = '⏸ 暂停';
      if (state === 'paused')  playBtn.innerHTML = '▶️ 继续';
    };
    // 朗读按钮：idle→播放  playing→暂停  paused→继续
    playBtn?.addEventListener('click', () => {
      if (state === 'idle')    { state = 'playing'; syncBtn(); speakText(s.text); return; }
      if (state === 'playing') { state = 'paused';  syncBtn(); pauseSpeech(); return; }
      if (state === 'paused')  { state = 'playing'; syncBtn(); resumeSpeech(); return; }
    });
    // 停止按钮（⏹）：停止并归 idle
    stopBtn?.addEventListener('click', () => { stopSpeech(); state = 'idle'; syncBtn(); });
    // 语音自然结束时归 idle
    const _resetHandler = () => { state = 'idle'; syncBtn(); };
    document.addEventListener('yaya:speechStopped', _resetHandler);

    sectionEl.querySelector('[data-action="understood"]')?.addEventListener('click', async () => {
      await api('/ai/feedback', { method: 'POST', body: JSON.stringify({ knowledgeCode: meta.knowledgeCode, knowledgeName: meta.knowledgeName, grade: meta.grade, subject: meta.subject, chapter: meta.chapter, explainType: resp.explainType, module: s.key, understood: true, note: '模块已懂' }) });
      playUiSound('good'); showToast(`🌟 太棒了！已记录：${s.label} 懂了`);
    });
    sectionEl.querySelector('[data-action="confused"]')?.addEventListener('click', async () => {
      await api('/ai/feedback', { method: 'POST', body: JSON.stringify({ knowledgeCode: meta.knowledgeCode, knowledgeName: meta.knowledgeName, grade: meta.grade, subject: meta.subject, chapter: meta.chapter, explainType: resp.explainType, module: s.key, understood: false, note: `模块没懂：${s.key}` }) });
      playUiSound('try'); showToast(`💪 没关系，继续加油！已记录：${s.label} 没懂`);
    });
  }

  const nextWrap = document.createElement('div');
  nextWrap.className = 'explain-next-block';
  nextWrap.innerHTML = `
    <div class="explain-feedback-title">下一步</div>
    <div class="explain-next-actions">
      <button type="button" class="chip explain-chip" data-next="knowledge">继续下一个知识点</button>
      <button type="button" class="chip explain-chip" data-next="quiz">去做真题测试</button>
    </div>
  `;
  nextWrap.querySelector('[data-next="knowledge"]')?.addEventListener('click', () => showToast('继续下一个知识点'));
  nextWrap.querySelector('[data-next="quiz"]')?.addEventListener('click', () => showToast('去做真题测试'));
  card.appendChild(nextWrap);
}
async function streamExplainRequest(payload, onEvent) {
  const res = await fetch(`${API_BASE}/ai/explain/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 2);
      if (!block) continue;
      const lines = block.split('\n');
      const eventLine = lines.find(l => l.startsWith('event:')) || 'event: message';
      const dataLine = lines.find(l => l.startsWith('data:')) || 'data: {}';
      const event = eventLine.slice(6).trim();
      const data = JSON.parse(dataLine.slice(5).trim() || '{}');
      onEvent?.(event, data);
    }
  }
}



async function loadLeaderboardPanel() {
  const wrap = document.getElementById('leaderboardWrap');
  if (!wrap) return;
  wrap.innerHTML = `
    <div class="card glass" style="padding:18px;">
      <div class="practice-title">🏆 榜单</div>
      <div class="practice-sub" style="margin-top:6px;">下一步接入周榜 / 月榜 / 学期榜</div>
      <div style="padding:18px 0;color:var(--muted);">榜单正在接入中，先把学习和练习跑顺。</div>
    </div>`;
}

async function loadBoardPanel() {
  const wrap = document.getElementById('boardWrap');
  if (!wrap) return;
  wrap.innerHTML = `
    <div class="board-panel glass">
      <div class="board-head">
        <div>
          <div class="practice-title">🛰️ 家长同步掌握度</div>
          <div class="practice-sub">看孩子哪些知识点还要补</div>
        </div>
        <button type="button" class="chip" id="boardRefreshBtn">刷新</button>
      </div>
      <div class="practice-form">
        <input id="boardUserId" class="chat-input" placeholder="学生ID，例如 demo-student" value="demo-student" />
        <button type="button" class="practice-start-btn" id="boardLoadBtn">加载看板</button>
      </div>
      <div class="board-grid">
        <div class="board-card card glass">
          <div class="board-card-title">复习计划</div>
          <div class="board-list" id="reviewPlanList"></div>
        </div>
        <div class="board-card card glass">
          <div class="board-card-title">错题聚合</div>
          <div class="board-list" id="wrongSummaryList"></div>
        </div>
      </div>
    </div>`;

  const userIdInput = document.getElementById('boardUserId');
  const loadBtn = document.getElementById('boardLoadBtn');
  const refreshBtn = document.getElementById('boardRefreshBtn');
  const reviewList = document.getElementById('reviewPlanList');
  const wrongList = document.getElementById('wrongSummaryList');

  const renderPlan = (items) => {
    reviewList.innerHTML = (items || []).slice(0, 10).map((it, idx) => `
      <div class="board-item">
        <div class="board-item-title">${idx + 1}. ${it.knowledgeName || it.knowledgeCode || '未知知识点'}</div>
        <div class="board-item-sub">掌握度 ${it.masteryScore || 0} · ${it.masteryLevel || ''} · ${it.status || ''}</div>
      </div>
    `).join('') || '<div class="board-empty">暂无复习计划</div>';
  };

  const renderWrong = (items) => {
    wrongList.innerHTML = (items || []).slice(0, 10).map((it, idx) => `
      <div class="board-item">
        <div class="board-item-title">${idx + 1}. ${it.knowledgeCode || '未知知识点'}</div>
        <div class="board-item-sub">累计错 ${it.retryCount || 0} 次 · 已订正 ${it.correctedCount || 0} 次</div>
      </div>
    `).join('') || '<div class="board-empty">暂无错题数据</div>';
  };

  const load = async () => {
    const userId = userIdInput.value.trim() || 'demo-student';
    try {
      const [plan, wrong] = await Promise.all([
        api(`/masteries/review-plan?userId=${encodeURIComponent(userId)}`),
        api(`/wrongbook/summary/${encodeURIComponent(userId)}`),
      ]);
      renderPlan(plan || []);
      renderWrong(wrong || []);
      showToast('看板已刷新');
    } catch (e) {
      reviewList.innerHTML = '<div class="board-empty">看板加载失败</div>';
      wrongList.innerHTML = '<div class="board-empty">看板加载失败</div>';
      showToast('看板加载失败：' + e.message);
    }
  };

  loadBtn.onclick = load;
  refreshBtn.onclick = load;
  load();
}

async function loadPracticePanel() {
  const wrap = document.getElementById('practiceWrap');
  if (!wrap) return;
  wrap.innerHTML = `
    <div class="practice-panel glass">
      <div class="practice-head">
        <div>
          <div class="practice-title">⚡ AI 测试题</div>
          <div class="practice-sub">按知识点和掌握度，给孩子出最合适的题</div>
        </div>
        <button type="button" class="chip" id="practiceRefreshBtn">换一题</button>
      </div>
      <div class="practice-form">
        <input id="practiceUserId" class="chat-input" placeholder="学生ID（可先随便填）" />
        <input id="practiceKnowledgeCode" class="chat-input" placeholder="知识点编码，例如 M1S1-0" value="M1S1-0" />
        <button type="button" class="practice-start-btn" id="practiceStartBtn">开始出题</button>
      </div>
      <div class="practice-meta" id="practiceMeta">请输入知识点编码开始。</div>
      <div class="practice-card-list" id="practiceCardList"></div>
    </div>`;

  const userIdInput = document.getElementById('practiceUserId');
  const codeInput = document.getElementById('practiceKnowledgeCode');
  const startBtn = document.getElementById('practiceStartBtn');
  const refreshBtn = document.getElementById('practiceRefreshBtn');
  const list = document.getElementById('practiceCardList');
  const meta = document.getElementById('practiceMeta');

  const renderQuestions = (payload) => {
    const questions = payload?.questions || [];
    if (!questions.length) {
      list.innerHTML = '<div class="card glass" style="padding:20px;text-align:center;">暂无题目</div>';
      return;
    }
    list.innerHTML = questions.map((q, idx) => `
      <div class="practice-question card glass" data-qid="${q.id || idx}">
        <div class="practice-q-head">
          <div class="practice-q-title">第${idx + 1}题 · ${q.questionType || 'basic'}</div>
          <span class="task-tag green">${q.difficulty || 'easy'}</span>
        </div>
        <div class="practice-q-prompt">${q.prompt || ''}</div>
        <div class="practice-options">${(q.choices || []).map((c, i) => `<button type="button" class="practice-option" data-idx="${i}">${c}</button>`).join('')}</div>
        <div class="practice-q-actions">
          <button type="button" class="practice-submit-btn">提交</button>
          <span class="practice-feedback"></span>
        </div>
      </div>
    `).join('');

    list.querySelectorAll('.practice-question').forEach((card, cardIdx) => {
      let selected = null;
      card.querySelectorAll('.practice-option').forEach(btn => {
        btn.onclick = () => {
          selected = Number(btn.dataset.idx);
          card.querySelectorAll('.practice-option').forEach(b => b.classList.toggle('active', b === btn));
          playUiSound('select');
        };
      });
      card.querySelector('.practice-submit-btn').onclick = async () => {
        const q = questions[cardIdx];
        if (selected === null) { showToast('先选一个答案吧'); return; }
        const isCorrect = Number(selected) === Number(q.answerIndex || 0);
        const attemptPayload = {
          userId: userIdInput.value.trim() || 'demo-student',
          questionId: q.id,
          knowledgeCode: q.knowledgeCode,
          userAnswer: String.fromCharCode(65 + selected),
          isCorrect,
          score: isCorrect ? 100 : 0,
          answerDurationSec: 12,
          attemptSource: 'practice',
          errorTag: q.errorTag || 'concept'
        };
        try {
          await api('/attempts/submit', { method: 'POST', body: JSON.stringify(attemptPayload) });
          card.querySelector('.practice-feedback').textContent = isCorrect ? '答对了！' : '再看一看讲解';
          playUiSound(isCorrect ? 'good' : 'try');
          showToast(isCorrect ? '🌟 答对啦' : '💪 再来一次');
        } catch (e) {
          showToast('提交失败：' + e.message);
        }
      };
    });
  };

  const fetchQuestions = async () => {
    const userId = userIdInput.value.trim() || 'demo-student';
    const knowledgeCode = codeInput.value.trim();
    if (!knowledgeCode) { showToast('先输入知识点编码'); return; }
    meta.textContent = '正在按 mastery 推荐题目...';
    try {
      const payload = await api('/ai/questions/recommend', { method: 'POST', body: JSON.stringify({ userId, knowledgeCode, count: 5 }) });
      meta.textContent = `掌握度：${payload.masteryLevel || '未知'} · 题型：${payload.questionType || 'basic'} · 共 ${payload.count || 0} 题`;
      renderQuestions(payload);
    } catch (e) {
      meta.textContent = '题目生成失败：' + e.message;
      showToast('题目生成失败');
    }
  };

  startBtn.onclick = fetchQuestions;
  refreshBtn.onclick = fetchQuestions;
}



function buildKnowledgeGraphic(knowledgeName = '', explain = null) {
  const name = String(knowledgeName || '这个知识点');
  if (/分数/.test(name)) {
    return `
      <div class="detail-card" style="display:grid;gap:10px;place-items:center;text-align:center;">
        <div class="detail-title">🧩 知识图示</div>
        <svg viewBox="0 0 320 120" width="100%" style="max-width:320px">
          <rect x="20" y="20" width="90" height="80" rx="14" fill="#17324f" stroke="#55efff"/>
          <rect x="130" y="20" width="90" height="80" rx="14" fill="#17324f" stroke="#55efff"/>
          <rect x="240" y="20" width="60" height="80" rx="14" fill="#17324f" stroke="#55efff"/>
          <text x="65" y="64" fill="#edf6ff" text-anchor="middle" font-size="28">1/2</text>
          <text x="175" y="64" fill="#edf6ff" text-anchor="middle" font-size="28">2/4</text>
          <text x="270" y="64" fill="#edf6ff" text-anchor="middle" font-size="24">=</text>
          <text x="160" y="108" fill="#ffd667" text-anchor="middle" font-size="12">同乘同除，分数不变</text>
        </svg>
        <div class="detail-muted">分子分母同乘同除，大小不变</div>
      </div>`;
  }
  if (/小数/.test(name)) {
    return `
      <div class="detail-card" style="display:grid;gap:10px;place-items:center;text-align:center;">
        <div class="detail-title">🧩 知识图示</div>
        <svg viewBox="0 0 320 120" width="100%" style="max-width:320px">
          <circle cx="70" cy="60" r="36" fill="#17324f" stroke="#55efff"/>
          <circle cx="160" cy="60" r="36" fill="#17324f" stroke="#55efff"/>
          <circle cx="250" cy="60" r="36" fill="#17324f" stroke="#55efff"/>
          <text x="70" y="68" fill="#edf6ff" text-anchor="middle" font-size="22">0.5</text>
          <text x="160" y="68" fill="#edf6ff" text-anchor="middle" font-size="22">×</text>
          <text x="250" y="68" fill="#edf6ff" text-anchor="middle" font-size="22">3</text>
        </svg>
        <div class="detail-muted">看成“3个0.5相加”</div>
      </div>`;
  }
  if (/平行四边形/.test(name)) {
    return `
      <div class="detail-card" style="display:grid;gap:10px;place-items:center;text-align:center;">
        <div class="detail-title">🧩 知识图示</div>
        <svg viewBox="0 0 320 120" width="100%" style="max-width:320px">
          <polygon points="60,90 110,30 260,30 210,90" fill="#17324f" stroke="#55efff" stroke-width="3"/>
          <line x1="70" y1="35" x2="100" y2="35" stroke="#ffd667" stroke-width="3"/>
          <line x1="230" y1="85" x2="260" y2="85" stroke="#ffd667" stroke-width="3"/>
        </svg>
        <div class="detail-muted">两组对边平行且相等，容易变形</div>
      </div>`;
  }
  return `
    <div class="detail-card" style="display:grid;gap:10px;place-items:center;text-align:center;">
      <div class="detail-title">🧩 知识图示</div>
      <div style="width:100%;height:120px;border-radius:18px;background:linear-gradient(135deg,#17324f,#0f2035);display:grid;place-items:center;border:1px solid rgba(85,239,255,.22);">
        <div style="font-size:42px;">✨</div>
      </div>
      <div class="detail-muted">${name}</div>
    </div>`;
}


function renderKnowledgeMiniQuiz(knowledgeName = '') {
  const name = String(knowledgeName || '');
  if (/分数/.test(name)) {
    return `
      <div class="detail-card">
        <div class="detail-title">🎯 小题卡</div>
        <div style="font-weight:800;margin-bottom:8px;">下面哪个分数和 1/2 相等？</div>
        <div style="display:grid;gap:8px;">
          <button type="button" class="chip" data-quiz-answer="wrong">1/3</button>
          <button type="button" class="chip" data-quiz-answer="right">2/4</button>
          <button type="button" class="chip" data-quiz-answer="wrong">2/5</button>
        </div>
        <div class="detail-feedback" style="margin-top:8px;font-size:12px;color:var(--muted);"></div>
      </div>`;
  }
  if (/小数/.test(name)) {
    return `
      <div class="detail-card">
        <div class="detail-title">🎯 小题卡</div>
        <div style="font-weight:800;margin-bottom:8px;">1.5 × 4 表示什么？</div>
        <div style="display:grid;gap:8px;">
          <button type="button" class="chip" data-quiz-answer="wrong">1.5 + 4</button>
          <button type="button" class="chip" data-quiz-answer="right">4 个 1.5 相加</button>
          <button type="button" class="chip" data-quiz-answer="wrong">1.5 乘 4 没意思</button>
        </div>
        <div class="detail-feedback" style="margin-top:8px;font-size:12px;color:var(--muted);"></div>
      </div>`;
  }
  if (/平行四边形/.test(name)) {
    return `
      <div class="detail-card">
        <div class="detail-title">🎯 小题卡</div>
        <div style="font-weight:800;margin-bottom:8px;">平行四边形最重要的特征是？</div>
        <div style="display:grid;gap:8px;">
          <button type="button" class="chip" data-quiz-answer="wrong">只有一组对边平行</button>
          <button type="button" class="chip" data-quiz-answer="right">两组对边分别平行且相等</button>
          <button type="button" class="chip" data-quiz-answer="wrong">四条边都不相等</button>
        </div>
        <div class="detail-feedback" style="margin-top:8px;font-size:12px;color:var(--muted);"></div>
      </div>`;
  }
  return '';
}

function renderSelfCheckInteractive(items = [], knowledgeName = '') {
  if (!Array.isArray(items) || !items.length) return '<div class="detail-card">暂无自测题。</div>';
  return `
    <div class="detail-card">
      <div class="detail-title">❓ 自测互动</div>
      <div class="detail-muted" style="margin-bottom:10px;">点一下选项，马上看结果。</div>
      <div style="display:grid;gap:10px;">
        ${items.slice(0, 2).map((q, idx) => `
          <div class="detail-card" data-selfcheck-item="${idx}">
            <div style="font-weight:800;margin-bottom:8px;">${q}</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              <button class="chip" data-answer="good">会了</button>
              <button class="chip" data-answer="try">还不太会</button>
            </div>
            <div class="detail-feedback" style="margin-top:8px;font-size:12px;color:var(--muted);"></div>
          </div>
        `).join('')}
      </div>
    </div>`;
}

async function playExplainAnimation(detail) {
  const modal = document.getElementById('chatModal');
  const player = document.getElementById('animationPlayer');
  const stage = document.getElementById('animationStage');
  const caption = document.getElementById('animationCaption');
  const prevBtn = document.getElementById('animationPrev');
  const nextBtn = document.getElementById('animationNext');
  const playBtn = document.getElementById('playExplainAnimation');
  if (!modal || !player || !stage || !caption) return;
  player.style.display = '';
  playBtn && (playBtn.disabled = true, playBtn.textContent = '正在生成动画...');

  try {
    const scriptRes = await api('/ai/explain/animation-script', {
      method: 'POST',
      body: JSON.stringify({
        knowledgeCode: detail.knowledgeCode,
        knowledgeName: detail.knowledgeName,
        grade: detail.grade,
        subject: detail.subject,
        chapter: detail.chapter,
        masteryLevel: '未学',
        style: 'card',
      }),
    });

    const scenes = scriptRes.scenes || [];
    if (!scenes.length) throw new Error('没有生成动画分镜');

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    let bgmTimer = null;
    let idx = 0;
    let playing = false;
    let sceneTimer = null;
    let currentAudio = null;

    const playTone = (freq = 440, duration = 0.12, type = 'sine', gain = 0.03) => {
      const osc = audioCtx.createOscillator();
      const g = audioCtx.createGain();
      osc.type = type;
      osc.frequency.value = freq;
      g.gain.value = gain;
      osc.connect(g);
      g.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    };

    const startBgm = () => {
      if (bgmTimer) return;
      let t = 0;
      bgmTimer = setInterval(() => {
        const seq = [523.25, 659.25, 783.99, 659.25];
        playTone(seq[t % seq.length], 0.08, 'triangle', 0.015);
        t += 1;
      }, 650);
    };

    const stopBgm = () => {
      if (bgmTimer) clearInterval(bgmTimer);
      bgmTimer = null;
    };

    const stopCurrentAudio = () => {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
      }
    };

    const renderVisual = (scene, stepIndex) => {
      const text = scene.visual || '';
      if (/cake|蛋糕/i.test(text)) {
        return `
          <div style="position:relative;width:220px;height:130px;">
            <div style="position:absolute;left:20px;top:30px;width:180px;height:70px;border-radius:18px;background:#ffd667;box-shadow:0 0 0 3px rgba(255,255,255,.08) inset;"></div>
            <div style="position:absolute;left:20px;top:30px;width:${stepIndex===0?90:stepIndex===1?90:180}px;height:70px;border-radius:${stepIndex===0?'18px 0 0 18px':'18px'};background:${stepIndex===0?'#ff8fb1':stepIndex===1?'#55efff':'rgba(255,255,255,.12)'};opacity:${stepIndex===2?0.25:1};transition:all .45s ease;"></div>
            <div style="position:absolute;left:${stepIndex===0?0:stepIndex===1?80:170}px;top:18px;font-size:18px;font-weight:900;color:#fff;animation:${stepIndex===0?'bounce 1s infinite':''};">${stepIndex===0?'1/2':''}</div>
            <div style="position:absolute;left:${stepIndex===1?70:140}px;top:18px;font-size:18px;font-weight:900;color:#fff;">${stepIndex===1?'2/4':''}</div>
          </div>`;
      }
      if (/1\/2|2\/4|4\/8/.test(scene.subtitle || '')) {
        const label = stepIndex === 0 ? '1/2' : stepIndex === 1 ? '2/4' : stepIndex === 2 ? '1/2' : '1/2';
        const side = stepIndex === 1 ? 'right:22px;' : 'left:22px;';
        return `
          <div style="position:relative;width:240px;height:120px;display:grid;place-items:center;">
            <div style="position:absolute;${side}top:24px;width:116px;height:72px;border-radius:18px;background:${stepIndex===1?'rgba(85,239,255,.18)':'rgba(255,255,255,.08)'};border:2px solid #55efff;transition:all .4s ease;"></div>
            <div style="position:absolute;${side==='left:22px;'?'left:40px;':'right:40px;'}top:26px;font-size:36px;font-weight:900;color:#fff;">${label}</div>
            <div style="position:absolute;right:20px;top:38px;font-size:28px;color:#ffd667;">${stepIndex===1?'→':'='}</div>
          </div>`;
      }
      return `<div style="font-size:68px;animation:zoomPulse 1.2s infinite;">✨</div>`;
    };

    const renderScene = async (i) => {
      const scene = scenes[i];
      if (!scene) return;
      const sceneHtml = `
        <div style="display:grid;gap:12px;place-items:center;text-align:center;padding:18px;">
          <div style="font-size:18px;font-weight:900;color:#fff;">${scene.title}</div>
          <div style="width:100%;min-height:150px;border-radius:22px;background:linear-gradient(135deg,rgba(255,255,255,.08),rgba(255,255,255,.03));display:grid;place-items:center;border:1px solid rgba(85,239,255,.18);overflow:hidden;position:relative;">
            ${renderVisual(scene, i)}
          </div>
          <div style="font-size:14px;color:var(--cyan);font-weight:800;">${scene.subtitle || ''}</div>
        </div>`;
      stage.innerHTML = sceneHtml;
      caption.textContent = scene.interactiveHint || '';

      const sfx = (scene.sfx || []).join(' ').toLowerCase();
      if (sfx.includes('pop')) playTone(880, 0.08, 'triangle', 0.03);
      if (sfx.includes('ding') || sfx.includes('chime')) playTone(1046.5, 0.12, 'sine', 0.035);
      if (sfx.includes('swish') || sfx.includes('whoosh')) playTone(330, 0.10, 'sawtooth', 0.02);

      stopCurrentAudio();
      if (scene.narration) {
        const tts = await api('/ai/tts', { method: 'POST', body: JSON.stringify({ text: scene.narration, voiceKey: 'zh-cn-female' }) });
        if (tts?.audioBase64) {
          currentAudio = new Audio(`data:${tts.mimeType || tts.audioMimeType || 'audio/mpeg'};base64,${tts.audioBase64}`);
          await currentAudio.play().catch(()=>{});
        }
      }
    };

    const step = async () => {
      if (idx >= scenes.length) {
        playing = false;
        stopCurrentAudio();
        stopBgm();
        playBtn && (playBtn.disabled = false, playBtn.textContent = '▶ 播放动画短片');
        return;
      }
      await renderScene(idx);
      const waitMs = Math.max(1800, (scenes[idx].durationSec || 6) * 1000);
      idx += 1;
      if (sceneTimer) clearTimeout(sceneTimer);
      if (playing) sceneTimer = setTimeout(step, waitMs);
    };

    await audioCtx.resume().catch(()=>{});
    startBgm();
    playing = true;
    step();

    prevBtn.onclick = async () => {
      stopCurrentAudio();
      idx = Math.max(0, idx - 2);
      await renderScene(idx);
    };
    nextBtn.onclick = async () => {
      stopCurrentAudio();
      idx = Math.min(scenes.length - 1, idx);
      await renderScene(idx);
      idx = Math.min(scenes.length, idx + 1);
    };
  } catch (err) {
    showToast('动画短片生成失败：' + (err?.message || err));
    playBtn && (playBtn.disabled = false, playBtn.textContent = '▶ 播放动画短片');
    player.style.display = 'none';
  }
}

function openAssistantView(title, html) {
  const modal = document.getElementById('chatModal');
  const body = document.getElementById('chatBody');
  const topic = document.getElementById('chatTopic');
  if (!modal || !body || !topic) return;
  modal.classList.add('active');
  modal.classList.remove('detail-mode');
  topic.textContent = title;
  body.innerHTML = html;
}

async function showTextbookMaterials(payload) {
  const kName = payload.knowledgeName || '这个知识点';
  try {
    const requestPayload = {
      ...payload,
      knowledgeCode: payload.knowledgeCode || '',
      knowledgeName: payload.knowledgeName || '',
      grade: payload.grade,
      subject: payload.subject,
      chapter: payload.chapter,
    };
    const data = await api('/ai/materials/textbook', { method: 'POST', body: JSON.stringify(requestPayload) });
    const versions = data.versions || [];
    const contents = (data.contents || []).filter(item => {
      const text = `${item.title || ''} ${item.body || ''}`;
      return !/^AI反馈/.test(text) && !/^\{\s*"knowledgeCode"/.test(text);
    });
    const pageSize = 4;
    let page = 0;
    const totalPages = Math.max(1, Math.ceil(contents.length / pageSize));
    const renderPage = () => {
      const slice = contents.slice(page * pageSize, (page + 1) * pageSize);
      const versionHtml = versions.length ? versions.slice(0, 8).map(v => `<div style="font-size:13px;line-height:1.6;">• ${v.subject} ${v.grade} ${v.semester || ''} · ${v.publisher || ''} · ${v.version}</div>`).join('') : '<div>暂无版本索引</div>';
      const contentHtml = slice.length ? slice.map(item => `<div style="margin-bottom:12px;padding:12px;border-radius:14px;background:rgba(255,255,255,.05);"><div style="font-weight:800;margin-bottom:6px;">${item.title || '教材内容'}</div><div style="white-space:pre-wrap;line-height:1.7;">${item.body || ''}</div></div>`).join('') : '<div>暂时还没有对应教材内容。</div>';
      return `
        <div class="chat-msg msg-ai"><div style="font-weight:900;margin-bottom:8px;">📚 教材版本</div>${versionHtml}</div>
        <div class="chat-msg msg-ai"><div style="font-weight:900;margin-bottom:8px;">📘 教材内容 · 第 ${page + 1} / ${totalPages} 页</div>${contentHtml}
          <div style="display:flex;gap:10px;justify-content:space-between;margin-top:12px;">
            <button type="button" class="chip" data-page-prev ${page <= 0 ? 'disabled' : ''}>上一页</button>
            <button type="button" class="chip" data-page-next ${page >= totalPages - 1 ? 'disabled' : ''}>下一页</button>
          </div>
        </div>`;
    };
    openAssistantView(`📚 教材 · ${kName}${payload.chapter ? ' · ' + payload.chapter : ''}`, renderPage());
    const body = document.getElementById('chatBody');
    const attachPager = () => {
      body.querySelector('[data-page-prev]')?.addEventListener('click', () => { if (page > 0) { page -= 1; body.innerHTML = renderPage(); attachPager(); } });
      body.querySelector('[data-page-next]')?.addEventListener('click', () => { if (page < totalPages - 1) { page += 1; body.innerHTML = renderPage(); attachPager(); } });
    };
    attachPager();
  } catch (e) {
    showToast('教材加载失败：' + e.message);
  }
}

async function showPastExamMaterials(payload) {
  const kName = payload.knowledgeName || '这个知识点';
  try {
    const requestPayload = {
      ...payload,
      knowledgeCode: payload.knowledgeCode || '',
      knowledgeName: payload.knowledgeName || '',
      grade: payload.grade,
      subject: payload.subject,
    };
    const data = await api('/ai/materials/past-exam', { method: 'POST', body: JSON.stringify(requestPayload) });
    const sources = data.sources || [];
    const questions = data.questions || [];
    const assets = data.assets || [];
    const pageSize = 4;
    let page = 0;
    const totalPages = Math.max(1, Math.ceil((questions.length + assets.length) / pageSize));
    const renderPage = () => {
      const merged = [...questions.map(q => ({ ...q, _kind: 'question' })), ...assets.map(q => ({ ...q, _kind: 'asset' }))];
      const slice = merged.slice(page * pageSize, (page + 1) * pageSize);
      const sourceHtml = sources.length ? sources.slice(0, 8).map(s => `<div style="font-size:13px;line-height:1.6;">• ${s.year || ''} ${s.subject} ${s.grade} · ${s.sourceType} · ${s.sourceName}</div>`).join('') : '<div>暂无来源索引</div>';
      const qHtml = slice.length ? slice.map((q, idx) => `<div style="margin-bottom:12px;padding:12px;border-radius:14px;background:rgba(255,255,255,.05);"><div style="font-weight:900;">${q._kind === 'asset' ? '题库资产' : '真题'} ${page * pageSize + idx + 1}</div><div style="white-space:pre-wrap;line-height:1.7;">${q.prompt || ''}</div><div style="font-size:12px;color:var(--muted);margin-top:8px;">答案：${q.answerIndex ?? 0}</div></div>`).join('') : '<div>暂时没有对应真题内容。</div>';
      return `
        <div class="chat-msg msg-ai"><div style="font-weight:900;margin-bottom:8px;">🗂️ 真题来源</div>${sourceHtml}</div>
        <div class="chat-msg msg-ai"><div style="font-weight:900;margin-bottom:8px;">📄 真题内容 · 第 ${page + 1} / ${totalPages} 页</div>${qHtml}
          <div style="display:flex;gap:10px;justify-content:space-between;margin-top:12px;">
            <button type="button" class="chip" data-page-prev ${page <= 0 ? 'disabled' : ''}>上一页</button>
            <button type="button" class="chip" data-page-next ${page >= totalPages - 1 ? 'disabled' : ''}>下一页</button>
          </div>
        </div>`;
    };
    openAssistantView(`🧠 真题 · ${kName}${payload.chapter ? ' · ' + payload.chapter : ''}`, renderPage());
    const body = document.getElementById('chatBody');
    const attachPager = () => {
      body.querySelector('[data-page-prev]')?.addEventListener('click', () => { if (page > 0) { page -= 1; body.innerHTML = renderPage(); attachPager(); } });
      body.querySelector('[data-page-next]')?.addEventListener('click', () => { if (page < totalPages - 1) { page += 1; body.innerHTML = renderPage(); attachPager(); } });
    };
    attachPager();
  } catch (e) {
    showToast('真题加载失败：' + e.message);
  }
}


async function openKnowledgeDetail(payload) {
  const data = typeof payload === 'string' ? { knowledgeName: payload } : payload;
  const kName = data.knowledgeName || '这个知识点';
  try {
    const detail = await api('/ai/knowledge/detail', { method: 'POST', body: JSON.stringify({
      knowledgeCode: String(data.knowledgeCode || data.id || data.knowledgeName || '').trim(),
      knowledgeName: data.knowledgeName,
      grade: data.grade,
      subject: data.subject,
      chapter: data.chapter,
      userId: appState.currentUserId || 'demo-student',
    }) });
    const explain = detail.explain || null;
    const textbook = detail.textbook || null;
    // 异步预热课堂包，保证用户下次打开更快
    api('/ai/classroom/prewarm', {
      method: 'POST',
      body: JSON.stringify({
        knowledgeCode: String(data.knowledgeCode || data.id || data.knowledgeName || '').trim(),
        knowledgeName: data.knowledgeName,
        grade: data.grade,
        subject: data.subject,
        chapter: data.chapter,
        userId: appState.currentUserId || 'demo-student',
        masteryLevel: detail.mastery?.masteryLevel || '未学',
      }),
    }).catch(() => {});
    const pastExam = detail.pastExam || null;
    const practice = detail.practice || null;
    const wrongbook = detail.wrongbook || [];
    const mastery = detail.mastery || null;
    const summary = detail.summary || {};

    const explainSections = explain ? [
      { title: '一句话', body: explain.oneLine },
      { title: '核心要点', body: (explain.corePoints || []).map(x => `• ${x}`).join('\n') },
      { title: '为什么这样', body: explain.whyItWorks },
      { title: '易错点', body: (explain.commonMistakes || []).map(x => `• ${x}`).join('\n') },
      { title: '例子', body: explain.example },
      { title: '自测', body: (explain.selfCheck || []).map(x => `• ${x}`).join('\n') },
      { title: '总结', body: explain.summary },
    ].filter(x => x.body && String(x.body).trim()) : [];
    const explainHtml = explain ? `
      <div class="chat-msg msg-ai detail-card">${buildKnowledgeGraphic(kName, explain)}
        <div class="detail-title" style="margin-top:12px;">💡 AI讲解</div>
        <div style="font-weight:800;margin-bottom:6px;">${explain.title || ''}</div>
        <div class="detail-muted" style="margin-bottom:10px;">按目录看，再配合上面的图示理解。</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
          <button type="button" class="chip" id="playExplainAnimation">▶ 播放动画短片</button>
          <button type="button" class="chip" id="startClassroomMode">🏫 进入课堂模式</button>
        </div>
        <div class="detail-panel">
          ${explainSections.map(sec => `<div class="detail-card section-fade"><div class="detail-title">${sec.title}</div><div style="white-space:pre-wrap;line-height:1.75;">${sec.body}</div></div>`).join('')}
        </div>
        <div class="detail-card" id="animationPlayer" style="display:none;">
          <div class="detail-title">🎬 动画短片</div>
          <div id="animationStage" style="min-height:180px;border-radius:18px;background:linear-gradient(135deg,#0f2035,#17324f);display:grid;place-items:center;position:relative;overflow:hidden;"></div>
          <div id="animationCaption" class="detail-muted" style="margin-top:10px;"></div>
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:10px;">
            <button type="button" class="chip" id="animationPrev">上一段</button>
            <button type="button" class="chip" id="animationNext">下一段</button>
          </div>
        </div>
        ${renderKnowledgeMiniQuiz(kName)}
        ${renderSelfCheckInteractive(explain.selfCheck || [], kName)}
      </div>` : '<div class="chat-msg msg-ai detail-card">暂无 AI讲解</div>';

    const textbookHtml = textbook && textbook.contents ? `<div class="chat-msg msg-ai detail-card"><div class="detail-title">📚 教材</div>${textbook.contents.slice(0, 4).map(item => `<div style="margin-bottom:10px;padding:10px;border-radius:12px;background:rgba(255,255,255,.05);"><div style="font-weight:800;">${item.title || '教材内容'}</div><div style="white-space:pre-wrap;line-height:1.7;">${item.body || ''}</div></div>`).join('')}</div>` : '<div class="chat-msg msg-ai">暂无教材</div>';
    const pastExamHtml = pastExam && (pastExam.questions || pastExam.assets) ? `<div class="chat-msg msg-ai detail-card"><div class="detail-title">🧠 真题</div>${(pastExam.questions || []).slice(0, 3).map(item => `<div style="margin-bottom:10px;padding:10px;border-radius:12px;background:rgba(255,255,255,.05);"><div style="font-weight:800;">${item.prompt || ''}</div></div>`).join('')}${(pastExam.assets || []).slice(0, 3).map(item => `<div style="margin-bottom:10px;padding:10px;border-radius:12px;background:rgba(255,255,255,.05);"><div style="font-weight:800;">${item.prompt || ''}</div></div>`).join('')}</div>` : '<div class="chat-msg msg-ai">暂无真题</div>';
    const practiceHtml = practice && practice.questions ? `<div class="chat-msg msg-ai detail-card"><div class="detail-title">⚡ 练习题</div>${practice.questions.slice(0, 3).map(item => `<div style="margin-bottom:10px;padding:10px;border-radius:12px;background:rgba(255,255,255,.05);"><div style="font-weight:800;">${item.prompt || ''}</div></div>`).join('')}</div>` : '<div class="chat-msg msg-ai">暂无练习题</div>';
    const wrongbookHtml = wrongbook.length ? `<div class="chat-msg msg-ai detail-card"><div class="detail-title">🧯 错题本</div>${wrongbook.slice(0, 5).map(item => `<div style="margin-bottom:10px;padding:10px;border-radius:12px;background:rgba(255,255,255,.05);"><div style="font-weight:800;">${item.questionId || ''}</div><div style="font-size:12px;color:var(--muted);">错因：${item.wrongType || ''} · 重试 ${item.retryCount || 0} 次</div></div>`).join('')}</div>` : '<div class="chat-msg msg-ai">暂无错题</div>';
    const masteryHtml = `<div class="chat-msg msg-ai detail-card"><div class="detail-title">📈 掌握度</div><div style="font-size:14px;line-height:1.8;">${mastery ? `掌握分：${mastery.masteryScore || 0} · 等级：${mastery.masteryLevel || ''} · 状态：${mastery.status || ''}` : '暂无掌握记录'}</div><div style="font-size:12px;color:var(--muted);margin-top:8px;">${summary.textbookCount || 0} 条教材 · ${summary.pastExamCount || 0} 条真题 · ${summary.wrongbookCount || 0} 条错题</div></div>`;

    const html = `
      <div class="chat-msg msg-ai" data-detail-root="1"><div style="font-weight:900;margin-bottom:8px;">📘 知识点详情 · ${kName}</div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:10px;">先看 AI讲解，再切到教材、真题、练习题、错题本和掌握度。</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
          <button type="button" class="chip active" data-ks-tab="explain">AI讲解</button>
          <button type="button" class="chip" data-ks-tab="textbook">教材</button>
          <button type="button" class="chip" data-ks-tab="pastExam">真题</button>
          <button type="button" class="chip" data-ks-tab="practice">练习题</button>
          <button type="button" class="chip" data-ks-tab="wrongbook">错题本</button>
          <button type="button" class="chip" data-ks-tab="mastery">掌握度</button>
        </div>
      </div>
      <div class="detail-panel" data-ks-panel="explain">${explainHtml}</div>
      <div class="detail-panel" data-ks-panel="textbook" style="display:none;">${textbookHtml}</div>
      <div class="detail-panel" data-ks-panel="pastExam" style="display:none;">${pastExamHtml}</div>
      <div class="detail-panel" data-ks-panel="practice" style="display:none;">${practiceHtml}</div>
      <div class="detail-panel" data-ks-panel="wrongbook" style="display:none;">${wrongbookHtml}</div>
      <div class="detail-panel" data-ks-panel="mastery" style="display:none;">${masteryHtml}</div>
    `;

    openAssistantView(`📘 ${kName}`, html);
    const modal = document.getElementById('chatModal');
    modal?.classList.add('detail-mode');
    const body = document.getElementById('chatBody');
    const playBtn = body.querySelector('#playExplainAnimation');
    playBtn?.addEventListener('click', () => {
      const knowledge = detail?.knowledge || detail || {};
      playExplainAnimation({
        knowledgeCode: knowledge.knowledgeCode || knowledge.code || kName,
        knowledgeName: knowledge.knowledgeName || knowledge.name || kName,
        grade: knowledge.grade || '',
        subject: knowledge.subject || '',
        chapter: knowledge.chapter || knowledge.chapterName || '',
      });
    });
    const classBtn = body.querySelector('#startClassroomMode');
    classBtn?.addEventListener('click', async () => {
      classBtn.disabled = true;
      classBtn.textContent = '课堂生成中...';
      try {
        const classroom = await getPreferredClassroomLesson(detail, kName);
        window.__selectedClassroomLessonId = classroom?.lessonId || classroom?.id || '';
        window.__selectedClassroomLessonPayload = classroom;
        modal.classList.remove('active');
        modal.classList.remove('detail-mode');
        body.innerHTML = '<div class="chat-msg msg-ai">课堂已打开，正在切换到播放器...</div>';
        switchTab('classroom');
        showToast('已打开真课堂播放器');
      } catch (e) {
        showToast('课堂模式生成失败：' + e.message);
      } finally {
        classBtn.disabled = false;
        classBtn.textContent = '🏫 进入课堂模式';
      }
    });
    body.querySelectorAll('[data-ks-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        body.querySelectorAll('[data-ks-panel]').forEach(p => p.style.display = 'none');
        body.querySelectorAll('[data-ks-tab]').forEach(b => b.classList.remove('active'));
        const panel = body.querySelector(`[data-ks-panel="${btn.dataset.ksTab}"]`);
        if (panel) panel.style.display = 'block';
        btn.classList.add('active');
      });
    });
    body.querySelectorAll('[data-selfcheck-item]').forEach(card => {
      card.querySelectorAll('[data-answer]').forEach(btn => {
        btn.addEventListener('click', () => {
          const feedback = card.querySelector('.detail-feedback');
          const answer = btn.dataset.answer;
          feedback.textContent = answer === 'good' ? '太好了，说明你已经开始会用了。' : '没关系，先回到上面的图示和核心规则再看一看。';
          feedback.className = `detail-feedback ${answer === 'good' ? 'good' : 'try'}`;
        });
      });
    });
    body.querySelectorAll('[data-quiz-answer]').forEach(btn => {
      btn.addEventListener('click', () => {
        const card = btn.closest('.detail-card');
        const feedback = card?.querySelector('.detail-feedback');
        const right = btn.dataset.quizAnswer === 'right';
        feedback.textContent = right ? (btn.dataset.quizNote || '答对了，这个知识点你抓住了关键。') : (btn.dataset.quizNote || '再想一想，回到图示和核心规则会更容易看出来。');
        feedback.className = `detail-feedback ${right ? 'good' : 'try'}`;
      });
    });
  } catch (e) {
    showToast('知识点详情加载失败：' + e.message);
  }
}

function setupCommonHandlers() {
  document.querySelectorAll('[data-tab]').forEach(btn => btn.onclick = () => switchTab(btn.dataset.tab));
  
  // 对话框逻辑
  const modal = document.getElementById('chatModal');
  const close = document.getElementById('closeChat');
  const body = document.getElementById('chatBody');

  if(close) close.onclick = () => { modal.classList.remove('active'); modal.classList.remove('detail-mode'); };

  const addMsg = (text, isAi = false) => {
    const div = document.createElement('div');
    div.className = `chat-msg ${isAi ? 'msg-ai' : 'msg-user'}`;
    div.textContent = text;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  };


  window.__showTextbook = (payload) => showTextbookMaterials(payload);
  window.__enterClassroom = async (payload) => {
    const data = typeof payload === 'string' ? { knowledgeName: payload } : payload;
    const kName = data.knowledgeName || '这个知识点';
    showToast('课堂生成中...');
    try {
      const knowledge = data?.knowledge || data || {};
      const code = String(knowledge.knowledgeCode || knowledge.code || kName || '').trim();
      const title = String(knowledge.knowledgeName || knowledge.name || kName || '').trim();
      const list = await api('/ai/classroom/list').catch(() => []);
      const exact = (list || []).find(item => item.knowledgeCode === code)
        || (list || []).find(item => String(item.knowledgeName || '').includes(title));
      let classroom;
      if (exact) {
        classroom = await api('/ai/classroom/replay/' + encodeURIComponent(exact.lessonId));
      } else {
        classroom = await api('/ai/classroom/start', { method: 'POST', body: JSON.stringify({
          knowledgeCode: code, knowledgeName: title,
          grade: knowledge.grade || '', subject: knowledge.subject || '',
          chapter: knowledge.chapter || knowledge.chapterName || '',
          userId: appState.currentUserId || 'demo-student',
          masteryLevel: data.masteryLevel || '未学',
        }) });
      }
      window.__selectedClassroomLessonId = classroom?.lessonId || classroom?.id || '';
      window.__selectedClassroomLessonPayload = classroom;
      switchTab('classroom');
      showToast('已打开真课堂播放器');
    } catch (e) { showToast('课堂模式生成失败：' + e.message); }
  };
  window.__showPastExam = (payload) => showPastExamMaterials(payload);
  window.__openKnowledgeDetail = (payload) => openKnowledgeDetail(payload);

  window.__diagnose = (id, masteryLabel) => {
    const titleEl = document.querySelector(`#ki_${id} .kp-name`);
    const title = titleEl ? titleEl.textContent.trim() : '这个知识点';
    modal.classList.add('active');
    document.getElementById('chatTopic').textContent = `正在聊：${title}`;
    
    const snapshotHTML = `<div class="msg-snapshot"><strong>已同步进度</strong>· 知识点：${title}<br/>· 状态：${masteryLabel}</div>`;
    const div = document.createElement('div');
    div.innerHTML = snapshotHTML;
    body.appendChild(div);

    addMsg(`我想聊聊“${title}”这个知识点，感觉还需要帮助。`, false);
    setTimeout(() => { addMsg(`没问题！我看到你对“${title}”的掌握度是‘${masteryLabel}’。我们从哪个细节开始聊？`, true); }, 800);
  };

  window.__askAI = async (payload) => {
    const data = typeof payload === 'string' ? { knowledgeName: payload } : payload;
    const kName = data.knowledgeName || '这个知识点';
    modal.classList.add('active');
    document.getElementById('chatTopic').textContent = kName;
    addMsg(`请给我讲解一下“${kName}”这个知识点吧。`, false);

    const knowledgeCode = String(data.knowledgeCode || data.id || data.knowledgeName || '').trim();
    if (!knowledgeCode) {
      addMsg('讲解生成失败：缺少 knowledgeCode', true);
      return;
    }

    const payloadReq = {
      knowledgeCode,
      knowledgeName: data.knowledgeName,
      grade: data.grade,
      subject: data.subject,
      chapter: data.chapter,
      masteryLevel: data.masteryLevel || 'learning',
      style: 'dialog',
      errorTag: 'general'
    };

    // 停止可能还在播放的上一段语音
    stopSpeech();

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-msg msg-ai explain-card loading';
    const voiceOptions = getVoicePresets();
    const currentVoiceKey = explainVoice.voiceKey || 'zh-cn-female';
    const voiceChipsHtml = voiceOptions.map(v => `<button type="button" class="explain-chip ${v.key === currentVoiceKey ? 'active' : ''}" data-voice="${v.key}">${v.label}</button>`).join('');
    const speedChipsHtml = [0.75, 1, 1.25, 1.5, 2].map(v => `<button type="button" class="explain-chip ${v === explainVoice.rate ? 'active' : ''}" data-speed="${v}">${v}x</button>`).join('');

    const activeVoiceLabel = voiceOptions.find(v => v.key === currentVoiceKey)?.label || '👩 普通话女声';
    const activeSpeedLabel = explainVoice.rate + 'x';
    loadingDiv.innerHTML = `
      <div class="explain-head">
        <div class="explain-title">🌱 芽芽正在生成讲解...</div>
        <div class="explain-meta">请稍等，正在整理成适合孩子看的内容</div>
      </div>
      <div class="explain-toolbar-card" id="explainToolbar">
        <div class="explain-toolbar-toggle" id="explainToolbarToggle">
          <div class="explain-toolbar-toggle-label">
            🎙️ <span id="toolbarVoiceLabel">${activeVoiceLabel}</span>
            &nbsp;·&nbsp;
            ⚡ <span id="toolbarSpeedLabel">${activeSpeedLabel}</span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="font-size:11px;color:var(--muted);">朗读设置</span>
            <span class="explain-toolbar-toggle-arrow">▲</span>
          </div>
        </div>
        <div class="explain-toolbar-panel">
          <div class="explain-chip-row">
            <span class="explain-chip-label">🎙️ 方言</span>
            <div class="explain-chip-scroll">${voiceChipsHtml}</div>
          </div>
          <div class="explain-chip-row">
            <span class="explain-chip-label">⚡ 语速</span>
            <div class="explain-chip-scroll">${speedChipsHtml}</div>
          </div>
        </div>
      </div>
      <div class="explain-sections"></div>`;

    // 折叠/展开
    loadingDiv.querySelector('#explainToolbarToggle')?.addEventListener('click', () => {
      loadingDiv.querySelector('#explainToolbar')?.classList.toggle('open');
    });

    // 绑定方言/语速 chip 事件
    loadingDiv.querySelectorAll('[data-voice]').forEach(btn => btn.addEventListener('click', () => {
      const key = btn.dataset.voice;
      const preset = TTS_VOICE_MAP[key] || TTS_VOICE_MAP['zh-cn-female'];
      explainVoice.voiceKey = key;
      explainVoice.voiceName = preset.voiceName;
      explainVoice.voiceLang = preset.lang;
      loadingDiv.querySelectorAll('[data-voice]').forEach(b => b.classList.toggle('active', b === btn));
      const lbl = loadingDiv.querySelector('#toolbarVoiceLabel');
      if (lbl) lbl.textContent = btn.textContent;
      stopSpeech();
      playUiSound('select');
      showToast('🎙️ 已切到：' + btn.textContent);
    }));
    loadingDiv.querySelectorAll('[data-speed]').forEach(btn => btn.addEventListener('click', () => {
      explainVoice.rate = Number(btn.dataset.speed || 1);
      loadingDiv.querySelectorAll('[data-speed]').forEach(b => b.classList.toggle('active', b === btn));
      const lbl = loadingDiv.querySelector('#toolbarSpeedLabel');
      if (lbl) lbl.textContent = explainVoice.rate + 'x';
      playUiSound('select');
      showToast('⚡ 语速：' + explainVoice.rate + 'x');
    }));
    body.appendChild(loadingDiv);
    body.scrollTop = body.scrollHeight;

    const sectionsWrap = loadingDiv.querySelector('.explain-sections');
    const sectionOrder = ['oneLine','corePoints','whyItWorks','commonMistakes','summary','selfCheck'];
    const sectionLabels = {
      oneLine: '💡 一句话理解',
      corePoints: '📌 核心规则',
      whyItWorks: '🔍 为什么这样',
      commonMistakes: '🚨 常见错误',
      summary: '✨ 总结',
      selfCheck: '❓ 自测问题',
    };
    const rendered = new Map();
    const ensureSection = (key) => {
      if (rendered.has(key)) return rendered.get(key);
      const el = document.createElement('section');
      el.className = 'explain-section';
      el.innerHTML = `
        <div class="explain-section-head">
          <div class="explain-section-title">${sectionLabels[key] || key}</div>
        </div>
        <div class="explain-section-body">加载中...</div>
        <div class="explain-section-actions explain-section-actions--playback">
          <button type="button" class="explain-play-btn" data-play-toggle="1">🔊 朗读</button>
          <button type="button" class="explain-ctrl-btn danger" data-action="stop" title="停止">⏹</button>
        </div>
        <div class="explain-section-actions explain-section-actions--feedback">
          <button type="button" class="explain-feedback-btn good" data-action="understood">✅ 我懂了！</button>
          <button type="button" class="explain-feedback-btn bad" data-action="confused">🤔 再说一遍</button>
        </div>`;
      sectionsWrap.appendChild(el);
      const rec = { key, el, body: el.querySelector('.explain-section-body') };
      rendered.set(key, rec);
      return rec;
    };

    const setModuleText = async (key, value) => {
      const rec = ensureSection(key);
      const text = Array.isArray(value) ? value.map((x, i) => key === 'selfCheck' ? `${i + 1}. ${x}` : `· ${x}`).join('\n') : String(value || '');
      await animateSectionText(rec.body, text);
      const playBtn = rec.el.querySelector('[data-play-toggle]');
      const stopBtn = rec.el.querySelector('[data-action="stop"]');
      let state = 'idle';
      const syncBtn = () => {
        if (state === 'idle')    playBtn.innerHTML = '🔊 朗读';
        if (state === 'playing') playBtn.innerHTML = '⏸ 暂停';
        if (state === 'paused')  playBtn.innerHTML = '▶️ 继续';
      };
      playBtn?.addEventListener('click', async () => {
        if (state === 'idle') {
          state = 'playing';
          syncBtn();
          try {
            await speakText(text);
          } catch (e) {
            state = 'idle';
            syncBtn();
            showToast('朗读失败：' + (e?.message || e));
          }
          return;
        }
        if (state === 'playing') { state = 'paused';  syncBtn(); pauseSpeech(); return; }
        if (state === 'paused')  { state = 'playing'; syncBtn(); resumeSpeech(); return; }
      });
      stopBtn?.addEventListener('click', () => { stopSpeech(); state = 'idle'; syncBtn(); });
      const _resetH = () => { state = 'idle'; syncBtn(); };
      document.addEventListener('yaya:speechStopped', _resetH);
      rec.el.querySelector('[data-action="understood"]')?.addEventListener('click', async () => {
        await api('/ai/feedback', { method: 'POST', body: JSON.stringify({ knowledgeCode: payloadReq.knowledgeCode, knowledgeName: payloadReq.knowledgeName, grade: payloadReq.grade, subject: payloadReq.subject, chapter: payloadReq.chapter, explainType: 'dialog', module: key, understood: true, note: '模块已懂' }) });
        playUiSound('good'); showToast(`🌟 太棒了！`);
      });
      rec.el.querySelector('[data-action="confused"]')?.addEventListener('click', async () => {
        await api('/ai/feedback', { method: 'POST', body: JSON.stringify({ knowledgeCode: payloadReq.knowledgeCode, knowledgeName: payloadReq.knowledgeName, grade: payloadReq.grade, subject: payloadReq.subject, chapter: payloadReq.chapter, explainType: 'dialog', module: key, understood: false, note: `模块没懂：${key}` }) });
        playUiSound('try'); showToast(`💪 没关系，再听一遍！`);
      });
    };

    try {
      await streamExplainRequest(payloadReq, async (event, dataEvt) => {
        if (event === 'module') {
          const { key, value } = dataEvt;
          await setModuleText(key, value);
          body.scrollTop = body.scrollHeight;
        }
        if (event === 'done') {
          loadingDiv.classList.remove('loading');
          loadingDiv.querySelector('.explain-title').textContent = data.knowledgeName || 'AI讲解';
          loadingDiv.querySelector('.explain-meta').textContent = '🎉 讲解完成！';
          const nextWrap = document.createElement('div');
          nextWrap.className = 'explain-next-block';
          nextWrap.innerHTML = `
            <div class="explain-feedback-title">下一步</div>
            <div class="explain-next-actions">
              <button type="button" class="chip explain-chip" data-next="knowledge">继续下一个知识点</button>
              <button type="button" class="chip explain-chip" data-next="quiz">去做真题测试</button>
            </div>`;
          nextWrap.querySelector('[data-next="knowledge"]')?.addEventListener('click', () => showToast('继续下一个知识点'));
          nextWrap.querySelector('[data-next="quiz"]')?.addEventListener('click', () => showToast('去做真题测试'));
          sectionsWrap.appendChild(nextWrap);
          body.scrollTop = body.scrollHeight;
        }
        if (event === 'error') {
          addMsg(`讲解生成失败：${dataEvt.message || 'stream error'}`, true);
        }
      });
    } catch (e) {
      if (loadingDiv.parentNode) loadingDiv.remove();
      addMsg(`讲解生成失败：${e.message}`, true);
    }
  };
}

function initDefaultVoice() {
  explainVoice.voiceKey = 'zh-cn-female';
  explainVoice.voiceName = 'Flo (中文（中国大陆）)';
  explainVoice.voiceLang = 'zh-CN';
}

async function bootstrap() {
  initDefaultVoice();
  setupCommonHandlers();
  await refreshBackendStatus();
  switchTab('home');
}

bootstrap();

// ──────────────────────────────────────────────
// 真课堂播放器
// ──────────────────────────────────────────────

const demoClassroomLesson = {
  lessonId: 'DEMO_M5S1_0',
  knowledgeCode: 'M5S1-0',
  knowledgeName: '小数乘整数的计算意义',
  grade: '五年级',
  subject: '数学',
  chapter: '第一单元 小数乘法 / 1.小数乘整数',
  lessonTitle: '小数乘整数：几个相同的小数加起来',
  teacherVoiceKey: 'zh-cn-female',
  scenes: [
    {
      id:'cover', title:'小数乘整数', subtitle:'今天的新知识：小数乘整数',
      keyText:'新知识',
      visual:'🎒', narration:'今天我们来学一个新知识：小数乘整数。',
      teacherSpeech:'今天我们来学一个新知识：小数乘整数。',
      interactiveHint:'先想一想：你见过 0.5 × 3 吗？',
      durationSec: 6,
      visualSpec: { kind:'stage', background:'blackboard', elements:[
        { id:'e1', type:'emoji', value:'🏠', x:30,  y:25, w:65, h:65, fontSize:55, anim:'bounce-in', delayMs:0,   durationMs:600 },
        { id:'e2', type:'emoji', value:'👦', x:120, y:35, w:55, h:55, fontSize:45, anim:'bounce-in', delayMs:200, durationMs:600 },
        { id:'e3', type:'emoji', value:'🏪', x:210, y:20, w:70, h:70, fontSize:55, anim:'pop',       delayMs:450, durationMs:500 },
        { id:'e4', type:'emoji', value:'🍬', x:280, y:45, w:50, h:50, fontSize:40, anim:'bounce-in', delayMs:700, durationMs:500 },
        { id:'e5', type:'text',  value:'开始', x:150, y:110, w:60, h:28, fontSize:18, color:'chalk-yellow', anim:'fade-in', delayMs:1000, durationMs:500 }
      ] }
    },
    {
      id:'intro', title:'买棒棒糖', subtitle:'买 3 支棒棒糖，每支 0.5 元，一共要多少钱？',
      keyText:'3 × 0.5',
      visual:'🍭', narration:'小明去糖果店买棒棒糖。每支棒棒糖 0.5 元，他想买 3 支。小朋友，你能帮小明算算一共要花多少钱吗？',
      teacherSpeech:'小明去糖果店买棒棒糖。每支棒棒糖 0.5 元，他想买 3 支。小朋友，你能帮小明算算一共要花多少钱吗？',
      interactiveHint:'3 支棒棒糖，每支 0.5 元。',
      durationSec: 7,
      visualSpec: { kind:'stage', background:'blackboard', elements:[
        { id:'e1', type:'emoji', value:'🍭', x:60,  y:40, w:60, h:60, fontSize:50, anim:'pop',       delayMs:0,    durationMs:400 },
        { id:'e2', type:'emoji', value:'🍭', x:150, y:40, w:60, h:60, fontSize:50, anim:'pop',       delayMs:300,  durationMs:400 },
        { id:'e3', type:'emoji', value:'🍭', x:240, y:40, w:60, h:60, fontSize:50, anim:'pop',       delayMs:600,  durationMs:400 },
        { id:'e4', type:'shape', value:'', x:40, y:110, w:280, h:2, fontSize:0, color:'chalk-blue', anim:'draw', delayMs:900, durationMs:600 },
        { id:'e5', type:'formula', value:'?', x:170, y:105, w:30, h:30, fontSize:22, color:'chalk-yellow', anim:'pulse', delayMs:1500, durationMs:1000 }
      ] }
    },
    {
      id:'explain', title:'乘法的意思', subtitle:'0.5 × 3 表示 3 个 0.5 相加',
      keyText:'3 个 0.5',
      visual:'0.5 × 3', narration:'0.5 × 3 就是把 3 个 0.5 加起来。就像 3 颗糖果，每颗 0.5 元，加在一起算总价。',
      teacherSpeech:'0.5 × 3 就是把 3 个 0.5 加起来。就像 3 颗糖果，每颗 0.5 元，加在一起算总价。',
      interactiveHint:'请跟着读一遍：3 个 0.5 相加。',
      durationSec: 8,
      visualSpec: { kind:'stage', background:'blackboard', elements:[
        { id:'e1', type:'emoji', value:'🍭', x:40,  y:35, w:50, h:50, fontSize:42, anim:'bounce-in',     delayMs:0,    durationMs:500 },
        { id:'e2', type:'text',  value:'+', x:100, y:42, w:30, h:30, fontSize:20, color:'chalk-yellow', anim:'pop',       delayMs:400,  durationMs:400 },
        { id:'e3', type:'emoji', value:'🍭', x:140, y:35, w:50, h:50, fontSize:42, anim:'bounce-in',     delayMs:600,  durationMs:500 },
        { id:'e4', type:'text',  value:'+', x:200, y:42, w:30, h:30, fontSize:20, color:'chalk-yellow', anim:'pop',       delayMs:1000, durationMs:400 },
        { id:'e5', type:'emoji', value:'🍭', x:240, y:35, w:50, h:50, fontSize:42, anim:'bounce-in',     delayMs:1200, durationMs:500 },
        { id:'e6', type:'arrow',  value:'↓', x:165, y:85, w:30, h:30, fontSize:22, color:'chalk-blue', anim:'fade-in', delayMs:1600, durationMs:500 }
      ] }
    },
    {
      id:'example', title:'算出答案', subtitle:'3 个 0.5 相加等于 1.5',
      keyText:'= 1.5',
      visual:'1.5', narration:'三个 0.5 加起来，等于 1.5。所以 0.5 × 3 就等于 1.5 元。小明买 3 颗糖果需要 1 元 5 角。',
      teacherSpeech:'三个 0.5 加起来，等于 1.5。所以 0.5 × 3 就等于 1.5 元。小明买 3 颗糖果需要 1 元 5 角。',
      interactiveHint:'想一想 0.2 × 4 等于多少？',
      durationSec: 8,
      visualSpec: { kind:'stage', background:'blackboard', elements:[
        { id:'e1', type:'emoji', value:'🍭', x:30,  y:20, w:45, h:45, fontSize:38, anim:'slide-in-left', delayMs:0,    durationMs:500 },
        { id:'e2', type:'text',  value:'+', x:80, y:25, w:25, h:30, fontSize:18, color:'chalk-yellow', anim:'pop',       delayMs:300,  durationMs:400 },
        { id:'e3', type:'emoji', value:'🍭', x:110, y:20, w:45, h:45, fontSize:38, anim:'slide-in-left', delayMs:500,  durationMs:500 },
        { id:'e4', type:'text',  value:'+', x:160, y:25, w:25, h:30, fontSize:18, color:'chalk-yellow', anim:'pop',       delayMs:700,  durationMs:400 },
        { id:'e5', type:'emoji', value:'🍭', x:190, y:20, w:45, h:45, fontSize:38, anim:'slide-in-left', delayMs:900,  durationMs:500 },
        { id:'e6', type:'text',  value:'=', x:245, y:25, w:25, h:30, fontSize:20, color:'chalk-yellow', anim:'pop',       delayMs:1200, durationMs:400 },
        { id:'e7', type:'formula', value:'1.5', x:150, y:85, w:80, h:42, fontSize:28, color:'chalk-yellow', anim:'bounce-in', delayMs:1500, durationMs:600 },
        { id:'e8', type:'emoji',   value:'✨', x:240, y:90, w:40, h:40, fontSize:32, anim:'pop',           delayMs:2000, durationMs:500 }
      ] }
    },
  ],
  quiz: [
    { id:'quiz-1', sceneId:'example', prompt:'1.2 × 4 表示什么？', options:['1.2 + 4','4 个 1.2 相加','1.2 乘 4 再加 1','4 个 2 相加'], answerIndex:1, explanation:'乘法表示几个相同加数的和。' }
  ],
  summary: { oneLine: '小数乘整数，就是几个相同小数相加。', corePoints:['0.5 × 3 表示 3 个 0.5 相加。','乘法表示几个相同加数的和。','先想意思，再写算式，再算结果。'], commonMistakes:['把 0.5 × 3 看成 0.5 + 3。','只会算结果，不知道表示什么。'] },
  nextStep: { mode: 'quiz', label: '去做下一题' }
};

const classroomState = {
  lesson: null,
  sceneIndex: 0,
  quizIndex: 0,
  playing: false,
  busy: false,
  playToken: 0,
};

function normalizeClassroomScenesAdv(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.scenes)) return payload.scenes;
  const anim = payload?.animationJson || payload?.animation;
  if (Array.isArray(anim)) return anim;
  if (Array.isArray(anim?.scenes)) return anim.scenes;
  return [];
}

function normalizeClassroomQuiz(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.quiz)) return payload.quiz;
  if (Array.isArray(payload?.questions)) return payload.questions;
  return [];
}

function defaultClassmatesForScene(scene, name) {
  return [
    { id: 'studentA', name: '小认真', voiceKey: 'zh-cn-male', speech: scene?.subtitle ? `我来总结：${scene.subtitle}` : `这一段讲的是「${scene?.title || name}」，我记住了。` },
    { id: 'studentB', name: '小好奇', voiceKey: 'zh-cn-female', speech: scene?.interactiveHint || '为什么会这样？我还想再想一想。' },
  ];
}

async function loadClassroomTtsAudio(text, voiceKey) {
  try {
    const res = await api('/ai/tts', { method: 'POST', body: JSON.stringify({ text, voiceKey: voiceKey || 'zh-cn-female' }) });
    if (!res?.ok || !res.audioBase64) return null;
    const mime = res.mimeType || res.audioMimeType || 'audio/mpeg';
    const bytes = atob(res.audioBase64);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    return URL.createObjectURL(new Blob([arr], { type: mime }));
  } catch { return null; }
}

function playClassroomAudio(url) {
  if (!url) return Promise.resolve();
  return new Promise(resolve => {
    const a = new Audio(url);
    a.onended = resolve; a.onerror = resolve;
    a.play().catch(resolve);
  });
}

async function runClassroomScene(token) {
  const lesson = classroomState.lesson;
  const scenes = normalizeClassroomScenesAdv(lesson);
  const scene = scenes[classroomState.sceneIndex];
  if (!lesson || !scene) return;
  if (token !== classroomState.playToken) return;

  const teacherText = scene.teacherSpeech || scene.narration || scene.title || '';
  const audioUrl = await loadClassroomTtsAudio(teacherText, lesson.teacherVoiceKey || 'zh-cn-female');
  await playClassroomAudio(audioUrl);
  if (token !== classroomState.playToken || !classroomState.playing) return;

  const mates = scene.aiClassmates?.length ? scene.aiClassmates : defaultClassmatesForScene(scene, lesson.knowledgeName);
  for (const cm of mates.slice(0, 2)) {
    const cmUrl = await loadClassroomTtsAudio(cm.speech || '', cm.voiceKey || 'zh-cn-female');
    await playClassroomAudio(cmUrl);
    if (token !== classroomState.playToken || !classroomState.playing) return;
  }

  await new Promise(resolve => setTimeout(resolve, Math.max(1800, (scene.durationSec || 6) * 1000)));
  if (token !== classroomState.playToken || !classroomState.playing) return;

  if (classroomState.sceneIndex < scenes.length - 1) {
    classroomState.sceneIndex += 1;
    renderClassroomPlayer();
    await runClassroomScene(token);
  } else {
    classroomState.playing = false;
    renderClassroomPlayer();
  }
}


function renderClassroomVisualSpec(scene){
  try {
    const spec = scene && scene.visualSpec;
    if (!spec || !Array.isArray(spec.elements) || !spec.elements.length){
      const emoji = (scene && (scene.visual || '🎬')) || '🎬';
      const key = (scene && (scene.keyText || '')) || '';
      const shortKey = String(key).slice(0, 6);
      return `<div class="board-canvas-wrap"><div class="board-fallback"><div class="fb-emoji">${emoji}</div>${shortKey?`<div class="fb-key">${shortKey}</div>`:''}</div></div>`;
    }
    const escape = (v) => String(v == null ? '' : v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    // 关键短词截断：text 元素最多 6 字
    const parts = spec.elements.map(el => {
      const x = Number(el.x)||0;
      const y = Number(el.y)||0;
      const w = Number(el.w)||60;
      const h = Number(el.h)||24;
      // 减小黑板字体，避免文字过大
      const fs = Math.min(Number(el.fontSize)||16, 20);
      const color = String(el.color || 'chalk-white');
      const anim = String(el.anim || 'fade-in');
      const delay = Number(el.delayMs)||0;
      const dur = Number(el.durationMs)||450;
      let raw = String(el.value == null ? '' : el.value);
      const type = String(el.type || 'text');
      if (type === 'text' && raw.length > 6) raw = raw.slice(0, 6);
      if (type === 'formula' && raw.length > 14) raw = raw.slice(0, 14);
      const val = escape(raw);
      const style = `left:${x}px;top:${y}px;width:${w}px;height:${h}px;font-size:${fs}px;animation:bb-${anim} ${dur}ms ease ${delay}ms both;`;
      const cls = `bb-el bb-${type} chalk-${color}`;
      return `<div class="${cls}" style="${style}">${val}</div>`;
    }).join('');
    return `<div class="board-canvas-wrap" data-bb-canvas="1"><div class="board-canvas" style="width:360px;height:146px;">${parts}</div></div>`;
  } catch (e) {
    return `<div class="board-canvas-wrap"><div class="board-fallback"><div class="fb-emoji">🎬</div></div></div>`;
  }
}

function fitClassroomCanvas(){
  document.querySelectorAll('.classroom-board .board-canvas-wrap[data-bb-canvas]').forEach(wrap => {
    const canvas = wrap.querySelector('.board-canvas');
    if (!canvas) return;
    const w = wrap.clientWidth || 360;
    const h = wrap.clientHeight || 146;
    const scale = Math.min(1, w / 360, h / 146);
    canvas.style.transformOrigin = 'top left';
    canvas.style.transform = `scale(${scale.toFixed(4)})`;
    canvas.style.left = `${Math.max(0, (w - 360 * scale) / 2)}px`;
    canvas.style.top = `${Math.max(0, (h - 146 * scale) / 2)}px`;
    canvas.style.position = 'absolute';
  });
}
window.addEventListener('resize', () => { try { fitClassroomCanvas(); } catch {} }, { passive: true });

function renderClassroomPlayer() {
  const wrap = document.getElementById('classroomWrap');
  if (!wrap) return;
  const lesson = classroomState.lesson;
  const scenes = normalizeClassroomScenesAdv(lesson);
  const quizzes = normalizeClassroomQuiz(lesson?.quiz);
  const scene = scenes[classroomState.sceneIndex] || null;
  const summary = lesson?.summary || {};
  const nextStep = lesson?.nextStep || {};
  const mates = scene ? (scene.aiClassmates?.length ? scene.aiClassmates : defaultClassmatesForScene(scene, lesson?.knowledgeName)) : [];
  const progress = scenes.length ? Math.round(((classroomState.sceneIndex + 1) / scenes.length) * 100) : 0;
  const teacherSubtitle = scene?.teacherSpeech || scene?.narration || '';

  if (!lesson) {
    wrap.innerHTML = `<div class="classroom-shell"><div class="classroom-stage"><div class="glass card" style="padding:32px;text-align:center;">
      <div style="font-size:32px;margin-bottom:16px;">🏫</div>
      <div style="font-weight:900;font-size:18px;margin-bottom:8px;">真课堂播放器</div>
      <div class="detail-muted">从知识树进入知识点，点击「进入课堂模式」即可开始</div>
    </div>`;
    return;
  }

  wrap.innerHTML = `
    <div class="glass card classroom-control-card">
      <div class="classroom-control-head">
        <div class="classroom-control-title">🏫 ${lesson.lessonTitle || lesson.knowledgeName || '真课堂'}</div>
        <div class="classroom-control-sub">${lesson.grade || ''} · ${lesson.subject || ''} · ${lesson.chapter || ''}</div>
      </div>
      <div class="classroom-metrics">
        <button type="button" class="classroom-metric">场景 ${scenes.length}</button>
        <button type="button" class="classroom-metric">题 ${quizzes.length}</button>
        <button type="button" class="classroom-metric">${classroomState.sceneIndex + 1}/${Math.max(scenes.length,1)}</button>
        <button type="button" class="classroom-metric">${classroomState.playing ? '播放中' : '已暂停'}</button>
      </div>
      <div class="classroom-progress-row">
        <div class="classroom-dots">
          ${scenes.map((_, i) => `<span class="dot${i===classroomState.sceneIndex?' active':''}"></span>`).join('')}
        </div>
        <div class="classroom-progress-bar"><div style="width:${progress}%"></div></div>
        <div class="classroom-progress-text">${classroomState.sceneIndex + 1}/${Math.max(scenes.length,1)} · ${progress}%</div>
      </div>
      <div class="classroom-controls">
        <button type="button" class="ctrl-btn" id="cr_prev">⏮</button>
        <button type="button" class="ctrl-btn primary" id="cr_play">${classroomState.playing ? '⏸' : '▶'}</button>
        <button type="button" class="ctrl-btn" id="cr_next">⏭</button>
        <button type="button" class="ctrl-btn" id="cr_replay">↻</button>
        <button type="button" class="ctrl-btn warn" id="cr_finish">✅</button>
      </div>
    </div>

    <div class="glass card classroom-board">
      ${scene ? `
        <div class="board-inner">
          <div class="board-content">
            <div class="board-head">
              <span class="scene-index">${classroomState.sceneIndex + 1}/${Math.max(scenes.length,1)}</span>
              <span class="scene-title">${scene.title || `场景 ${classroomState.sceneIndex + 1}`}</span>
            </div>
            ${renderClassroomVisualSpec(scene)}
          </div>
          <div class="board-subtitle-bar">
            <div class="board-avatar">👩‍🏫</div>
            <div class="board-subtitle-text"><b>芽芽老师：</b>${teacherSubtitle}</div>
          </div>
        </div>
      ` : `<div class="empty" style="color:#fff;">暂无场景</div>`}
    </div>

    <div class="grid-two classroom-bottom-grid" style="margin-top:8px;grid-template-columns:1fr 1fr;align-items:start;">
      <div class="glass card" style="padding:8px;min-height:72px;">
        <div class="detail-title">📚 总结</div>
        <div style="line-height:1.8;margin-top:8px;">${summary.oneLine || summary.summary || lesson.lessonTitle || lesson.knowledgeName || ''}</div>
        <div style="margin-top:10px;color:var(--muted);font-size:12px;">下一步：${nextStep.label || nextStep.mode || '继续学习'}</div>
      </div>
      <div class="glass card" style="padding:8px;min-height:72px;">
        <div class="detail-title">👩‍🏫 老师</div>
        <div style="line-height:1.8;margin-top:8px;">${scene ? (scene.teacherSpeech || scene.narration || '') : ''}</div>
      </div>
    </div>

    <div class="glass card" style="padding:8px;margin-top:10px;">
      <div class="detail-title">💬 同学</div>
      <div style="display:flex;flex-direction:column;gap:12px;margin-top:12px;">
        ${mates.map((m, mi) => `<div style="display:flex;align-items:flex-start;gap:10px;${mi%2===1 ? 'flex-direction:row-reverse;' : ''}">
          <div style="min-width:36px;height:36px;border-radius:50%;background:${mi%2===0 ? 'rgba(85,239,255,.2)' : 'rgba(162,155,254,.2)'};display:flex;align-items:center;justify-content:center;font-size:18px;">${mi%2===0 ? '🧒' : '👧'}</div>
          <div style="flex:1;background:${mi%2===0 ? 'rgba(85,239,255,.08)' : 'rgba(162,155,254,.08)'};border-radius:14px;padding:10px 14px;${mi%2===1 ? 'text-align:right;' : ''}">
            <strong style="font-size:12px;color:${mi%2===0 ? 'var(--cyan)' : '#a29bfe'};">${m.name}</strong>
            <div style="margin-top:4px;line-height:1.35;font-size:10px;">${m.speech || ''}</div>
          </div>
        </div>`).join('')}
      </div>
    </div>

    <div class="glass card" style="padding:16px;margin-top:16px;" id="cr_quizPanel">
      <div class="detail-title">⚡ 题目 ${quizzes.length ? `${classroomState.quizIndex + 1}/${quizzes.length}` : '0/0'}</div>
      ${quizzes.length ? (() => {
        const q = quizzes[classroomState.quizIndex] || quizzes[0];
        const opts = Array.isArray(q.options) ? q.options : [];
        return `<div style="line-height:1.8;margin-top:8px;font-size:15px;">${q.prompt || ''}</div>
        <div style="display:flex;flex-direction:column;gap:8px;margin-top:12px;">
          ${opts.map((opt, i) => `<button type="button" class="chip" data-qidx="${i}" style="text-align:left;padding:7px 9px;font-size:10px;line-height:1.2;white-space:normal;">${opt}</button>`).join('')}
        </div>
        <div id="cr_quizFeedback" style="margin-top:8px;color:var(--muted);">请选择答案</div>`;
      })() : '<div class="empty" style="margin-top:8px;">暂无互动题</div>'}
    </div></div></div>  `;

  const replay = () => { classroomState.sceneIndex = 0; classroomState.quizIndex = 0; classroomState.playing = false; classroomState.playToken += 1; renderClassroomPlayer(); };
  try { fitClassroomCanvas(); requestAnimationFrame(() => { try { fitClassroomCanvas(); } catch {} }); } catch {}
  document.getElementById('cr_replay')?.addEventListener('click', replay);
  document.getElementById('cr_prev')?.addEventListener('click', () => {
    classroomState.sceneIndex = Math.max(0, classroomState.sceneIndex - 1);
    classroomState.playing = false; classroomState.playToken += 1;
    renderClassroomPlayer();
  });
  document.getElementById('cr_next')?.addEventListener('click', () => {
    classroomState.sceneIndex = Math.min(scenes.length - 1, classroomState.sceneIndex + 1);
    classroomState.playToken += 1;
    renderClassroomPlayer();
    if (classroomState.playing) runClassroomScene(classroomState.playToken).catch(() => {});
  });
  document.getElementById('cr_play')?.addEventListener('click', () => {
    classroomState.playing = !classroomState.playing;
    classroomState.playToken += 1;
    renderClassroomPlayer();
    if (classroomState.playing) runClassroomScene(classroomState.playToken).catch(() => {});
  });
  document.getElementById('cr_finish')?.addEventListener('click', async () => {
    classroomState.playing = false; classroomState.playToken += 1;
    const fin = await api('/ai/classroom/finish', { method: 'POST', body: JSON.stringify({
      lessonId: lesson.lessonId || lesson.id,
      userId: appState.currentUserId || 'demo-student',
      knowledgeCode: lesson.knowledgeCode,
      knowledgeName: lesson.knowledgeName,
      isCompleted: true,
    }) }).catch(() => ({ masteryDelta: 0 }));
    showToast(`课堂完成 · mastery +${fin.masteryDelta || 0}`);
    renderClassroomPlayer();
  });
  document.querySelectorAll('[data-qidx]').forEach(btn => btn.addEventListener('click', async () => {
    const idx = Number(btn.getAttribute('data-qidx'));
    const q = quizzes[classroomState.quizIndex] || quizzes[0];
    const correct = idx === (q.answerIndex ?? 0);
    const fb = document.getElementById('cr_quizFeedback');
    document.querySelectorAll('[data-qidx]').forEach((b, bi) => {
      b.disabled = true;
      b.style.background = bi === (q.answerIndex ?? 0) ? 'rgba(0,230,118,.25)' : (bi === idx && !correct ? 'rgba(255,71,87,.2)' : '');
      b.style.borderColor = bi === (q.answerIndex ?? 0) ? '#00e676' : (bi === idx && !correct ? '#ff4757' : '');
    });
    if (fb) {
      fb.textContent = correct ? '✅ 答对了！继续加油！' : '❌ 再想一想，' + (q.explanation || '回到场景重新理解。');
      fb.style.color = correct ? '#00e676' : '#ff4757';
      fb.style.fontWeight = '900';
    }
    await api('/ai/classroom/response', { method: 'POST', body: JSON.stringify({
      lessonId: lesson.lessonId || lesson.id, sceneId: q.sceneId || 'quiz',
      userId: appState.currentUserId || 'demo-student', answer: correct ? 'right' : 'bad',
    }) }).catch(() => {});
    if (correct) {
      await new Promise(r => setTimeout(r, 900));
      if (classroomState.quizIndex < quizzes.length - 1) {
        classroomState.quizIndex += 1; renderClassroomPlayer();
        document.getElementById('cr_quizPanel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        if (fb) fb.textContent = '🎉 所有题目已完成！课堂结束，记得复习！';
      }
    }
  }));
}




async function initClassroomPage() {
  // 强制使用 demoClassroomLesson，不从后端加载
  classroomState.lesson = demoClassroomLesson;
  classroomState.sceneIndex = 0; classroomState.quizIndex = 0;
  classroomState.playing = false; classroomState.playToken += 1;
  renderClassroomPlayer();
  return;
  // const selectedId = window.__selectedClassroomLessonId || demoClassroomLesson.lessonId;
  // const preferPayload = window.__selectedClassroomLessonPayload || demoClassroomLesson;
  // if (selectedId && preferPayload?.lessonId === selectedId) {
  //   classroomState.lesson = preferPayload;
  //   classroomState.sceneIndex = 0; classroomState.quizIndex = 0;
  //   classroomState.playing = false; classroomState.playToken += 1;
  //   window.__selectedClassroomLessonPayload = null;
  //   renderClassroomPlayer();
  //   return;
  // }
  // if (selectedId) {
  //   try {
  //     const lesson = await api(`/ai/classroom/replay/${encodeURIComponent(selectedId)}`);
  //     classroomState.lesson = lesson;
  //     classroomState.sceneIndex = 0; classroomState.quizIndex = 0;
  //     classroomState.playing = false; classroomState.playToken += 1;
  //     window.__selectedClassroomLessonPayload = null;
  //     renderClassroomPlayer();
  //   } catch { renderClassroomPlayer(); }
  //   return;
  // }
  // renderClassroomPlayer();
}
