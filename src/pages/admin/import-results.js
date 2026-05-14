export function renderImportResults({ title, result, error }) {
  const box = document.getElementById('importResultPanel');
  if (!box) return;
  if (error) {
    box.innerHTML = `<div class="import-result error"><strong>${title}</strong><p>${error}</p></div>`;
    return;
  }
  const json = typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result);
  box.innerHTML = `<div class="import-result success"><strong>${title}</strong><pre>${json}</pre></div>`;
}
