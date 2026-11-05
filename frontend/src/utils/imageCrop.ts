export function cropRectangle(width: number, height: number, aspect: number, zoom: number, x: number, y: number) {
  const w = Math.min(width, height * aspect) / Math.max(1, zoom)
  const h = w / aspect
  return { x: (width - w) * Math.max(0, Math.min(1, x)), y: (height - h) * Math.max(0, Math.min(1, y)), width: w, height: h }
}
