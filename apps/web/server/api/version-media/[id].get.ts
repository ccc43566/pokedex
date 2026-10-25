import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id') || ''
  if (!/^\d+$/.test(id)) throw createError({ statusCode: 400, statusMessage: 'Invalid Pokémon ID' })
  const file = resolve(process.cwd(), '..', '..', 'data', 'version-media', `${id}.json`)
  try {
    const contents = await readFile(file, 'utf8')
    setHeader(event, 'Cache-Control', 'no-store')
    return JSON.parse(contents)
  } catch {
    throw createError({ statusCode: 404, statusMessage: 'Version media preview not exported yet' })
  }
})
