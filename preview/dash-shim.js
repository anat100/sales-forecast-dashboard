/* A small local stand-in for the `dash` runtime that Claude Dashboards give a page.
   It loads the CSVs in ../data, runs the page's dash.calc() joins, and calls its
   dash.onData() renderers, so dashboard/index.html renders unchanged in any browser.
   On claude.ai the real runtime adds provenance (click a number to see its source),
   live connector queries, refresh and CSV export. */
(function () {
  const DATASETS = {
    crm_deals: '../data/crm_deals.csv',
    sales_quotas: '../data/sheets_sales_quotas.csv',
    stage_probabilities: '../data/sheets_stage_probabilities.csv',
    mrr_plan: '../data/sheets_mrr_plan.csv',
    warehouse_mrr: '../data/warehouse_mrr.csv'
  };
  const raw = {}, calcs = {}, memo = {}, listeners = [];
  let params = {}, defaults = {};

  const result = (id) => {
    if (raw[id]) return { status: 'ok', data: raw[id], columns: raw[id].columns || [], refreshing: false, meta: [] };
    if (calcs[id]) {
      if (!(id in memo)) {
        const inputs = calcs[id].inputs.map(i => result(i));
        if (inputs.some(r => r.status !== 'ok')) return { status: 'loading', data: [], columns: [] };
        memo[id] = calcs[id].fn(...inputs.map(r => r.data));
      }
      const d = memo[id];
      return { status: 'ok', data: d, columns: Array.isArray(d) && d[0] ? Object.keys(d[0]) : [], refreshing: false, meta: [] };
    }
    return { status: Object.keys(raw).length ? 'missing' : 'loading', data: [], columns: [] };
  };
  const fire = () => listeners.forEach(fn => { try { fn(); } catch (e) { console.error(e); } });

  window.dash = {
    data: result,
    calc: (id, def) => { calcs[id] = def; },
    loader: () => {},
    onData: (fn) => { listeners.push(fn); try { fn(); } catch (e) { console.error(e); } },
    params: () => ({ ...params }),
    setParams: (p) => { params = { ...params, ...p }; fire(); },
    resetParams: () => { params = { ...defaults }; fire(); },
    refresh: () => {},
    setLink: () => {},
    colors: ['#2f6fdb', '#d9822b', '#1f9e89', '#8e5cd9', '#d6455d', '#5b8fb9', '#b5932f', '#6d7480']
  };

  const qs = new URLSearchParams(location.search);
  if (qs.get('theme') === 'dark' || (!qs.get('theme') && matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.dataset.theme = 'dark';
  }

  async function boot() {
    const [page, dashParams] = await Promise.all([
      fetch('../dashboard/index.html').then(r => r.text()),
      fetch('../dashboard/params.json').then(r => r.ok ? r.json() : {}).catch(() => ({}))
    ]);
    defaults = dashParams; params = { ...dashParams };
    if (qs.get('rep')) params.rep = qs.get('rep');

    // Put the page's markup in place, then run its scripts in order, each in its own scope.
    const root = document.getElementById('dash-root');
    const tpl = document.createElement('template');
    tpl.innerHTML = page;
    const scripts = [...tpl.content.querySelectorAll('script')];
    scripts.forEach(s => s.remove());
    root.appendChild(tpl.content);
    scripts.forEach(s => {
      const el = document.createElement('script');
      el.textContent = '(function(){\n' + s.textContent + '\n})();';
      document.body.appendChild(el);
    });

    await Promise.all(Object.entries(DATASETS).map(async ([id, url]) => {
      raw[id] = d3.csvParse(await fetch(url).then(r => r.text()));
    }));
    fire();
    let w = innerWidth;
    addEventListener('resize', () => { if (innerWidth !== w) { w = innerWidth; fire(); } });
    document.documentElement.dataset.ready = '1';
  }
  boot();
})();
