---
name: vue-component-analysis
description: Analyze Vue 3 components in client/src for structure, performance and reuse problems, and suggest concrete optimizations. Use when asked to review, audit, optimize or refactor a .vue file or the views/components folders.
---

# Vue Component Analysis

Produce a prioritized list of concrete, file:line-anchored improvements for one or more Vue components. Analysis only: do not edit files unless the user asks you to apply the findings.

## Scope

- One file: analyze it plus anything it imports from `client/src`.
- Two or more files (or a folder, or "all views"): analyze each file, then add a cross-file **Reuse** section.

## Checklist

Work through each area and record only real findings (skip any area with nothing to report).

### Structure
- Uses the Composition API (`setup()` or `<script setup>`), not the Options API; no mixing of the two.
- Template over ~100 lines or script over ~150 lines: suggest extracting components or composables.
- Data loading follows the project pattern: `loading` / `error` refs, try/catch/finally, and loading and error states in the template. `error` is reset at the start of each load so a retry can recover.
- API calls go through `client/src/api.js`, never raw axios with hard-coded URLs.

### Reactivity and performance
- Derived values are `computed`, not methods called from the template (especially inside `v-for`).
- No O(n²) work in render, such as recomputing a max or sum per row.
- `v-for` keys are stable IDs (`sku`, `id`, `month`), not the array index.
- Watchers are scoped to what they need; no `deep: true` on large arrays without a reason.
- `v-show` for frequently toggled content, `v-if` for rarely shown content.
- No `console.log` left in render or hot paths.

### Consistency
- All user-facing strings go through `t()` from `useI18n`, with keys in both `locales/en.js` and `locales/ja.js`.
- Money uses `utils/currency.js` so USD and JPY both work.
- Respects the global filters from `useFilters` where the data supports them.
- Doesn't redefine global styles from `App.vue` (`.card`, `.stat-card`, `.badge`) in scoped CSS.

### Reuse
- Repeated markup (stat cards, tables with the same columns, modals) that appears in two or more files: propose a shared component and its props.
- Repeated logic (formatting, status-to-class maps, date handling): propose a composable or util, and name it.

## How to measure

Use Grep across `client/src` to back reuse claims with counts, for example how many files define `getOrderStatusClass` or `formatDate`. Quote line numbers.

## Output

```
## <Component>.vue
| Priority | Area | Line | Finding | Suggested change |
|---|---|---|---|---|
| High | Performance | 255 | max revenue recomputed per bar | hoist into a computed |

## Reuse opportunities (multi-file runs only)
- `formatDate` duplicated in 4 files (Orders.vue:146, ...) → `utils/date.js`
```

Cite an issue that repeats within a file once, listing all its lines. Keep the report to about 15 rows per file.

Priority: **High** for wrong output, errors or broken i18n/filters; **Medium** for performance and pattern violations; **Low** for style and reuse. End with the top three changes to make first.
