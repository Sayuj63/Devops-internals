(function () {
  const params = new URLSearchParams(location.search);
  const API_BASE = params.get('api') || window.API_BASE_OVERRIDE || 'http://localhost:8000';
  window.API_BASE = API_BASE;

  const STATUS_COLORS = {
    PENDING: '#94A3B8', ALLOCATED: '#8B5CF6', ACTIVE: '#10B981',
    SUSPENDED: '#F59E0B', PORTED: '#22D3EE', RECYCLED: '#EF4444'
  };
  const STATE_FLOW = [
    ['PENDING', 'ALLOCATED'], ['ALLOCATED', 'ACTIVE'], ['ACTIVE', 'SUSPENDED'],
    ['SUSPENDED', 'ACTIVE'], ['ACTIVE', 'PORTED'], ['ALLOCATED', 'RECYCLED']
  ];

  const fmt = {
    n: x => x == null ? '—' : x.toLocaleString('en-IN'),
    iccid: s => s ? s.replace(/(\d{4})(\d{4})(\d{4})(\d{4})(\d+)/, '$1 $2 $3 $4 $5') : '—',
    msisdn: s => s || '—',
    timeAgo: t => {
      if (!t) return '—';
      const d = (Date.now() - new Date(t).getTime()) / 1000;
      if (d < 60) return Math.floor(d) + 's';
      if (d < 3600) return Math.floor(d / 60) + 'm';
      if (d < 86400) return Math.floor(d / 3600) + 'h';
      return Math.floor(d / 86400) + 'd';
    },
    clock: () => {
      const d = new Date();
      return [d.getHours(), d.getMinutes(), d.getSeconds()].map(n => String(n).padStart(2, '0')).join(':');
    }
  };

  async function api(path) {
    const r = await fetch(API_BASE + path);
    if (!r.ok) throw new Error(path + ' ' + r.status);
    return r.json();
  }
  window.api = api;
  window.fmt = fmt;
  window.STATUS_COLORS = STATUS_COLORS;

  function setEnvBadge() {
    const el = document.getElementById('env-badge');
    if (!el) return;
    if (window.__MOCK_API__) {
      el.textContent = 'mock';
      el.className = 'ml-2 px-2 py-0.5 rounded-sm text-[10px] font-mono uppercase tracking-wider border border-accent-amber/40 text-accent-amber bg-accent-amber/10';
    } else {
      el.textContent = 'live';
      el.className = 'ml-2 px-2 py-0.5 rounded-sm text-[10px] font-mono uppercase tracking-wider border border-accent-emerald/40 text-accent-emerald bg-accent-emerald/10';
    }
  }

  function setApiBase() {
    const el = document.getElementById('api-base');
    if (el) el.textContent = window.__MOCK_API__ ? 'in-browser mock' : API_BASE;
  }

  function tickClock() {
    const el = document.getElementById('now-clock');
    if (el) el.textContent = fmt.clock();
  }

  function bindHeader() {
    const t = document.getElementById('theme-toggle');
    if (t) t.addEventListener('click', () => {
      const html = document.documentElement;
      html.classList.toggle('dark');
      html.classList.toggle('light');
    });
    const r = document.getElementById('refresh-btn');
    if (r) r.addEventListener('click', () => location.reload());
    document.addEventListener('keydown', e => {
      if (e.key === 'r' && !e.metaKey && !e.ctrlKey && document.activeElement.tagName !== 'INPUT') {
        location.reload();
      }
    });
  }

  function pill(status) {
    return `<span class="status-pill s-${status}">${status}</span>`;
  }
  window.pill = pill;

  function kpiCard(label, value, delta, deltaDir, sparkData, color) {
    const spark = miniSpark(sparkData, color);
    const deltaCls = deltaDir === 'up' ? 'kpi__delta--up' : 'kpi__delta--down';
    const arrow = deltaDir === 'up' ? '↑' : '↓';
    return `<div class="kpi">
      <div class="kpi__label"><span class="status-dot status-dot--ok" style="width:6px;height:6px"></span>${label}</div>
      <div class="kpi__value">${value}</div>
      <div class="kpi__delta ${deltaCls}">${arrow} ${delta}</div>
      ${spark}
    </div>`;
  }

  function miniSpark(values, color) {
    if (!values || !values.length) return '';
    const w = 80, h = 28, n = values.length;
    const mn = Math.min(...values), mx = Math.max(...values);
    const rng = mx - mn || 1;
    const pts = values.map((v, i) => `${(i / (n - 1)) * w},${h - ((v - mn) / rng) * (h - 4) - 2}`).join(' ');
    return `<svg class="kpi__spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
      <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>`;
  }

  async function renderKPIs(stats) {
    const host = document.getElementById('kpi-row');
    if (!host) return;
    const totalActive = stats.by_status.ACTIVE;
    const totalPending = stats.by_status.PENDING + stats.by_status.ALLOCATED;
    const susp = stats.by_status.SUSPENDED;
    const series = stats.activations_last_24h.map(p => p.activated);
    const last24Total = series.reduce((a, b) => a + b, 0);
    host.innerHTML = [
      kpiCard('Active SIMs', fmt.n(totalActive), '2.4% vs 24h', 'up', series, '#10B981'),
      kpiCard('Activations · 24h', fmt.n(last24Total), '11.8% vs prev', 'up', series, '#22D3EE'),
      kpiCard('Pending queue', fmt.n(totalPending), '0.6% vs 24h', 'down', stats.activations_last_24h.map(p => Math.max(0, 80 - p.activated)), '#8B5CF6'),
      kpiCard('Mean activation', stats.mean_activation_latency_ms + ' ms', '4.1% vs SLO', 'up', stats.activations_last_24h.map(p => p.suspended), '#F59E0B')
    ].join('');
  }

  function renderSparkline(data) {
    const host = document.getElementById('sparkline-host');
    if (!host) return;
    const W = host.clientWidth || 720, H = 220;
    const padL = 36, padR = 12, padT = 12, padB = 24;
    const innerW = W - padL - padR, innerH = H - padT - padB;
    const n = data.length;
    const valsA = data.map(d => d.activated);
    const valsS = data.map(d => d.suspended);
    const mx = Math.max(...valsA, ...valsS) * 1.1;
    const ySteps = 4;
    const x = i => padL + (i / (n - 1)) * innerW;
    const y = v => padT + innerH - (v / mx) * innerH;
    const path = vals => vals.map((v, i) => (i === 0 ? 'M' : 'L') + x(i) + ',' + y(v)).join(' ');
    const area = vals => path(vals) + ` L ${x(n - 1)},${padT + innerH} L ${x(0)},${padT + innerH} Z`;
    const grid = [];
    for (let i = 0; i <= ySteps; i++) {
      const yy = padT + (i / ySteps) * innerH;
      const v = Math.round(mx - (i / ySteps) * mx);
      grid.push(`<line class="spark-grid" x1="${padL}" y1="${yy}" x2="${W - padR}" y2="${yy}"/>`);
      grid.push(`<text class="spark-label" x="${padL - 6}" y="${yy + 3}" text-anchor="end">${v}</text>`);
    }
    const xLabels = [];
    for (let i = 0; i < n; i += 4) {
      const d = new Date(data[i].ts);
      xLabels.push(`<text class="spark-label" x="${x(i)}" y="${H - 6}" text-anchor="middle">${String(d.getUTCHours()).padStart(2, '0')}h</text>`);
    }
    host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}">
      <defs>
        <linearGradient id="grad-cyan" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#22D3EE" stop-opacity=".35"/>
          <stop offset="100%" stop-color="#22D3EE" stop-opacity="0"/>
        </linearGradient>
        <linearGradient id="grad-amber" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#F59E0B" stop-opacity=".25"/>
          <stop offset="100%" stop-color="#F59E0B" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${grid.join('')}
      <path class="spark-area-amber" d="${area(valsS)}"/>
      <path class="spark-area-cyan" d="${area(valsA)}"/>
      <path class="spark-line-amber" d="${path(valsS)}"/>
      <path class="spark-line-cyan" d="${path(valsA)}"/>
      ${valsA.map((v, i) => `<circle cx="${x(i)}" cy="${y(v)}" r="2" fill="#22D3EE"/>`).join('')}
      ${xLabels.join('')}
    </svg>`;
  }

  function renderDonut(stats) {
    const host = document.getElementById('donut-host');
    if (!host) return;
    const total = stats.total;
    document.getElementById('donut-total').textContent = fmt.n(total) + ' SIMs';
    const S = 160, r = 60, sw = 16, cx = S / 2, cy = S / 2;
    const C = 2 * Math.PI * r;
    const entries = Object.entries(stats.by_status);
    let acc = 0;
    const segs = entries.map(([k, v]) => {
      const frac = v / total;
      const dasharray = `${(frac * C).toFixed(2)} ${C.toFixed(2)}`;
      const dashoffset = (-acc * C).toFixed(2);
      acc += frac;
      return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${STATUS_COLORS[k]}" stroke-width="${sw}" stroke-dasharray="${dasharray}" stroke-dashoffset="${dashoffset}" transform="rotate(-90 ${cx} ${cy})"><title>${k}: ${v}</title></circle>`;
    }).join('');
    const legend = entries.map(([k, v]) => `<li class="flex items-center gap-2 text-[11px] font-mono">
      <span style="width:8px;height:8px;border-radius:2px;background:${STATUS_COLORS[k]}"></span>
      <span class="text-slate-300 w-20">${k}</span>
      <span class="text-slate-100 ml-auto tabnum">${fmt.n(v)}</span>
      <span class="text-slate-500 w-10 text-right tabnum">${(100 * v / total).toFixed(1)}%</span>
    </li>`).join('');
    host.innerHTML = `<svg viewBox="0 0 ${S} ${S}" width="${S}" height="${S}" class="shrink-0">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#1F2937" stroke-width="${sw}"/>
      ${segs}
      <text class="donut-label-num" x="${cx}" y="${cy + 4}" text-anchor="middle">${fmt.n(stats.by_status.ACTIVE)}</text>
      <text class="donut-label-cap" x="${cx}" y="${cy + 22}" text-anchor="middle">ACTIVE</text>
    </svg>
    <ul class="flex-1 space-y-1.5">${legend}</ul>`;
  }

  function renderRecent(items) {
    const tbody = document.querySelector('#recent-sims-table tbody');
    if (!tbody) return;
    tbody.innerHTML = items.slice(0, 12).map(s => `<tr>
      <td>${fmt.iccid(s.iccid)}</td>
      <td>${fmt.msisdn(s.msisdn)}</td>
      <td>${s.plan_id}</td>
      <td>${pill(s.status)}</td>
      <td class="text-right text-slate-500">${fmt.timeAgo(s.activated_at)}</td>
    </tr>`).join('');
  }

  function renderTopPlans(top) {
    const host = document.getElementById('top-plans');
    if (!host) return;
    const max = Math.max(...top.map(t => t.count), 1);
    host.innerHTML = top.slice(0, 6).map(t => {
      const pct = (100 * t.count / max).toFixed(1);
      return `<div class="bar-row">
        <span class="text-slate-300 truncate">${t.plan}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
        <span class="text-right text-slate-200 tabnum">${fmt.n(t.count)}</span>
      </div>`;
    }).join('');
  }

  function renderStateMachine() {
    const host = document.getElementById('state-machine');
    if (!host) return;
    const nodes = ['PENDING', 'ALLOCATED', 'ACTIVE', 'SUSPENDED', 'PORTED', 'RECYCLED'];
    host.innerHTML = nodes.map((n, i) => {
      const arrow = i < nodes.length - 1 ? '<span class="sm-arrow">→</span>' : '';
      return `<span class="sm-node" style="color:${STATUS_COLORS[n]};border-color:${STATUS_COLORS[n]}33;background:${STATUS_COLORS[n]}10">${n}</span>${arrow}`;
    }).join('');
    host.insertAdjacentHTML('beforeend', `<div class="w-full mt-3 text-[10px] font-mono text-slate-500 leading-relaxed">
      Allowed transitions:<br>${STATE_FLOW.map(([a, b]) => `${a} → ${b}`).join(' · ')}
    </div>`);
  }

  const seenAudit = new Set();
  function renderAuditTail(events, animate) {
    const ul = document.getElementById('audit-tail');
    if (!ul) return;
    const frag = document.createDocumentFragment();
    events.slice(0, 30).forEach(e => {
      const key = e.ts + e.iccid + e.to;
      const isNew = animate && !seenAudit.has(key);
      seenAudit.add(key);
      const li = document.createElement('li');
      if (isNew) li.classList.add('is-new');
      const ts = new Date(e.ts);
      li.innerHTML = `<span class="audit-ts">${String(ts.getHours()).padStart(2, '0')}:${String(ts.getMinutes()).padStart(2, '0')}:${String(ts.getSeconds()).padStart(2, '0')}</span>
        <span class="audit-iccid">${e.iccid.slice(-8)} <span class="audit-arrow">·</span> ${pill(e.from)} <span class="audit-arrow">→</span> ${pill(e.to)}</span>
        <span class="text-slate-500 text-[10px]">${e.actor}</span>`;
      frag.appendChild(li);
    });
    ul.innerHTML = '';
    ul.appendChild(frag);
  }

  async function loadOverview() {
    try {
      const [stats, sims, audit] = await Promise.all([
        api('/api/v1/stats'),
        api('/api/v1/sims?limit=12'),
        api('/api/v1/audit?limit=30')
      ]);
      renderKPIs(stats);
      renderSparkline(stats.activations_last_24h);
      renderDonut(stats);
      renderRecent(sims.items);
      renderTopPlans(stats.top_plans);
      renderStateMachine();
      renderAuditTail(audit.events, false);
    } catch (e) {
      console.error(e);
    }
  }

  async function pollAudit() {
    try {
      const r = await api('/api/v1/audit?limit=30');
      renderAuditTail(r.events, true);
    } catch (e) {}
  }

  function init() {
    setEnvBadge();
    setApiBase();
    tickClock();
    setInterval(tickClock, 1000);
    bindHeader();
    if (document.getElementById('kpi-row')) {
      loadOverview();
      setInterval(pollAudit, 3000);
      window.addEventListener('resize', () => {
        api('/api/v1/stats').then(s => renderSparkline(s.activations_last_24h));
      });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
