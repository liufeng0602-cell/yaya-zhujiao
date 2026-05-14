const leaderboardData = {
  unlock: {
    podium: [
      ['星尘少年', '61个'],
      ['银河小虎', '68个'],
      ['北北', '56个']
    ],
    rows: [
      ['3', '北北', '56个知识点', true],
      ['4', '火箭丸子', '54个知识点', false],
      ['5', '未来舰长', '51个知识点', false],
      ['6', '云帆', '49个知识点', false]
    ]
  },
  time: {
    podium: [
      ['晨光引擎', '612分'],
      ['太空阿布', '688分'],
      ['北北', '598分']
    ],
    rows: [
      ['3', '北北', '598分钟', true],
      ['4', '火箭丸子', '584分钟', false],
      ['5', '未来舰长', '560分钟', false],
      ['6', '云帆', '548分钟', false]
    ]
  }
};

export function initLeaderboardPage(state) {
  const podium = document.getElementById('podium');
  const rankList = document.getElementById('rankList');
  const toggleBtns = document.querySelectorAll('.toggle-btn');
  if (!podium || !rankList) return;
  state.boardType = state.boardType || 'unlock';
  const render = () => {
    const data = leaderboardData[state.boardType];
    const [second, first, third] = data.podium;
    podium.innerHTML = `
      <div class="winner second"><span>2</span><strong>${second[0]}</strong><em>${second[1]}</em></div>
      <div class="winner first"><span>1</span><strong>${first[0]}</strong><em>${first[1]}</em></div>
      <div class="winner third"><span>3</span><strong>${third[0]}</strong><em>${third[1]}</em></div>`;
    rankList.innerHTML = data.rows.map(([rank, name, value, me]) => `
      <div class="rank-row glass ${me ? 'me' : ''}">
        <div class="rank-no">${rank}</div>
        <div class="rank-main"><strong>${name}</strong><span>${me ? '你的当前排名' : '本月持续上升'}</span></div>
        <div class="rank-value">${value}</div>
      </div>`).join('');
  };
  toggleBtns.forEach(btn => btn.onclick = () => {
    toggleBtns.forEach(x => x.classList.remove('active'));
    btn.classList.add('active');
    state.boardType = btn.dataset.board;
    render();
  });
  render();
}
