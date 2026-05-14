import { api } from '../../api/client.js';

function esc(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function normalizeScenes(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  // {scenes:[...], music, style, ...}
  if (Array.isArray(payload?.scenes)) return payload.scenes;
  // lesson top-level has animationJson nested
  const anim = payload?.animationJson || payload?.animation;
  if (Array.isArray(anim)) return anim;
  if (Array.isArray(anim?.scenes)) return anim.scenes;
  return [];
}

function normalizeQuiz(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.quiz)) return payload.quiz;
  if (Array.isArray(payload?.questions)) return payload.questions;
  return [];
}

function defaultClassmates(scene) {
  const hint = scene?.interactiveHint || scene?.narration || scene?.title || '这个知识点';
  return [
    { id: 'studentA', name: '小认真', voiceKey: 'zh-cn-male', speech: `我来总结一下：${hint}` },
    { id: 'studentB', name: '小好奇', voiceKey: 'zh-cn-female', speech: '为什么会这样？我还想再想一想。' },
  ];
}

async function loadTtsAudio(text, voiceKey = 'zh-cn-female', voiceName = '') {
  const res = await api.tts({ text, voiceKey, voiceName });
  if (!res?.ok || !res.audioBase64) return null;
  const mime = res.audioMimeType || res.mimeType || 'audio/mp4';
  const bytes = atob(res.audioBase64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i += 1) arr[i] = bytes.charCodeAt(i);
  return URL.createObjectURL(new Blob([arr], { type: mime }));
}

function playAudio(url) {
  if (!url) return Promise.resolve();
  return new Promise((resolve) => {
    const audio = new Audio(url);
    audio.onended = () => resolve();
    audio.onerror = () => resolve();
    audio.play().catch(() => resolve());
  });
}

function buildSceneVisual(scene) {
  const parts = [];
  parts.push(`<div class="scene-visual-main">${esc(scene.visual || scene.title || '🎬')}</div>`);
  if (Array.isArray(scene.elements) && scene.elements.length) {
    parts.push(`<div class="scene-elements">${scene.elements.map(el => `<div class="scene-element chip">${esc(el.label || el.value || el.type || '')}</div>`).join('')}</div>`);
  }
  return parts.join('');
}

export async function initClassroomPage(state) {
  const wrap = document.getElementById('classroomWrap');
  if (!wrap) return;

  state.classroom = state.classroom || {
    lesson: null,
    sceneIndex: 0,
    quizIndex: 0,
    playing: false,
    autoPlay: true,
    busy: false,
    playToken: 0,
  };

  async function fetchOverview() {
    const [stats, tasks, packages, knowledge] = await Promise.allSettled([
      api.classroomStats(),
      api.classroomTasks(),
      api.classroomList(),
      api.knowledge(),
    ]);
    return {
      stats: stats.status === 'fulfilled' ? stats.value : { total: 0, ready: 0, pending: 0, failed: 0 },
      tasks: tasks.status === 'fulfilled' ? tasks.value : [],
      packages: packages.status === 'fulfilled' ? packages.value : [],
      knowledge: knowledge.status === 'fulfilled' ? knowledge.value : [],
    };
  }

  async function loadLesson(lessonId, preferPayload) {
    if (preferPayload?.lessonId === lessonId) return preferPayload;
    return api.classroomReplay(lessonId);
  }

  function getActiveScene() {
    const lesson = state.classroom.lesson;
    const scenes = normalizeScenes(lesson?.scenes || lesson?.animation || lesson?.animationJson);
    return scenes[state.classroom.sceneIndex] || null;
  }

  function renderPlayer() {
    const lesson = state.classroom.lesson;
    const scenes = normalizeScenes(lesson?.scenes || lesson?.animation || lesson?.animationJson || lesson);
    const quizes = normalizeQuiz(lesson?.quiz || lesson?.questions);
    const scene = getActiveScene();
    const summary = lesson?.summary || lesson?.summaryJson || {};
    const nextStep = lesson?.nextStep || lesson?.nextStepJson || {};

    const classmates = scene ? (scene.aiClassmates && scene.aiClassmates.length ? scene.aiClassmates : defaultClassmates(scene)) : [];

    wrap.innerHTML = `
      <div class="glass card" style="padding:16px;">
        <div class="section-title" style="margin-top:0;">
          <span>🏫 真课堂播放器</span>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button type="button" class="text-btn" id="classroomRefresh">刷新</button>
            <button type="button" class="text-btn" id="classroomReplayBtn">重播</button>
          </div>
        </div>
        <div class="stats-grid">
          <div class="stat-card"><strong>${scenes.length || 0}</strong><span>场景数</span></div>
          <div class="stat-card"><strong>${quizes.length || 0}</strong><span>题目数</span></div>
          <div class="stat-card"><strong>${state.classroom.sceneIndex + 1}</strong><span>当前镜</span></div>
          <div class="stat-card"><strong>${state.classroom.playing ? '播放中' : '暂停'}</strong><span>课堂状态</span></div>
        </div>
      </div>

      <div class="glass card" style="padding:16px;margin-top:16px;">
        <div class="section-title" style="margin-top:0;"><span>⚡ 批量预热</span><button class="text-btn" id="batchWarm">预热当前年级弱项优先知识点</button></div>
        <div class="empty">课堂播放器支持直接播放已生成的课堂包。若为空，先从知识点页触发生成。</div>
      </div>

      <div class="grid-two" style="margin-top:16px;align-items:start;">
        <div class="glass card" style="padding:16px;">
          <div class="section-title" style="margin-top:0;"><span>课堂包列表</span></div>
          <div class="task-list" id="classroomPkgList">
            ${(Array.isArray(state.classroom.packages) ? state.classroom.packages : []).map(p => `
              <button type="button" class="list-item glass-mini classroom-pkg" data-lesson-id="${esc(p.lessonId || p.id || '')}" style="width:100%;text-align:left;">
                <strong>${esc(p.lessonTitle || p.knowledgeName || '课堂包')}</strong>
                <p>${esc(p.status || '-') } · ${esc(p.engine || '-') } · ${esc(p.updatedAt || '')}</p>
              </button>
            `).join('') || '<div class="empty">暂无课堂包</div>'}
          </div>
        </div>

        <div class="glass card" style="padding:16px;">
          <div class="section-title" style="margin-top:0;"><span>课堂场景列表</span></div>
          <div class="task-list" id="classroomSceneList">
            ${scenes.map((s, i) => `
              <button type="button" class="list-item glass-mini scene-jump" data-scene-index="${i}" style="width:100%;text-align:left;">
                <strong>第 ${i + 1} 镜：${esc(s.title || `场景 ${i + 1}`)}</strong>
                <p>${esc(s.subtitle || '')} · ${esc(s.durationSec || 0)} 秒</p>
              </button>
            `).join('') || '<div class="empty">暂无场景</div>'}
          </div>
        </div>
      </div>

      <div class="glass card" style="padding:16px;margin-top:16px;">
        <div class="section-title" style="margin-top:0;"><span>📺 课堂舞台</span></div>
        <div id="stageMount"></div>
      </div>

      <div class="glass card" style="padding:16px;margin-top:16px;">
        <div class="section-title" style="margin-top:0;"><span>💬 老师字幕 / AI 同学 / 互动题</span></div>
        <div id="speechMount"></div>
        <div id="classmateMount" style="margin-top:12px;"></div>
        <div id="quizMount" style="margin-top:12px;"></div>
      </div>

      <div class="glass card" style="padding:16px;margin-top:16px;">
        <div class="section-title" style="margin-top:0;"><span>📚 课堂总结</span></div>
        <div class="detail-card glass-mini"><div class="detail-title">总结</div><div style="line-height:1.7;">${esc(summary.summary || summary.oneLine || lesson?.lessonTitle || '')}</div></div>
        <div class="detail-card glass-mini" style="margin-top:10px;"><div class="detail-title">下一步</div><div style="line-height:1.7;">${esc(nextStep.label || nextStep.mode || '继续学习')}</div></div>
      </div>
    `;

    document.getElementById('classroomRefresh')?.addEventListener('click', () => renderPlayer());
    document.getElementById('classroomReplayBtn')?.addEventListener('click', () => {
      state.classroom.sceneIndex = 0;
      state.classroom.quizIndex = 0;
      state.classroom.playing = true;
      state.classroom.playToken += 1;
      runCurrentScene(state.classroom.playToken).catch(() => {});
      renderPlayer();
    });
    document.getElementById('batchWarm')?.addEventListener('click', async () => {
      const knowledge = await api.knowledge();
      const items = (knowledge || []).filter(item => item.grade === state.grade && item.subject === state.subject).slice(0, 6).map(item => ({
        knowledgeCode: item.code || item.id || item.knowledgeCode,
        knowledgeName: item.name || item.topic || item.knowledgeName || item.code,
        grade: item.grade,
        subject: item.subject,
        chapter: item.chapter || item.level || '',
        userId: state.currentUserId || 'demo-student',
      }));
      const result = await api.classroomPrewarmBatch({ userId: state.currentUserId || 'demo-student', items });
      alert(`已发起批量预热：成功 ${result.success}/${result.total}`);
      await renderOverview();
    });

    document.querySelectorAll('[data-scene-index]').forEach(btn => btn.addEventListener('click', () => {
      state.classroom.sceneIndex = Number(btn.dataset.sceneIndex || 0);
      state.classroom.playing = false;
      state.classroom.playToken += 1;
      renderPlayer();
    }));

    document.querySelectorAll('[data-lesson-id]').forEach(btn => btn.addEventListener('click', async () => {
      const lessonId = btn.getAttribute('data-lesson-id');
      if (!lessonId) return;
      await openLesson(lessonId);
    }));

    renderStage();
    renderSpeech();
    renderClassmates();
    renderQuiz();
  }

  function renderStage() {
    const stageMount = document.getElementById('stageMount');
    const lesson = state.classroom.lesson;
    const scene = getActiveScene();
    if (!stageMount) return;
    if (!lesson || !scene) {
      stageMount.innerHTML = '<div class="empty">请选择一个课堂包，开始播放真课堂。</div>';
      return;
    }

    stageMount.innerHTML = `
      <div class="detail-card glass-mini classroom-stage-card" style="text-align:center;min-height:320px;display:flex;flex-direction:column;justify-content:center;gap:12px;">
        <div class="detail-title">${esc(scene.title || `第 ${state.classroom.sceneIndex + 1} 镜`)}</div>
        <div class="scene-visual-main" style="font-size:48px;line-height:1.2;">${esc(scene.visual || scene.subtitle || '🎬')}</div>
        <div class="detail-muted">${esc(scene.subtitle || '')}</div>
        <div style="white-space:pre-wrap;line-height:1.8;max-width:100%;">${esc(scene.narration || scene.teacherSpeech || '')}</div>
        <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;">
          <button type="button" class="chip" id="prevScene">上一段</button>
          <button type="button" class="chip" id="playScene">${state.classroom.playing ? '暂停播放' : '播放课堂'}</button>
          <button type="button" class="chip" id="nextScene">下一段</button>
          <button type="button" class="chip" id="finishLesson">结束课堂</button>
        </div>
      </div>
    `;
    document.getElementById('prevScene')?.addEventListener('click', () => {
      state.classroom.sceneIndex = Math.max(0, state.classroom.sceneIndex - 1);
      state.classroom.playing = false;
      state.classroom.playToken += 1;
      renderPlayer();
    });
    document.getElementById('nextScene')?.addEventListener('click', async () => {
      if (state.classroom.sceneIndex >= normalizeScenes(lesson?.scenes || lesson?.animation || lesson?.animationJson).length - 1) {
        state.classroom.playing = false;
        renderQuiz();
        return;
      }
      state.classroom.sceneIndex += 1;
      state.classroom.playToken += 1;
      renderPlayer();
      if (state.classroom.playing) await runCurrentScene(state.classroom.playToken);
    });
    document.getElementById('playScene')?.addEventListener('click', async () => {
      state.classroom.playing = !state.classroom.playing;
      state.classroom.playToken += 1;
      renderPlayer();
      if (state.classroom.playing) await runCurrentScene(state.classroom.playToken);
    });
    document.getElementById('finishLesson')?.addEventListener('click', async () => {
      const payload = {
        lessonId: lesson.id,
        userId: state.currentUserId || 'demo-student',
        knowledgeCode: lesson.knowledgeCode,
        knowledgeName: lesson.knowledgeName,
        isCompleted: true,
      };
      const finish = await api.classroomFinish(payload).catch(() => ({ masteryDelta: 0 }));
      alert(`课堂已完成 · mastery +${finish.masteryDelta || 0}`);
      state.classroom.playing = false;
      state.classroom.playToken += 1;
      renderPlayer();
    });
  }

  function renderSpeech() {
    const speechMount = document.getElementById('speechMount');
    const lesson = state.classroom.lesson;
    const scene = getActiveScene();
    if (!speechMount) return;
    if (!lesson || !scene) {
      speechMount.innerHTML = '<div class="empty">暂无老师字幕</div>';
      return;
    }
    const teacher = scene.teacherSpeech || scene.narration || scene.title || '';
    speechMount.innerHTML = `
      <div class="detail-card glass-mini">
        <div class="detail-title">老师在说</div>
        <div style="line-height:1.8;">${esc(teacher)}</div>
      </div>
    `;
  }

  function renderClassmates() {
    const classmateMount = document.getElementById('classmateMount');
    const lesson = state.classroom.lesson;
    const scene = getActiveScene();
    if (!classmateMount) return;
    if (!lesson || !scene) {
      classmateMount.innerHTML = '<div class="empty">暂无 AI 同学发言</div>';
      return;
    }
    const classmates = scene.aiClassmates && scene.aiClassmates.length ? scene.aiClassmates : defaultClassmates(scene);
    classmateMount.innerHTML = `
      <div class="detail-card glass-mini">
        <div class="detail-title">AI 同学陪读</div>
        <div class="task-list" style="margin-top:10px;">
          ${classmates.map(c => `
            <div class="chat-msg msg-ai" style="background:rgba(255,255,255,.05);padding:12px;border-radius:14px;">
              <strong>${esc(c.name || c.id || 'AI 同学')}</strong>
              <div style="margin-top:6px;line-height:1.7;">${esc(c.speech || '')}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  function renderQuiz() {
    const quizMount = document.getElementById('quizMount');
    const lesson = state.classroom.lesson;
    const quizzes = normalizeQuiz(lesson?.quiz || lesson?.questions);
    if (!quizMount) return;
    if (!lesson || !quizzes.length) {
      quizMount.innerHTML = '<div class="empty">暂无互动题</div>';
      return;
    }
    const quiz = quizzes[state.classroom.quizIndex] || quizzes[0];
    const options = Array.isArray(quiz.options) ? quiz.options : Array.isArray(quiz.choices) ? quiz.choices : [];
    quizMount.innerHTML = `
      <div class="detail-card glass-mini">
        <div class="detail-title">互动题</div>
        <div style="line-height:1.8;">${esc(quiz.prompt || quiz.title || '')}</div>
        <div class="task-list" style="margin-top:10px;">
          ${options.map((opt, idx) => `<button type="button" class="chip quiz-option" data-answer-index="${idx}" style="text-align:left;">${esc(opt)}</button>`).join('')}
        </div>
        <div id="quizFeedback" style="margin-top:8px;color:var(--muted);">请选择答案</div>
      </div>
    `;
    quizMount.querySelectorAll('[data-answer-index]').forEach(btn => btn.addEventListener('click', async () => {
      const answerIndex = Number(btn.getAttribute('data-answer-index'));
      const selected = options[answerIndex];
      const correct = typeof quiz.answerIndex === 'number' ? quiz.answerIndex : (quiz.answer ? options.indexOf(quiz.answer) : 0);
      const isCorrect = answerIndex === correct;
      const res = await api.classroomResponse({
        lessonId: lesson.id,
        sceneId: quiz.sceneId || getActiveScene()?.id || `scene-${state.classroom.sceneIndex + 1}`,
        userId: state.currentUserId || 'demo-student',
        answer: isCorrect ? 'right' : 'bad',
      }).catch(() => ({ feedback: isCorrect ? '答对了' : '再想想' }));
      const fb = quizMount.querySelector('#quizFeedback');
      if (fb) fb.textContent = res.feedback || (isCorrect ? '答对了' : '再想想');
      if (isCorrect) {
        if (state.classroom.quizIndex < quizzes.length - 1) {
          state.classroom.quizIndex += 1;
          renderPlayer();
        } else {
          await api.classroomFinish({
            lessonId: lesson.id,
            userId: state.currentUserId || 'demo-student',
            knowledgeCode: lesson.knowledgeCode,
            knowledgeName: lesson.knowledgeName,
            isCompleted: true,
          }).catch(() => {});
          quizMount.innerHTML = `
            <div class="detail-card glass-mini">
              <div class="detail-title">课堂完成</div>
              <div style="line-height:1.8;">这节课已经完成。\n${esc(lesson?.nextStep?.label || lesson?.nextStep?.mode || '继续学习')}</div>
            </div>
          `;
        }
      }
    }));
  }

  async function runCurrentScene(token) {
    const lesson = state.classroom.lesson;
    const scene = getActiveScene();
    if (!lesson || !scene) return;
    if (token != null && token !== state.classroom.playToken) return;
    const teacherSpeech = scene.teacherSpeech || scene.narration || scene.title || '';
    const teacherVoice = scene.teacherVoice?.voiceKey || lesson.teacherVoiceKey || 'zh-cn-female';
    const audioUrl = await loadTtsAudio(teacherSpeech, teacherVoice).catch(() => null);
    await playAudio(audioUrl);
    if (!state.classroom.playing) return;
    if (token != null && token !== state.classroom.playToken) return;

    const classmates = scene.aiClassmates && scene.aiClassmates.length ? scene.aiClassmates : defaultClassmates(scene);
    for (const cm of classmates.slice(0, 2)) {
      const cmUrl = await loadTtsAudio(cm.speech || '', cm.voiceKey || 'zh-cn-female').catch(() => null);
      await playAudio(cmUrl);
    }

    const waitMs = Math.max(1800, Number(scene.durationSec || 6) * 1000);
    await new Promise(resolve => setTimeout(resolve, waitMs));
    if (!state.classroom.playing) return;
    if (token != null && token !== state.classroom.playToken) return;

    const scenes = normalizeScenes(lesson?.scenes || lesson?.animation || lesson?.animationJson);
    if (state.classroom.sceneIndex < scenes.length - 1) {
      state.classroom.sceneIndex += 1;
      renderPlayer();
      await runCurrentScene(token);
    } else {
      state.classroom.playing = false;
      renderQuiz();
      renderPlayer();
    }
  }

  async function openLesson(lessonId, preferPayload = window.__selectedClassroomLessonPayload) {
    state.classroom.busy = true;
    const lesson = await loadLesson(lessonId, preferPayload).catch(() => null);
    if (!lesson) {
      state.classroom.busy = false;
      renderPlayer();
      return;
    }
    state.classroom.lesson = lesson;
    state.classroom.sceneIndex = 0;
    state.classroom.quizIndex = 0;
    state.classroom.playing = true;
    state.classroom.playToken += 1;
    window.__selectedClassroomLessonPayload = null;
    window.__selectedClassroomLessonId = lesson.id;
    renderPlayer();
    await runCurrentScene(state.classroom.playToken);
    state.classroom.busy = false;
  }

  async function renderOverview() {
    const { stats, tasks, packages, knowledge } = await fetchOverview();
    state.classroom.stats = stats;
    state.classroom.tasks = tasks;
    state.classroom.packages = packages;
    state.classroom.knowledge = knowledge;

    if (!state.classroom.lesson && !state.classroom.busy) {
      const selectedLessonId = window.__selectedClassroomLessonId || packages[0]?.lessonId || packages[0]?.id;
      if (selectedLessonId) {
        const prefer = window.__selectedClassroomLessonPayload;
        state.classroom.busy = true;
        await openLesson(selectedLessonId, prefer);
        return;
      }
    }
    renderPlayer();
  }

  await renderOverview();
}
