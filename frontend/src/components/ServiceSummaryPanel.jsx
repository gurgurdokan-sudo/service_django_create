import { useState, useMemo } from 'react';

export default function ServiceSummaryPanel() {
  // DjangoからJSONとして渡されたデータを取得
  const initialPlans = window.initialPlans || [];
  const initialAddons = window.initialAddons || [];
  const initialMonthlyRecord = window.initialMonthlyRecord || {};

  // 状態（必要に応じて将来的に画面側の入力変更と連動させることも可能）
  const [plans, setPlans] = useState(initialPlans);
  const [addons, setAddons] = useState(initialAddons);
  const [record, setRecord] = useState(initialMonthlyRecord);

  // 1. 各基本プランの予定・実績合計回数を計算
  const planSummaries = plans.map((plan) => {
    // 予定回数の計算
    const scheduleCount = plan.schedule_dict
      ? Object.values(plan.schedule_dict).filter((v) => v !== '' && v != null).length
      : 0;

    // 実績回数の計算（mainのカウント）
    const actualCount = plan.actual_dict
      ? Object.values(plan.actual_dict).filter((d) => d && d.main !== '' && d.main != null).length
      : 0;

    const unit = plan.unit || 0;

    return {
      id: plan.id,
      name: plan.service_name,
      unit,
      scheduleCount,
      actualCount,
      totalUnits: unit * actualCount,
    };
  });

  // 2. 加算の合計日数を計算
  const addonSummaries = useMemo(() => {
    // addonsが辞書またはリストの場合の安全な処理
    const list = Array.isArray(addons) ? addons : Object.values(addons);
    return list.map((a) => {
      const daysCount = a.days ? a.days.length : a.total || 0;
      return {
        name: a.name,
        count: daysCount,
      };
    });
  }, [addons]);

  // 全プランの実績単位数の合計を簡易算出
  const totalServiceUnits = planSummaries.reduce((sum, p) => sum + p.totalUnits, 0);

  return (
    <div className="card mt-4 mb-4 shadow-sm">
      <div className="card-header bg-dark text-white d-flex justify-content-between align-items-center">
        <h5 className="mb-0">📊 月間集計サマリー（リアルタイム試算）</h5>
        <span className="badge bg-light text-dark">自動計算</span>
      </div>

      <div className="card-body">
        <div className="row">
          {/* 左側：プラン・加算別の実績回数・単位数 */}
          <div className="col-md-7 border-end">
            <h6 className="text-secondary fw-bold mb-3">■ プラン別実績・単位数内訳</h6>
            <div className="table-responsive">
              <table className="table table-sm table-bordered align-middle">
                <thead className="table-light">
                  <tr>
                    <th>サービス名</th>
                    <th className="text-center">単価/単位</th>
                    <th className="text-center">実績回数</th>
                    <th className="text-end">小計単位</th>
                  </tr>
                </thead>
                <tbody>
                  {planSummaries.map((p, idx) => (
                    <tr key={p.id ?? idx}>
                      <td>{p.name}</td>
                      <td className="text-center">{p.unit} 単位</td>
                      <td className="text-center fw-bold text-primary">{p.actualCount} 回</td>
                      <td className="text-end fw-bold">{p.totalUnits.toLocaleString()} 単位</td>
                    </tr>
                  ))}
                  {planSummaries.length === 0 && (
                    <tr>
                      <td colSpan="4" className="text-center text-muted">
                        プランデータがありません
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {addonSummaries.length > 0 && (
              <>
                <h6 className="text-secondary fw-bold mt-3 mb-2">■ 適用加算一覧</h6>
                <ul className="list-group list-group-flush small">
                  {addonSummaries.map((a, idx) => (
                    <li
                      key={idx}
                      className="list-group-item d-flex justify-content-between align-items-center py-1"
                    >
                      <span className="text-danger fw-bold">{a.name}</span>
                      <span>
                        実績日数: <strong>{a.count}</strong> 日
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>

          {/* 右側：MonthlyRecord モデルに基づく金額・単位のサマリー */}
          <div className="col-md-5">
            <h6 className="text-secondary fw-bold mb-3">■ 請求・費用サマリー (ServiceMonthlyRecord)</h6>
            <div className="p-3 bg-light rounded border">
              <div className="d-flex justify-content-between mb-2">
                <span>総単位数:</span>
                <strong className="fs-6">{record.total_units || totalServiceUnits} 単位</strong>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span>限度内単位数 / 超過:</span>
                <span>
                  {record.within_units || 0} / {record.over_units || 0} 単位
                </span>
              </div>

              <hr className="my-2" />

              <div className="d-flex justify-content-between mb-2">
                <span>総費用:</span>
                <strong>¥ {(record.total_cost || 0).toLocaleString()}</strong>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span>国保給付費請求額:</span>
                <strong className="text-success">¥ {(record.benefit_amount || 0).toLocaleString()}</strong>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span>利用者負担額:</span>
                <strong className="text-primary">¥ {(record.user_share_amount || 0).toLocaleString()}</strong>
              </div>
              {record.public_amount > 0 && (
                <div className="d-flex justify-content-between mb-2">
                  <span>公費請求額:</span>
                  <span>¥ {record.public_amount.toLocaleString()}</span>
                </div>
              )}
              <div className="d-flex justify-content-between text-muted small mt-3 pt-2 border-top">
                <span>実績日数:</span>
                <span>{record.actual_count || 0} 日</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}