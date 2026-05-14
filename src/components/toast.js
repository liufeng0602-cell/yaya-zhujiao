let timer;
export function toast(text, type = 'info') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = text;
  el.dataset.type = type;
  el.classList.add('show');
  clearTimeout(timer);
  timer = setTimeout(() => el.classList.remove('show'), 1800);
}
