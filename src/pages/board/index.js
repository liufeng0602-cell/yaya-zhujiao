export function initBoardPage(state) {
  const boardScore = document.getElementById('boardScore');
  const subjectRows = document.getElementById('subjectRows');
  const weakList = document.getElementById('weakList');
  if (boardScore) boardScore.textContent = state.apiStatus === '已连接' ? '82' : '75';
  if (subjectRows) {
    subjectRows.innerHTML = `
      <div class="subject-row"><span>数学</span><div class="subject-bar"><i style="width:86%"></i></div><em>86%</em></div>
      <div class="subject-row"><span>语文</span><div class="subject-bar"><i style="width:72%"></i></div><em>72%</em></div>
      <div class="subject-row"><span>英语</span><div class="subject-bar"><i style="width:79%"></i></div><em>79%</em></div>`;
  }
  if (weakList) {
    weakList.innerHTML = `
      <div class="task-card glass pop-card">
        <div><strong>分数乘分数</strong><p>当前掌握：卫星 · 大纲要求：熟练应用</p></div>
        <span class="task-tag red">优先补弱</span>
      </div>
      <div class="task-card glass pop-card">
        <div><strong>英语一般过去时</strong><p>当前掌握：恒星 · 大纲要求：熟练应用</p></div>
        <span class="task-tag yellow">继续巩固</span>
      </div>`;
  }
}
