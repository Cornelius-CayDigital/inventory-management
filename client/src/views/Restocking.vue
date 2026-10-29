<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-header">
          <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
          <span class="budget-value">{{ formatMoney(budget) }}</span>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          :max="maxBudget"
          :step="budgetStep"
          :aria-valuetext="formatMoney(budget)"
        />
        <div class="budget-scale">
          <span>{{ formatMoney(0) }}</span>
          <span>{{ formatMoney(maxBudget) }}</span>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.selectedItems') }}</div>
          <div class="stat-value">{{ selectedLines.length }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.orderTotal') }}</div>
          <div class="stat-value">{{ formatMoney(orderTotal) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
          <div class="stat-value">{{ formatMoney(budget - orderTotal) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.leadTime') }}</div>
          <div class="stat-value">{{ t('restocking.days', { count: orderLeadTime }) }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
          <button
            class="place-order-btn"
            :disabled="selectedLines.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="successMessage" class="notice success-notice" role="status">{{ successMessage }}</div>
        <div v-if="submitError" class="notice error-notice" role="alert">{{ submitError }}</div>

        <div class="table-container">
          <table class="restock-table">
            <thead>
              <tr>
                <th>{{ t('demand.table.sku') }}</th>
                <th>{{ t('demand.table.itemName') }}</th>
                <th>{{ t('demand.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.gap') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th class="num">{{ t('restocking.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="line in recommendations"
                :key="line.sku"
                :class="{ 'not-selected': line.quantity === 0 }"
              >
                <td><strong>{{ line.sku }}</strong></td>
                <td>{{ translateProductName(line.name) }}</td>
                <td>
                  <span :class="['badge', line.trend]">{{ t(`trends.${line.trend}`) }}</span>
                </td>
                <td class="num">{{ line.gap.toLocaleString() }}</td>
                <td class="num">{{ formatMoney(line.unitCost, 2) }}</td>
                <td class="num">
                  {{ line.quantity.toLocaleString() }}
                  <span v-if="line.quantity > 0 && line.quantity < line.gap" class="partial-tag">
                    {{ t('restocking.partial') }}
                  </span>
                </td>
                <td class="num">{{ formatMoney(line.lineTotal, 2) }}</td>
                <td class="num">{{ t('restocking.days', { count: line.leadTimeDays }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

// Increasing demand is restocked first, decreasing last
const TREND_PRIORITY = { increasing: 0, stable: 1, decreasing: 2 }

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()
    const router = useRouter()

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(0)
    const submitting = ref(false)
    const submitError = ref(null)
    const successMessage = ref(null)

    // Units needed to cover forecasted demand above current demand
    const candidates = computed(() => {
      return forecasts.value
        .filter(f => f.unit_cost > 0)
        .map(f => ({
          sku: f.item_sku,
          name: f.item_name,
          trend: f.trend.toLowerCase(),
          gap: Math.max(0, f.forecasted_demand - f.current_demand),
          unitCost: f.unit_cost,
          leadTimeDays: f.lead_time_days || 0
        }))
        .sort((a, b) =>
          (TREND_PRIORITY[a.trend] ?? 3) - (TREND_PRIORITY[b.trend] ?? 3) || b.gap - a.gap
        )
    })

    const fullRestockCost = computed(() =>
      candidates.value.reduce((sum, c) => sum + c.gap * c.unitCost, 0)
    )

    // Slider tops out at the cost of covering every gap, rounded up to a whole step
    const budgetStep = 50
    const maxBudget = computed(() =>
      Math.max(budgetStep, Math.ceil(fullRestockCost.value / budgetStep) * budgetStep)
    )

    // Greedy fill in priority order; an item that doesn't fully fit gets as many units as remain affordable
    const recommendations = computed(() => {
      let remaining = budget.value
      return candidates.value.map(c => {
        const affordable = Math.floor((remaining + 1e-9) / c.unitCost)
        const quantity = Math.min(c.gap, affordable)
        const lineTotal = Math.round(quantity * c.unitCost * 100) / 100
        remaining -= lineTotal
        return { ...c, quantity, lineTotal }
      })
    })

    const selectedLines = computed(() => recommendations.value.filter(r => r.quantity > 0))

    const orderTotal = computed(() =>
      Math.round(selectedLines.value.reduce((sum, r) => sum + r.lineTotal, 0) * 100) / 100
    )

    const orderLeadTime = computed(() =>
      selectedLines.value.reduce((max, r) => Math.max(max, r.leadTimeDays), 0)
    )

    const formatMoney = (amount, decimals = 0) =>
      formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

    const loadForecasts = async () => {
      try {
        loading.value = true
        error.value = null
        forecasts.value = await api.getDemandForecasts()
        // Start at half the full restock cost so the slider has room both ways
        budget.value = Math.round(maxBudget.value / 2 / budgetStep) * budgetStep
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      try {
        submitting.value = true
        submitError.value = null
        successMessage.value = null
        const order = await api.createRestockOrder({
          items: selectedLines.value.map(r => ({ sku: r.sku, quantity: r.quantity })),
          budget: budget.value
        })
        successMessage.value = t('restocking.submitted', { orderNumber: order.order_number })
        setTimeout(() => router.push('/orders'), 1200)
      } catch (err) {
        submitError.value = t('restocking.submitFailed') + ' ' + (err.response?.data?.detail || err.message)
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      t,
      translateProductName,
      loading,
      error,
      budget,
      budgetStep,
      maxBudget,
      recommendations,
      selectedLines,
      orderTotal,
      orderLeadTime,
      submitting,
      submitError,
      successMessage,
      formatMoney,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  margin-bottom: 1.5rem;
}

.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-weight: 600;
  color: #0f172a;
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #0f172a;
  cursor: pointer;
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.place-order-btn {
  background: #0f172a;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.notice {
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.success-notice {
  background: #dcfce7;
  color: #166534;
}

.error-notice {
  background: #fee2e2;
  color: #991b1b;
}

.restock-table {
  width: 100%;
}

.num {
  text-align: right;
}

.not-selected td {
  color: #94a3b8;
}

.partial-tag {
  display: inline-block;
  margin-left: 0.375rem;
  font-size: 0.75rem;
  color: #b45309;
}
</style>
