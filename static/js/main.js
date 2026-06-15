/* ═══════════════════════════════════════════════════
   آفاق الفكر — main.js
═══════════════════════════════════════════════════ */

// ── Auto-dismiss alerts ───────────────────────────
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity .5s, transform .5s';
    el.style.opacity = '0';
    el.style.transform = 'translateY(-6px)';
    setTimeout(() => el.remove(), 500);
  }, 4500);
});

// ── Tabs ──────────────────────────────────────────
document.querySelectorAll('.tabs').forEach(group => {
  group.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      group.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const wrap = btn.closest('.tabs-wrap') || document.body;
      wrap.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      const el = document.getElementById(btn.dataset.tab);
      if (el) el.classList.add('active');
    });
  });
});

// ── Modals ────────────────────────────────────────
function openModal(id)  { const m=document.getElementById(id); if(m){m.classList.add('open');document.body.style.overflow='hidden';} }
function closeModal(id) { const m=document.getElementById(id); if(m){m.classList.remove('open');document.body.style.overflow='';} }

document.querySelectorAll('.modal-ov').forEach(ov => {
  ov.addEventListener('click', e => { if(e.target===ov){ov.classList.remove('open');document.body.style.overflow='';} });
});
document.querySelectorAll('[data-open]').forEach(b => b.addEventListener('click', () => openModal(b.dataset.open)));
document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', () => closeModal(b.dataset.close)));

// ── Confirm forms ─────────────────────────────────
document.querySelectorAll('form[data-confirm]').forEach(f => {
  f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm || 'هل أنت متأكد؟')) e.preventDefault(); });
});

// ── Active nav ────────────────────────────────────
const path = window.location.pathname;
document.querySelectorAll('.nav-link[href]').forEach(a => {
  const href = a.getAttribute('href');
  if (href && href !== '/' && path.startsWith(href)) a.classList.add('active');
});

// ── Table search ──────────────────────────────────
const si = document.getElementById('tblSearch');
if (si) si.addEventListener('input', () => {
  const t = si.value.toLowerCase();
  document.querySelectorAll('.s-row').forEach(r => {
    r.style.display = r.textContent.toLowerCase().includes(t) ? '' : 'none';
  });
});

// ═══════════════════════════════════════════════════
//  POLICIES SLIDE PANEL
// ═══════════════════════════════════════════════════
let policiesLoaded = false;

function openPolicies() {
  document.getElementById('polPanel').classList.add('open');
  document.getElementById('polOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
  if (!policiesLoaded) loadPolicies();
}

function closePolicies() {
  document.getElementById('polPanel').classList.remove('open');
  document.getElementById('polOverlay').classList.remove('open');
  document.body.style.overflow = '';
}

async function loadPolicies() {
  try {
    const res  = await fetch('/api/policies');
    const data = await res.json();
    const list = document.getElementById('polList');

    if (!data.length) {
      list.innerHTML = `
        <div style="text-align:center;padding:40px 20px;color:var(--text-3)">
          <i class="fas fa-file-contract" style="font-size:36px;opacity:.15;display:block;margin-bottom:12px"></i>
          <p style="font-size:12px">لا توجد سياسات لقسمك حتى الآن</p>
        </div>`;
      policiesLoaded = true;
      return;
    }

    list.innerHTML = data.map(p => `
      <div class="policy-item" id="pol-${p.id}">
        <div class="policy-item-head" onclick="togglePolicy(${p.id})">
          <div style="flex:1;min-width:0">
            <div class="policy-item-title">${p.title}</div>
            <div class="policy-item-meta">
              ${p.dept_name} · ${p.author} · ${p.created_at.slice(0,10)}
            </div>
          </div>
          <i class="fas fa-chevron-left policy-item-chevron"></i>
        </div>
        <div class="policy-item-body">
          <p>${p.body.replace(/\n/g,'<br>')}</p>
        </div>
      </div>
    `).join('');

    policiesLoaded = true;
  } catch(e) {
    document.getElementById('polList').innerHTML = `
      <div style="text-align:center;padding:32px;color:var(--red)">
        <i class="fas fa-exclamation-triangle" style="display:block;margin-bottom:8px;font-size:22px"></i>
        <p style="font-size:12px">تعذّر تحميل السياسات</p>
      </div>`;
  }
}

function togglePolicy(id) {
  const item = document.getElementById('pol-' + id);
  if (!item) return;
  const wasOpen = item.classList.contains('expanded');
  // Close all
  document.querySelectorAll('.policy-item.expanded').forEach(el => el.classList.remove('expanded'));
  // Toggle clicked
  if (!wasOpen) item.classList.add('expanded');
}

// Close panel on Escape
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePolicies(); });
