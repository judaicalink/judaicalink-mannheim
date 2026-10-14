// Suggestions while typing in the graph search (progressive: the form works without this script).
(function () {
  const input = document.querySelector('.gs-bar input[type=search]');
  if (!input) return;
  const form = input.form;
  const box = document.createElement('ul');
  box.className = 'gs-suggest';
  box.setAttribute('role', 'listbox');
  box.hidden = true;
  input.setAttribute('autocomplete', 'off');
  input.setAttribute('aria-autocomplete', 'list');
  input.parentNode.style.position = 'relative';
  input.parentNode.appendChild(box);
  let timer = null, active = -1, items = [];

  function datasets() {
    const ds = [...form.querySelectorAll('input[name=ds]:checked')].map(i => i.value);
    return ds.length ? ds : ['ep'];
  }
  function show(list) {
    items = list; active = -1;
    box.replaceChildren(...list.map((s, i) => {
      const li = document.createElement('li');
      li.setAttribute('role', 'option');
      const a = document.createElement('a');
      a.href = s.iri.replace('http://data.judaicalink.org', '');
      const name = document.createElement('span'); name.textContent = s.label; name.dir = 'auto';
      const meta = document.createElement('span'); meta.className = 'jl-meta';
      meta.textContent = ' ' + [s.kind, s.dates].filter(Boolean).join(' · ');
      a.append(name, meta); li.append(a);
      li.addEventListener('mousedown', e => e.preventDefault());
      return li;
    }));
    box.hidden = !list.length;
  }
  function mark() { [...box.children].forEach((li, i) => li.classList.toggle('gs-act', i === active)); }
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { show([]); return; }
    timer = setTimeout(async () => {
      const p = new URLSearchParams({ q, limit: 8 });
      datasets().forEach(d => p.append('ds', d));
      try {
        const r = await fetch('/search/suggest?' + p);
        if (r.ok && input.value.trim() === q) show(await r.json());
      } catch (e) { /* suggestions are optional */ }
    }, 180);
  });
  input.addEventListener('keydown', e => {
    if (box.hidden) return;
    if (e.key === 'ArrowDown') { active = Math.min(items.length - 1, active + 1); mark(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { active = Math.max(-1, active - 1); mark(); e.preventDefault(); }
    else if (e.key === 'Enter' && active >= 0) { location.href = box.children[active].querySelector('a').href; e.preventDefault(); }
    else if (e.key === 'Escape') { show([]); }
  });
  input.addEventListener('blur', () => setTimeout(() => show([]), 150));
})();
