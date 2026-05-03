# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Taiwan personal-finance life simulator (台灣人生財務模擬器, currently v7.4.1) — a single-page React app that projects a user's net assets year-by-year from their current age to life expectancy, modelling income, inflation, housing/car loans, children, parents, marriage, passive income, and custom expenses.

The entire application is **one self-contained file**: `index.html` (~1540 lines). There is no build system, no package manager, no tests, and no CI. README.md is a two-line Chinese description.

## Running the App

Open `index.html` directly in a browser, or serve the directory with any static server (e.g. `python3 -m http.server`). All dependencies load from CDNs at runtime — no install step.

## Tech Stack (all via CDN, pinned in `<head>`)

- **React 18** (UMD production build) + **Babel Standalone** for in-browser JSX compilation. Code is in `<script type="text/babel">`, so changes take effect on browser refresh — there is no transpile step.
- **Tailwind CSS** (CDN script, JIT) for styling.
- **Chart.js** for the asset-accumulation line chart and expense doughnut chart.
- **Phosphor Icons** (`ph-*` / `ph-fill ph-*` / `ph-bold ph-*` class names).
- **Marked.js** for rendering AI advice as Markdown (`marked.parse(...)` used inside `dangerouslySetInnerHTML`).
- **Gemini API** (`gemini-2.5-flash-preview-09-2025`) for the optional AI advisor — the `apiKey` constant near the top of the script (currently `""`) must be filled in by the user; the rest of the app works without it.

## Architecture

### Money & units convention (critical)

All user-facing inputs are in **萬 (man = 10,000 TWD)**. The simulation engine converts to raw TWD by multiplying by `10000`, computes internally in TWD, then converts back to 萬 for display (`/ 10000`). When editing any calculation, check whether you are in 萬 or TWD space — mixing them silently produces results that are off by 10,000×.

### Nominal vs. real (實質) assets

The engine tracks `nominalAssets` (TWD, inflated) but reports `realAssets = nominalAssets / deflator` so the chart shows purchasing power in today's dollars. `deflator = (1 + inflationRate/100) ^ (age - currentAge)`. Most expenses are scaled by `deflator` when accumulated. The header KPI `finalRealAssets` is real, but `expenseStats` totals shown in the doughnut are **nominal** lifetime sums — preserve this distinction in any new aggregation.

### `coreSimulation(data)` — the engine (around line 199)

The single source of truth for projections. Takes `{ params, properties, cars, childrenList, passiveIncomes, customExpenses }` and runs one loop from `currentAge` to `lifeExpectancy`. Each year it:

1. Adds salary (until `retireAge`, grown by `incomeGrowth`) and active passive incomes.
2. Adds living, parents, housing (down payment + amortized monthly via `calculateLoan`), car (down payment + loan + 10% annual maintenance for first 15 years), children (per life-stage), marriage, and custom expenses.
3. Updates `nominalAssets += income - expense`, then applies `investReturn` if positive or **5% debt interest if negative** (and records `bankruptAge` on first negative year).
4. Pushes `realAssets`, labels, and a per-year `yearlyDetails` record (income/expense items with formula strings used by `DetailedBreakdownModal`).

Returns `{ labels, dataPoints, bankruptAge, totalEarned, totalPassive, expenseStats, customBreakdown, finalRealAssets, yearlyDetails }`.

**Number-coercion gotcha:** `propertyPlans` and `carPlans` explicitly `Number(...)` every numeric field at the top of the function because plan inputs from the form are strings — see the "修正開始/結束" comment block. Any new numeric field on properties or cars must be coerced the same way or comparisons like `i === plan.buyAge` silently fail.

The function is called from `App` inside `useMemo` keyed on every dependency object; it is also called repeatedly inside `safeRetireAge` (a binary-ish search across retirement ages) and once per saved scenario in `comparisonSimulations`. Keep it pure and reasonably fast.

### `calculateLoan(priceWan, downPaymentPercent, years, ratePercent)`

Standard amortized monthly payment. Used both at plan construction (with `priceWan` in 萬) and inside the year loop with **inflated price** (`plan.price * deflator`) to compute `actualMonthlyPayment` for that purchase year. Returns `{ monthly, daily, totalLoan }` in TWD.

### Component tree (all in the same `<script>` block)

- `App` — owns all state via `useState`. Persists scenarios to `localStorage` under key `life_sim_saves`. Uses `useMemo` for `simulation`, `comparisonSimulations`, `safeRetireAge`, `dailyStats`, `suggestedHousePrice`, `suitableBuyAge`.
- `FinanceChart`, `ExpensePieChart` — Chart.js wrappers; both destroy and recreate the chart on every prop change (see `chartInstanceRef.current.destroy()`); the cleanup function does the same on unmount. Don't forget this if you add another chart.
- `AIAdvisorModal`, `AIBudgetOptimizer` — call `callGeminiAPI(prompt)` (with 3-attempt exponential-backoff retry). Both gracefully render an error string if the key is missing.
- `DetailedBreakdownModal` — renders the per-year breakdown from `simulation.yearlyDetails`.
- `CollapsibleSection`, `AddItemBox`, `NumberControl` — generic UI primitives used throughout the sidebar.
- `IMEInput` — **use this, not raw `<input type="text">`, anywhere the user might type Chinese.** It buffers `onChange` during `compositionstart`/`compositionend` so IME candidate selection doesn't fire premature updates. Existing usage: scenario name, item names for properties/cars/children/passive/custom expenses.

### Save / load / compare

- Save: `handleSave` snapshots `{ params, dailyItems, properties, cars, childrenList, passiveIncomes, customExpenses, useDailyDetail }` into `savedScenarios` and `localStorage`.
- Export/Import: JSON file containing the full `savedScenarios` array (filename `taiwan_life_sim_backup_YYYY-MM-DD.json`).
- Compare: checking a saved scenario adds it to `compareTargets`; each gets re-simulated and overlaid as a dashed line on `FinanceChart`.

If you add a new top-level state slice that should persist, you must add it to **both** `handleSave`'s `currentData` and `handleLoad`'s setters, or the field will be lost across save/load.

## Conventions

- Code comments and all UI strings are in **Traditional Chinese**. Match that style when adding new ones.
- The version number appears in two places — the `<title>` and the header `<h1>` ("人生財務模擬 v7.4.1"). Bump both together.
- Use Tailwind utility classes inline; there are only a few custom classes (`custom-scrollbar`, `chart-container`, `ai-pulse`, `prose *` overrides) defined in the `<style>` block.
- Default child life-stages live in `DEFAULT_CHILD_STAGES` and are deep-cloned per child (`JSON.parse(JSON.stringify(...))`) — preserve the deep copy or all children will share stage edits.
- `parseFloat` (not `parseInt`) is used for monetary fields so users can enter decimals like `1.5` 萬; only ages/years use `parseInt`.

## Git

Active development branch for AI-assisted changes: `claude/add-claude-documentation-hHXZ5` (per repo instructions, push only here unless told otherwise).
