import { useEffect, useMemo, useState } from 'react';

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
// サーバー（get_total_count）と同じく '1' だけを数える
const countScheduled = (dict) => Object.values(dict || {}).filter((v) => String(v) === '1').length;
const countActual = (dict) => Object.values(dict || {}).filter((d) => d && String(d.main) === '1').length;
const insuranceTypeOf = (a) => a.insurance_type ?? a.addon?.insurance_type ?? 'insurance';
const addonTypeOf = (a) => a.type ?? a.addon?.type;

function SummaryTable({ title, badge, badgeClass, headers, rows, footer, emptyText, tableClass = '' }) {
  return (
    <div className="summary-block mb-4">
      <div className="d-flex align-items-center mb-2">
        <span className={`badge me-2 ${badgeClass}`}>{badge}</span>
        <h6 className="fw-bold mb-0">{title}</h6>
      </div>
      <div className="table-responsive">
        <table className={`summary-table ${tableClass} table table-sm table-bordered table-hover align-middle mb-0`}>
          {/* 列幅はCSSで指定（国保・自費で共通のクラス） */}
          <colgroup>
            {headers.map((h) => (
              <col key={h.col} className={`summary-col-${h.col}`} />
            ))}
          </colgroup>
          <thead className="table-light">
            <tr>
              {headers.map((h) => (
                <th key={h.label} className={`summary-col-${h.col} text-nowrap ${h.className ?? 'text-center'}`}>
                  {h.label}
                </th>
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
                    <td key={i} className={`summary-col-${headers[i].col} ${headers[i].className ?? 'text-center'}`}>
                      {c}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
          {rows.length > 0 && footer && (
            <tfoot className="table-group-divider">
              <tr className="fw-bold">
                <td colSpan={headers.length - 1} className="text-end">{footer.label}</td>
                <td className="summary-col-subtotal text-end">{footer.value}</td>
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
  // DjangoからJSONとして渡されたデータ
  const [plans, setPlans] = useState(() => window.initialPlans || []);
  const [addons, setAddons] = useState(() => window.initialAddons || []);
  const [record, setRecord] = useState(() => window.initialMonthlyRecord || null);

  // 初期データの確認
  useEffect(() => {
    log.debug('初期データ', { plans: window.initialPlans, addons: window.initialAddons, record: window.initialMonthlyRecord });
    if (!window.initialMonthlyRecord) log.warn('initialMonthlyRecord がありません（月次記録が未作成？）');
  }, []);

  // カレンダーの更新を受け取る（detail: { plans?, addons?, record? }）
  useEffect(() => {
    const onUpdate = (e) => {
      const d = e.detail || {};
      log.debug('service-summary:update 受信', d);
      if (d.plans) setPlans(d.plans);
      if (d.addons) setAddons(d.addons);
      if ('record' in d) setRecord(d.record);
    };
    window.addEventListener('service-summary:update', onUpdate);
    return () => window.removeEventListener('service-summary:update', onUpdate);
  }, []);

  // 1. 国保：基本プラン
  const planRows = useMemo(() => {
    const rows = plans.map((plan) => {
      const unit = num(plan.unit);
      const scheduleCount = countScheduled(plan.schedule_dict);
      const actualCount = countActual(plan.actual_dict);
      return { id: plan.id, name: plan.service_name, code: plan.service_code, unit, scheduleCount, actualCount, subtotal: unit * actualCount };
    });
    log.table('国保：プラン', rows);
    rows.filter((r) => r.actualCount > r.scheduleCount)
      .forEach((r) => log.warn('実績が予定より多い', { planId: r.id, code: r.code, schedule: r.scheduleCount, actual: r.actualCount }));
    return rows;
  }, [plans]);

  // 2. 加算を国保と自費に分ける
  const { insuranceAddons, selfPayItems, rateAddons } = useMemo(() => {
    const list = Array.isArray(addons) ? addons : Object.values(addons || {});
    const ins = [];
    const self = [];
    const rate = [];
    list.forEach((a, i) => {
      const count = a.days ? a.days.length : num(a.total);
      const base = { key: a.id ?? a.addon?.id ?? a.code ?? `${a.name}-${i}`, name: a.name ?? a.addon?.service_name, count };
      if (insuranceTypeOf(a) === 'self_pay') {
        const price = num(a.price ?? a.addon?.price);
        self.push({ ...base, price, subtotal: price * count });
      } else if (addonTypeOf(a) === 'rate') {
        rate.push(base);                              // 処遇改善加算など：回数で数えない
      } else {
        const unit = num(a.unit ?? a.addon?.unit);
        ins.push({ ...base, unit, subtotal: unit * count });
      }
    });
    log.table('国保：加算', ins);
    log.table('自費', self);
    if (ins.some((r) => r.unit === 0)) {
      log.warn('単位数が0の国保加算があります（addonsに unit が入っていない？）', ins);
    }
    return { insuranceAddons: ins, selfPayItems: self, rateAddons: rate };
  }, [addons]);

  const insuranceUnits = planRows.reduce((s, p) => s + p.subtotal, 0) + insuranceAddons.reduce((s, a) => s + a.subtotal, 0);
  const selfPayTotal = selfPayItems.reduce((s, i) => s + i.subtotal, 0);

  // 画面の集計と月次記録がずれていないか（記録が古いと出る）
  useEffect(() => {
    if (!record) return;
    if (record.service_units != null && num(record.service_units) !== insuranceUnits) {
      log.warn('画面の単位数と月次記録が一致しません', { screen: insuranceUnits, record: record.service_units });
    } else {
      log.debug('単位数一致', insuranceUnits);
    }
  }, [record, insuranceUnits]);

  const insuranceTableRows = [
    ...planRows.map((p) => ({
      key: `p-${p.id}`,
      cells: [
        <>{p.name}<div className="small text-muted">{p.code}</div></>,
        `${fmt(p.unit)} 単位`,
        <span className={p.actualCount === p.scheduleCount ? 'text-primary fw-bold' : 'text-danger fw-bold'}>
          {p.actualCount} / {p.scheduleCount} 回
        </span>,
        `${fmt(p.subtotal)} 単位`,
      ],
    })),
    ...insuranceAddons.map((a) => ({
      key: `a-${a.key}`,
      rowClass: 'table-info',
      cells: [<>└ {a.name}</>, `${fmt(a.unit)} 単位`, `${a.count} 回`, `${fmt(a.subtotal)} 単位`],
    })),
    ...rateAddons.map((a) => ({
      key: `r-${a.key}`,
      rowClass: 'text-muted',
      cells: [<>└ {a.name}（率加算）</>, '—', '—', '月次記録で計算'],
    })),
  ];

  const selfPayTableRows = selfPayItems.map((i) => ({
    key: `s-${i.key}`,
    cells: [i.name, `¥ ${fmt(i.price)}`, `${i.count} 回`, `¥ ${fmt(i.subtotal)}`],
  }));

  return (
    <div className="card mt-4 mb-4 shadow-sm">
      <div className="card-header bg-dark text-white d-flex justify-content-between align-items-center">
        <h5 className="mb-0">月間集計サマリー</h5>
        {record && (
          <span className={`badge ${record.confirmed ? 'bg-success' : 'bg-warning text-dark'}`}>
            {record.confirmed ? '確定済み' : '未確定'}
          </span>
        )}
      </div>

      <div className="card-body">
        <div className="row">
          {/* 左側：国保 / 自費 */}
          <div className="col-md-7 border-end">
            <SummaryTable
              title="国保（介護保険）"
              badge="保険"
              badgeClass="bg-primary"
              tableClass="summary-table--insurance"
              headers={[
                { label: 'サービス名/加算', col: 'name', className: 'text-center' },
                { label: '単位', col: 'price', className: 'text-center' },
                { label: '実績 / 予定', col: 'count', className: 'text-center' },
                { label: '小計', col: 'subtotal', className: 'text-center' },
              ]}
              rows={insuranceTableRows}
              footer={{ label: '限度額管理対象 合計', value: `${fmt(insuranceUnits)} 単位` }}
              emptyText="プランデータがありません"
            />
            <SummaryTable
              title="自費（国保請求なし）"
              badge="自費"
              badgeClass="bg-secondary"
              tableClass="summary-table--self-pay"
              headers={[
                { label: '品目', col: 'name', className: 'text-center' },
                { label: '単価', col: 'price', className: 'text-center' },
                { label: '回数', col: 'count', className: 'text-center' },
                { label: '小計', col: 'subtotal', className: 'text-center' },
              ]}
              rows={selfPayTableRows}
              footer={{ label: '自費 合計', value: `¥ ${fmt(selfPayTotal)}` }}
              emptyText="自費の利用はありません"
            />
          </div>

          {/* 右側：月次記録（DB）の値だけを表示 */}
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