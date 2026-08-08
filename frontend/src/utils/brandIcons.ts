
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

// Icons are rendered with <img src>, not fetched and injected as markup.
//
// This used to fetch the SVG and hand it to v-html behind a regex sanitizer.
// That sanitizer was bypassable — its attribute stripper required whitespace
// before the handler name, but HTML parsers also accept "/" as an attribute
// separator, so `<svg><img/onerror=...>` survived it intact. Rather than
// harden the regex, the sink is gone: an SVG loaded through <img> cannot run
// scripts at all, which removes the whole class of problem instead of playing
// whack-a-mole with parser quirks.
//
// Returns candidate URLs in preference order; the component falls through them
// on load error.
export function brandIconUrls(slug: string): string[] {
  const color = encodeURIComponent(ICONIFY_COLORS[slug] ?? '#94a3b8')
  return [
    // Simple Icons bakes the brand hex in.
    `https://cdn.simpleicons.org/${slug}`,
    // Iconify uses currentColor, so the colour is passed explicitly.
    `https://api.iconify.design/simple-icons/${slug}.svg?color=${color}`,
  ]
}
