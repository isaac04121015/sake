/* Sakego UI Kit — primitives + screen pieces.
   Loads alongside React 18 + Babel.                                       */

const { useState, useEffect, useMemo } = React;
const D = window.SAKEGO_DATA;

const byId = (arr, id) => arr.find(x => x.id === id);
const byBrewery = (bid) => D.products.filter(p => p.brewery_id === bid);

/* ===== Route helpers ===== */
function parseHash() {
  const h = (window.location.hash || '#/').slice(2);
  const parts = h.split('/').filter(Boolean);
  if (!parts.length) return { name: 'home' };
  if (parts[0] === 'region') return { name: 'region', id: parts[1] };
  if (parts[0] === 'brewery') return { name: 'brewery', id: parts[1] };
  if (parts[0] === 'product') return { name: 'product', id: parts[1] };
  return { name: 'home' };
}
function useRoute() {
  const [r, setR] = useState(parseHash());
  useEffect(() => {
    const f = () => setR(parseHash());
    window.addEventListener('hashchange', f);
    return () => window.removeEventListener('hashchange', f);
  }, []);
  return r;
}
const go = (path) => { window.location.hash = '#' + path; window.scrollTo({ top: 0, behavior: 'instant' }); };

/* ===== Chrome ===== */
function WarningBar() {
  return (
    <div className="warning-bar">
      ⚠️ 禁止酒駕・飲酒過量，有害健康
    </div>
  );
}
function SiteHeader() {
  return (
    <header className="site-header">
      <div className="container">
        <h1 className="site-title"><a onClick={() => go('/')} style={{cursor:'pointer'}}>日本酒造資料庫</a></h1>
        <p className="site-tagline">Sakego ｜ 探索 {D.breweries.length}+ 家酒造、{D.products.length}+ 款日本酒</p>
      </div>
    </header>
  );
}
function SiteFooter() {
  /* SVG prohibition icon — professional redraw */
  const ProhibitionIcon = () => (
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="禁止酒駕">
      <defs>
        <clipPath id="warn-clip"><circle cx="50" cy="50" r="42"/></clipPath>
      </defs>
      {/* White circle */}
      <circle cx="50" cy="50" r="44" fill="#fff"/>
      <g clipPath="url(#warn-clip)">
        {/* ── Car body ── */}
        <rect x="8" y="51" width="56" height="13" rx="3" fill="#1a2535"/>
        {/* cabin */}
        <path d="M 17,51 L 22,38 L 53,38 L 58,51 Z" fill="#1a2535"/>
        {/* windshield glass tint */}
        <path d="M 23,50 L 27,41 L 52,41 L 56,50 Z" fill="rgba(160,210,245,0.38)"/>
        {/* headlight */}
        <ellipse cx="62" cy="56" rx="2.2" ry="1.6" fill="#ffd740"/>
        {/* front bumper detail */}
        <rect x="6" y="53" width="4" height="7" rx="2" fill="#243040"/>
        {/* rear bumper */}
        <rect x="64" y="53" width="4" height="7" rx="2" fill="#243040"/>
        {/* door line */}
        <line x1="38" y1="39" x2="38" y2="64" stroke="rgba(255,255,255,0.12)" strokeWidth="1"/>
        {/* Wheel left */}
        <circle cx="23" cy="64" r="8.5" fill="#0d0d0d"/>
        <circle cx="23" cy="64" r="5"   fill="#555"/>
        <circle cx="23" cy="64" r="2.2" fill="#c0c0c0"/>
        {/* Wheel right */}
        <circle cx="53" cy="64" r="8.5" fill="#0d0d0d"/>
        <circle cx="53" cy="64" r="5"   fill="#555"/>
        <circle cx="53" cy="64" r="2.2" fill="#c0c0c0"/>

        {/* ── Martini glass ── */}
        {/* bowl */}
        <path d="M 63,22 L 87,22 L 75,44 Z" fill="#1a2535"/>
        {/* liquid fill */}
        <path d="M 65.5,24.5 L 84.5,24.5 L 75,42 Z" fill="rgba(201,169,97,0.82)"/>
        {/* olive on pick */}
        <line x1="75" y1="22" x2="75" y2="36" stroke="#7a4e28" strokeWidth="1.2" strokeLinecap="round"/>
        <ellipse cx="75" cy="29" rx="3" ry="2.5" fill="#4a7c30"/>
        <ellipse cx="75" cy="29" rx="1.2" ry="1" fill="#c0392b"/>
        {/* stem */}
        <line x1="75" y1="44" x2="75" y2="55" stroke="#1a2535" strokeWidth="2.8" strokeLinecap="round"/>
        {/* base */}
        <line x1="69" y1="55" x2="81" y2="55" stroke="#1a2535" strokeWidth="3.2" strokeLinecap="round"/>
      </g>
      {/* Red ring */}
      <circle cx="50" cy="50" r="44" fill="none" stroke="#CC0000" strokeWidth="7.5"/>
      {/* Red diagonal slash — bottom-left to top-right */}
      <line x1="14" y1="83" x2="86" y2="17" stroke="#CC0000" strokeWidth="7.5" strokeLinecap="round"/>
    </svg>
  );

  return (
    <footer className="site-footer">
      <div className="container">
        <p>資料來源:<a>Sakenowa Data Project</a>｜事實規格欄位來自各酒造官網</p>
        <p className="footer-meta">情境圖片來自 <a>Unsplash</a>(CC0/Unsplash License)</p>
        <p className="footer-meta">最後更新:2026-05-12</p>
      </div>
      <div className="footer-warning-bar">
        <p className="footer-warning-text">禁止酒駕</p>
        <div className="footer-warning-icon-wrap"><ProhibitionIcon /></div>
        <p className="footer-warning-text">飲酒過量有害健康</p>
      </div>
    </footer>
  );
}

/* ===== Breadcrumb ===== */
function Breadcrumb({ items, light }) {
  return (
    <nav className={"breadcrumb" + (light ? " breadcrumb-light" : "")}>
      {items.map((it, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span className="sep">›</span>}
          {it.path
            ? <a onClick={() => go(it.path)} style={{cursor:'pointer'}}>{it.label}</a>
            : <span className="current">{it.label}</span>}
        </React.Fragment>
      ))}
    </nav>
  );
}

/* ===== Sake bottle "card" — signature element ===== */
function SakeCard({ product, brewery, mini }) {
  const theme = brewery.theme;
  if (mini) {
    return (
      <div className="mini-sake" style={{ background: `linear-gradient(180deg, ${theme.primary} 0%, ${theme.secondary} 100%)` }}>
        <div className="mini-sake-label">{theme.label}</div>
        <div className="mini-sake-name">{product.name_zhtw || product.name_jp}</div>
        <div className="mini-sake-div"></div>
        <div className="mini-sake-brewery">{brewery.name_jp}</div>
      </div>
    );
  }
  return (
    <div className="sake-card" style={{ background: `linear-gradient(180deg, ${theme.primary} 0%, ${theme.secondary} 100%)` }}>
      <div className="sake-inner">
        <div className="sake-label">{theme.label}</div>
        <div className="sake-name">{product.name_zhtw || product.name_jp}</div>
        {product.name_jp && product.name_jp !== product.name_zhtw && <div className="sake-jp">{product.name_jp}</div>}
        <div className="sake-divider"></div>
        <div className="sake-brewery">{brewery.name_jp}</div>
        <div className="sake-area">{brewery.area.toUpperCase()}</div>
      </div>
    </div>
  );
}

/* ===== Product card (used in brewery grid) ===== */
function ProductCard({ product, brewery }) {
  return (
    <article className="product-card" onClick={() => go('/product/' + product.id)}>
      <div className="product-card-visual" style={{ background: brewery.theme.bg }}>
        <SakeCard product={product} brewery={brewery} mini />
      </div>
      <div className="product-card-body">
        <h3 className="product-card-name">{product.name_zhtw || product.name_jp}</h3>
        <p className="product-card-jp">{product.name_jp !== product.name_zhtw ? product.name_jp : '\u00A0'}</p>
        <dl className="product-quickspec">
          {product.sake_type && <div><dt>類型</dt><dd>{product.sake_type}</dd></div>}
          {product.rice && <div><dt>米</dt><dd>{product.rice}</dd></div>}
          {product.seimaibuai && <div><dt>精米</dt><dd>{product.seimaibuai}%</dd></div>}
        </dl>
        {product.tags && (
          <div>{product.tags.slice(0,3).map(t => <span key={t} className="tag-mini">{t}</span>)}</div>
        )}
      </div>
    </article>
  );
}

/* ===== Hexagonal flavor radar ===== */
function FlavorRadar({ data, color }) {
  const axes = ['華麗', '芳醇', '厚重', '穩重', '辛口', '輕快'];
  const xs = [0, 0.866, 0.866, 0, -0.866, -0.866];
  const ys = [-1, -0.5, 0.5, 1, 0.5, -0.5];
  return (
    <svg viewBox="0 0 300 300" className="flavor-radar" xmlns="http://www.w3.org/2000/svg">
      {[30, 60, 90, 120].map((r, i) => (
        <polygon key={i} points={xs.map((x, j) => `${150 + r*x},${150 + r*ys[j]}`).join(' ')} fill="none" stroke="rgba(0,0,0,.08)"/>
      ))}
      {xs.map((x, i) => (
        <line key={i} x1="150" y1="150" x2={150 + 120*x} y2={150 + 120*ys[i]} stroke="rgba(0,0,0,.1)"/>
      ))}
      <polygon
        points={axes.map((a, i) => {
          const v = data[a] || 0;
          return `${150 + 120*v*xs[i]},${150 + 120*v*ys[i]}`;
        }).join(' ')}
        fill={color} fillOpacity=".3" stroke={color} strokeWidth="2"
      />
      {axes.map((a, i) => {
        const v = data[a] || 0;
        return <circle key={a} cx={150 + 120*v*xs[i]} cy={150 + 120*v*ys[i]} r="4" fill={color} />;
      })}
      {axes.map((a, i) => (
        <text key={a} x={150 + 145*xs[i]} y={150 + 145*ys[i]} textAnchor="middle" dominantBaseline="middle" fontSize="14" fontWeight="500" fill="#2C2C2C" fontFamily="Noto Sans TC, sans-serif">{a}</text>
      ))}
    </svg>
  );
}

window.SakegoUI = { WarningBar, SiteHeader, SiteFooter, Breadcrumb, SakeCard, ProductCard, FlavorRadar, useRoute, go, byId, byBrewery };
