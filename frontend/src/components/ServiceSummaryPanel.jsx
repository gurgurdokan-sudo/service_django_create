import { useEffect, useState } from 'react';

/* eslint-disable no-console */
const DEBUG = import.meta.env.DEV || localStorage.getItem('LOG_LEVEL') === 'debug';
const log = {
  debug: (...a) => DEBUG && console.debug('[ServiceSummary]', ...a),
  warn: (...a) => console.warn('[ServiceSummary]', ...a),
  error: (...a) => console.error('[ServiceSummary]', ...a),
  table: (label, rows) => {
    if (!DEBUG) return;
    console.groupCollapsed(`[ServiceSummary] ${label}`);
    console.table(rows);
    console.groupEnd();
  },
};
/* eslint-enable no-console */

// ---- ヘルパー ----
const num = (v) => Number(v) || 0;
const fmt = (v) => num(v).toLocaleString();

const EMPTY_SUMMARY = {
  insurance: { plans: [], addons: [], rate_addon: null },
  self_pay: { items: [], total: 0 },
  record: null,
  error: null,
};

// APIのサマリーを、足りない項目があっても壊れない形にそろえる
function normalizeSummary(s) {
  const ins = s?.insurance ?? {};
  const self = s?.self_pay ?? {};
  return {
    insurance: {
      plans: ins.plans ?? [],
      addons: ins.addons ?? [],
      rate_addon: ins.rate_addon ?? null,
    },
    self_pay: { items: self.items ?? [], total: num(self.total) },
    record: s?.record ?? null,
    error: s?.error ?? null,
  };
}

// #service-summary-root の data属性から集計APIを呼ぶ
async function fetchSummary() {
  const { userId, year, month } =
    document.getElementById('service-summary-root')?.dataset ?? {};
  if (!userId || !year || !month) {
    throw new Error('data-user-id / data-year / data-month がありません');
  }
  const url =
    `/api/users/${encodeURIComponent(userId)}/summary/` +
    `?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`;

  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  const json = await response.json().catch(() => null);
  if (!response.ok || json?.status !== 'ok') {
    throw new Error(json?.message || `集計APIエラー（${response.status}）`);
  }
  return json.summary;
}

function SummaryTable({ title, badge, badgeClass, headers, rows, footer, emptyText }) {
  return (
    <div className="mb-4">
      <div className="d-flex align-items-center mb-2">
        <span className={`badge me-2 ${badgeClass}`}>{badge}</span>
        <h6 className="fw-bold mb-0">{title}</h6>
      </div>
      <div className="table-responsive">
        <table className="table table-sm table-bordered table-hover align-middle mb-0">
          <thead className="table-light">
            <tr>
              {headers.map((h) => (
                <th key={h.label} className={`text-nowrap ${h.className ?? 'text-center'}`}>{h.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={headers.length} className="text-center text-muted py-3">{emptyText}</td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.key} className={r.rowClass}>
                  {r.cells.map((c, i) => (
                    <td key={i} className={headers[i].className ?? 'text-center'}>{c}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
          {rows.length > 0 && footer && (
            <tfoot className="table-group-divider">
              <tr className="fw-bold">
                <td colSpan={headers.length - 1} className="text-end">{footer.label}</td>
                <td className="text-end">{footer.value}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}

function Row({ label, value, strong, className = '' }) {
  return (
    <div className={`d-flex justify-content-between mb-2 ${className}`}>
      <span>{label}</span>
      {strong ? <strong>{value}</strong> : <span>{value}</span>}
    </div>
  );
}

export default function ServiceSummaryPanel() {
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  // 1. 初回：自分で集計APIを呼ぶ  2. 以降：edit.js からの更新を受け取る
  useEffect(() => {
    let alive = true;

    const apply = (s) => {
      if (!alive) return;
      log.debug('サマリー受信', s);
      setSummary(normalizeSummary(s));
      setLoadError(null);
      setLoading(false);
    };

    const onUpdate = (e) => apply(e.detail);
    window.addEventListener('service-summary:update', onUpdate);

    if (window.latestSummary) {
      apply(window.latestSummary);
    } else {
      fetchSummary()
        .then(apply)
        .catch((err) => {
          if (!alive) return;
          log.error('初回の集計取得に失敗', err);
          setLoadError(err.message);
          setLoading(false);
        });
    }

    return () => {
      alive = false;
      window.removeEventListener('service-summary:update', onUpdate);
    };
  }, []);

  const { insurance, self_pay: selfPay, record, error } = summary;

  // 国保：プラン（APIの値をそのまま使う）
  const planRows = insurance.plans.map((p) => ({
    key: `p-${p.id}`,
    cells: [
      <>{p.name}<div className="small text-muted">{p.code}</div></>,
      `${fmt(p.unit)} 単位`,
      <span className={num(p.actual_count) === num(p.schedule_count) ? 'text-primary fw-bold' : 'text-danger fw-bold'}>
        {fmt(p.actual_count)} / {fmt(p.schedule_count)} 回
      </span>,
      `${fmt(p.subtotal)} 単位`,
    ],
  }));

  // 国保：加算
  const addonRows = insurance.addons.map((a, i) => ({
    key: `a-${a.id ?? a.code ?? i}`,
    rowClass: 'table-info',
    cells: [
      <>└ {a.name ?? a.service_name}</>,
      `${fmt(a.unit)} 単位`,
      `${fmt(a.count)} 回`,
      `${fmt(a.subtotal)} 単位`,
    ],
  }));

  // 国保：処遇改善加算などの率加算
  const rate = insurance.rate_addon;
  const rateRows = rate
    ? [{
        key: `r-${rate.code}`,
        rowClass: 'text-muted',
        cells: [
          <>└ {rate.name}（{num(rate.rate)}%）</>,
          '—',
          '—',
          `${fmt(rate.units)} 単位`,
        ],
      }]
    : [];

  const insuranceUnits =
    insurance.plans.reduce((s, p) => s + num(p.subtotal), 0) +
    insurance.addons.reduce((s, a) => s + num(a.subtotal), 0) +
    num(rate?.units);

  // 自費
  const selfPayRows = selfPay.items.map((it) => ({
    key: `s-${it.id}`,
    cells: [it.name, `¥ ${fmt(it.price)}`, `${fmt(it.count)} 回`, `¥ ${fmt(it.subtotal)}`],
  }));
  const selfPayTotal = selfPay.total;

  log.table('国保：プラン', insurance.plans);
  log.table('国保：加算', insurance.addons);
  log.table('自費', selfPay.items);

  if (loading) {
    return <div className="text-muted small my-3">集計を読み込み中…</div>;
  }

  return (
    <div className="card mt-4 mb-4 shadow-sm">
      <div className="card-header kon-dark text-white d-flex justify-content-between align-items-center">
        <h5 className="mb-0">月間集計サマリー</h5>
        {record && (
          <span className={`badge ${record.confirmed ? 'bg-success' : 'bg-warning text-dark'}`}>
            {record.confirmed ? '確定済み' : '未確定'}
          </span>
        )}
      </div>

      <div className="card-body">
        {(loadError || error) && (
          <div className="alert alert-danger small">{loadError || error}</div>
        )}

        <div className="row">
          {/* 左側：国保 / 自費 */}
          <div className="col-md-7 border-end">
            <SummaryTable
              title="国保（介護保険）"
              badge="保険"
              badgeClass="bg-primary"
              headers={[
                { label: 'サービス名/加算', className: 'text-start' },
                { label: '単位', className: 'text-end' },
                { label: '実績 / 予定', className: 'text-center' },
                { label: '小計', className: 'text-end' },
              ]}
              rows={[...planRows, ...addonRows, ...rateRows]}
              footer={{ label: '国保 合計', value: `${fmt(insuranceUnits)} 単位` }}
              emptyText="プランデータがありません"
            />
            <SummaryTable
              title="自費（国保請求なし）"
              badge="自費"
              badgeClass="bg-secondary"
              headers={[
                { label: '品目', className: 'text-start' },
                { label: '単価', className: 'text-end' },
                { label: '回数', className: 'text-center' },
                { label: '小計', className: 'text-end' },
              ]}
              rows={selfPayRows}
              footer={{ label: '自費 合計', value: `¥ ${fmt(selfPayTotal)}` }}
              emptyText="自費の利用はありません"
            />
          </div>

          {/* 右側：請求・費用 */}
          <div className="col-md-5">
            <h6 className="text-secondary fw-bold mb-3">請求・費用サマリー</h6>
            {!record ? (
              <div className="alert alert-secondary small mb-0">月次記録がまだありません（未計算）</div>
            ) : (
              <div className="p-3 bg-light rounded border">
                <Row label="総単位数" value={`${fmt(record.total_units)} 単位`} strong />
                <Row label="限度内 / 超過" value={`${fmt(record.within_units)} / ${fmt(record.over_units)} 単位`} />
                <hr className="my-2" />
                <Row label="総費用（10割）" value={`¥ ${fmt(record.total_cost)}`} strong />
                <Row label="国保給付費請求額" value={<span className="text-success">¥ {fmt(record.benefit_amount)}</span>} strong />
                {num(record.public_amount) > 0 && (
                  <Row label="公費請求額" value={`¥ ${fmt(record.public_amount)}`} />
                )}
                <Row label="利用者負担額（保険分）" value={<span className="text-primary">¥ {fmt(record.user_share_amount)}</span>} strong />
                <hr className="my-2" />
                <Row label="自費請求額" value={`¥ ${fmt(selfPayTotal)}`} />
                <Row
                  label="利用者請求 合計"
                  value={`¥ ${fmt(num(record.user_share_amount) + selfPayTotal)}`}
                  strong
                  className="fs-6"
                />
                <div className="d-flex justify-content-between text-muted small mt-3 pt-2 border-top">
                  <span>実績日数</span>
                  <span>{fmt(record.actual_count)} 日</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}