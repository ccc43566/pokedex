<script setup lang="ts">
defineProps<{ part: 'library' | 'sky' | 'branches' | 'lantern' }>()
</script>
<template>
  <svg v-if="part === 'library'" class="svg-library" aria-hidden="true">
    <defs>
      <symbol id="home-i-search" viewBox="0 0 24 24">
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 4.5 4.5" />
      </symbol>
      <symbol id="home-i-ball" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h6m6 0h6" />
        <circle cx="12" cy="12" r="3" />
      </symbol>
      <symbol id="home-i-move" viewBox="0 0 24 24"><path d="m14 2-9 12h6l-1 8 9-12h-6z" /></symbol>
      <symbol id="home-i-bag" viewBox="0 0 24 24">
        <path d="M6 8h12l2 13H4L6 8Zm3 0V6a3 3 0 0 1 6 0v2M9 13h6" />
      </symbol>
      <symbol id="home-i-type" viewBox="0 0 24 24">
        <path d="m12 2 9 10-9 10L3 12z" />
        <path d="m8 12 4-5 4 5-4 5z" />
      </symbol>
      <symbol id="home-i-down" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" /></symbol>
      <symbol id="home-i-settings" viewBox="0 0 24 24">
        <path d="M4 7h16M4 17h16" />
        <circle cx="9" cy="7" r="3" />
        <circle cx="15" cy="17" r="3" />
      </symbol>
    </defs>
  </svg>
  <div v-else-if="part === 'sky'" class="sky" aria-hidden="true">
    <svg class="moon" viewBox="0 0 160 160" shape-rendering="crispEdges">
      <path
        fill="#B9A8CF"
        d="M56 4h48v8h24v12h16v20h8v24h4v32h-8v24h-12v12h-20v12H92v8H60v-8H40v-12H24v-16H12V96H4V64h8V40h12V24h16V12h16z"
      />
      <path
        fill="#E3D9E9"
        d="M60 8h40v8h24v12h16v24h8v40h-8v24h-12v12h-24v12H64v-8H40v-16H24V92H16V56h12V36h16V20h16z"
      />
      <path
        fill="#CBBED8"
        d="M49 37h21v12h9v15H61V53H43V43h6zm46 47h25v11h9v18h-25V99h-9zm-47 8h14v16H48zm43-65h14v10H91z"
      />
    </svg>
    <svg class="cloud cloud--back" viewBox="0 0 440 84" shape-rendering="crispEdges">
      <path d="M0 58h47V44h32V30h61V18h49V8h60v12h29v13h60v12h43v13h59v18H0z" fill="#665A84" />
    </svg>
    <svg class="cloud cloud--front" viewBox="0 0 440 84" shape-rendering="crispEdges">
      <path d="M0 58h40V47h39V32h45V20h58V9h72v15h51v13h37v12h52v10h46v17H0z" fill="#413C66" />
    </svg>
  </div>
  <svg
    v-else-if="part === 'branches'"
    class="front-branches"
    viewBox="0 0 1440 240"
    preserveAspectRatio="none"
    aria-hidden="true"
  >
    <path
      d="M0 240V26l20 15 8 47 31-21 20-39 9 7-11 46-43 28 7 38 35-4 30-29 9 8-27 35-44 9 16 74zm1440 0V0l-21 32-10 52-42-32-16-37-12 8 14 42 50 39-12 44-37-17-27-36-13 9 27 45 41 24-18 67z"
      fill="#17182c"
    />
  </svg>
  <svg v-else viewBox="0 0 64 64" aria-hidden="true" shape-rendering="crispEdges">
    <path fill="#817459" d="M28 5h9v7h-4v5h-6z" />
    <path fill="currentColor" d="M18 16h10v-3h13v3h9v6h6v25h-6v7H16v-4H9V24h9z" />
    <path fill="#f3c178" opacity=".24" d="M27 18h10v34H27z" />
    <path
      class="jack-face"
      d="m17 30 9-7v10h-9zm30 0-9-7v10h9zM18 39h7v5h13v-5h8v8h-7v4H25v-4h-7z"
    />
  </svg>
</template>
