// Copy the original Scarlet/Violet front-facing PNG icons without resizing.
// Keep pixel edges and transparency exactly as supplied by the local media library.
const fs = require('node:fs/promises')
const path = require('node:path')
const web = path.resolve(__dirname, '../apps/web')
async function main() {
  const output = path.join(web, 'public/generation-starters')
  await fs.mkdir(output, { recursive: true })
  const ids = [1,4,7,152,155,158,252,255,258,387,390,393,495,498,501,650,653,656,722,725,728,810,813,816,906,909,912]
  const sources = []
  const queue = [...ids]
  await Promise.all(Array.from({ length: 3 }, async () => {
    while (queue.length) {
      const id = queue.shift()
      const response = await fetch(`http://127.0.0.1:8001/api/v1/pokemon/${id}/version-sprites`)
      if (!response.ok) throw new Error(`Metadata ${id}: ${response.status}`)
      const data = await response.json()
      const sprite = data.sprites.find(s => s.ownerType === 'pokemon' && s.ownerId === id && s.game === 'scarlet-violet' && s.kind === 'icons/front_default' && s.status === 'downloaded')
      if (!sprite?.url) throw new Error(`Missing Scarlet/Violet front icon: ${id}`)
      const image = await fetch(`http://127.0.0.1:8080${sprite.url}`)
      if (!image.ok) throw new Error(`Media ${id}: ${image.status}`)
      const bytes = Buffer.from(await image.arrayBuffer())
      if (!bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) throw new Error(`Expected PNG icon: ${id}`)
      await fs.writeFile(path.join(output, `${id}.png`), bytes)
      sources.push({ id, game: sprite.game, kind: sprite.kind, width: sprite.width, height: sprite.height, sourceUrl: sprite.sourceUrl, localMedia: sprite.url })
    }
  }))
  await fs.writeFile(path.join(output, 'sources.json'), JSON.stringify(sources.sort((a,b) => a.id-b.id), null, 2) + '\n')
  // These exact files are the previous 3D previews exported by this script.
  for (const id of ids) await fs.unlink(path.join(output, `${id}.webp`)).catch(error => { if (error.code !== 'ENOENT') throw error })
  console.log(`Exported ${sources.length} original Scarlet/Violet front PNG icons.`)
}
main().catch(error => { console.error(error); process.exitCode = 1 })
