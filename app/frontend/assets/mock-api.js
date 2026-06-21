(function () {
  const params = new URLSearchParams(location.search);
  const isMock = params.get('mock') === '1' || !window.API_BASE_OVERRIDE && (location.hostname === '' || location.protocol === 'file:' || params.get('mock') !== '0');

  const STATUSES = ['PENDING', 'ALLOCATED', 'ACTIVE', 'SUSPENDED', 'PORTED', 'RECYCLED'];
  const STATUS_DIST = { PENDING: 0.12, ALLOCATED: 0.15, ACTIVE: 0.55, SUSPENDED: 0.08, PORTED: 0.06, RECYCLED: 0.04 };
  const PLANS = [
    { id: 'PLN-PRE-99',  name: 'Prepaid Lite',     data_gb: 1.5,  voice_min: 200,  sms_count: 100, monthly_inr: 99  },
    { id: 'PLN-PRE-249', name: 'Prepaid Smart',    data_gb: 30,   voice_min: 2000, sms_count: 100, monthly_inr: 249 },
    { id: 'PLN-PRE-399', name: 'Prepaid Max',      data_gb: 75,   voice_min: 3000, sms_count: 100, monthly_inr: 399 },
    { id: 'PLN-POST-499',name: 'Postpaid Essential',data_gb: 50,  voice_min: 3000, sms_count: 100, monthly_inr: 499 },
    { id: 'PLN-POST-799',name: 'Postpaid Plus',    data_gb: 100,  voice_min: 5000, sms_count: 200, monthly_inr: 799 },
    { id: 'PLN-IOT-49',  name: 'IoT Connect',      data_gb: 0.5,  voice_min: 0,    sms_count: 0,   monthly_inr: 49  }
  ];

  let seed = 0xCAFE1234;
  function rng() {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 0xFFFFFFFF;
  }
  function pickStatus() {
    const r = rng(); let acc = 0;
    for (const s of STATUSES) { acc += STATUS_DIST[s]; if (r < acc) return s; }
    return 'ACTIVE';
  }
  function pad(n, w) { return String(n).padStart(w, '0'); }
  function iccid(i) { return '8991' + pad(70000000000 + i * 7, 11) + pad((i * 31) % 10, 1); }
  function imsi(i)  { return '40410' + pad(2000000 + i * 3, 10); }
  function msisdn(i){ return '+9198' + pad(70000000 + i * 11, 8); }

  const TOTAL = 5000;
  const SIMS = [];
  const now = Date.now();
  for (let i = 0; i < TOTAL; i++) {
    const status = pickStatus();
    const plan = PLANS[Math.floor(rng() * PLANS.length)];
    const activated = (status === 'ACTIVE' || status === 'SUSPENDED' || status === 'PORTED')
      ? new Date(now - Math.floor(rng() * 90 * 86400 * 1000)).toISOString() : null;
    SIMS.push({
      iccid: iccid(i),
      imsi: imsi(i),
      msisdn: status === 'PENDING' ? null : msisdn(i),
      status,
      plan_id: plan.id,
      activated_at: activated
    });
  }

  const AUDIT = [];
  const ACTORS = ['ops.kavya', 'ops.rohan', 'system.worker', 'api.bulk', 'cs.team'];
  const REASONS = ['Customer KYC complete', 'Auto-suspend (overdue)', 'Port-out request', 'Bulk activation batch', 'Manual reactivation', 'Recycle policy 90d'];
  for (let i = 0; i < 200; i++) {
    const sim = SIMS[Math.floor(rng() * SIMS.length)];
    const from = STATUSES[Math.floor(rng() * 4)];
    let to = STATUSES[Math.floor(rng() * STATUSES.length)];
    if (to === from) to = 'ACTIVE';
    AUDIT.push({
      ts: new Date(now - i * 60000 - Math.floor(rng() * 30000)).toISOString(),
      iccid: sim.iccid,
      from, to,
      actor: ACTORS[Math.floor(rng() * ACTORS.length)],
      reason: REASONS[Math.floor(rng() * REASONS.length)]
    });
  }

  function recentActivations() {
    const out = [];
    for (let h = 23; h >= 0; h--) {
      const base = 40 + Math.floor(60 * Math.abs(Math.sin((24 - h) / 3.4)));
      const noise = Math.floor(rng() * 25);
      const sus = Math.floor(rng() * 18) + 5;
      out.push({
        ts: new Date(now - h * 3600 * 1000).toISOString(),
        activated: base + noise,
        suspended: sus
      });
    }
    return out;
  }

  function computeStats() {
    const by_status = {};
    STATUSES.forEach(s => by_status[s] = 0);
    SIMS.forEach(s => by_status[s.status]++);
    const top = PLANS.map(p => ({
      plan: p.name, plan_id: p.id,
      count: SIMS.filter(s => s.plan_id === p.id && s.status === 'ACTIVE').length
    })).sort((a, b) => b.count - a.count);
    return {
      total: SIMS.length,
      by_status,
      activations_last_24h: recentActivations(),
      top_plans: top,
      mean_activation_latency_ms: 1840 + Math.floor(rng() * 300)
    };
  }

  function ok(data) {
    return Promise.resolve(new Response(JSON.stringify(data), {
      status: 200, headers: { 'content-type': 'application/json' }
    }));
  }

  function notFound() {
    return Promise.resolve(new Response(JSON.stringify({ error: 'not found' }), { status: 404 }));
  }

  function route(url, init) {
    const u = new URL(url, 'http://mock');
    const p = u.pathname;
    const q = u.searchParams;

    if (p === '/healthz') return ok({ status: 'ok', uptime_s: 3812, version: '0.1.0' });
    if (p === '/api/v1/stats') return ok(computeStats());
    if (p === '/api/v1/plans') return ok({ items: PLANS });

    if (p === '/api/v1/sims') {
      const status = q.get('status');
      const plan = q.get('plan_id');
      const search = (q.get('q') || '').toLowerCase();
      const limit = Math.min(parseInt(q.get('limit') || '50', 10), 500);
      const offset = parseInt(q.get('offset') || '0', 10);
      let arr = SIMS;
      if (status) arr = arr.filter(s => s.status === status);
      if (plan) arr = arr.filter(s => s.plan_id === plan);
      if (search) arr = arr.filter(s => s.iccid.includes(search) || (s.msisdn || '').includes(search));
      const total = arr.length;
      return ok({ items: arr.slice(offset, offset + limit), total });
    }

    const simDetail = p.match(/^\/api\/v1\/sims\/(\d+)$/);
    if (simDetail) {
      const sim = SIMS.find(s => s.iccid === simDetail[1]);
      return sim ? ok(sim) : notFound();
    }

    const transition = p.match(/^\/api\/v1\/sims\/(\d+)\/(allocate|activate|suspend|resume|port|recycle)$/);
    if (transition && init && (init.method || '').toUpperCase() === 'POST') {
      const sim = SIMS.find(s => s.iccid === transition[1]);
      if (!sim) return notFound();
      const action = transition[2];
      const next = { allocate: 'ALLOCATED', activate: 'ACTIVE', suspend: 'SUSPENDED', resume: 'ACTIVE', port: 'PORTED', recycle: 'RECYCLED' }[action];
      const from = sim.status;
      sim.status = next;
      if (next === 'ACTIVE' && !sim.activated_at) sim.activated_at = new Date().toISOString();
      AUDIT.unshift({
        ts: new Date().toISOString(), iccid: sim.iccid,
        from, to: next, actor: 'ops.console', reason: 'Manual ' + action
      });
      return ok(sim);
    }

    if (p === '/api/v1/audit') {
      const limit = Math.min(parseInt(q.get('limit') || '50', 10), 500);
      const since = q.get('since');
      let arr = AUDIT;
      if (since) arr = arr.filter(e => e.ts > since);
      else {
        if (rng() < 0.6) {
          const sim = SIMS[Math.floor(rng() * SIMS.length)];
          AUDIT.unshift({
            ts: new Date().toISOString(), iccid: sim.iccid,
            from: sim.status, to: 'ACTIVE', actor: ACTORS[Math.floor(rng() * ACTORS.length)],
            reason: REASONS[Math.floor(rng() * REASONS.length)]
          });
          arr = AUDIT;
        }
      }
      return ok({ events: arr.slice(0, limit) });
    }

    if (p === '/api/v1/health/components') {
      return ok({
        components: [
          { name: 'API Gateway',   status: 'ok',   latency_ms: 12, samples: pingSeries(24, 0.95) },
          { name: 'PostgreSQL',    status: 'ok',   latency_ms: 6,  samples: pingSeries(24, 0.98) },
          { name: 'HLR Adapter',   status: 'warn', latency_ms: 187,samples: pingSeries(24, 0.78) },
          { name: 'Vault',         status: 'ok',   latency_ms: 9,  samples: pingSeries(24, 0.99) },
          { name: 'Worker Queue',  status: 'ok',   latency_ms: 21, samples: pingSeries(24, 0.92) },
          { name: 'Prometheus',    status: 'ok',   latency_ms: 14, samples: pingSeries(24, 0.97) }
        ]
      });
    }

    return notFound();
  }

  function pingSeries(n, okRate) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const r = rng();
      out.push(r < okRate ? 'ok' : (r < okRate + 0.06 ? 'warn' : 'err'));
    }
    return out;
  }

  if (isMock) {
    const orig = window.fetch.bind(window);
    window.fetch = function (input, init) {
      const url = typeof input === 'string' ? input : input.url;
      try {
        const u = new URL(url, location.origin);
        if (u.pathname.startsWith('/api/') || u.pathname === '/healthz' || (window.API_BASE && url.startsWith(window.API_BASE))) {
          return route(url.replace(window.API_BASE || '', ''), init);
        }
      } catch (e) {}
      return orig(input, init);
    };
    window.__MOCK_API__ = true;
  }
})();
