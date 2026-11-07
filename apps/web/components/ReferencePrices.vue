<script setup lang="ts">
import type { ItemPrice } from '~/types/references'
import { formatPrice } from '~/utils/references'
const props = defineProps<{ prices: ItemPrice[] }>()
const { locale } = useI18n()
const { tr } = useReferenceText()
const selected = ref('')
const groups = computed(() => [
  ...new Map(props.prices.map((p) => [p.versionGroup.id, p.versionGroup])).values(),
])
const rows = computed(() =>
  props.prices.filter((p) => !selected.value || p.versionGroup.id === Number(selected.value)),
)
</script>

<template>
  <section class="ref-section" aria-labelledby="item-prices-title">
    <h3 id="item-prices-title">{{ tr('游戏价格', 'Game prices') }}</h3>
    <template v-if="prices.length">
      <label class="ref-select-label"
        >{{ tr('版本组', 'Version group') }}
        <select v-model="selected" :aria-label="tr('版本组', 'Version group')">
          <option value="">{{ tr('全部已记录版本组', 'All recorded version groups') }}</option>
          <option v-for="group in groups" :key="group.id" :value="String(group.id)">
            {{ group.localizedName }}
          </option>
        </select>
      </label>
      <div
        v-for="(price, i) in rows"
        :key="`${price.versionGroup.id}:${price.currency.id}:${i}`"
        class="ref-price-row"
      >
        <h4>
          {{ price.versionGroup.localizedName }}
          <span class="ref-muted">· {{ price.currency.localizedName }}</span>
        </h4>
        <dl class="ref-values">
          <div>
            <dt>{{ tr('购买价', 'Purchase') }}</dt>
            <dd>{{ formatPrice(price.purchase, true, locale === 'zh-Hans') }}</dd>
          </div>
          <div>
            <dt>{{ tr('出售价格', 'Sell') }}</dt>
            <dd>{{ formatPrice(price.sell, false, locale === 'zh-Hans') }}</dd>
          </div>
        </dl>
      </div>
      <p class="ref-note">
        {{
          tr(
            '以上价格与买卖状态仅对应所列版本组和货币；0 为上游明确记录的数值。其他版本没有记录时，不据此判断能否买卖。',
            'Prices and availability apply only to the listed version group and currency. Zero is an explicit upstream value. Missing records do not determine availability in other games.',
          )
        }}
      </p>
    </template>
    <template v-else
      ><p>{{ tr('暂无价格资料', 'No price data available') }}</p>
      <p class="ref-note">
        {{
          tr(
            '这不表示该道具在所有游戏中都不可买卖。',
            'This does not mean the item cannot be bought or sold in every game.',
          )
        }}
      </p></template
    >
  </section>
</template>
