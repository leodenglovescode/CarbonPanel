const _cache = new Map<string, string | null>()
const _inflight = new Map<string, Promise<string | null>>()

// All slugs verified against api.iconify.design/simple-icons/{slug}.svg
// Icons whose brand color is too dark to see on a dark background
export const DARK_SLUGS = new Set(['kingstontechnology', 'westerndigital', 'sandisk'])

const BRAND_MAP: [RegExp, string][] = [
  [/nvidia|geforce|quadro|rtx[\s\d]|gtx[\s\d]|tesla[\s\d]/i,         'nvidia'],
  [/\bintel\b|core[\s_]i[3579]|xeon|celeron|pentium/i,               'intel'],
  [/\bamd\b|radeon|ryzen|epyc|athlon/i,                              'amd'],
  [/samsung/i,                                                        'samsung'],
  [/seagate|barracuda|ironwolf|skyhawk|firecuda/i,                   'seagate'],
  [/toshiba/i,                                                        'toshiba'],
  [/kingston/i,                                                       'kingstontechnology'],
  [/western[\s_]?digital|wd\s+(blue|red|green|black|gold|purple)|^wdc\s/i, 'westerndigital'],
  [/sandisk/i,                                                        'sandisk'],
]

export function detectBrand(name: string): string | null {
  if (!name) return null
  for (const [re, slug] of BRAND_MAP) {
    if (re.test(name)) return slug
  }
  return null
}

// Brand colors for slugs not on the Simple Icons CDN (used when falling back to Iconify)
const ICONIFY_COLORS: Record<string, string> = {
  westerndigital: '#0073BE',
  sandisk:        '#E5251E',
}

// The fetched SVG is rendered via v-html — a compromised/MITM'd CDN response
// could otherwise inject a <script>, an event-handler attribute, or a
// <foreignObject> carrying arbitrary HTML straight into the DOM. This is a
// lightweight belt-and-suspenders filter (root element must be <svg>, no
// script-capable constructs survive) rather than a full sanitizer.
function _sanitizeSvg(raw: string): string | null {
  const text = raw.trim()
  if (!/^<svg[\s>]/i.test(text)) return null
  if (!/<\/svg>\s*$/i.test(text)) return null
  return text
    .replace(/<script[\s\S]*?<\/script\s*>/gi, '')
    .replace(/<foreignObject[\s\S]*?<\/foreignObject\s*>/gi, '')
    .replace(/\son\w+\s*=\s*(".*?"|'.*?'|[^\s>]+)/gi, '')
    .replace(/(href|xlink:href)\s*=\s*(".*?"|'.*?')/gi, (m, attr, val) =>
      /^["']\s*javascript:/i.test(val) ? '' : m,
    )
}

async function _fetchSvg(slug: string): Promise<string | null> {
  // Simple Icons CDN returns SVGs with brand hex baked in — prefer it
  const r1 = await fetch(`https://cdn.simpleicons.org/${slug}`).catch(() => null)
  if (r1?.ok) {
    const svg = _sanitizeSvg(await r1.text())
    if (svg) return svg
  }

  // Fallback: Iconify uses currentColor — pass the brand color explicitly
  const color = encodeURIComponent(ICONIFY_COLORS[slug] ?? '#94a3b8')
  const r2 = await fetch(`https://api.iconify.design/simple-icons/${slug}.svg?color=${color}`).catch(() => null)
  if (r2?.ok) {
    const svg = _sanitizeSvg(await r2.text())
    if (svg) return svg
  }

  return null
}

export async function fetchBrandSvg(slug: string): Promise<string | null> {
  if (_cache.has(slug)) return _cache.get(slug)!
  if (_inflight.has(slug)) return _inflight.get(slug)!

  const p = _fetchSvg(slug)
    .then(svg => { _cache.set(slug, svg); _inflight.delete(slug); return svg })
    .catch(() => { _cache.set(slug, null); _inflight.delete(slug); return null })

  _inflight.set(slug, p)
  return p
}
