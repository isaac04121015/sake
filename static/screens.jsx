/* Sakego UI Kit — screens. Consumes window.SakegoUI primitives. */

const { SiteHeader, SiteFooter, Breadcrumb, SakeCard, ProductCard, FlavorRadar, useRoute, go, byId, byBrewery } = window.SakegoUI;
const SD = window.SAKEGO_DATA;

/* Region metadata for ranking cards */
const REGION_META = {
  kanto:    { prefectures: '東京都 · 神奈川縣 · 埼玉縣', maxCount: 8 },
  chubu:    { prefectures: '靜岡縣 · 山口縣 · 福井縣 · 新潟縣', maxCount: 8 },
  kansai:   { prefectures: '兵庫縣 · 京都府 · 大阪府', maxCount: 8 },
  kyushu:   { prefectures: '福岡縣 · 佐賀縣 · 熊本縣', maxCount: 8 },
  tohoku:   { prefectures: '宮城縣 · 秋田縣 · 山形縣', maxCount: 8 },
  hokkaido: { prefectures: '北海道', maxCount: 8 },
};

function rankedRegions() {
  return [...SD.regions].sort((a, b) => b.count - a.count);
}

function rankedProducts() {
  return [...SD.products].sort((a, b) => {
    const aScore = (a.stars || 0) * 10 + (a.awards?.length || 0);
    const bScore = (b.stars || 0) * 10 + (b.awards?.length || 0);
    return bScore - aScore;
  });
}

/* ===== Star Rating ===== */
function StarRating({ stars, max = 5, size = 20 }) {
  return (
    <div className="star-row">
      {Array.from({length: max}).map((_, i) => (
        <span key={i} className={"star " + (i < stars ? "full" : "empty")} style={{fontSize: size}}>★</span>
      ))}
      <span className="star-label">{stars}/{max} 推薦</span>
    </div>
  );
}

/* ===== Region Ranking Card ===== */
function RankCard({ region, rank, maxCount }) {
  const meta = REGION_META[region.id] || {};
  const barPct = Math.round((region.count / maxCount) * 100);
  const ordinal = String(rank).padStart(2, '0');
  return (
    <article className="rank-card" onClick={() => go('/region/' + region.id)}>
      <div className="rank-card-accent"></div>
      <span className="rank-num-bg">{ordinal}</span>
      <span className="rank-ordinal">No. {ordinal}</span>
      <h3 className="rank-name">{region.name}</h3>
      <p className="rank-prefectures">{meta.prefectures || ''}</p>
      <div className="rank-bar-track">
        <div className="rank-bar-fill" style={{width: barPct + '%'}}></div>
      </div>
      <p className="rank-count"><strong>{region.count}</strong> 家酒造</p>
    </article>
  );
}

/* ===== Brand Ranking Row ===== */
function BrandRankRow({ product, rank }) {
  const brewery = byId(SD.breweries, product.brewery_id);
  return (
    <div className="brand-rank-row" onClick={() => go('/product/' + product.id)}>
      <div className="brand-rank-num">{String(rank).padStart(2,'0')}</div>
      <div>
        <p className="brand-rank-name">{product.name_zhtw || product.name_jp}</p>
        <p className="brand-rank-meta">{brewery?.name_jp} · {brewery?.area} · {product.sake_type}</p>
        {product.awards?.length > 0 && (
          <p className="brand-rank-meta" style={{marginTop:4, color:'var(--accent)'}}>
            🏆 {product.awards.slice(0,2).join(' · ')}{product.awards.length > 2 ? ` +${product.awards.length - 2}` : ''}
          </p>
        )}
      </div>
      <div className="brand-rank-stars">
        {Array.from({length:5}).map((_,i) => (
          <span key={i} className={"star " + (i < (product.stars||0) ? "full" : "empty")}>★</span>
        ))}
      </div>
    </div>
  );
}

/* ===== Spotlight Panel ===== */
function SpotlightPanel({ brewery, flipped }) {
  const products = byBrewery(brewery.id);
  return (
    <div className={"spotlight-panel" + (flipped ? " flipped" : "")} onClick={() => go('/brewery/' + brewery.id)}>
      <div className="spotlight-img">
        <img src={brewery.heroBg} alt={brewery.name_jp} loading="lazy" />
        <div className="spotlight-img-overlay"></div>
      </div>
      <div className="spotlight-body">
        <span className="spotlight-eyebrow">精選酒造</span>
        <h3 className="spotlight-title">{brewery.name_zhtw}</h3>
        <p className="spotlight-jp">{brewery.name_jp}</p>
        <div className="spotlight-meta">
          <span>📍 {brewery.area}</span>
          {brewery.founded && <span>🏯 創業 {brewery.founded}</span>}
          <span>🍶 {products.length} 款銘柄</span>
        </div>
        <button className="spotlight-cta" onClick={e => { e.stopPropagation(); go('/brewery/' + brewery.id); }}>
          探索銘柄 &nbsp;›
        </button>
      </div>
    </div>
  );
}

/* ===== Brewery entry (editorial card) ===== */
function BreweryEntry({ brewery }) {
  return (
    <div className="brewery-entry" onClick={() => go('/brewery/' + brewery.id)}>
      <div className="brewery-entry-body">
        <span className="brewery-entry-name">{brewery.name_zhtw}</span>
        <span className="brewery-entry-jp">{brewery.name_jp}</span>
        <span className="brewery-entry-count">{byBrewery(brewery.id).length} 款銘柄</span>
      </div>
      <span className="brewery-entry-arrow">›</span>
    </div>
  );
}

/* ===== Home Screen ===== */
function HomeScreen() {
  const totalB = SD.breweries.length;
  const totalP = SD.products.length;
  const totalR = SD.regions.length;
  const ranked = rankedRegions();
  const maxCount = ranked[0]?.count || 1;
  const brandRanked = rankedProducts();
  const regionsWithBreweries = SD.regions.filter(r => SD.breweries.some(b => b.region_id === r.id));
  const spotlightBreweries = SD.breweries.filter(b => b.heroBg).slice(0, 2);

  return (
    <>
      {/* ── Full-viewport Hero ── */}
      <section className="home-hero">
        <div className="hero-bg" style={{backgroundImage: "url('https://images.unsplash.com/photo-1597290282695-edc43d0e7129?w=1600&q=85')"}}></div>
        <div className="hero-overlay"></div>
        <div className="hero-texture"></div>
        <div className="hero-vignette"></div>
        <div className="hero-deco-kanji">酒</div>

        {/* Vertical side text */}
        <div className="hero-vert-text">清酒 · 純米 · 吟釀 · 大吟釀 · 本醸造 · 風土</div>

        {/* Gold bokeh particles */}
        {[
          {l:'12%',b:'18%',s:8, dur:'4.2s',delay:'0s',   dx:'18px'},
          {l:'22%',b:'8%', s:5, dur:'5.1s',delay:'1.2s', dx:'-14px'},
          {l:'35%',b:'25%',s:10,dur:'3.8s',delay:'2.4s', dx:'24px'},
          {l:'48%',b:'12%',s:6, dur:'4.8s',delay:'0.6s', dx:'-20px'},
          {l:'58%',b:'30%',s:4, dur:'6.0s',delay:'1.8s', dx:'12px'},
          {l:'70%',b:'10%',s:9, dur:'4.4s',delay:'3.0s', dx:'-16px'},
          {l:'80%',b:'22%',s:5, dur:'5.5s',delay:'0.3s', dx:'22px'},
          {l:'18%',b:'40%',s:4, dur:'3.6s',delay:'2.1s', dx:'-10px'},
          {l:'42%',b:'45%',s:7, dur:'5.2s',delay:'1.5s', dx:'18px'},
          {l:'65%',b:'38%',s:5, dur:'4.0s',delay:'3.6s', dx:'-22px'},
          {l:'88%',b:'15%',s:6, dur:'4.9s',delay:'0.9s', dx:'14px'},
          {l:'28%',b:'55%',s:3, dur:'6.2s',delay:'4.2s', dx:'-8px'},
        ].map((p, i) => (
          <div key={i} className="hero-bokeh" style={{
            left:p.l, bottom:p.b, width:p.s+'px', height:p.s+'px',
            '--dur':p.dur, '--delay':p.delay, '--dx':p.dx
          }}></div>
        ))}

        {/* Floating sake card (desktop) */}
        <div className="hero-float-card">
          <div style={{
            width:200, height:280, borderRadius:12,
            background:'linear-gradient(180deg,#722F37 0%,#3a181c 100%)',
            boxShadow:'0 16px 48px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.15)',
            position:'relative', overflow:'hidden', color:'#fff',
            display:'flex', flexDirection:'column', alignItems:'center',
            justifyContent:'center', textAlign:'center', padding:'32px 20px'
          }}>
            <div style={{position:'absolute',top:10,left:10,right:10,bottom:10,border:'1px solid rgba(255,255,255,.2)',borderRadius:8,pointerEvents:'none'}}></div>
            <div style={{font:'600 .65rem/1 var(--font-serif)',letterSpacing:'.3em',textTransform:'uppercase',color:'rgba(255,255,255,.65)',padding:'3px 10px',border:'1px solid rgba(255,255,255,.25)',borderRadius:3,marginBottom:24}}>JUNMAI</div>
            <div style={{font:'600 1.4rem/1.3 var(--font-serif)',marginBottom:8,letterSpacing:'.05em'}}>磯自慢</div>
            <div style={{fontSize:'.8rem',color:'rgba(255,255,255,.6)',marginBottom:16}}>いそじまん</div>
            <div style={{width:32,height:1,background:'rgba(255,255,255,.35)',margin:'12px 0'}}></div>
            <div style={{font:'500 .85rem/1 var(--font-serif)',letterSpacing:'.08em'}}>磯自慢酒造</div>
            <div style={{fontSize:'.7rem',color:'rgba(255,255,255,.55)',marginTop:6,letterSpacing:'.14em'}}>SHIZUOKA</div>
          </div>
        </div>

        {/* Main content */}
        <div className="container hero-content" style={{paddingBottom:110, paddingRight: 'min(340px, 30%)'}}>
          <span className="hero-eyebrow hero-anim-1">Sakego ｜ 日本酒造資料庫</span>
          <h1 className="hero-title hero-anim-2">
            探索<span className="hero-shimmer">日本酒</span><br/>的世界
          </h1>
          <div className="hero-ornament hero-anim-3">
            <span className="hero-orn-dot"></span>
            <span className="hero-orn-line"></span>
            <span className="hero-orn-dia"></span>
            <span className="hero-orn-dot"></span>
            <span className="hero-orn-dia"></span>
            <span className="hero-orn-line r"></span>
            <span className="hero-orn-dot"></span>
          </div>
          <p className="hero-sub hero-anim-3">從北海道到九州，{totalB} 家酒造、{totalP} 款銘柄，一次掌握</p>
          <div className="hero-search hero-anim-4">
            <input placeholder="搜尋酒造、銘柄或地區⋯" />
          </div>
        </div>

        <div className="hero-stats-strip">
          <div className="hero-stat"><span className="hero-stat-num">{totalB}+</span><span className="hero-stat-label">酒造</span></div>
          <div className="hero-stat"><span className="hero-stat-num">{totalP}+</span><span className="hero-stat-label">銘柄</span></div>
          <div className="hero-stat"><span className="hero-stat-num">{totalR}</span><span className="hero-stat-label">地區</span></div>
        </div>
      </section>

      {/* ── Brand manifesto ── */}
      <div className="manifesto-strip">
        <div className="manifesto-deco">酒造</div>
        <span className="manifesto-eyebrow">我們的信念</span>
        <p className="manifesto-text">
          「&ensp;從產地到杯中，每一滴都有故事。&ensp;」
          <br/>
          <span style={{fontSize:'clamp(.85rem,1.4vw,1rem)', opacity:.6, letterSpacing:'.04em', lineHeight:2, display:'block', marginTop:16}}>
            土壤、水、米、酵母——四者共同書寫一款清酒的風土個性。Sakego 讓你讀懂每一瓶的語言。
          </span>
        </p>
      </div>

      <main>
        {/* ── 地區英雄榜 ── */}
        <div className="container">
          <section className="rankings-section">
            <p className="section-eyebrow">地區英雄榜</p>
            <h2 className="section-heading">各地風土，按酒造數排行</h2>
            <p className="section-sub">點擊任一地區，深入探索當地酒造與銘柄</p>
            <div className="rank-grid">
              {ranked.map((r, i) => (
                <RankCard key={r.id} region={r} rank={i + 1} maxCount={maxCount} />
              ))}
            </div>
          </section>
        </div>

        {/* ── 銘柄英雄榜 ── */}
        <div style={{background:'var(--secondary)', padding:'72px 0'}}>
          <div className="container">
            <p className="section-eyebrow" style={{color:'var(--accent)'}}>銘柄英雄榜</p>
            <h2 className="section-heading" style={{color:'#fff', marginBottom:8}}>得獎銘柄排行</h2>
            <p style={{fontSize:'.9rem', color:'rgba(255,255,255,.5)', margin:'0 0 40px', letterSpacing:'.04em'}}>
              依星級推薦與國際競賽得獎數綜合排名
            </p>
            <div className="brand-rank-grid">
              {brandRanked.map((p, i) => (
                <BrandRankRow key={p.id} product={p} rank={i + 1} />
              ))}
            </div>
          </div>
        </div>

        {/* ── Brewery spotlight ── */}
        <div className="container">
          <section className="spotlight-section">
            <p className="section-eyebrow">精選酒造</p>
            <h2 className="section-heading" style={{marginBottom: 36}}>值得深探的名門</h2>
            {spotlightBreweries.map((b, i) => (
              <SpotlightPanel key={b.id} brewery={b} flipped={i % 2 === 1} />
            ))}
          </section>
        </div>

        {/* ── Featured products ── */}
        <div className="featured-strip">
          <div className="container">
            <p className="section-eyebrow" style={{marginBottom:8}}>精選銘柄</p>
            <h2 className="section-heading" style={{marginBottom:32}}>近期推薦</h2>
            <div className="featured-scroll">
              {SD.products.map(p => {
                const b = byId(SD.breweries, p.brewery_id);
                return <div key={p.id} style={{flexShrink:0}}><ProductCard product={p} brewery={b} /></div>;
              })}
            </div>
          </div>
        </div>

        {/* ── Region-grouped brewery list — all areas in one grid ── */}
        <div className="container">
          {regionsWithBreweries.map(region => {
            const breweries = SD.breweries.filter(b => b.region_id === region.id);
            return (
              <section key={region.id} className="region-block">
                <header className="region-header">
                  <h2 onClick={() => go('/region/' + region.id)}>{region.name}</h2>
                  <span className="region-count">{region.count} 家酒造</span>
                </header>
                {/* All breweries in one unified grid — no area subgroups */}
                <div className="brewery-entries">
                  {breweries.map(b => (
                    <div key={b.id} className="brewery-entry" onClick={() => go('/brewery/' + b.id)}>
                      <div className="brewery-entry-body">
                        <span className="brewery-entry-name">{b.name_zhtw}</span>
                        <span className="brewery-entry-jp">{b.name_jp}</span>
                        <span className="brewery-entry-count">{b.area} · {byBrewery(b.id).length} 款銘柄</span>
                      </div>
                      <span className="brewery-entry-arrow">›</span>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </main>
    </>
  );
}

/* ===== Region Screen ===== */
function RegionScreen({ id }) {
  const region = byId(SD.regions, id);
  if (!region) return <main className="container"><p>地區未找到</p></main>;
  const breweries = SD.breweries.filter(b => b.region_id === id);
  return (
    <main className="container">
      <Breadcrumb items={[{label:'首頁', path:'/'}, {label: region.name}]} />
      <header style={{padding:'32px 0', borderBottom:'2px solid var(--secondary)', marginBottom:40}}>
        <p className="section-eyebrow" style={{margin:'0 0 8px'}}>{REGION_META[id]?.prefectures || ''}</p>
        <h1 style={{font:'600 2.8rem/1.3 var(--font-serif)', color:'var(--secondary)', margin:'0 0 6px'}}>{region.name}</h1>
        <p style={{margin:0, color:'var(--text-muted)'}}>{breweries.length} 家酒造</p>
      </header>
      {Array.from(new Set(breweries.map(b => b.area))).map(area => (
        <section key={area} style={{margin:'40px 0'}}>
          <h2 className="area-name">{area}</h2>
          <div className="brewery-entries" style={{gridTemplateColumns:'repeat(auto-fill, minmax(280px, 1fr))'}}>
            {breweries.filter(b => b.area === area).map(b => (
              <BreweryEntry key={b.id} brewery={b} />
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}

/* ===== Brewery Screen ===== */
function BreweryScreen({ id }) {
  const brewery = byId(SD.breweries, id);
  if (!brewery) return <main className="container"><p>酒造未找到</p></main>;
  const region = byId(SD.regions, brewery.region_id);
  const products = byBrewery(id);
  return (
    <>
      <section className="brewery-hero">
        <div className="hero-bg" style={{backgroundImage:`url(${brewery.heroBg})`}}></div>
        <div className="hero-overlay"></div>
        <div className="container hero-content">
          <Breadcrumb light items={[{label:'首頁', path:'/'}, {label: region.name, path:'/region/'+region.id}, {label: brewery.area}]} />
          <h1 className="brewery-hero-title">{brewery.name_zhtw}</h1>
          {brewery.name_jp !== brewery.name_zhtw && <p className="brewery-hero-jp">{brewery.name_jp}</p>}
          <div className="brewery-meta-row">
            <span>📍 {brewery.area}</span>
            {brewery.founded && <span>🏯 創業 {brewery.founded}</span>}
            {brewery.website && <span>🔗 <a>官網</a></span>}
          </div>
        </div>
      </section>
      <main className="container">
        <section style={{margin:'0 0 60px'}}>
          <h2 className="section-title">旗下銘柄 <span className="section-count">{products.length}</span></h2>
          <div className="product-grid">
            {products.map(p => <ProductCard key={p.id} product={p} brewery={brewery} />)}
          </div>
        </section>
      </main>
    </>
  );
}

/* ===== Product Screen ===== */
function ProductScreen({ id }) {
  const product = byId(SD.products, id);
  if (!product) return <main className="container"><p>銘柄未找到</p></main>;
  const brewery = byId(SD.breweries, product.brewery_id);
  const region = byId(SD.regions, brewery.region_id);
  const theme = brewery.theme;

  return (
    <>
      <section className="product-hero" style={{background: theme.tint}}>
        <div className="container">
          <div className="product-hero-3col">
            {/* Zone 1: drag-and-drop bottle photo */}
            <div className="bottle-slot-wrap">
              <span className="bottle-slot-label">酒瓶照片</span>
              <image-slot
                id={"bottle-" + product.id}
                shape="rounded"
                radius="14"
                placeholder="拖曳酒瓶照片至此"
                style={{width:'140px', height:'300px'}}
              ></image-slot>
            </div>
            {/* Zone 2: CSS sake card */}
            <div style={{display:'flex', justifyContent:'center'}}>
              <SakeCard product={product} brewery={brewery} />
            </div>
            {/* Zone 3: text info */}
            <div>
              <Breadcrumb items={[
                {label:'首頁', path:'/'},
                {label: region.name, path:'/region/'+region.id},
                {label: brewery.name_jp, path:'/brewery/'+brewery.id}
              ]} />
              <h1 className="product-title">{product.name_zhtw || product.name_jp}</h1>
              {product.name_jp !== product.name_zhtw && <p className="product-title-jp">{product.name_jp}</p>}
              <p className="product-brewery-line">
                <a onClick={() => go('/brewery/'+brewery.id)}>{brewery.name_jp}</a>
                <span className="sep">·</span>
                <span>{brewery.area}</span>
              </p>
              {/* Star rating */}
              {product.stars && <StarRating stars={product.stars} />}
              {/* Award badges */}
              {product.awards?.length > 0 && (
                <div className="awards-list">
                  {product.awards.map(a => (
                    <span key={a} className="award-badge">{a}</span>
                  ))}
                </div>
              )}
              <div className="quick-badges" style={{marginTop:20}}>
                {product.sake_type && <span className="badge primary">{product.sake_type}</span>}
                {product.rice && <span className="badge">{product.rice}</span>}
                {product.seimaibuai && <span className="badge">精米 {product.seimaibuai}%</span>}
                {product.abv && <span className="badge">{product.abv}% ABV</span>}
              </div>
            </div>
          </div>
        </div>
      </section>

      <main className="container product-page">
        <article className="product-detail">
          {product.description && (
            <section className="product-section"><h2>關於這款酒</h2><p>{product.description}</p></section>
          )}
          {product.tasting && (
            <section className="product-section"><h2>品飲建議</h2><p>{product.tasting}</p></section>
          )}
          {product.pairing && (
            <section className="product-section"><h2>搭餐建議</h2><p>{product.pairing}</p></section>
          )}
          <section className="product-section">
            <h2>規格</h2>
            <table className="sake-specs"><tbody>
              <tr><th>酒造</th><td>{brewery.name_jp}</td></tr>
              <tr><th>產地</th><td>{brewery.area}</td></tr>
              {product.sake_type && <tr><th>酒類型</th><td>{product.sake_type}</td></tr>}
              {product.rice && <tr><th>使用米</th><td>{product.rice}</td></tr>}
              {product.rice_origin && <tr><th>米產地</th><td>{product.rice_origin}</td></tr>}
              {product.seimaibuai && <tr><th>精米步合</th><td>{product.seimaibuai}%</td></tr>}
              {product.yeast && <tr><th>酵母</th><td>{product.yeast}</td></tr>}
              {product.abv && <tr><th>酒精度</th><td>{product.abv}%</td></tr>}
              {product.smv && <tr><th>日本酒度 (SMV)</th><td>{product.smv}</td></tr>}
              {product.acidity && <tr><th>酸度</th><td>{product.acidity}</td></tr>}
            </tbody></table>
          </section>
          {product.flavor && (
            <section className="product-section">
              <h2>風味輪廓</h2>
              <div className="flavor-radar-container">
                <FlavorRadar data={product.flavor} color={theme.primary} />
                <div>
                  {Object.entries(product.flavor).map(([k,v]) => (
                    <div className="flavor-legend-item" key={k}>
                      <span style={{fontWeight:500}}>{k}</span>
                      <span className="flavor-legend-value">{v.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <p style={{margin:'16px 0 0', fontSize:'.8rem', color:'var(--text-muted)'}}>資料來源：Sakenowa 用戶評分整體</p>
            </section>
          )}
          {product.tags && (
            <section className="product-section">
              <h2>風味標籤</h2>
              <div>{product.tags.map(t => <span className="tag" key={t}>{t}</span>)}</div>
            </section>
          )}
          {/* Awards section */}
          {product.awards?.length > 0 && (
            <section className="product-section">
              <h2>國際得獎記錄</h2>
              <div className="awards-list">
                {product.awards.map(a => (
                  <span key={a} className="award-badge">{a}</span>
                ))}
              </div>
            </section>
          )}
        </article>
      </main>
    </>
  );
}

/* ===== App root ===== */
function App() {
  const route = useRoute();
  let screen;
  if (route.name === 'home')         screen = <HomeScreen />;
  else if (route.name === 'region')  screen = <RegionScreen id={route.id} />;
  else if (route.name === 'brewery') screen = <BreweryScreen id={route.id} />;
  else if (route.name === 'product') screen = <ProductScreen id={route.id} />;
  else                               screen = <HomeScreen />;
  return (<><SiteHeader />{screen}<SiteFooter /></>);
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
