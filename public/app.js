const root = document.querySelector('#app');
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date = value => new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));
let user = null;

async function api(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { 'Content-Type':'application/json', ...(options.headers || {}) } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed.');
  return data;
}
function notice(message, type='error') {
  const el = document.querySelector('#notice');
  if (!el) return;
  el.textContent = message; el.className = `notice ${type}`; el.hidden = false;
  window.setTimeout(() => { if (el) el.hidden = true; }, 4500);
}
function loginView() {
  root.innerHTML = `<main class="login-shell"><section class="login-card"><div class="brand-mark">N</div><p class="eyebrow">NORTHSTAR · IT SERVICES</p><h1>Good to have you here.</h1><p class="muted">Sign in to get your team back on track.</p><div id="notice" class="notice" hidden></div><form id="login-form"><label>Email address<input name="email" type="email" placeholder="you@company.com" autocomplete="username" required></label><label>Password<input name="password" type="password" placeholder="Enter your password" autocomplete="current-password" required></label><button class="button primary full" type="submit">Sign in <span>→</span></button></form><div class="demo"><b>Assessment demo accounts</b><span>Employee: sara@example.com · Employee123!</span><span>IT Support: omar@example.com · Support123!</span></div></section><aside class="login-art"><div class="orb"></div><div class="art-copy"><span class="eyebrow">SERVICE DESK · 01</span><h2>IT should work<br>for everyone.</h2><p>One place to get help, keep work moving, and know what happens next.</p></div><div class="art-foot">A calmer way to solve tech problems <span>✳</span></div></aside></main>`;
  document.querySelector('#login-form').addEventListener('submit', async e => {
    e.preventDefault(); const button=e.currentTarget.querySelector('button'); button.disabled=true;
    try { const data=await api('/api/login',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(e.currentTarget)))}); user=data.user; await dashboard(); }
    catch(error){ notice(error.message); button.disabled=false; }
  });
}
function shell(content, active='Overview') {
  const support = user.role === 'support';
  root.innerHTML = `<div class="shell"><aside class="sidebar"><a class="brand" href="#"><span class="brand-mark small">N</span><span>northstar<small>IT SERVICE DESK</small></span></a><div class="workspace"><span class="workspace-icon">${support?'✳':'◈'}</span><span>${support?'Support team':'Employee portal'}<small>${support?'OPERATIONS':'MY WORKSPACE'}</small></span><span class="chevron">⌄</span></div><p class="nav-label">WORKSPACE</p><nav><a class="nav-item active"><span>▦</span>Overview</a><a class="nav-item" id="tickets-link"><span>▤</span>${support?'All tickets':'My tickets'}<span class="nav-count" id="nav-count">–</span></a>${!support?'<a class="nav-item" id="new-link"><span>＋</span>New request</a>':''}</nav><div class="sidebar-bottom"><div class="help-card"><div class="help-icon">✦</div><b>Need a hand?</b><p>Our support team is here to help you get back to work.</p><a href="mailto:helpdesk@example.com">Contact IT <span>↗</span></a></div><button class="profile" id="logout"><span class="avatar">${esc(user.name.split(' ').map(n=>n[0]).join('').slice(0,2))}</span><span><b>${esc(user.name)}</b><small>${support?'IT Support':'Employee'}</small></span><span class="dots">···</span></button></div></aside><main class="main"><header class="topbar"><div class="crumb">Workspace <span>/</span> <b id="crumb-current">${active}</b></div><div class="top-actions"><span class="today" id="today"></span><span class="top-avatar">${esc(user.name[0])}</span></div></header><div class="content">${content}</div></main></div>`;
  document.querySelector('#today').textContent=new Intl.DateTimeFormat(undefined,{weekday:'short',month:'short',day:'numeric'}).format(new Date());
  document.querySelector('#logout').onclick=async()=>{await api('/api/logout',{method:'POST'});user=null;loginView();};
  document.querySelector('#tickets-link').onclick=()=>ticketList();
  const newLink=document.querySelector('#new-link'); if(newLink)newLink.onclick=()=>newTicket();
}
function metricsCards(metrics={}) { return `<section class="metric-grid"><article class="metric-card"><span>Total tickets</span><b>${metrics.total||0}</b><small class="metric-icon blue">▤</small></article><article class="metric-card"><span>Open tickets</span><b>${metrics.open||0}</b><small class="metric-icon amber">◷</small></article><article class="metric-card"><span>In progress</span><b>${metrics.inProgress||0}</b><small class="metric-icon violet">↗</small></article><article class="metric-card"><span>Resolved</span><b>${metrics.resolved||0}</b><small class="metric-icon green">✓</small></article></section>`; }
function table(tickets, title) {
  if (!tickets.length) return `<section class="panel empty"><div class="empty-mark">▤</div><h3>No tickets yet</h3><p>When requests come in, they’ll show up here.</p>${user.role==='employee'?'<button class="button primary" id="empty-new">Create your first ticket <span>→</span></button>':''}</section>`;
  return `<section class="panel"><div class="panel-head"><div><h2>${title}</h2><p>Stay up to date on every request.</p></div><span class="subtle-count">${tickets.length} ${tickets.length===1?'request':'requests'}</span></div><div class="table-scroll"><table><thead><tr><th>REQUEST</th><th>STATUS</th><th>PRIORITY</th><th>${user.role==='support'?'REQUESTER':'CREATED'}</th><th></th></tr></thead><tbody>${tickets.map(t=>`<tr class="ticket-row" data-id="${t.id}"><td><div class="ticket-title">${esc(t.title)}</div><div class="ticket-meta">HD-${String(t.id).padStart(4,'0')} · ${esc(t.category)}</div></td><td><span class="status status-${t.status.toLowerCase().replaceAll(' ','-')}"><i></i>${esc(t.status)}</span></td><td><span class="priority priority-${t.priority.toLowerCase()}"><i></i>${esc(t.priority)}</span></td><td><span class="date-cell">${user.role==='support'?esc(t.created_by_name):date(t.created_at)}</span></td><td class="arrow">↗</td></tr>`).join('')}</tbody></table></div></section>`;
}
async function dashboard() {
  try {
    const {tickets,metrics}=await api('/api/tickets');
    shell(`<div class="welcome"><div><span class="eyebrow">${user.role==='support'?'SUPPORT OPERATIONS':'YOUR WORKSPACE'}</span><h1>${user.role==='support'?'Good morning':'Welcome back'}, ${esc(user.name.split(' ')[0])}<span class="wave">✳</span></h1><p>${user.role==='support'?'Here’s what’s happening across the helpdesk today.':'Here’s a snapshot of your IT support requests.'}</p></div>${user.role==='employee'?'<button class="button primary" id="hero-new">＋ <span>New request</span></button>':''}</div>${metricsCards(metrics)}${table(tickets,user.role==='support'?'Recent tickets':'Your recent requests')}`,'Overview');
    const badge=document.querySelector('#nav-count'); if(badge)badge.textContent=tickets.length;
    const add=document.querySelector('#hero-new');if(add)add.onclick=()=>newTicket();
    const empty=document.querySelector('#empty-new');if(empty)empty.onclick=()=>newTicket();
    document.querySelectorAll('.ticket-row').forEach(row=>row.onclick=()=>ticketDetails(row.dataset.id));
  } catch(error) { loginView(); }
}
async function ticketList() {
  const {tickets,metrics}=await api('/api/tickets');
  shell(`<div class="welcome"><div><span class="eyebrow">${user.role==='support'?'SUPPORT OPERATIONS':'YOUR WORKSPACE'}</span><h1>${user.role==='support'?'All tickets':'My tickets'}</h1><p>Review the latest requests and their status.</p></div>${user.role==='employee'?'<button class="button primary" id="hero-new">＋ <span>New request</span></button>':''}</div>${metricsCards(metrics)}${table(tickets,user.role==='support'?'All tickets':'Your requests')}`,'Tickets');
  document.querySelectorAll('.ticket-row').forEach(row=>row.onclick=()=>ticketDetails(row.dataset.id));
  const add=document.querySelector('#hero-new');if(add)add.onclick=()=>newTicket();
  const empty=document.querySelector('#empty-new');if(empty)empty.onclick=()=>newTicket();
}
function newTicket() {
  shell(`<div class="welcome"><div><span class="eyebrow">NEW REQUEST · STEP 1 OF 1</span><h1>Tell us what’s going on.</h1><p>Share a few details and we’ll get the right person on it.</p></div></div><section class="form-panel"><div id="notice" class="notice" hidden></div><form id="ticket-form"><label>What do you need help with?<input name="title" maxlength="160" placeholder="e.g. Can't connect to office Wi-Fi" required></label><label>Tell us a little more<textarea name="description" rows="5" placeholder="What happened? What have you tried so far?" required></textarea></label><div class="form-row"><label>Category<select name="category" required><option value="">Select a category</option>${['Hardware','Software','Network','Email','Access Issue','Other'].map(x=>`<option>${x}</option>`).join('')}</select></label><label>Priority<select name="priority"><option>Low</option><option selected>Medium</option><option>High</option><option>Critical</option></select></label></div><div class="form-actions"><button class="button secondary" type="button" id="cancel">Cancel</button><button class="button primary" type="submit">Submit request <span>→</span></button></div></form></section>`,'New request');
  document.querySelector('#cancel').onclick=dashboard;
  document.querySelector('#ticket-form').onsubmit=async e=>{e.preventDefault();const button=e.currentTarget.querySelector('[type=submit]');button.disabled=true;try{const data=await api('/api/tickets',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(e.currentTarget)))});await ticketDetails(data.id,true);}catch(error){notice(error.message);button.disabled=false;}};
}
async function ticketDetails(id, created=false) {
  const {ticket:t}=await api(`/api/tickets/${id}`);
  shell(`<div class="welcome"><div><button class="back-link" id="back">← Back to tickets</button><span class="eyebrow">REQUEST HD-${String(t.id).padStart(4,'0')}</span><h1>${esc(t.title)}</h1><p>Submitted by ${esc(t.created_by_name)} · ${date(t.created_at)}</p></div></div>${created?'<div class="notice success">Your request is in. The support team will take it from here.</div>':''}<section class="details-grid"><article class="panel detail-main"><div class="detail-top"><div><span class="status status-${t.status.toLowerCase().replaceAll(' ','-')}"><i></i>${esc(t.status)}</span> <span class="priority priority-${t.priority.toLowerCase()}"><i></i>${esc(t.priority)}</span></div><span class="subtle-count">Updated ${date(t.updated_at)}</span></div><h2>Request details</h2><p class="description">${esc(t.description).replaceAll('\n','<br>')}</p></article><aside class="panel detail-side"><h3>Request information</h3><dl><dt>Category</dt><dd>${esc(t.category)}</dd><dt>Priority</dt><dd>${esc(t.priority)}</dd><dt>Status</dt><dd>${esc(t.status)}</dd><dt>Assigned to</dt><dd>${esc(t.assigned_to_name||'Not assigned yet')}</dd><dt>Created</dt><dd>${date(t.created_at)}</dd></dl></aside></section>`,'Ticket details');
  document.querySelector('#back').onclick=()=>ticketList();
}
async function boot() { try { user=(await api('/api/me')).user; await dashboard(); } catch { loginView(); } }
boot();
