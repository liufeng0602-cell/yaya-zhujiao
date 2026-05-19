import { api } from '../../api/client.js';
import { renderImportResults } from './import-results.js';
import { setLoading, setPageLoading } from '../../components/loading.js';
import { toast } from '../../components/toast.js';

export async function initAdminPage(state) {
  const registerBtn = document.getElementById('registerBtn');
  const importContentBtn = document.getElementById('importContentBtn');
  const importKnowledgeBtn = document.getElementById('importKnowledgeBtn');
  const importQuestionBtn = document.getElementById('importQuestionBtn');
  const genExplainBtn = document.getElementById('genExplainBtn');
  const saveExplainBtn = document.getElementById('saveExplainBtn');
  const genQuestionBtn = document.getElementById('genQuestionBtn');
  const saveQuestionBtn = document.getElementById('saveQuestionBtn');
  const refreshBtn = document.getElementById('refreshBtn');
  const batchWarmBtn = document.getElementById('batchWarmBtn');

  const run = async (btn, fn, label) => {
    try {
      setLoading(btn.id, true, '处理中...');
      setPageLoading(true, label);
      const result = await fn();
      renderImportResults({ title: label, result });
      toast(`${label} 成功`, 'success');
      await loadAdminData(state);
      return result;
    } catch (e) {
      renderImportResults({ title: label, error: e.message });
      toast(`${label} 失败：${e.message}`, 'error');
      throw e;
    } finally {
      setLoading(btn.id, false);
      setPageLoading(false);
    }
  };

  registerBtn.onclick = () => run(registerBtn, async () => {
    const body = collectForm(['regName','regEmail','regPassword','regGrade','regProvince','regCity','regTextbook','regTargetGrade']);
    const result = await api.register({
      name: body.regName || '北北',
      email: body.regEmail || 'parent@example.com',
      password: body.regPassword || '12345678',
      grade: body.regGrade || '五年级',
      province: body.regProvince || '浙江',
      city: body.regCity || '杭州',
      textbookVersion: body.regTextbook || '浙教版',
      targetGrade: body.regTargetGrade || '六年级'
    });
    state.currentUser = result.user;
    state.currentUserId = result.user.id;
    return result;
  }, '注册 / 初始化');

  importContentBtn.onclick = () => run(importContentBtn, async () => {
    const body = collectForm(['contentTitle','contentSourceName','contentType','contentSubject','contentGrade','contentChapter','contentKnowledge','contentBody']);
    return api.importContent({
      title: body.contentTitle,
      body: body.contentBody,
      sourceName: body.contentSourceName,
      contentType: body.contentType || 'textbook',
      subject: body.contentSubject,
      grade: body.contentGrade,
      chapter: body.contentChapter,
      knowledgeCode: body.contentKnowledge
    });
  }, '内容导入');

  importKnowledgeBtn.onclick = () => run(importKnowledgeBtn, async () => {
    const body = collectForm(['knowledgeCode','knowledgeStage','knowledgeGrade','knowledgeSubject','knowledgeChapter','knowledgeName','knowledgeObjective','knowledgeRequirement','knowledgeParent','knowledgePrereqs','knowledgeTags']);
    return api.importKnowledge({
      code: body.knowledgeCode,
      stage: body.knowledgeStage,
      grade: body.knowledgeGrade,
      subject: body.knowledgeSubject,
      chapter: body.knowledgeChapter,
      name: body.knowledgeName,
      objective: body.knowledgeObjective,
      syllabusRequirement: body.knowledgeRequirement,
      parentCode: body.knowledgeParent || undefined,
      prereqCodes: safeJson(body.knowledgePrereqs, []),
      tags: safeJson(body.knowledgeTags, [])
    });
  }, '知识图谱导入');

  importQuestionBtn.onclick = () => run(importQuestionBtn, async () => {
    const body = collectForm(['questionPrompt','questionAnswerIndex','questionDifficulty','questionKnowledge','questionSubject','questionGrade','questionChapter','questionSourceType','questionExplanation','questionAbility','questionErrorTag','questionTags','questionChoices']);
    return api.importQuestions([{ 
      prompt: body.questionPrompt,
      choices: safeJson(body.questionChoices, []),
      answerIndex: Number(body.questionAnswerIndex || 0),
      explanation: body.questionExplanation,
      difficulty: body.questionDifficulty || 'easy',
      knowledgeCode: body.questionKnowledge,
      subject: body.questionSubject,
      grade: body.questionGrade,
      chapter: body.questionChapter,
      sourceType: body.questionSourceType || 'manual',
      sourceName: 'manual-import',
      abilityTag: body.questionAbility,
      errorTag: body.questionErrorTag,
      tags: safeJson(body.questionTags, [])
    }]);
  }, '题库导入');

  genExplainBtn.onclick = () => run(genExplainBtn, async () => api.genExplain(readAiPayload()), '生成讲解');
  saveExplainBtn.onclick = () => run(saveExplainBtn, async () => api.saveExplain(readAiPayload()), '生成并保存讲解');
  genQuestionBtn.onclick = () => run(genQuestionBtn, async () => api.genQuestions(readAiQuestionPayload()), '生成题目');
  saveQuestionBtn.onclick = () => run(saveQuestionBtn, async () => api.saveQuestions(readAiQuestionPayload()), '生成并保存题目');
  refreshBtn.onclick = () => run(refreshBtn, async () => loadAdminData(state), '刷新联调数据');
  if (batchWarmBtn) batchWarmBtn.onclick = () => run(batchWarmBtn, async () => {
    const knowledge = await api.knowledge();
    const items = (knowledge || []).filter(item => item.grade === state.grade && item.subject === state.subject).slice(0, 6).map(item => ({
      knowledgeCode: item.code || item.id || item.knowledgeCode,
      knowledgeName: item.name || item.topic || item.knowledgeName || item.code,
      grade: item.grade,
      subject: item.subject,
      chapter: item.chapter || item.level || '',
      userId: state.currentUserId || 'demo-student',
    }));
    return api.classroomPrewarmBatch({ userId: state.currentUserId || 'demo-student', items });
  }, '批量预热课堂');

  await loadAdminData(state);
}

function collectForm(ids) {
  return ids.reduce((acc, id) => ({ ...acc, [id]: document.getElementById(id)?.value || '' }), {});
}

function safeJson(value, fallback) {
  try { return value ? JSON.parse(value) : fallback; } catch { return fallback; }
}

function readAiPayload() {
  const body = collectForm(['aiKnowledgeCode','aiKnowledgeName','aiSubject','aiGrade','aiChapter','aiStyle']);
  return {
    knowledgeCode: body.aiKnowledgeCode,
    knowledgeName: body.aiKnowledgeName,
    subject: body.aiSubject,
    grade: body.aiGrade,
    chapter: body.aiChapter,
    style: body.aiStyle || 'dialog'
  };
}

function readAiQuestionPayload() {
  const body = collectForm(['aiKnowledgeCode','aiKnowledgeName','aiSubject','aiGrade','aiQuestionDifficulty','aiQuestionCount','aiQuestionType','aiAbilityTag']);
  return {
    knowledgeCode: body.aiKnowledgeCode,
    knowledgeName: body.aiKnowledgeName,
    subject: body.aiSubject,
    grade: body.aiGrade,
    difficulty: body.aiQuestionDifficulty || 'easy',
    count: Number(body.aiQuestionCount || 3),
    questionType: body.aiQuestionType || 'choice',
    abilityTag: body.aiAbilityTag || 'understanding'
  };
}

async function loadAdminData(state) {
  const [user, membership, content, knowledge, questions, reports, classroomStats, classroomTasks, classroomPackages] = await Promise.allSettled([
    state.currentUserId ? api.me(state.currentUserId) : Promise.resolve(null),
    state.currentUserId ? api.membership(state.currentUserId) : Promise.resolve(null),
    api.content(state.currentUserId ? `?userId=${encodeURIComponent(state.currentUserId)}` : ''),
    api.knowledge(),
    api.questions(),
    state.currentUserId ? api.reports(state.currentUserId) : Promise.resolve([]),
    api.classroomStats().catch(() => ({ total: 0, ready: 0, pending: 0, failed: 0 })),
    api.classroomTasks().catch(() => []),
    api.classroomList().catch(() => []),
  ]);

  if (user.status === 'fulfilled' && user.value) {
    state.currentUser = user.value;
    document.getElementById('currentUserLabel').textContent = `${user.value.name} · ${user.value.email}`;
    document.getElementById('adminCurrentUser').textContent = `${user.value.name} (${user.value.role})`;
  }
  if (membership.status === 'fulfilled' && membership.value) {
    document.getElementById('adminMembership').textContent = membership.value.memberStatus || '-';
    document.getElementById('adminTrialEnd').textContent = membership.value.trialEndAt || '-';
    document.getElementById('adminExpireAt').textContent = membership.value.memberExpireAt || '-';
  }
  renderLists({
    content: content.status === 'fulfilled' ? content.value : [],
    knowledge: knowledge.status === 'fulfilled' ? knowledge.value : [],
    questions: questions.status === 'fulfilled' ? questions.value : [],
    reports: reports.status === 'fulfilled' ? reports.value : [],
  });
  renderClassroomPanel({
    stats: classroomStats.status === 'fulfilled' ? classroomStats.value : { total: 0, ready: 0, pending: 0, failed: 0 },
    tasks: classroomTasks.status === 'fulfilled' ? classroomTasks.value : [],
    packages: classroomPackages.status === 'fulfilled' ? classroomPackages.value : [],
    state,
  });
}

function renderLists({ content, knowledge, questions, reports }) {
  const contentList = document.getElementById('contentList');
  const questionList = document.getElementById('questionList');
  const knowledgeList = document.getElementById('knowledgeList');
  const reportList = document.getElementById('reportList');
  if (contentList) contentList.innerHTML = (content || []).slice(0, 8).map(item => itemCard(item.title, `${item.contentType || 'content'} · ${item.rightsStatus || 'draft'} · ${item.subject || ''}`)).join('') || emptyCard('暂无内容');
  if (questionList) questionList.innerHTML = (questions || []).slice(0, 8).map(item => itemCard(item.prompt, `${item.difficulty} · ${item.knowledgeName || item.knowledgeCode || ''}`)).join('') || emptyCard('暂无题目');
  if (knowledgeList) knowledgeList.innerHTML = (knowledge || []).slice(0, 8).map(item => itemCard(item.topic || item.name || item.code, item.description || item.objective || '')).join('') || emptyCard('暂无知识图谱');
  if (reportList) reportList.innerHTML = (reports || []).slice(0, 8).map(item => itemCard(item.reportTitle || '报告', `得分 ${item.score}/${item.totalScore} · 正确率 ${item.accuracy || 0}%`)).join('') || emptyCard('暂无报告');
}


function renderClassroomPanel({ stats, tasks, packages, state }) {
  const anchor = document.getElementById('knowledgeList')?.parentElement || document.getElementById('reportList')?.parentElement;
  if (!anchor) return;
  let panel = document.getElementById('classroomPanel');
  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'classroomPanel';
    panel.className = 'glass';
    panel.style.padding = '16px';
    panel.style.marginTop = '16px';
    anchor.parentElement?.appendChild(panel);
  }
  const statsHtml = `
    <div class="stat-card"><strong>${stats.total || 0}</strong><span>课堂包总数</span></div>
    <div class="stat-card"><strong>${stats.ready || 0}</strong><span>已就绪</span></div>
    <div class="stat-card"><strong>${stats.pending || 0}</strong><span>待生成</span></div>
    <div class="stat-card"><strong>${stats.failed || 0}</strong><span>失败</span></div>`;
  const taskHtml = (tasks || []).slice(0, 6).map(t => `<button type="button" class="list-item glass-mini classroom-task" data-task-id="${t.id}" style="width:100%;text-align:left;"><strong>${t.knowledgeName || t.knowledgeCode || '课堂任务'}</strong><p>${t.status || '-'} · ${t.mode || '-'} · ${t.errorMessage || ''}</p></button>`).join('') || emptyCard('暂无课堂任务');
  const pkgHtml = (packages || []).slice(0, 6).map(p => `<button type="button" class="list-item glass-mini classroom-pkg" data-lesson-id="${p.lessonId || p.id || ''}" style="width:100%;text-align:left;"><strong>${p.lessonTitle || p.knowledgeName || '课堂包'}</strong><p>${p.status || '-'} · ${p.engine || '-'} · ${p.updatedAt || ''}</p></button>`).join('') || emptyCard('暂无课堂包');
  panel.innerHTML = `
    <div class="section-title"><span>🏫 课堂引擎</span><div style="display:flex;gap:8px;"><button class="text-btn" id="batchWarmBtn">批量预热</button><button class="text-btn" id="classroomRefreshBtn">刷新</button></div></div>
    <div class="stats-grid">${statsHtml}</div>
    <div class="section-title"><span>任务状态</span></div>
    <div class="task-list">${taskHtml}</div>
    <div class="section-title"><span>课堂包</span></div>
    <div class="task-list">${pkgHtml}</div>
  `;
  document.getElementById('classroomRefreshBtn')?.addEventListener('click', () => loadAdminData(state));
  panel.querySelectorAll('[data-lesson-id]').forEach(el => el.addEventListener('click', async () => {
    const lessonId = el.getAttribute('data-lesson-id');
    if (!lessonId) return;
    const data = await api.classroomReplay(lessonId).catch(() => null);
    if (!data) return;
    const scenes = Array.isArray(data.scenes?.scenes) ? data.scenes.scenes : (Array.isArray(data.scenes) ? data.scenes : []);
    renderClassroomDetail(data.lessonTitle || '课堂回放', `
      <div class="detail-card"><div class="detail-title">基础信息</div><div>知识点：${data.knowledgeName || ''}</div><div>状态：${data.status || ''}</div><div>引擎：${data.engine || ''}</div></div>
      <div class="detail-card"><div class="detail-title">讲解摘要</div><div style="line-height:1.8;">${renderMiniSummary(data.explain || {})}</div></div>
      <div class="detail-card"><div class="detail-title">分镜</div><div>${scenes.map(scene => `<div class=\"scene-card\"><strong>${esc(scene.title || scene.id || '分镜')}</strong><p>${esc(scene.subtitle || '')}</p><p>${esc(scene.narration || '')}</p><div class=\"info-line\">${esc(scene.interactiveHint || '')}</div></div>`).join('')}</div></div>
    `);
  }));
  panel.querySelectorAll('[data-task-id]').forEach(el => el.addEventListener('click', async () => {
    const taskId = el.getAttribute('data-task-id');
    if (!taskId) return;
    const task = await api.classroomTaskDetail(taskId).catch(() => null);
    if (!task) return;
    renderClassroomDetail(task.knowledgeName || '课堂任务', `
      <div class="detail-card"><div class="detail-title">任务状态</div><div>状态：${task.status || ''}</div><div>模式：${task.mode || ''}</div><div>开始：${task.startedAt || ''}</div><div>结束：${task.finishedAt || ''}</div><div>知识点：${task.knowledgeCode || ''}</div></div>
      <div class="detail-card"><div class="detail-title">错误信息</div><div style="white-space:pre-wrap;line-height:1.7;">${task.errorMessage || '无'}</div></div>
      <div class="detail-card"><div class="detail-title">结果</div><div style="white-space:pre-wrap;line-height:1.7;">${task.resultJson ? JSON.stringify(task.resultJson, null, 2) : '无'}</div></div>
    `);
  }));
}


function renderClassroomDetail(title, bodyHtml) {
  let modal = document.getElementById('classroomDetailModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'classroomDetailModal';
    modal.className = 'modal show';
    modal.innerHTML = `
      <div class="modal-content glass" style="max-width:760px;max-height:80vh;overflow:auto;padding:18px;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px;">
          <strong id="classroomDetailTitle">课堂详情</strong>
          <button class="text-btn" id="classroomDetailClose">关闭</button>
        </div>
        <div id="classroomDetailBody"></div>
      </div>`;
    document.body.appendChild(modal);
    modal.querySelector('#classroomDetailClose')?.addEventListener('click', () => modal.remove());
  }
  modal.querySelector('#classroomDetailTitle').textContent = title;
  modal.querySelector('#classroomDetailBody').innerHTML = bodyHtml;
}

function itemCard(title, desc) { return `<div class="list-item glass-mini"><strong>${title}</strong><p>${desc}</p></div>`; }
function renderMiniSummary(obj) {
  if (!obj || typeof obj !== 'object') return '无';
  const parts = [];
  for (const key of ['oneLine', 'corePoints', 'whyItWorks', 'commonMistakes', 'example', 'summary', 'selfCheck']) {
    if (obj[key]) parts.push(`<div><strong>${esc(key)}</strong>：${esc(Array.isArray(obj[key]) ? obj[key].join('、') : String(obj[key]))}</div>`);
  }
  return parts.join('') || '无';
}
function emptyCard(text) { return `<div class="empty">${text}</div>`; }
