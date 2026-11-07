<script setup lang="ts">
import {recommendedOpacity,type AppearanceMode} from '~/utils/appearance'
const props=withDefaults(defineProps<{modelValue:number;mode?:AppearanceMode}>(),{mode:'day'})
const emit=defineEmits<{'update:modelValue':[value:number]}>()
const {locale}=useI18n()
const zh=computed(()=>locale.value==='zh-Hans')
const recommended=computed(()=>recommendedOpacity[props.mode])
const opened=ref(false)
const root=ref<HTMLElement|null>(null)
const trigger=ref<HTMLButtonElement|null>(null)
const slider=ref<HTMLInputElement|null>(null)
const id=useId()
function change(value:number){emit('update:modelValue',value)}
async function toggle(){opened.value=!opened.value;if(opened.value){await nextTick();slider.value?.focus()}}
function close(){opened.value=false;trigger.value?.focus()}
function outside(event:PointerEvent){if(!root.value?.contains(event.target as Node))opened.value=false}
onMounted(()=>document.addEventListener('pointerdown',outside))
onBeforeUnmount(()=>document.removeEventListener('pointerdown',outside))
</script>

<template>
  <div ref="root" class="card-background-control" @keydown.esc.stop.prevent="close">
    <div v-if="opened" :id="`${id}-panel`" class="card-background-panel" role="group" :aria-label="zh?'卡片背景设置':'Card background settings'">
      <div class="card-background-heading"><strong>{{ zh?'卡片背景':'Card background' }}</strong><button type="button" :aria-label="zh?'关闭背景设置':'Close background settings'" @click="close"><svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m6 6 8 8M14 6l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg></button></div>
      <div class="card-background-value"><label :for="`${id}-range`">{{ zh?'纸面不透明度':'Paper opacity' }}</label><output :for="`${id}-range`">{{ modelValue }}%</output></div>
      <input :id="`${id}-range`" ref="slider" type="range" min="0" max="100" step="1" :value="modelValue" :aria-valuetext="zh?`${modelValue}% 不透明，${100-modelValue}% 透明`:`${modelValue}% opaque, ${100-modelValue}% transparent`" @input="change(Number(($event.target as HTMLInputElement).value))">
      <div class="card-background-scale"><span>{{ zh?'透明':'Transparent' }}</span><span>{{ zh?'实色':'Solid' }}</span></div>
      <div class="card-background-presets"><button v-for="value in [60,recommended,100]" :key="value" type="button" :aria-pressed="modelValue===value" @click="change(value)">{{ value }}%<span v-if="value===recommended">{{ zh?' 推荐':' Recommended' }}</span></button></div>
      <p>{{ zh?`${mode==='day'?'日间':'夜间'}推荐 ${recommended}% 不透明度（${100-recommended}% 透明），兼顾背景层次与文字辨识。`:`Recommended for ${mode}: ${recommended}% opacity (${100-recommended}% transparency).` }}</p>
      <p class="card-background-note">{{ zh?'同步调整世代长条与宝可梦卡片的纸面底色，图片和文字保持清晰。设置自动保存。':'Adjusts generation bars and Pokémon card paper together. Artwork and text stay clear. Saved automatically.' }}</p>
    </div>
    <button ref="trigger" type="button" class="card-background-trigger" :aria-expanded="opened" :aria-controls="`${id}-panel`" @click="toggle"><svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14M7 3v4m6 1v4m-6 1v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg><span>{{ zh?'卡片背景':'Card background' }}</span><b>{{ modelValue }}%</b></button>
  </div>
</template>

<style scoped>
.card-background-control{position:fixed;right:16px;bottom:16px;z-index:45;color:#294435;font-size:13px}
.card-background-trigger{display:flex;align-items:center;gap:9px;padding:10px 13px;border:1px solid #CDDCCF;border-radius:10px;background:#fffffff5;box-shadow:0 3px 15px #243b2d12;cursor:pointer}
.card-background-trigger>svg{width:17px;height:17px;color:#668471}.card-background-trigger b{font-variant-numeric:tabular-nums;font-size:12px;padding-left:8px;border-left:1px solid #DDE6DD}
.card-background-panel{position:absolute;right:0;bottom:calc(100% + 10px);width:min(316px,calc(100vw - 24px));padding:18px;border:1px solid #CDDCCF;border-radius:13px;background:#fff;box-shadow:0 10px 34px #243b2d1c}
.card-background-heading{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.card-background-heading strong{font-size:15px}.card-background-heading button{cursor:pointer;padding:3px;border-radius:4px;color:#74877A}.card-background-heading svg{width:18px;height:18px}
.card-background-value{display:flex;justify-content:space-between;margin-bottom:7px}.card-background-value output{font-weight:750;font-variant-numeric:tabular-nums}
input[type=range]{display:block;accent-color:#3E6650;width:100%;height:26px;cursor:pointer;margin:0}.card-background-scale{display:flex;justify-content:space-between;font-size:11px;color:#819086;margin-bottom:15px}
.card-background-presets{display:flex;gap:7px;margin-bottom:13px}.card-background-presets button{flex:1;padding:7px 3px;border:1px solid #DBE4DA;border-radius:6px;font-size:12px;cursor:pointer}.card-background-presets button[aria-pressed=true]{border-color:#7B9B80;background:#EDF4EB;color:#2F593D}.card-background-presets span{font-size:10px}
p{font-size:12px;line-height:1.7;margin:0 0 8px;color:#4C6756}.card-background-note{font-size:11px;color:#819086;margin:0}
button:focus-visible,input:focus-visible{outline:2px solid #568465;outline-offset:3px}
@media(max-width:600px){.card-background-control{right:12px;bottom:12px}.card-background-trigger{padding:9px 11px}}
</style>
