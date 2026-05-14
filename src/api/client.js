const API_BASE = 'http://localhost:3001';

export async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) {
    const message = data?.message || data?.error || `HTTP ${res.status}`;
    const err = new Error(message);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

export const api = {
  get: (path) => request(path),
  health: () => request('/health'),
  register: (body) => request('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  me: (userId) => request(`/auth/me?userId=${encodeURIComponent(userId)}`),
  membership: (userId) => request(`/auth/membership?userId=${encodeURIComponent(userId)}`),
  trial: (body) => request('/auth/trial', { method: 'POST', body: JSON.stringify(body) }),
  renew: (body) => request('/auth/renew', { method: 'POST', body: JSON.stringify(body) }),
  content: (params = '') => request(`/content${params}`),
  knowledge: () => request('/knowledge'),
  questions: () => request('/questions'),
  reports: (userId) => request(`/reports${userId ? `?userId=${encodeURIComponent(userId)}` : ''}`),
  importContent: (body) => request('/imports/content', { method: 'POST', body: JSON.stringify(body) }),
  importKnowledge: (body) => request('/imports/knowledge', { method: 'POST', body: JSON.stringify(body) }),
  importKnowledgeBatch: (items) => request('/imports/knowledge/batch', { method: 'POST', body: JSON.stringify({ items }) }),
  importQuestions: (items) => request('/imports/questions/batch', { method: 'POST', body: JSON.stringify({ items }) }),
  genExplain: (body) => request('/ai/explain', { method: 'POST', body: JSON.stringify(body) }),
  saveExplain: (body) => request('/ai/explain/save', { method: 'POST', body: JSON.stringify(body) }),
  genQuestions: (body) => request('/ai/questions', { method: 'POST', body: JSON.stringify(body) }),
  saveQuestions: (body) => request('/ai/questions/save', { method: 'POST', body: JSON.stringify(body) }),
  tts: (body) => request('/ai/tts', { method: 'POST', body: JSON.stringify(body) }),

  classroomStats: () => request('/ai/classroom/stats'),
  classroomTasks: () => request('/ai/classroom/tasks'),
  classroomList: () => request('/ai/classroom/list'),
  classroomReplay: (lessonId) => request(`/ai/classroom/replay/${encodeURIComponent(lessonId)}`),
  classroomStart: (body) => request('/ai/classroom/start', { method: 'POST', body: JSON.stringify(body) }),
  classroomPrewarm: (body) => request('/ai/classroom/prewarm', { method: 'POST', body: JSON.stringify(body) }),
  classroomPrewarmBatch: (body) => request('/ai/classroom/prewarm/batch', { method: 'POST', body: JSON.stringify(body) }),
  classroomResponse: (body) => request('/ai/classroom/response', { method: 'POST', body: JSON.stringify(body) }),
  classroomTaskDetail: (taskId) => request(`/ai/classroom/tasks/${encodeURIComponent(taskId)}`),
  classroomFinish: (body) => request('/ai/classroom/finish', { method: 'POST', body: JSON.stringify(body) }),
  wrongbookSummary: (userId) => request(`/wrongbook/summary/${encodeURIComponent(userId)}`),
};
