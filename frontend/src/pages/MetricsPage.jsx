import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { Activity, Clock, Target, AlertTriangle, RefreshCw, ThumbsUp, DollarSign, HelpCircle } from 'lucide-react';
import { API_BASE } from '../config';

/* ─── helpers ─────────────────────────────────────────────────────────────── */

function timeAgo(isoStr) {
  if (!isoStr) return '—';
  const diff = Math.floor((Date.now() - new Date(isoStr + 'Z').getTime()) / 1000);
  if (diff < 5)   return 'just now';
  if (diff < 60)  return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function scoreToConfidence(score) {
  if (score >= 0.70) return 'HIGH';
  if (score >= 0.50) return 'MEDIUM';
  return 'LOW';
}

/* ─── sub-components ─────────────────────────────────────────────────────── */

function HeroCard({ icon: Icon, value, suffix, label, color, subtext }) {
  return (
    <div style={{
      background: '#1a1a1a',
      border: '1px solid #2a2a2a',
      borderRadius: '12px',
      padding: '24px',
    }}>
      <div className="flex items-start justify-between mb-3">
        <Icon className="w-4 h-4 opacity-40" style={{ color }} />
      </div>
      <div className="flex items-end gap-1 mb-2">
        <span className="font-mono-ui leading-none" style={{ fontSize: '48px', color, lineHeight: 1 }}>
          {value ?? '—'}
        </span>
        {suffix && (
          <span className="font-mono-ui pb-1.5" style={{ fontSize: '18px', color, opacity: 0.6 }}>
            {suffix}
          </span>
        )}
      </div>
      <p className="font-mono-ui uppercase tracking-widest text-xs" style={{ color: '#555' }}>
        {label}
      </p>
      {subtext && (
        <p className="text-xs mt-1.5" style={{ color: '#444', lineHeight: '1.4' }}>
          {subtext}
        </p>
      )}
    </div>
  );
}

function ConfidenceBadgePill({ level }) {
  const map = {
    HIGH:   { cls: 'badge-high',   icon: '●' },
    MEDIUM: { cls: 'badge-medium', icon: '◐' },
    LOW:    { cls: 'badge-low',    icon: '○' },
  };
  const { cls, icon } = map[level] || map.LOW;
  return (
    <span className={cls} style={{ fontSize: '10px', padding: '3px 9px' }}>
      <span>{icon}</span> {level}
    </span>
  );
}

/* ─── custom tooltip for line chart ─────────────────────────────────────── */

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const ms = payload[0].value;
  return (
    <div style={{
      background: '#1a1a1a',
      border: '1px solid #2a2a2a',
      borderRadius: '8px',
      padding: '8px 12px',
      fontSize: '12px',
      fontFamily: "'DM Mono', monospace",
    }}>
      <span style={{ color: '#888' }}>Query #{payload[0].payload.idx}  </span>
      <span style={{ color: '#c6f135' }}>{ms} ms</span>
    </div>
  );
}

/* ─── main page ──────────────────────────────────────────────────────────── */

export default function MetricsPage() {
  const [data,       setData]       = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/metrics`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastRefresh(Date.now());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + 10-second auto-refresh
  useEffect(() => {
    fetchMetrics();
    const id = setInterval(fetchMetrics, 10_000);
    return () => clearInterval(id);
  }, [fetchMetrics]);


  /* ── derived values ──────────────────────────────────────────────────── */

  const latencyColor = !data ? '#555'
    : data.avg_response_latency_ms < 500 ? '#4ade80'
    : data.avg_response_latency_ms < 1500 ? '#fbbf24'
    : '#f87171';

  const scoreColor = !data ? '#555'
    : data.avg_retrieval_score > 0.70 ? '#4ade80'
    : data.avg_retrieval_score > 0.50 ? '#fbbf24'
    : '#f87171';

  const fallbackColor = !data ? '#555'
    : data.fallback_rate_percent < 10 ? '#4ade80'
    : data.fallback_rate_percent < 25 ? '#fbbf24'
    : '#f87171';

  const helpfulColor = !data ? '#555'
    : data.helpfulness_percent > 80 ? '#4ade80'
    : data.helpfulness_percent > 50 ? '#fbbf24'
    : '#f87171';

  // Chart data — last 50 reversed (oldest → newest left to right)
  const chartData = data?.recent_queries
    ? [...data.recent_queries].reverse().map((q, i) => ({
        idx:     i + 1,
        ms:      q.response_latency_ms,
        label:   `#${i + 1}`,
      }))
    : [];

  // Confidence distribution
  const confCounts = { HIGH: 0, MEDIUM: 0, LOW: 0 };
  (data?.recent_queries || []).forEach(q => {
    confCounts[scoreToConfidence(q.retrieval_score)]++;
  });
  const confTotal = confCounts.HIGH + confCounts.MEDIUM + confCounts.LOW || 1;
  const confPct = {
    HIGH:   Math.round((confCounts.HIGH   / confTotal) * 100),
    MEDIUM: Math.round((confCounts.MEDIUM / confTotal) * 100),
    LOW:    Math.round((confCounts.LOW    / confTotal) * 100),
  };

  /* ── render ──────────────────────────────────────────────────────────── */

  return (
    <div className="flex-1 overflow-y-auto min-h-0" style={{ background: '#0a0a0a' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px 48px' }}>

        {/* ── Page header ─────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="font-brand" style={{ fontSize: '22px', color: '#c6f135', letterSpacing: '3px' }}>
              METRICS
            </h2>
            <p className="font-mono-ui text-xs mt-1" style={{ color: '#555' }}>
              Last 50 queries · auto-refreshes every 10 s
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Live indicator */}
            <span className="flex items-center gap-1.5 font-mono-ui text-xs" style={{ color: '#4ade80' }}>
              <span className="animate-volt-pulse">●</span> LIVE
            </span>
            {/* Manual refresh */}
            <button
              onClick={fetchMetrics}
              className="flex items-center gap-1.5 font-mono-ui text-xs px-3 py-1.5 rounded-lg"
              style={{
                background: '#1a1a1a',
                border: '1px solid #2a2a2a',
                color: '#888',
              }}
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 px-4 py-3 rounded-xl font-mono-ui text-sm"
               style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.25)', color: '#f87171' }}>
            Failed to load metrics: {error}
          </div>
        )}

        {/* ── Section 1: Hero stats ────────────────────────────────────── */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(5, 1fr)',
          gap: '16px',
          marginBottom: '32px',
        }}>
          <HeroCard
            icon={Activity}
            value={loading ? '…' : (data?.total_queries_served ?? 0).toLocaleString()}
            label="Queries Served"
            color="#c6f135"
          />
          <HeroCard
            icon={Clock}
            value={loading ? '…' : data?.avg_response_latency_ms ?? 0}
            suffix="ms"
            label="Avg Response Time"
            color={latencyColor}
          />
          <HeroCard
            icon={Target}
            value={loading ? '…' : data?.avg_retrieval_score?.toFixed(2) ?? '0.00'}
            label="Retrieval Quality"
            color={scoreColor}
          />
          <HeroCard
            icon={AlertTriangle}
            value={loading ? '…' : data?.fallback_rate_percent ?? 0}
            suffix="%"
            label="Fallback Rate"
            color={fallbackColor}
            subtext="How often the system refuses to answer"
          />
          <HeroCard
            icon={ThumbsUp}
            value={loading ? '…' : (data?.feedback_total ?? 0) === 0 ? '—' : Math.round(data?.helpfulness_percent ?? 0)}
            suffix={(data?.feedback_total ?? 0) > 0 ? '%' : undefined}
            label="Helpfulness"
            color={helpfulColor}
            subtext={data?.feedback_total ? `${data.feedback_up} 👍 · ${data.feedback_down} 👎` : 'No feedback yet'}
          />
        </div>

        {/* ── Section 2: Recent queries table ─────────────────────────── */}
        <div style={{
          background: '#111',
          border: '1px solid #1e1e1e',
          borderRadius: '12px',
          overflow: 'hidden',
          marginBottom: '32px',
        }}>
          <div className="px-5 py-4 flex items-center justify-between"
               style={{ borderBottom: '1px solid #1e1e1e' }}>
            <span className="font-mono-ui uppercase tracking-widest text-xs" style={{ color: '#555' }}>
              Last {Math.min(data?.recent_queries?.length ?? 0, 20)} Queries
            </span>
            {lastRefresh && (
              <span className="font-mono-ui text-xs" style={{ color: '#333' }}>
                updated {timeAgo(new Date(lastRefresh).toISOString().slice(0, -1))}
              </span>
            )}
          </div>

          {loading ? (
            <div className="py-16 text-center font-mono-ui text-xs" style={{ color: '#444' }}>
              Loading…
            </div>
          ) : !data?.recent_queries?.length ? (
            <div className="py-16 text-center font-mono-ui text-xs" style={{ color: '#444' }}>
              No queries logged yet
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#1e1e1e' }}>
                    {['Time', 'Query', 'Confidence', 'Response', 'Sources'].map(h => (
                      <th key={h}
                          className="font-mono-ui uppercase tracking-widest"
                          style={{
                            fontSize: '10px',
                            color: '#555',
                            padding: '10px 16px',
                            textAlign: 'left',
                            fontWeight: 600,
                            whiteSpace: 'nowrap',
                          }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.recent_queries.slice(0, 20).map((q, i) => {
                    const conf = scoreToConfidence(q.retrieval_score);
                    return (
                      <tr key={q.query_id}
                          style={{
                            background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.012)',
                            cursor: 'default',
                          }}>
                        {/* Time */}
                        <td className="font-mono-ui"
                            style={{ padding: '10px 16px', fontSize: '11px', color: '#555', whiteSpace: 'nowrap' }}>
                          {timeAgo(q.timestamp)}
                        </td>
                        {/* Query text */}
                        <td style={{ padding: '10px 16px', maxWidth: '360px' }}>
                          <span
                            style={{
                              display: 'block',
                              fontSize: '12px',
                              color: '#aaa',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                            title={q.query_text}
                          >
                            {q.query_text.length > 60
                              ? q.query_text.slice(0, 60) + '…'
                              : q.query_text}
                          </span>
                        </td>
                        {/* Confidence */}
                        <td style={{ padding: '10px 16px', whiteSpace: 'nowrap' }}>
                          <ConfidenceBadgePill level={conf} />
                        </td>
                        {/* Response time */}
                        <td className="font-mono-ui"
                            style={{
                              padding: '10px 16px',
                              fontSize: '12px',
                              color: q.response_latency_ms < 500 ? '#4ade80'
                                   : q.response_latency_ms < 1500 ? '#fbbf24'
                                   : '#f87171',
                              whiteSpace: 'nowrap',
                            }}>
                          {q.response_latency_ms} ms
                        </td>
                        {/* Sources */}
                        <td className="font-mono-ui"
                            style={{ padding: '10px 16px', fontSize: '12px', color: '#555' }}>
                          {q.chunks_retrieved}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Section 3: Response time chart ──────────────────────────── */}
        <div style={{
          background: '#0f0f0f',
          border: '1px solid #1e1e1e',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '32px',
        }}>
          <div className="flex items-center justify-between mb-5">
            <span className="font-mono-ui uppercase tracking-widest text-xs" style={{ color: '#555' }}>
              Response Time — Last {chartData.length} Queries
            </span>
            <span className="font-mono-ui text-xs" style={{ color: '#333' }}>
              ms per query
            </span>
          </div>

          {chartData.length < 2 ? (
            <div className="py-12 text-center font-mono-ui text-xs" style={{ color: '#333' }}>
              Need at least 2 queries to render chart
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#1e1e1e" strokeDasharray="0" vertical={false} />
                <XAxis
                  dataKey="idx"
                  tick={{ fill: '#444', fontSize: 10, fontFamily: "'DM Mono', monospace" }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: '#444', fontSize: 10, fontFamily: "'DM Mono', monospace" }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                  tickFormatter={v => `${v}`}
                />
                <Tooltip content={<ChartTooltip />} />
                {/* SLA threshold */}
                <ReferenceLine
                  y={1500}
                  stroke="#f87171"
                  strokeDasharray="4 4"
                  strokeOpacity={0.5}
                  label={{
                    value: 'SLA 1500 ms',
                    fill: '#f87171',
                    fontSize: 10,
                    fontFamily: "'DM Mono', monospace",
                    position: 'insideTopRight',
                    opacity: 0.6,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="ms"
                  stroke="#c6f135"
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 4, fill: '#c6f135', strokeWidth: 0 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* ── Section 4: Cost + Confidence (2-col) ────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '16px', marginBottom: '32px' }}>

          {/* Cost card */}
          <div style={{ background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: '12px', padding: '24px' }}>
            <div className="flex items-start justify-between mb-3">
              <DollarSign className="w-4 h-4 opacity-40" style={{ color: '#c6f135' }} />
            </div>
            <div className="flex items-end gap-1 mb-2">
              <span className="font-mono-ui" style={{ fontSize: '36px', color: '#c6f135', lineHeight: 1 }}>
                {loading ? '…' : `$${(data?.avg_cost_per_query_usd ?? 0).toFixed(4)}`}
              </span>
            </div>
            <p className="font-mono-ui uppercase tracking-widest text-xs" style={{ color: '#555' }}>
              Cost Per Query
            </p>
            <p className="text-xs mt-1.5" style={{ color: '#444', lineHeight: '1.4' }}>
              ${loading ? '…' : (data?.total_cost_usd ?? 0).toFixed(4)} total
              &nbsp;·&nbsp;{loading ? '…' : (data?.total_tokens ?? 0).toLocaleString()} tokens
            </p>
            <p className="text-xs mt-1" style={{ color: '#333' }}>
              Gemini 2.5 Flash · $0.075/$0.30 per M tokens
            </p>
          </div>

          {/* Confidence distribution */}
          <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: '12px', padding: '24px' }}>
            <span className="font-mono-ui uppercase tracking-widest text-xs block mb-5" style={{ color: '#555' }}>
              Confidence Distribution
            </span>
            {confTotal <= 1 && !data?.recent_queries?.length ? (
              <p className="font-mono-ui text-xs" style={{ color: '#333' }}>No data yet</p>
            ) : (
              <>
                <div style={{ display: 'flex', height: '40px', borderRadius: '6px', overflow: 'hidden', gap: '2px' }}>
                  {confPct.HIGH > 0 && (
                    <div style={{ flex: confPct.HIGH, background: 'rgba(74,222,128,0.18)', border: '1px solid rgba(74,222,128,0.3)', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span className="font-mono-ui" style={{ fontSize: '11px', color: '#4ade80', fontWeight: 600 }}>
                        {confPct.HIGH > 6 ? `${confPct.HIGH}%` : ''}
                      </span>
                    </div>
                  )}
                  {confPct.MEDIUM > 0 && (
                    <div style={{ flex: confPct.MEDIUM, background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.25)', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span className="font-mono-ui" style={{ fontSize: '11px', color: '#fbbf24', fontWeight: 600 }}>
                        {confPct.MEDIUM > 6 ? `${confPct.MEDIUM}%` : ''}
                      </span>
                    </div>
                  )}
                  {confPct.LOW > 0 && (
                    <div style={{ flex: confPct.LOW, background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.2)', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span className="font-mono-ui" style={{ fontSize: '11px', color: '#f87171', fontWeight: 600 }}>
                        {confPct.LOW > 6 ? `${confPct.LOW}%` : ''}
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-6 mt-4">
                  {[
                    { label: 'HIGH',   pct: confPct.HIGH,   color: '#4ade80', count: confCounts.HIGH   },
                    { label: 'MEDIUM', pct: confPct.MEDIUM, color: '#fbbf24', count: confCounts.MEDIUM },
                    { label: 'LOW',    pct: confPct.LOW,    color: '#f87171', count: confCounts.LOW    },
                  ].map(({ label, pct, color, count }) => (
                    <div key={label} className="flex items-center gap-2">
                      <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: color, opacity: 0.7 }} />
                      <span className="font-mono-ui text-xs" style={{ color: '#555' }}>{label}</span>
                      <span className="font-mono-ui text-xs" style={{ color }}>{pct}%</span>
                      <span className="font-mono-ui text-xs" style={{ color: '#333' }}>({count})</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* ── Section 5: Top unanswered queries ───────────────────────── */}
        <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: '12px', overflow: 'hidden', marginBottom: '32px' }}>
          <div className="px-5 py-4 flex items-center gap-2" style={{ borderBottom: '1px solid #1e1e1e' }}>
            <HelpCircle className="w-3.5 h-3.5" style={{ color: '#f87171' }} />
            <span className="font-mono-ui uppercase tracking-widest text-xs" style={{ color: '#555' }}>
              Queries the System Could Not Answer
            </span>
          </div>
          {!data?.unanswered_queries?.length ? (
            <div className="py-10 text-center font-mono-ui text-xs" style={{ color: '#444' }}>
              No unanswered queries — all questions resolved with confidence.
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: '#1e1e1e' }}>
              {data.unanswered_queries.map((q, i) => (
                <div key={i} className="px-5 py-3 flex items-center gap-4">
                  <span className="flex-1 text-xs" style={{ color: '#888', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={q.query_text}>
                    {q.query_text.length > 80 ? q.query_text.slice(0, 80) + '…' : q.query_text}
                  </span>
                  <span className="flex-shrink-0 font-mono-ui text-xs px-2 py-0.5 rounded"
                        style={{ background: 'rgba(248,113,113,0.1)', color: '#f87171', border: '1px solid rgba(248,113,113,0.2)' }}>
                    score {q.retrieval_score?.toFixed(2) ?? '0.00'}
                  </span>
                  <span className="flex-shrink-0 font-mono-ui text-xs" style={{ color: '#444' }}>
                    {timeAgo(q.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
