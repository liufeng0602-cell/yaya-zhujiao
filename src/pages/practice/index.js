const questions = [
  { tier: '行星级', title: '1/4 × 3 = ?', options: ['3/4', '4/3', '1/12', '7/4'], answer: '3/4', hint: '把 1/4 连加 3 次。' },
  { tier: '恒星级', title: '2/7 × 4 = ?', options: ['8/7', '6/7', '4/7', '2/28'], answer: '8/7', hint: '分母不变，分子乘整数。' },
  { tier: '超新星级', title: '一袋能量糖每次吃 3/8 袋，连续吃 2 次，一共吃了多少？', options: ['6/8', '3/16', '1/8', '5/8'], answer: '6/8', hint: '把 3/8 连续加 2 次。' }
];

export function initPracticePage(state) {
  const tierRow = document.getElementById('tierRow');
  const questionTitle = document.getElementById('questionTitle');
  const optionsWrap = document.getElementById('options');
  const submitBtn = document.getElementById('submitBtn');
  const hintBtn = document.getElementById('hintBtn');
  const hintBox = document.getElementById('hintBox');
  const feedback = document.getElementById('feedback');
  const progressBar = document.getElementById('progressBar');
  const questionCount = document.getElementById('questionCount');
  const questionCard = document.getElementById('questionCard');
  const resultPreview = document.getElementById('resultPreview');

  if (!tierRow || !questionTitle || !optionsWrap || !submitBtn) return;

  state.practiceIndex = state.practiceIndex || 0;
  state.practiceCorrect = state.practiceCorrect || 0;
  state.practiceSelected = '';

  const render = () => {
    const q = questions[state.practiceIndex];
    questionTitle.textContent = q.title;
    questionCount.textContent = `${state.practiceIndex + 1} / ${questions.length}`;
    progressBar.style.width = `${((state.practiceIndex + 1) / questions.length) * 100}%`;
    tierRow.innerHTML = questions.map((item, idx) => `<span class="tier-pill ${idx === state.practiceIndex ? 'active' : ''}">${item.tier}</span>`).join('');
    optionsWrap.innerHTML = q.options.map(option => `<button class="option" data-option="${option}">${option}</button>`).join('');
    submitBtn.disabled = true;
    hintBox.classList.add('hidden');
    feedback.className = 'feedback hidden';
    optionsWrap.querySelectorAll('.option').forEach(btn => btn.onclick = () => {
      optionsWrap.querySelectorAll('.option').forEach(el => el.classList.remove('selected'));
      btn.classList.add('selected');
      state.practiceSelected = btn.dataset.option;
      submitBtn.disabled = false;
    });
  };

  hintBtn.onclick = () => {
    hintBox.textContent = questions[state.practiceIndex].hint;
    hintBox.classList.toggle('hidden');
  };

  submitBtn.onclick = () => {
    if (!state.practiceSelected) return;
    const q = questions[state.practiceIndex];
    const correct = state.practiceSelected === q.answer;
    optionsWrap.querySelectorAll('.option').forEach(btn => {
      btn.disabled = true;
      if (btn.dataset.option === q.answer) btn.classList.add('correct');
      if (btn.dataset.option === state.practiceSelected && !correct) btn.classList.add('wrong');
    });
    feedback.className = `feedback ${correct ? 'ok' : 'bad'}`;
    feedback.textContent = correct ? '答对了，继续冲。' : `这题错了，正确答案是 ${q.answer}`;
    if (correct) state.practiceCorrect += 1;
    setTimeout(() => {
      if (state.practiceIndex < questions.length - 1) {
        state.practiceIndex += 1;
        render();
      } else {
        questionCard.classList.add('hidden');
        resultPreview.classList.remove('hidden');
        const score = Math.round((state.practiceCorrect / questions.length) * 100);
        const level = score >= 95 ? '超新星' : score >= 80 ? '星云' : score >= 60 ? '恒星' : '卫星';
        document.getElementById('resultLevel').textContent = level;
        document.getElementById('previewScore').textContent = score;
        document.getElementById('previewAccuracy').textContent = `${score}%`;
        document.getElementById('previewPoints').textContent = score >= 95 ? '+100' : '+50';
      }
    }, 700);
  };

  state.practiceIndex = 0;
  state.practiceCorrect = 0;
  questionCard.classList.remove('hidden');
  resultPreview.classList.add('hidden');
  render();
}
