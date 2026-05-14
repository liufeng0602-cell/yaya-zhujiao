const syllabus = {
  '五年级': {
    '数学': [
      {
        chapter: '第1章 分数的意义与性质',
        progress: '已掌握 4 / 6',
        items: [
          { name: '分数的意义', target: '理解', goal: '能解释分数表示的含义', mastery: '超新星', status: 'mastered', weak: false, code: 'K-FRACTION-0' },
          { name: '真分数和假分数', target: '会做基础题', goal: '能区分真分数和假分数', mastery: '星云', status: 'mastered', weak: false, code: 'K-FRACTION-1' },
          { name: '分数乘整数', target: '熟练应用', goal: '能完成分数与整数乘法计算和简单应用', mastery: '恒星', status: 'learning', weak: false, code: 'K-FRACTION-2' },
          { name: '分数乘分数', target: '熟练应用', goal: '能解决连续分配类问题', mastery: '卫星', status: 'weak', weak: true, code: 'K-FRACTION-3' }
        ]
      }
    ]
  }
};

export function initHomePage(state) {
  const homeMastery = document.getElementById('homeMastery');
  const chapterWrap = document.getElementById('chapterWrap');
  const gradeWrap = document.getElementById('gradeChips');
  const subjectWrap = document.getElementById('subjectChips');
  const currentUserLabel = document.getElementById('currentUserLabel');

  if (currentUserLabel && state.currentUser) {
    currentUserLabel.textContent = `${state.currentUser.name} · ${state.currentUser.email}`;
  }
  if (homeMastery) homeMastery.textContent = state.apiStatus === '已连接' ? '78%' : '72%';

  const grades = ['五年级', '六年级'];
  const subjects = ['数学', '语文', '英语'];
  const currentGrade = state.grade || '五年级';
  const currentSubject = state.subject || '数学';
  if (gradeWrap) {
    gradeWrap.innerHTML = grades.map(g => `<button class="chip ${g === currentGrade ? 'active' : ''}" data-grade="${g}">${g}</button>`).join('');
    gradeWrap.querySelectorAll('[data-grade]').forEach(btn => btn.onclick = () => {
      state.grade = btn.dataset.grade;
      initHomePage(state);
    });
  }
  if (subjectWrap) {
    subjectWrap.innerHTML = subjects.map(s => `<button class="chip ${s === currentSubject ? 'active' : ''}" data-subject="${s}">${s}</button>`).join('');
    subjectWrap.querySelectorAll('[data-subject]').forEach(btn => btn.onclick = () => {
      state.subject = btn.dataset.subject;
      initHomePage(state);
    });
  }

  if (chapterWrap) {
    const chapters = syllabus[currentGrade]?.[currentSubject] || [];
    chapterWrap.innerHTML = chapters.map((chapter, idx) => `
      <div class="chapter-card glass ${idx === 0 ? 'open' : ''}">
        <button class="chapter-summary" data-open="${idx}">
          <div class="chapter-left">
            <strong>${chapter.chapter}</strong>
            <p>${currentGrade} · ${currentSubject} · ${chapter.items.length} 个知识点</p>
          </div>
          <div class="chapter-right">
            <div class="chapter-progress">${chapter.progress}</div>
            <div class="chapter-arrow">›</div>
          </div>
        </button>
        <div class="chapter-body">
          <div class="chapter-items">
            ${chapter.items.map(item => {
              const [label, cls] = statusLabel(item.status);
              return `
                <div class="chapter-item">
                  <div class="chapter-item-head">
                    <div>
                      <h4>${item.name}</h4>
                      <div class="info-line">教学目标：${item.goal}</div>
                    </div>
                    <span class="chapter-status ${cls}">${label}</span>
                  </div>
                  <div class="tag-row">
                    <span class="info-tag goal-tag">大纲要求：${item.target}</span>
                    <span class="info-tag mastery-tag">当前掌握：${item.mastery}</span>
                    ${item.weak ? '<span class="info-tag">系统建议：优先补弱</span>' : '<span class="info-tag">系统建议：继续推进</span>'}
                  </div>
                </div>`;
            }).join('')}
          </div>
        </div>
      </div>`).join('');

    chapterWrap.querySelectorAll('[data-open]').forEach(btn => btn.onclick = () => {
      btn.closest('.chapter-card')?.classList.toggle('open');
    });
  }
}

function statusLabel(status) {
  const map = {
    mastered: ['已掌握', 'status-mastered'],
    learning: ['学习中', 'status-learning'],
    weak: ['待补弱', 'status-weak'],
    locked: ['未解锁', 'status-locked']
  };
  return map[status] || ['未知', 'status-locked'];
}
