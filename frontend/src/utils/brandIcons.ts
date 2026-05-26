const _cache = new Map<string, string | null>()
const _inflight = new Map<string, Promise<string | null>>()

const BRAND_MAP: [RegExp, string][] = [
  [/nvidia|geforce|quadro|rtx[\s\d]|gtx[\s\d]|tesla[\s\d]/i, 'nvidia'],
  [/\bintel\b|core[\s_]i[3579]|xeon|celeron|pentium/i, 'intel'],
  [/\bamd\b|radeon|ryzen|epyc|athlon/i, 'amd'],
  [/samsung/i, 'samsung'],
  [/western[\s_]?digital|wd\s+(blue|red|green|black|gold|purple)|^wdc\s/i, 'westerndigital'],
  [/seagate|barracuda|ironwolf|skyhawk|firecuda/i, 'seagate'],
  [/toshiba/i, 'toshiba'],
  [/kingston/i, 'kingston'],
  [/crucial/i, 'crucial'],
  [/sandisk/i, 'sandisk'],
]

export function detectBrand(name: string): string | null {
  if (!name) return null
  for (const [re, slug] of BRAND_MAP) {
    if (re.test(name)) return slug
  }
  return null
}

export async function fetchBrandSvg(slug: string): Promise<string | null> {
  if (_cache.has(slug)) return _cache.get(slug)!
  if (_inflight.has(slug)) return _inflight.get(slug)!

  const p = fetch(`https://cdn.simpleicons.org/${slug}`)
    .then(r => (r.ok ? r.text() : null))
    .then(svg => { _cache.set(slug, svg); _inflight.delete(slug); return svg })
    .catch(() => { _cache.set(slug, null); _inflight.delete(slug); return null })

  _inflight.set(slug, p)
  return p
}
