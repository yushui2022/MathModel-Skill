/* MathModel: the conversation decides; this panel shows current project evidence. */
(() => {
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const token = new URLSearchParams(location.search).get('token') || '';
  const api = path => `${path}${path.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
  const names = {P0:'输入与指令',P1:'审题与确认',P2:'模型路线',P3:'真实实验',P4:'独立复算',P5:'稳健性与结论',P6:'证据冻结',P7:'论文写作',P8:'独立审稿',P9:'正式交付'};
  const labels = {pending:'待执行',not_checked:'待验证',running:'运行中',queued:'排队中',cancelling:'正在停止',succeeded:'执行完成',passed:'验证通过',failed:'失败',stale:'已失效',validating:'待验证',awaiting_validation:'待验证',cancelled:'已取消',interrupted:'已中断',unknown:'待核实',current:'哈希有效',recorded:'已记录'};
  const jobNames = {preflight:'环境与输入预检',model_run:'模型实验',evidence_check:'证据检查',format_check:'格式检查',final_check:'完整交付检查'};
  const active = status => ['queued','running','cancelling'].includes(status);
  const badge = value => `<span class="badge ${Object.hasOwn(labels,value) ? value : 'unknown'}"><i></i>${esc(labels[value] || value)}</span>`;
  const empty = message => `<div class="empty">${esc(message)}</div>`;
  const fmt = value => value ? new Date(value).toLocaleString('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '—';
  let state = {project:'MathModel',stages:[],artifacts:[],jobs:[],history:[]};
  let view = 'overview', context = null, question = '', selected = null, selectedJob = null;
  let preview = null, revision = null, busy = false, first = true, contextCursor = null;
  let contextDirty = true;
  const folders = new Set(), details = new Set();
  const jobLogs = new Map();

  async function request(path, options = {}) {
    const response = await fetch(api(path), {cache:'no-store', ...options});
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `请求失败 (${response.status})`);
    }
    return response.json();
  }
  function notice(message, bad = false) {
    $('notice').textContent = message;
    $('notice').className = bad ? 'notice error' : 'notice';
    $('notice').hidden = !message;
  }
  const files = () => state.artifacts || [];
  const selectedMeta = () => files().find(f => f.id === selected);
  const chip = a => `<button class="artifact-chip" data-file="${esc(a.id)}" title="${esc(a.path)}"><span>${esc(a.path.split('/').pop())}</span><small>${esc(a.kind)}</small></button>`;
  function fileGroup(f) {
    if (f.path.startsWith('problem_files/')) return '题目与附件';
    if (/\.(py|ipynb|r|m|jl)$/i.test(f.path)) return '建模代码';
    if (/\.(docx|pdf|md)$/i.test(f.path) && !/research|reviews/.test(f.path)) return '论文与交付';
    if (/experiments|results|figures|tables|data_cleaned/.test(f.path)) return '实验与数据';
    return '决策与验证';
  }
  function renderTree() {
    const tree = $('file-tree'), scroll = tree.scrollTop;
    const groups = {};
    files().forEach(f => (groups[fileGroup(f)] ||= []).push(f));
    tree.innerHTML = Object.entries(groups).map(([name, items]) => `<div class="tree-group"><button class="folder" data-folder="${esc(name)}" aria-expanded="${!folders.has(name)}"><span class="chevron">${folders.has(name) ? '›' : '⌄'}</span>${esc(name)}<small>${items.length}</small></button><div class="tree-children" ${folders.has(name) ? 'hidden' : ''}>${items.map(f => `<button class="file ${selected===f.id?'selected':''}" data-file="${esc(f.id)}" title="${esc(f.path)}"><span class="file-icon">·</span><span>${esc(f.path.split('/').pop())}</span></button>`).join('')}</div></div>`).join('') || empty('题目和运行产物将在这里同步。');
    tree.scrollTop = scroll;
  }
  function stageTable() {
    return `<div class="stage-table">${state.stages.map(s => `<details class="stage-detail" data-stage="${esc(s.code)}" ${details.has(s.code)?'open':''}><summary class="stage-line ${s.code===state.stage?'current':''}"><span class="stage-code">${esc(s.code)}</span><span class="stage-title">${esc(s.name || names[s.code] || s.code)}</span>${badge(s.status)}</summary><div class="stage-description">${esc(s.message || (s.status==='passed'?'当前版本的阶段条件已验证。':'等待对应 Skill 完成输入、产物与验证。'))}</div></details>`).join('')}</div>`;
  }
  function eventList() {
    return state.history?.length ? `<div class="event-list">${state.history.slice(-6).reverse().map(e => `<div class="event"><span class="event-time">${fmt(e.timestamp || e.created_at)}</span><span class="event-code">${esc(e.stage || '')}</span><span>${esc(e.message || e.current_task || '活动记录')}</span></div>`).join('')}</div>` : empty('尚无运行活动。');
  }
  function factValue(value) {
    if (value == null) return '尚未记录';
    if (typeof value !== 'object') return esc(value);
    if (value.truncated) return `<pre class="fact-excerpt">${esc(value.excerpt)}</pre><small>内容已节选，完整内容见来源文件。</small>`;
    if (Array.isArray(value)) return `<ul>${value.map(v=>`<li>${factValue(v)}</li>`).join('')}</ul>`;
    return `<dl class="fact-values">${Object.entries(value).filter(([,v])=>v!=null).map(([k,v])=>`<dt>${esc(({selected_route_id:'选中路线',backup_route_id:'备用路线',rejected_routes:'淘汰路线',reason:'理由',route_id:'路线',task:'任务',depends_on:'依赖',assumptions:'假设',recommended_experiment_plan:'实验计划',implementation_risks:'实现风险',subproblem_id:'问题',failure_reason:'失败原因',run_id:'实验',seed:'随机种子',exit_code:'退出码',hash_issues:'版本问题'})[k] || k)}</dt><dd>${factValue(v)}</dd>`).join('')}</dl>`;
  }
  function factCard(f) {
    const source = files().find(a => a.path === f.source.path);
    return `<article class="fact-card"><div class="fact-heading"><h3>${esc(f.title)}</h3>${badge(f.state)}</div>${factValue(f.value)}<div class="fact-source">${source ? `<button class="subtle-btn" data-file="${esc(source.id)}">查看来源 ↗</button>` : esc(f.source.path)}<span class="mono">${esc(f.source.pointer)}</span></div></article>`;
  }
  function questionPicker() {
    const qs = context?.focus?.available_questions || [];
    return `<div class="question-toolbar"><label for="question-picker">当前问题</label><select id="question-picker"><option value="">全项目</option>${qs.map(q=>`<option value="${esc(q)}" ${q===question?'selected':''}>${esc(q)}</option>`).join('')}</select><button class="subtle-btn" data-copy-context>复制恢复摘要</button></div>`;
  }
  function renderOverview() {
    const verified = state.verified_count || 0, total = state.stage_count || state.stages.length || 10;
    const facts = context?.facts || [];
    return `<div class="page-title"><div><span class="eyebrow">MathModel Pro · 项目上下文</span><h1>${esc(state.project)}</h1><p>从实际文件恢复判断，接着完成当前问题。</p></div>${badge(state.status || 'pending')}</div>${questionPicker()}<div class="context-next"><div><span class="metric-label">下一步</span><p>${esc(state.next_action || '读取当前验证状态…')}</p></div><button class="subtle-btn" data-view="workflow">查看验证 →</button></div><div class="metric-strip"><div><span class="metric-label">已验证阶段</span><strong>${verified}<small> / ${total}</small></strong></div><div><span class="metric-label">当前阶段</span><strong>${esc(state.stage || 'P0')}</strong></div><div><span class="metric-label">活动实验</span><strong>${state.jobs.filter(j=>active(j.status)).length}<small> 个</small></strong></div></div><section class="panel"><div class="panel-head"><div><h2>接下来需要知道的事</h2><span>每条记录保留来源与当前有效性</span></div></div><div class="facts">${facts.length ? facts.map(factCard).join('') : empty('还没有题意共识或模型路线。在 Codex 对话中开始审题，完成后这里会同步。')}</div>${contextCursor !== null ? '<button class="load-more" data-more-context>读取更多上下文</button>' : ''}</section><section class="panel"><div class="panel-head"><h2>最新产物</h2><span>${files().length} 个登记文件</span></div><div class="artifact-row">${files().slice(-6).map(chip).join('') || empty('尚无登记产物。')}</div></section>`;
  }
  function renderWorkflow() {
    return `<div class="page-title"><div><span class="eyebrow">Pro · P0–P9</span><h1>建模流程</h1><p>展开阶段查看当前验证依据和阻塞原因。</p></div><button class="subtle-btn" data-run-check="evidence_check">检查证据</button></div><section class="panel">${stageTable()}</section><section class="panel"><div class="panel-head"><h2>活动记录</h2><span>活动完成不会授予阶段通过</span></div>${eventList()}</section>`;
  }
  function jobList() {
    return state.jobs.length ? state.jobs.map(j=>`<div class="job-line"><div><strong>${esc(jobNames[j.type] || j.type)}</strong><small class="mono">${esc(j.id?.slice(0,12))} · ${fmt(j.started_at || j.created_at)}</small></div>${badge(j.status)}<div class="job-actions"><button class="subtle-btn" data-job="${esc(j.id)}">日志</button>${active(j.status) ? `<button class="subtle-btn danger" data-cancel="${esc(j.id)}" ${j.status==='cancelling'?'disabled':''}>停止</button>` : ['failed','interrupted','cancelled'].includes(j.status) ? `<button class="subtle-btn" data-retry="${esc(j.id)}">重试</button>` : ''}</div></div>`).join('') : empty('当前服务尚无任务记录；已有实验可从下面的运行回执读取。');
  }
  function renderExperiments() {
    const outputs = files().filter(f=>/results|figures|tables/.test(f.path));
    const receipts=files().filter(f=>/\/experiments\/[^/]+\/receipt\.json$/.test(f.path));
    const runs=receipts.map(r=>{const directory=r.path.slice(0,-'receipt.json'.length);const related=files().filter(f=>f.path.startsWith(directory) && /metrics\.json$|stdout\.log$|stderr\.log$/.test(f.path));return `<div class="recorded-run"><h3>${esc(directory.split('/').filter(Boolean).pop())}</h3><div class="artifact-row">${[r,...related].map(chip).join('')}</div></div>`;}).join('');
    return `<div class="page-title"><div><span class="eyebrow">执行与验证分别记录</span><h1>实验结果</h1><p>运行结束后，仍需通过数值、约束和证据检查。</p></div></div><section class="panel"><div class="panel-head"><h2>服务任务</h2><span>${state.jobs.length} 个任务</span></div>${jobList()}</section><section class="panel"><div class="panel-head"><h2>已有运行回执</h2><span>${receipts.length} 个登记回执 · 有效性见流程验证</span></div>${runs || empty('还没有保存实验回执。')}</section><section class="panel"><div class="panel-head"><h2>科学图表与数据</h2></div><div class="artifact-row">${outputs.map(chip).join('') || empty('等待真实实验产物。')}</div></section>`;
  }
  function previewHTML() {
    if (!selected) return empty('从项目文件中选择题目、代码、图表、表格或论文。');
    const file = selectedMeta();
    if (!file) return empty('文件已删除或不再登记。请重新选择当前产物。');
    return `<div class="preview-head"><span class="mono">${esc(file.path)}</span><a class="subtle-btn" href="${api('/api/artifacts/'+encodeURIComponent(file.id)+'?download=1')}" download>下载</a></div><div id="artifact-preview" data-preview-key="${esc(selected+':'+file.sha256)}">${preview?.id===selected && preview.sha256===file.sha256 ? preview.html : empty('正在读取文件…')}</div>`;
  }
  function renderCode() {
    return `<div class="page-title"><div><span class="eyebrow">实际代码 · 增量日志</span><h1>代码与日志</h1><p>文件保持只读，计算由项目服务持续管理。</p></div><button class="subtle-btn" data-toggle-files>项目文件</button></div><section class="panel preview-panel">${previewHTML()}</section><section class="panel"><div class="panel-head"><h2>${selectedJob ? '实验日志' : '最近日志'}</h2><span id="job-log-status">${esc(selectedJob?.slice(0,12) || '')}</span></div><pre id="live-log" class="log-block">${esc(state.logs || '暂无日志。')}</pre></section>`;
  }
  function renderDelivery() {
    const documents = files().filter(f=>/final_paper|paper_plan|paper_audit|review_board|final_format|pro_gate/.test(f.path));
    return `<div class="page-title"><div><span class="eyebrow">同一源稿 · 可追溯交付</span><h1>论文与交付</h1><p>查看正文、评审问题与真实格式检查结果。</p></div></div><section class="panel"><div class="panel-head"><h2>交付文件</h2><button class="subtle-btn" data-run-check="format_check">检查格式</button></div><div class="artifact-row">${documents.map(chip).join('') || empty('尚未生成正式论文。先完成实验和证据冻结。')}</div></section><section class="panel preview-panel">${previewHTML()}</section>`;
  }
  function render() {
    const oldPreview = $('artifact-preview'), oldKey = oldPreview?.dataset.previewKey;
    const main = document.querySelector('.main-pane'), scroll = main.scrollTop;
    const bodyScroll = window.scrollY;
    const scope=state.guard?.acceptance_scope==='ENGINEERING_SMOKE_ONLY' ? '<div class="scope-note">工程验收项目 · 合成数据与模拟评审记录，不代表竞赛论文通过验收。</div>' : '';
    $('app').innerHTML = scope + ({overview:renderOverview,workflow:renderWorkflow,experiments:renderExperiments,code:renderCode,delivery:renderDelivery}[view])();
    if (oldPreview && $('artifact-preview')?.dataset.previewKey === oldKey) $('artifact-preview').replaceWith(oldPreview);
    main.scrollTop = scroll;
    window.scrollTo(0,bodyScroll);
    document.querySelectorAll('.tab').forEach(tab=>{tab.classList.toggle('active',tab.dataset.view===view);tab.setAttribute('aria-current',tab.dataset.view===view?'page':'false');});
    renderTree();
    $('guard-summary').innerHTML = `<div class="guard-score"><strong>${state.verified_count || 0}</strong><span>/ ${state.stage_count || 10} 阶段已验证</span></div><p class="guard-status">${esc(state.guard?.acceptance_scope === 'ENGINEERING_SMOKE_ONLY' ? '工程测试范围，不是比赛论文验收' : state.guard?.next_action || '等待当前版本验证')}</p>`;
    const running = state.jobs.find(j=>active(j.status));
    $('inspector-task').innerHTML = `<div><strong>${esc(running ? jobNames[running.type] || running.type : names[state.stage] || '等待审题')}</strong><p>${esc(running ? labels[running.status] : state.message || '在对话中继续当前问题')}</p></div>`;
    $('next-action').textContent = state.next_action || '等待 Pro 验证建议';
    $('side-log').innerHTML = eventList();
  }
  function parseCSV(text) {
    const rows=[], row=[]; let cell='', quoted=false;
    for(let i=0;i<text.length && rows.length<200;i++) {
      const c=text[i];
      if(c==='"') {if(quoted && text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
      else if(c===',' && !quoted){row.push(cell);cell='';}
      else if(c==='\n' && !quoted){row.push(cell.replace(/\r$/,''));rows.push(row.splice(0));cell='';}
      else cell+=c;
    }
    if(cell || row.length){row.push(cell);rows.push(row);}
    return `<div class="table-scroll"><table>${rows.map((r,i)=>`<tr>${r.slice(0,30).map(c=>`<${i?'td':'th'}>${esc(c)}</${i?'td':'th'}>`).join('')}</tr>`).join('')}</table></div><small class="preview-note">预览最多 200 行、30 列；下载可读取完整数据。</small>`;
  }
  function pdfPageHTML(id, info, page) {
    const limit=info.preview_page_count;
    return `<div class="pdf-controls"><button class="subtle-btn" data-pdf-page="${page-1}" ${page===0?'disabled':''}>上一页</button><span>第 ${page+1} / ${info.page_count} 页</span><button class="subtle-btn" data-pdf-page="${page+1}" ${page+1>=limit?'disabled':''}>下一页</button></div><div class="pdf-page"><img src="${api('/api/artifacts/'+encodeURIComponent(id)+'/pdf-page?page='+page)}" alt="PDF 第 ${page+1} 页"></div>${limit<info.page_count?`<p class="preview-note">此处最多预览 ${limit} 页，可下载完整 PDF。</p>`:''}`;
  }
  async function openArtifact(id) {
    selected=id; preview=null;
    const file = selectedMeta();
    if (!file) return notice('文件已失效，请刷新后重新选择。',true);
    view = /final_paper.*\.(pdf|docx|md)$/i.test(file.path) ? 'delivery' : 'code';
    render();
    try {
      const url=api('/api/artifacts/'+encodeURIComponent(id));
      const ext=file.path.split('.').pop().toLowerCase();
      let html, pdfInfo;
      if (['png','jpg','jpeg','webp','gif'].includes(ext)) html=`<figure class="scientific-figure"><img src="${url}" alt="${esc(file.path.split('/').pop())}"><figcaption>${esc(file.path)}</figcaption></figure>`;
      else if (ext==='pdf') {pdfInfo=await request('/api/artifacts/'+encodeURIComponent(id)+'/pdf-info');html=pdfInfo.needs_password?empty('此 PDF 需要密码。请下载后打开，或先生成无密码的论文预览版。'):pdfInfo.preview_page_count?pdfPageHTML(id,pdfInfo,0):empty('PDF 没有可预览页面。');}
      else if (['docx','zip','xlsx','xls'].includes(ext)) html=empty('此文件可下载；论文请同时选择 PDF 或 Markdown 预览。');
      else {
        if (file.size>2*1024*1024) html=empty('文本超过 2 MiB 预览上限，请下载完整文件。');
        else {
          const response=await fetch(url,{cache:'no-store'});
          if(!response.ok) throw new Error(`读取失败 (${response.status})`);
          const text=await response.text();
          if(ext==='csv') html=parseCSV(text);
          else if(ext==='md') html=`<article class="markdown-preview">${text.split(/\r?\n/).slice(0,3000).map(line=>/^#{1,4} /.test(line)?`<h3>${esc(line.replace(/^#+ /,''))}</h3>`:`<p>${esc(line) || '&nbsp;'}</p>`).join('')}</article>`;
          else html=`<ol class="code-lines">${text.split(/\r?\n/).slice(0,3000).map(line=>`<li><code>${esc(line) || ' '}</code></li>`).join('')}</ol><small class="preview-note">只读预览 · 最多 3000 行</small>`;
        }
      }
      if(selected!==id) return;
      preview={id,html,sha256:file.sha256,pdfInfo,pdfPage:0};
      const slot=$('artifact-preview'); if(slot) slot.innerHTML=html;
    } catch(error) {if(selected===id){preview={id,sha256:file.sha256,html:empty(error.message)};if($('artifact-preview'))$('artifact-preview').innerHTML=preview.html;}}
  }
  async function loadContext(append=false) {
    const requestedQuestion=question;
    const query = new URLSearchParams({max_chars:'8000',cursor:String(append ? contextCursor || 0 : 0)});
    if(append && context?.pagination?.source_revision) query.set('source_revision',context.pagination.source_revision);
    if(question) query.set('question_id',question);
    const result=await request('/api/context?'+query);
    if(requestedQuestion!==question) return;
    if(!append && context?.focus?.question_id === result.focus?.question_id && context?.pagination?.source_revision === result.pagination?.source_revision && context.facts.length > result.facts.length) {
      context={...result,facts:context.facts}; return;
    }
    context=append && context ? {...result,facts:[...context.facts,...result.facts]} : result;
    contextCursor=result.pagination?.next_cursor ?? null;
  }
  async function refresh(force=false) {
    if(busy) return;
    busy=true;
    try {
      const incoming=await request('/api/status'+(!force && revision!==null?'?after_revision='+revision:''));
      if(!incoming.unchanged) {
        let cursor=incoming.artifacts_next_cursor;
        const allFiles=new Map((incoming.artifacts || []).map(f=>[f.id,f]));
        while(cursor!==null && cursor!==undefined) {
          const page=await request('/api/artifacts?cursor='+cursor+'&limit=200');
          (page.items || []).forEach(f=>allFiles.set(f.id,f));
          if(page.next_cursor!==null && page.next_cursor<=cursor) throw new Error('文件分页没有前进，请重试');
          cursor=page.next_cursor;
        }
        incoming.artifacts=[...allFiles.values()];
        state={...state,...incoming}; revision=incoming.revision;
        state.stages=(incoming.stages || []).map(s=>({...s,name:s.name || names[s.code] || s.code}));
        contextDirty=true;
      }
      if(contextDirty) {
        await loadContext(); contextDirty=false;
        render();
      }
      if(selected && selectedMeta() && preview?.sha256!==selectedMeta().sha256 && ['code','delivery'].includes(view)) await openArtifact(selected);
      $('project-name').textContent=state.project;
      $('project-path').textContent=state.project_root || '';
      $('connection-label').innerHTML='<i class="online"></i>已连接';
      $('last-sync').textContent=fmt(new Date());
      if(first){notice('');first=false;}
      if(selectedJob && view==='code') {
        const selectedId=selectedJob, saved=jobLogs.get(selectedId) || {cursor:0,text:''};
        const job=await request('/api/jobs/'+encodeURIComponent(selectedId)+'?cursor='+saved.cursor+'&limit=64000');
        saved.text=(saved.text+(job.log || '')).slice(-128000); saved.cursor=job.next_cursor ?? saved.cursor;
        jobLogs.set(selectedId,saved);
        if(selectedJob!==selectedId) return;
        const log=$('live-log'); if(log){const bottom=log.scrollTop+log.clientHeight>=log.scrollHeight-24;const y=log.scrollTop;log.textContent=saved.text || job.error || '等待日志…';log.scrollTop=bottom?log.scrollHeight:y;}
        if($('job-log-status')) $('job-log-status').textContent=`${labels[job.status] || job.status} · 退出码 ${job.exit_code ?? '—'}${job.has_more?' · 继续读取中':''}${job.log_truncated?' · 日志已达上限':''}`;
      }
    } catch(error) {
      $('connection-label').innerHTML='<i class="offline"></i>连接中断';
      notice(`${error.message}。保留当前视图，稍后自动重连。`,true);
    } finally {busy=false;}
  }
  async function submit(type, options={}) {
    const result=await request('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type,options})});
    notice('任务已提交，可在实验页查看运行与日志。');
    view='experiments'; await refresh(true); return result;
  }
  async function copyContext() {
    if(!context || (context.focus?.question_id || '')!==question) await loadContext();
    if(!context || (context.focus?.question_id || '')!==question) throw new Error('问题已切换，等待当前问题的上下文读取后再复制。');
    const text=[`继续 ${question || '当前'} 建模任务：${state.project_root}`,`下一步：${state.next_action}`,...(context?.facts || []).map(f=>`${f.title} [${f.state}]：${JSON.stringify(f.value)}\n来源：${f.source.path}#${f.source.pointer}`),'请先读取新的 Pro 状态与上下文包，核验来源版本。'].join('\n\n');
    try {await navigator.clipboard.writeText(text);notice('恢复摘要已复制，可粘贴到 Codex 对话。');}
    catch {notice('剪贴板不可用；可在对话中说“读取当前项目的恢复包”。',true);}
  }
  document.addEventListener('click', async event=>{
    const b=event.target.closest('button');if(!b) return;
    try {
      if(b.dataset.view){view=b.dataset.view;render();}
      if(b.dataset.file) await openArtifact(b.dataset.file);
      if(b.hasAttribute('data-pdf-page') && preview?.pdfInfo) {const page=Number(b.dataset.pdfPage);if(Number.isInteger(page) && page>=0 && page<preview.pdfInfo.preview_page_count){preview.pdfPage=page;preview.html=pdfPageHTML(selected,preview.pdfInfo,page);$('artifact-preview').innerHTML=preview.html;}}
      if(b.dataset.folder){folders.has(b.dataset.folder)?folders.delete(b.dataset.folder):folders.add(b.dataset.folder);renderTree();}
      if(b.hasAttribute('data-more-context')){await loadContext(true);render();}
      if(b.hasAttribute('data-copy-context'))await copyContext();
      if(b.hasAttribute('data-toggle-files')){const shell=document.querySelector('.shell'); if(innerWidth<=780){shell.classList.remove('files-hidden');shell.classList.toggle('files-open');}else shell.classList.toggle('files-hidden');}
      if(b.dataset.job){selectedJob=b.dataset.job;view='code';render();await refresh(true);}
      if(b.dataset.cancel){b.disabled=true;await request('/api/jobs/'+encodeURIComponent(b.dataset.cancel)+'/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});await refresh(true);}
      if(b.dataset.retry){b.disabled=true;await request('/api/jobs/'+encodeURIComponent(b.dataset.retry)+'/retry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({idempotency_key:crypto.randomUUID()})});notice('已创建独立重试，原实验与日志已保留。');await refresh(true);}
      if(b.dataset.runCheck){b.disabled=true;await submit(b.dataset.runCheck);}
    } catch(error){notice(error.message,true);} finally{b.disabled=false;}
  });
  $('app').addEventListener('error',event=>{if(event.target.tagName==='IMG')notice('当前图像或 PDF 页读取失败。重新选择文件可重试，原文件仍可下载。',true);},true);
  $('app').addEventListener('change',async event=>{if(event.target.id==='question-picker'){question=event.target.value;try{await loadContext();render();}catch(error){notice(error.message,true);}}});
  $('app').addEventListener('toggle',event=>{if(event.target.dataset.stage){event.target.open?details.add(event.target.dataset.stage):details.delete(event.target.dataset.stage);}},true);
  $('refresh-button').addEventListener('click',()=>refresh(true));
  $('run-check').addEventListener('click',()=>submit('evidence_check').catch(error=>notice(error.message,true)));
  $('copy-next').addEventListener('click',copyContext);
  $('collapse-files').addEventListener('click',()=>{const shell=document.querySelector('.shell');shell.classList.remove('files-open');shell.classList.add('files-hidden');});
  const scheme=matchMedia('(prefers-color-scheme: light)');
  document.documentElement.dataset.theme=localStorage.getItem('mathmodel-theme') || (scheme.matches?'light':'dark');
  scheme.addEventListener('change',()=>{if(!localStorage.getItem('mathmodel-theme'))document.documentElement.dataset.theme=scheme.matches?'light':'dark';});
  $('theme-toggle').addEventListener('click',()=>{const value=document.documentElement.dataset.theme==='light'?'dark':'light';document.documentElement.dataset.theme=value;localStorage.setItem('mathmodel-theme',value);});
  document.addEventListener('keydown',event=>{if(event.ctrlKey || event.metaKey || event.altKey || event.target.closest('input,textarea,select'))return;const v=['overview','workflow','experiments','code','delivery'][+event.key-1];if(v){view=v;render();}});
  render();refresh(true);setInterval(()=>refresh(),4000);
})();
