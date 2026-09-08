const STAGES = ['S0','S1','S2','S3','S4','S5','S6','S7','S8'];
const TITLES = {S0:'Input admission',S1:'Problem analysis',S2:'Model route',S3:'Data & visualization',S4:'Reproducible code',S5:'Real execution',S6:'Evidence gate',S7:'Formal writing',S8:'Format & render QA'};
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
function renderStatus(s) {
  const index = Number.isFinite(s.stage_index) ? s.stage_index : STAGES.indexOf(s.stage);
  const pct = Math.max(0, Math.min(100, Math.round(((index + (s.status === 'passed' ? 1 : 0)) / STAGES.length) * 100)));
  $('project').textContent = s.project || 'MathModel project'; $('stage').textContent = `${s.stage || 'S0'} · ${TITLES[s.stage] || 'Workflow'}`;
  $('badge').textContent = s.status || 'pending'; $('badge').className = `badge ${s.status || 'pending'}`; $('bar').style.width = `${pct}%`;
  $('message').textContent = s.message || 'No message'; $('fraction').textContent = `${Math.max(0,index + (s.status === 'passed' ? 1 : 0))} / ${STAGES.length}`; $('task').textContent = s.current_task || '—';
  $('updated').textContent = s.updated_at ? `Updated ${new Date(s.updated_at).toLocaleString()}` : 'Waiting for status';
  $('timeline').innerHTML = STAGES.map((stage,i) => `<div class="step ${i < index || (i === index && s.status === 'passed') ? 'done' : ''} ${i === index && s.status !== 'passed' ? 'active' : ''}"><b></b><em>${stage}</em></div>`).join('');
  const artifacts = s.artifacts || []; $('artifacts').innerHTML = artifacts.length ? artifacts.map(p => `<a class="artifact" href="/project/${String(p).split('/').map(encodeURIComponent).join('/')}" target="_blank">${esc(p)}</a>`).join('') : '<div class="empty">No artifacts recorded yet.</div>';
}
function renderEvents(text) {
  const rows = text.trim().split('\n').filter(Boolean).slice(-20).reverse().map(line => { try { return JSON.parse(line); } catch { return null; } }).filter(Boolean);
  $('feed').innerHTML = rows.length ? rows.map(e => `<div class="event"><strong>${esc(e.stage)}</strong><div><strong>${esc(e.status)}</strong><p>${esc(e.message || e.current_task || '')}</p></div><time>${e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : ''}</time></div>`).join('') : '<div class="empty">No events yet.</div>';
}
async function refresh() { try { const [s,e] = await Promise.all([fetch('/api/status',{cache:'no-store'}),fetch('/api/events',{cache:'no-store'})]); renderStatus(await s.json()); renderEvents(await e.text()); } catch (err) { $('updated').textContent = `Dashboard error: ${err.message}`; } }
refresh(); setInterval(refresh, 2500);
