// Only derive reviewed assets; never modify the original materials.
const fs = require('node:fs')
const path = require('node:path')
const crypto = require('node:crypto')
const repo = path.resolve(__dirname, '..')
const source = path.resolve(repo, '..')
const palette = JSON.parse(fs.readFileSync(path.join(source, 'design/type-palette/pokemon-type-colors.json'), 'utf8')).types
const output = path.join(repo, 'apps/web/public/type-icons')
fs.mkdirSync(output, { recursive: true })
const provenance = []
for (const type of palette) {
  const file = path.join(source, `UI/icons/${type.type}.svg`)
  const svg = fs.readFileSync(file, 'utf8')
  const colors = {}
  for (const match of svg.matchAll(/\.(cls-\d+)\s*\{\s*fill:\s*(#[a-f\d]+);/gi)) colors[match[1]] = match[2]
  let shapes = svg.replace(/[\s\S]*?<\/defs>/, '').replace(/<\/svg>[\s\S]*/, '').replace(/<circle\b[^>]*\br="128"[^>]*\/>/g, '')
  shapes = shapes.replace(/class="(cls-\d+)"/g, (_, cls) => {
    if (!colors[cls]) throw Error(`Unknown SVG class ${type.type}:${cls}`)
    const color = colors[cls]
    const full = color.length === 4 ? color.slice(1).split('').map(x => x+x).join('') : color.slice(1)
    return `fill="${[0,2,4].every(i => parseInt(full.slice(i,i+2),16) > 240) ? 'white' : 'black'}"`
  })
  fs.writeFileSync(path.join(output, `${type.type}.svg`), `<svg xmlns="http://www.w3.org/2000/svg" viewBox="30 30 196 196"><defs><mask id="glyph" maskUnits="userSpaceOnUse" x="0" y="0" width="256" height="256">${shapes}</mask></defs><rect width="256" height="256" fill="white" mask="url(#glyph)"/></svg>\n`)
  provenance.push({ type: type.type, source: `UI/icons/${type.type}.svg`, sha256: crypto.createHash('sha256').update(svg).digest('hex') })
}
fs.copyFileSync(path.join(source, 'UI/icons/stellar.png'), path.join(output, 'stellar.png'))
fs.writeFileSync(path.join(output, 'sources.json'), JSON.stringify(provenance, null, 2)+'\n')
const colors = Object.fromEntries(palette.map(t => [t.type, { icon: t.icon, label: t.label }]))
colors.stellar = { icon: 'linear-gradient(125deg,#C6F2FF,#DDD1FF 38%,#FFD6EC 70%,#FFF0B8)', label: 'linear-gradient(110deg,#286A85,#59519A 38%,#8C4F7B 72%,#827139)' }
fs.writeFileSync(path.join(repo, 'apps/web/utils/typePalette.ts'), '// Generated from reviewed local palette by scripts/generate-type-assets.cjs.\nexport const typePalette: Record<string, { icon: string; label: string }> = '+JSON.stringify(colors, null, 2)+'\n')
console.log(`Derived ${palette.length} glyphs; copied stellar PNG unchanged.`)
