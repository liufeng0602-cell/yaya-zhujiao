import { api } from './api/client.js';
import { initAdminPage } from './pages/admin/index.js';
import { initHomePage } from './pages/home/index.js';
import { initKnowledgePage } from './pages/knowledge/index.js';
import { initPracticePage } from './pages/practice/index.js';
import { initBoardPage } from './pages/board/index.js';
import { initLeaderboardPage } from './pages/leaderboard/index.js';
import { initClassroomPage } from './pages/classroom/index.js';
import { setPageLoading } from './components/loading.js';

const appState = {
  currentTab: 'home',
  apiStatus: '未连接',
  grade: '五年级',
  subject: '数学',
  boardType: 'unlock'
};

const pageInits = {
  home: initHomePage,
  knowledge: initKnowledgePage,
  practice: initPracticePage,
  board: initBoardPage,
  leaderboard: initLeaderboardPage,
  classroom: initClassroomPage,
  admin: initAdminPage,
};
const pages = [...document.querySelectorAll('.page')];
const navItems = [...document.querySelectorAll('.nav-item')];
const navIndicator = document.getElementById('navIndicator');
const topbarTitle = document.getElementById('topbarTitle');
const topbarSub = document.getElementById('topbarSub');
const topbarBadge = document.getElementById('topbarBadge');
const toastEl = document.getElementById('toast');

const topbarMap = {
  home: ['芽芽 AI 学习宇宙站', '首页'],
  knowledge: ['按年级-学科-章节展开', '知识树'],
  practice: ['AI 动态出题测评', '练习'],
  board: ['家长同步掌握度', '看板'],
  leaderboard: ['周榜 / 月榜 / 学期榜', '榜单'],
  classroom: ['课堂引擎回放 / 批量预热', '课堂'],
  admin: ['后台导入 / 联调', '后台管理']
};

function showToast(text) {
  toastEl.textContent = text;
  toastEl.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toastEl.classList.remove('show'), 1400);
}

function switchTab(tab) {
  appState.currentTab = tab;
  pages.forEach(page => page.classList.toggle('active', page.id === `page-${tab}`));
  navItems.forEach(item => item.classList.toggle('active', item.dataset.tab === tab));
  const idx = navItems.findIndex(item => item.dataset.tab === tab);
  navIndicator.style.transform = `translateX(${idx * 100}%)`;
  const [sub, title] = topbarMap[tab] || topbarMap.home;
  topbarSub.textContent = sub;
  topbarTitle.textContent = title;
  pageInits[tab]?.(appState);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function bindNav() {
  navItems.forEach(item => item.addEventListener('click', () => switchTab(item.dataset.tab)));
  document.querySelectorAll('[data-tab]').forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
}

async function bootstrap() {
  bindNav();
  try {
    setPageLoading(true, '正在连接后端...');
    await api.health();
    appState.apiStatus = '已连接';
    topbarBadge.textContent = '数据库已连接';
  } catch {
    appState.apiStatus = '未连接';
    topbarBadge.textContent = '后端离线';
    showToast('后端暂时不可用，请检查服务');
  } finally {
    setPageLoading(false);
  }
  switchTab('home');
}

bootstrap();
