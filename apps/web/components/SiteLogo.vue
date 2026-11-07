<template>
  <span class="site-logo" role="img" aria-label="PokéCodex"><span class="site-logo__poke">Poké</span><span class="site-logo__codex">Codex</span></span>
</template>
<style scoped>
@font-face { font-family:'Codex Brand'; src:url('/home/night/Baloo2-variable.ttf') format('truetype'); font-style:normal; font-weight:400 800; font-display:swap; }
.site-logo { display:inline-flex; align-items:baseline; white-space:nowrap; font:800 32px/1 'Codex Brand',sans-serif; letter-spacing:-.8px; filter:drop-shadow(0 1px 0 #4a2e86) drop-shadow(0 1px 0 #33206a); }
.site-logo__poke { background:linear-gradient(#fff,#f2f5fc 45%,#c9d3ea); background-clip:text; color:transparent; }
.site-logo__codex { background:linear-gradient(#ffe489,#ffc23c 48%,#e8891f); background-clip:text; color:transparent; }
@media(max-width:420px) { .site-logo { font-size:29px; } }
</style>
