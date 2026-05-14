export function setLoading(id, loading, text = '加载中...') {
  const el = document.getElementById(id);
  if (!el) return;
  if (loading) {
    el.dataset.loadingText = el.textContent;
    el.textContent = text;
    el.disabled = true;
    el.classList.add('is-loading');
  } else {
    el.textContent = el.dataset.loadingText || el.textContent;
    el.disabled = false;
    el.classList.remove('is-loading');
  }
}

export function setPageLoading(isLoading, text = '正在加载数据...') {
  const overlay = document.getElementById('loadingOverlay');
  if (!overlay) return;
  overlay.classList.toggle('show', isLoading);
  overlay.querySelector('.loading-text').textContent = text;
}
