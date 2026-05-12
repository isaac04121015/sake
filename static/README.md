# Sakego Web — UI Kit

High-fidelity recreation of the Sakego static website. Pixel values, gradients, type, spacing and hover behavior are lifted directly from `source_repo/static/styles.css`.

## Files

| File | Purpose |
|---|---|
| `index.html` | Interactive prototype — clickable home → region → brewery → product flow |
| `components.jsx` | React components: SiteHeader, SiteFooter, Hero, RegionPill, BreweryCell, BreweryCard, ProductCard, SakeCard, FlavorRadar, SpecsTable, Badge, Tag |
| `screens.jsx` | Screen-level composites: HomeScreen, RegionScreen, BreweryScreen, ProductScreen |
| `data.js` | Fixture data — 3 regions, 4 breweries, 6 products, all real names from common Japanese sake catalog |
| `styles.css` | Imports `colors_and_type.css` from the design system root + adds UI-kit layout rules |

## Design source

- `source_repo/static/styles.css` — every pixel value
- `source_repo/templates/{index,region,brewery,product}.html.j2` — layout structure
- `source_repo/config/brand_voice.md` — sample copy

## Click-through

The prototype boots on Home. Clicking a region pill or a brewery name navigates. Hash-based routing — `#/region/kanto`, `#/brewery/iso-jiman`, `#/product/iso-jiman-junmai-daiginjo`. No backend; everything is data fixtures.
