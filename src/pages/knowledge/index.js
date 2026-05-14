import { api } from '../../api/client.js';

function esc(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function getNodeLabel(node) {
  return node.name || node.topic || node.knowledgeName || node.code || node.id;
}

export async function initKnowledgePage(state) {
  const gradeWrap = document.getElementById('gradeChips');
  const subjectWrap = document.getElementById('subjectChips');
  const wrap = document.getElementById('chapterWrap');
  if (!gradeWrap || !subjectWrap || !wrap) return;

  const renderLoading = () => {
    wrap.innerHTML = '<div class="card glass"><strong>正在读取数据库知识树...</strong><p style="margin:8px 0 0;color:#94b5d8;">请稍等。</p></div>';
  };

  const renderError = (msg) => {
    wrap.innerHTML = `<div class="card glass"><strong>知识树加载失败</strong><p style="margin:8px 0 0;color:#ffb3c0;">${esc(msg)}</p></div>`;
  };

  const render = async () => {
    renderLoading();
    try {
      const data = await api.knowledge();
      const grades = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级'];
      const subjects = ['数学', '语文', '英语'];
      gradeWrap.innerHTML = grades.map(g => `<button class="chip ${g === state.grade ? 'active' : ''}" data-grade="${g}">${g}</button>`).join('');
      subjectWrap.innerHTML = subjects.map(s => `<button class="chip ${s === state.subject ? 'active' : ''}" data-subject="${s}">${s}</button>`).join('');

      gradeWrap.querySelectorAll('[data-grade]').forEach(btn => btn.addEventListener('click', () => {
        state.grade = btn.dataset.grade;
        render();
      }));
      subjectWrap.querySelectorAll('[data-subject]').forEach(btn => btn.addEventListener('click', () => {
        state.subject = btn.dataset.subject;
        render();
      }));

      const nodes = (data || []).filter(item => {
        const gradeOk = !state.grade || item.grade === state.grade;
        const subjectOk = !state.subject || item.subject === state.subject;
        return gradeOk && subjectOk;
      });

      if (!nodes.length) {
        wrap.innerHTML = '<div class="card glass"><strong>当前筛选下还没有知识点</strong><p style="margin:8px 0 0;color:#94b5d8;">先导入批次数据，再回来查看。</p></div>';
        return;
      }

      const grouped = new Map();
      for (const node of nodes) {
        const key = `${node.grade || ''}__${node.subject || ''}__${node.chapter || node.level || ''}`;
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key).push(node);
      }

      wrap.innerHTML = Array.from(grouped.entries()).map(([key, items]) => {
        const [grade, subject, chapter] = key.split('__');
        return `
          <div class="chapter-card glass open">
            <button class="chapter-summary" data-open="${esc(key)}">
              <div class="chapter-left">
                <strong>${esc(chapter || '未命名章节')}</strong>
                <p>${esc(grade)} · ${esc(subject)} · ${items.length} 个知识点</p>
              </div>
              <div class="chapter-right">
                <div class="chapter-progress">数据库真实树</div>
                <div class="chapter-arrow">›</div>
              </div>
            </button>
            <div class="chapter-body">
              <div class="chapter-items">
                ${items.map(node => `
                  <div class="chapter-item">
                    <div class="chapter-item-head">
                      <div>
                        <h4>${esc(getNodeLabel(node))}</h4>
                        <div class="info-line">知识点编码：${esc(node.code || node.id || '')}</div>
                      </div>
                      <span class="chapter-status status-learning">${esc(node.level || node.stage || '知识点')}</span>
                    </div>
                    <div class="tag-row">
                      <span class="info-tag goal-tag">父节点：${esc(node.parentCode || node.parentId || '无')}</span>
                      <span class="info-tag mastery-tag">标签：${esc(Array.isArray(node.tags) ? node.tags.join('，') : '')}</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        `;
      }).join('');

      wrap.querySelectorAll('[data-open]').forEach(btn => btn.addEventListener('click', () => {
        const card = btn.closest('.chapter-card');
        card.classList.toggle('open');
      }));
    } catch (e) {
      renderError(e.message);
    }
  };

  await render();
}
