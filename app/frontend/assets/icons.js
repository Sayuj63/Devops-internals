(function () {
  const I = {
    'chart-bar': '<path d="M3 3v18h18"/><path d="M7 15v3M12 9v9M17 12v6"/>',
    'server': '<rect x="3" y="4" width="18" height="7" rx="1.5"/><rect x="3" y="13" width="18" height="7" rx="1.5"/><circle cx="7" cy="7.5" r=".7"/><circle cx="7" cy="16.5" r=".7"/>',
    'lock-closed': '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    'list-bullet': '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
    'signal': '<path d="M3 20h2M8 20v-4M13 20V10M18 20V4"/>',
    'exclamation-triangle': '<path d="M12 3 2 21h20L12 3z"/><path d="M12 10v5M12 18v.5"/>',
    'check-circle': '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    'arrow-up': '<path d="M12 19V5M5 12l7-7 7 7"/>',
    'arrow-down': '<path d="M12 5v14M19 12l-7 7-7-7"/>',
    'search': '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    'x': '<path d="M6 6l12 12M18 6 6 18"/>',
    'database': '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    'cpu': '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v3M12 2v3M15 2v3M9 19v3M12 19v3M15 19v3M2 9h3M2 12h3M2 15h3M19 9h3M19 12h3M19 15h3"/>',
    'cloud': '<path d="M6 18h11a4 4 0 0 0 .9-7.9A6 6 0 0 0 6 11.5 4.5 4.5 0 0 0 6 18z"/>',
    'shield': '<path d="M12 3 4 6v6c0 5 3.5 8.5 8 9 4.5-.5 8-4 8-9V6l-8-3z"/>'
  };
  function svg(name, cls) {
    const inner = I[name] || '';
    return `<svg viewBox="0 0 24 24" class="${cls || ''}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
  }
  window.Icons = { svg, raw: I };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-icon]').forEach(el => {
      const name = el.getAttribute('data-icon');
      el.insertAdjacentHTML('afterbegin', svg(name));
    });
  });
})();
