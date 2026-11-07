// Build the actual workspace source without disturbing a running Nuxt dev server.
import { createRequire } from 'node:module'
import { delimiter, dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

process.env.NODE_ENV = 'production'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const web = resolve(root, 'apps/web')
process.chdir(web)
process.env.PATH = [resolve(web, 'node_modules/.bin'), resolve(root, '.tools/node'), process.env.PATH].join(delimiter)
const require = createRequire(resolve(web, 'package.json'))
const { loadNuxt, buildNuxt } = await import(pathToFileURL(require.resolve('nuxt/kit')).href)
const output = resolve(root, '../migration-audit/search-production-build')
const nuxt = await loadNuxt({
  cwd: web,
  dev: false,
  overrides: {
    buildDir: resolve(web, '.nuxt-search-check'),
    nitro: { output: { dir: output, serverDir: resolve(output, 'server'), publicDir: resolve(output, 'public') } },
  },
})
try {
  await buildNuxt(nuxt)
} finally {
  await nuxt.close()
}
