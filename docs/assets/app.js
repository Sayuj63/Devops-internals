// SIM-OPS docs interactivity — no external libs.
// Author: Sayuj. Strictly DOM + IntersectionObserver + tiny helpers.

(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ----- Theme toggle -----
  const root = document.documentElement;
  const stored = localStorage.getItem('simops-theme');
  if (stored === 'light' || stored === 'dark') root.setAttribute('data-theme', stored);

  const toggle = $('.theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', next);
      localStorage.setItem('simops-theme', next);
    });
  }

  // ----- Sticky nav scrolled state -----
  const nav = $('.nav');
  if (nav) {
    const setScrolled = () => nav.classList.toggle('scrolled', window.scrollY > 8);
    setScrolled();
    window.addEventListener('scroll', setScrolled, { passive: true });
  }

  // ----- Section reveal -----
  if (!prefersReduced && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    $$('.reveal').forEach((el) => io.observe(el));
  } else {
    $$('.reveal').forEach((el) => el.classList.add('visible'));
  }

  // ----- Section progress / active nav link -----
  const sections = $$('section[id]');
  const links = $$('.nav-links a[data-section]');
  if (sections.length && links.length && 'IntersectionObserver' in window) {
    const map = new Map(links.map((l) => [l.dataset.section, l]));
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          links.forEach((l) => l.classList.remove('active'));
          const link = map.get(e.target.id);
          if (link) link.classList.add('active');
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach((s) => obs.observe(s));
  }

  // ----- Count-up metrics -----
  const counters = $$('[data-count]');
  const animateCount = (el) => {
    const target = parseFloat(el.dataset.count);
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const dur = prefersReduced ? 0 : 1400;
    const start = performance.now();
    const step = (t) => {
      const p = Math.min(1, (t - start) / dur || 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = target * eased;
      el.textContent = decimals ? val.toFixed(decimals) : Math.round(val).toLocaleString();
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = decimals ? target.toFixed(decimals) : target.toLocaleString();
    };
    requestAnimationFrame(step);
  };
  if (counters.length && 'IntersectionObserver' in window) {
    const co = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { animateCount(e.target); co.unobserve(e.target); }
      });
    }, { threshold: 0.4 });
    counters.forEach((c) => co.observe(c));
  }

  // ----- Accordion -----
  $$('.acc-head').forEach((head) => {
    head.addEventListener('click', () => {
      const item = head.closest('.acc-item');
      const open = item.getAttribute('aria-expanded') === 'true';
      // single-open behavior within a group
      const group = item.parentElement;
      $$('.acc-item', group).forEach((i) => i.setAttribute('aria-expanded', 'false'));
      item.setAttribute('aria-expanded', open ? 'false' : 'true');
    });
  });

  // ----- Carousel -----
  const carousel = $('.carousel');
  if (carousel) {
    const slides = $$('.car-slide', carousel);
    const pips = $$('.car-pips button', carousel);
    let idx = 0;
    const go = (n) => {
      idx = (n + slides.length) % slides.length;
      slides.forEach((s, i) => s.classList.toggle('active', i === idx));
      pips.forEach((p, i) => p.classList.toggle('active', i === idx));
      const url = $('.car-url', carousel);
      if (url && slides[idx].dataset.url) url.textContent = slides[idx].dataset.url;
    };
    $('.car-prev', carousel)?.addEventListener('click', () => go(idx - 1));
    $('.car-next', carousel)?.addEventListener('click', () => go(idx + 1));
    pips.forEach((p, i) => p.addEventListener('click', () => go(i)));
    let auto;
    const restart = () => { clearInterval(auto); auto = setInterval(() => go(idx + 1), 5500); };
    if (!prefersReduced) restart();
    carousel.addEventListener('mouseenter', () => clearInterval(auto));
    carousel.addEventListener('mouseleave', () => { if (!prefersReduced) restart(); });
    go(0);
  }

  // ----- Copy to clipboard -----
  $$('.code-copy').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const block = btn.closest('.code-block');
      const code = $('pre', block)?.innerText || '';
      try {
        await navigator.clipboard.writeText(code);
        const orig = btn.textContent;
        btn.textContent = 'Copied';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 1500);
      } catch (_) { /* clipboard blocked */ }
    });
  });

  // ----- Architecture diagram tooltips -----
  const archFrame = $('.arch-frame');
  if (archFrame) {
    const tip = document.createElement('div');
    tip.className = 'arch-tooltip';
    archFrame.appendChild(tip);
    archFrame.style.position = 'relative';
    $$('[data-arch-tip]', archFrame).forEach((node) => {
      node.style.cursor = 'crosshair';
      node.addEventListener('mouseenter', (e) => {
        const [title, body] = (node.dataset.archTip || '').split('|');
        tip.innerHTML = `<div class="t-title">${title || ''}</div><div class="t-body">${body || ''}</div>`;
        tip.classList.add('show');
      });
      node.addEventListener('mousemove', (e) => {
        const r = archFrame.getBoundingClientRect();
        const x = Math.min(e.clientX - r.left + 14, r.width - 260);
        const y = Math.min(e.clientY - r.top + 14, r.height - 80);
        tip.style.left = x + 'px';
        tip.style.top = y + 'px';
      });
      node.addEventListener('mouseleave', () => tip.classList.remove('show'));
    });
  }
})();
