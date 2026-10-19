// Shapes of web/public/data/lab.json (written by scripts/build_site.py) and
// the derived values every section shares.

export interface RawRow {
  d: string // Friday close date
  c: number // SPY close (dividend-adjusted)
  v: number // VIX
  p?: number // P(next week closes higher), from the ledger
  s?: number // range half-width as a log-return sigma, from the ledger
  src?: 'live' | 'backfilled' // absent = walk-forward backtest
}

export interface DirectionMetrics {
  weeks: number
  accuracy: number
  always_up_accuracy: number
  brier_skill: number
  mcnemar_p_vs_always_up: number
  down_call_share: number
  down_call_accuracy: number | null
}

export interface RangeMetrics {
  coverage: number
  avg_half_width_pct: number
  coverage_in_biggest_10pct_moves: number
  worst_year_coverage: number
  best_year_coverage: number
}

export interface LabFile {
  updated: string
  launched: string
  rows: RawRow[]
  experiment: {
    test_start: string
    last_week: string
    direction: Record<string, DirectionMetrics>
    range: Record<string, RangeMetrics>
  }
}

export interface Row extends RawRow {
  lo?: number
  hi?: number
}

export interface GradedWeek {
  i: number // index of the Friday the call was made
  d: string // Friday the call was graded
  rangeHit: boolean
  dirHit: boolean
  upWeek: boolean
  live: boolean
}

export interface Lab {
  file: LabFile
  rows: Row[]
  graded: GradedWeek[]
}

export function buildLab(file: LabFile): Lab {
  const rows: Row[] = file.rows.map((r) =>
    r.s == null ? r : { ...r, lo: r.c * Math.exp(-r.s), hi: r.c * Math.exp(r.s) },
  )
  const graded: GradedWeek[] = []
  for (let i = 0; i < rows.length - 1; i++) {
    const r = rows[i]
    if (r.p == null || r.lo == null || r.hi == null) continue
    const next = rows[i + 1].c
    const up = next > r.c
    graded.push({
      i,
      d: rows[i + 1].d,
      rangeHit: next >= r.lo && next <= r.hi,
      dirHit: up === r.p >= 0.5,
      upWeek: up,
      live: r.src != null,
    })
  }
  return { file, rows, graded }
}

export async function loadLab(): Promise<Lab> {
  const res = await fetch('/data/lab.json')
  if (!res.ok) throw new Error(String(res.status))
  return buildLab(await res.json())
}

// ---------- formatting ----------

const asDate = (d: string) => new Date(d + 'T12:00:00Z')

export const money = (v: number) => '$' + v.toFixed(2)
export const pct = (v: number) => Math.round(v * 100) + '%'
export const pct1 = (v: number) => (v * 100).toFixed(1) + '%'
export const widthPct = (s: number) => (Math.exp(s) - 1) * 100

export const longDate = (d: string) =>
  asDate(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
export const shortDate = (d: string) =>
  asDate(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })

export function nextFriday(d: string): string {
  const t = asDate(d)
  t.setUTCDate(t.getUTCDate() + 7)
  return t.toISOString().slice(0, 10)
}

/** A round tick step giving roughly `count` gridlines across [min, max]. */
export function tickStep(min: number, max: number, count: number): number {
  const raw = (max - min) / count
  const p = 10 ** Math.floor(Math.log10(raw))
  return [1, 2, 2.5, 5, 10].map((s) => s * p).find((s) => s >= raw)!
}

export function ticks(min: number, max: number, count: number): number[] {
  const step = tickStep(min, max, count)
  const out: number[] = []
  for (let v = Math.ceil(min / step) * step; v <= max; v += step) out.push(v)
  return out
}
