// Extract approved artwork and isolated theme styles; never touches database/media.
const fs = require('node:fs')
const path = require('node:path')
const root = path.resolve(__dirname, '..')
const source = path.resolve(root, '../design/halloween-native-review')
const web = path.join(root, 'apps/web')
const store = path.join(web, 'node_modules/.pnpm')
const postcss = require(path.join(store, fs.readdirSync(store).find(name => name.startsWith('postcss@')), 'node_modules/postcss'))
const destination = path.join(web, 'public/home/night')
fs.mkdirSync(destination, { recursive: true })
for (const file of ['observatory-night.png', 'catalog-border.svg', 'edge-branches.svg', 'frame-edge-mask.svg', 'moving-bush.svg']) {
  fs.copyFileSync(path.join(source, 'assets', file), path.join(destination, file))
}
for (const file of ['Baloo2-variable.ttf', 'OFL.txt']) {
  fs.copyFileSync(path.resolve(source, '../logo-review/fonts', file), path.join(destination, file))
}
const sheets = ['logo.css', 'night.css', 'scroll-layout.css', 'framing.css', 'native.css', 'visitors.css', 'edges.css', 'stories.css']
const unused = /preview-tools|tools-panel|background-only|entrances|results-line|scroll-guide|season-nav|catalog-end|pokemon-card|pokemon-grid|pokemon-number|pokemon-art|pokemon-types|type-bar|type-icon|type-name|section-context|catalog-description|\.empty|#renderer-status|#clear-search/
const css = postcss.root()
for (const file of sheets) {
  const sheet = postcss.parse(fs.readFileSync(path.join(source, file), 'utf8'))
  sheet.walkRules(rule => {
    if (rule.parent.type === 'atrule' && /keyframes$/.test(rule.parent.name)) return
    const selectors = rule.selectors.filter(selector => !unused.test(selector)).map(selector => {
      if (selector === ':root' || selector === 'body' || selector === 'html') return '.night-home'
      if (selector.startsWith('body.')) return selector.replace(/^body/, '.night-home')
      if (selector.startsWith('.is-scrolled')) return '.night-home' + selector
      return '.night-home ' + selector
    })
    if (!selectors.length) rule.remove()
    else rule.selectors = selectors
  })
  sheet.walkAtRules('keyframes', rule => { rule.params = 'home-' + rule.params })
  sheet.walkDecls(decl => {
    decl.value = decl.value.replaceAll("../logo-review/fonts/", '/home/night/').replaceAll('assets/', '/home/night/').replaceAll('Baloo 2', 'Home Baloo')
    if (/^animation(-name)?$/.test(decl.prop)) {
      for (const name of ['logo-float', 'logo-wave', 'logo-sheen', 'cloud-drift', 'ghost-drift', 'visitor-wiggle', 'moon-drift', 'cloud-crossing-back', 'cloud-crossing']) {
        decl.value = decl.value.replace(new RegExp('(?<![\\w-])' + name + '(?![\\w-])', 'g'), 'home-' + name)
      }
    }
  })
  css.append(sheet.nodes)
}
fs.writeFileSync(path.join(web, 'assets/css/night-home.css'), '/* Extracted by scripts/generate-night-home-assets.cjs. Home-only selectors. */\n' + css.toString())
const markup = fs.readFileSync(path.join(source, 'index.html'), 'utf8')
const library = markup.match(/<svg class="svg-library"[\s\S]*?<\/svg>/)[0].replace('<svg ', '<svg v-if="part === \'library\'" ')
const sky = markup.match(/<div class="sky"[\s\S]*?<\/div>/)[0].replace('<div ', '<div v-else-if="part === \'sky\'" ')
const branches = markup.match(/<svg class="front-branches"[\s\S]*?<\/svg>/)[0].replace('<svg ', '<svg v-else-if="part === \'branches\'" ')
const lantern = fs.readFileSync(path.join(source, 'lanterns.js'), 'utf8').match(/const drawing='([^']+)'/)[1].replace('<svg ', '<svg v-else ')
fs.writeFileSync(path.join(web, 'components/NightHomeArtwork.vue'), `<script setup lang="ts">\ndefineProps<{ part: 'library' | 'sky' | 'branches' | 'lantern' }>()\n</script>\n<template>\n${[library, sky, branches, lantern].join('\n').replaceAll('id="i-', 'id="home-i-')}\n</template>\n`)
const curated = JSON.parse(fs.readFileSync(path.join(source, 'pokemon-data.js'), 'utf8').replace(/^window\.previewPokemon\s*=\s*/, '').replace(/;\s*$/, ''))
async function main() {
  const rows = curated
  const output = Array(rows.length)
  let next = 0
  await Promise.all(Array.from({ length: 3 }, async () => {
    while (next < rows.length) {
      const index = next++, row = rows[index]
      const response = await fetch(`http://127.0.0.1:8001/api/v1/pokemon/${row.id}?locale=en`, { signal: AbortSignal.timeout(30000) })
      if (!response.ok) throw new Error(`Existing local record ${row.id}: HTTP ${response.status}`)
      const current = await response.json()
      output[index] = { id: row.id, name: row.name, englishName: current.displayName || current.localizedName, slug: row.slug, displayNumber: current.displayNumber, sprite: row.source, types: row.types, animation: row.animation ? { path: row.animation.source, width: row.animation.width, height: row.animation.height } : null }
    }
  }))
  fs.mkdirSync(path.join(web, 'assets/night'), { recursive: true })
  fs.writeFileSync(path.join(web, 'assets/night/visitors.json'), JSON.stringify(output, null, 2) + '\n')
  console.log(`Prepared ${output.length} curated visitors with verified local IDs/names; all Pokémon images keep existing /media SHA-256 addresses.`)
}
main().catch(error => { console.error(error); process.exitCode = 1 })
