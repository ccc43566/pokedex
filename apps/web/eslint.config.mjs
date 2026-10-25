import withNuxt from './.nuxt/eslint.config.mjs'

export default await withNuxt().append({ ignores: ['.nuxt.stale/**'] }).toConfigs()
