import { useEffect, useState } from "react";
import React from "react";

export default function ClaimMonthly() {
  const today = new Date();
  const initialYear = today.getFullYear();
  const initialMonth = today.getMonth() + 1;

  const [selectedYearMonth, setSelectedYearMonth] = useState(`${initialYear}-${initialMonth}`);
  const [monthlyData, setMonthlyData] = useState(null);

  const generateYearMonthOptions = () => {
    const options = [];
    const startYear = 2024;
    const endYear = today.getFullYear() + 1;

    for (let y = startYear; y <= endYear; y++) {
      for (let m = 1; m <= 12; m++) {
        options.push({
          value: `${y}-${m}`,
          label: `${y}年 ${m}月`
        });
      }
    }
    return options;
  };

  const fetchMonthlyData = async () => {
    try {
      const [year, month] = selectedYearMonth.split("-").map(Number);
      const response = await fetch(`/created_service_list/api/?year=${year}&month=${month}`);
      const data = await response.json();

      setMonthlyData(data);
      console.log("APIレスポンス:", data);
    } catch (e) {
      console.error("データ取得エラー:", e);
    }
  };

  useEffect(() => {
    fetchMonthlyData();
  }, [selectedYearMonth]);

  if (!monthlyData) {
    return <div>読み込み中...</div>;
  }

  const { summary, amounts, checks, records, csv } = monthlyData;

  return (
    <div className="container">

      {/* =========================
          1. ページヘッダー
      ========================= */}
      <div className="page-header">
        <div >
          <h2>国保連請求（月次）</h2>
          <p className="page-description">
            月単位で請求対象者・確定状況・請求金額を確認し、国保連CSVを作成します。
          </p>
        </div>

        <div className="month-selector">
          <select
            value={selectedYearMonth}
            onChange={(e) => setSelectedYearMonth(e.target.value)}
          >
            {generateYearMonthOptions().map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* =========================
          2. 請求ステータス
      ========================= */}
      <section className="card">
        <div className="section-title">
          <h2>請求状況</h2>
          <span className={`status-badge ${summary.unconfirmed_count > 0 ? "status-warning" : "status-ok"}`}>
            {summary.unconfirmed_count > 0 ? "確認中" : "OK"}
          </span>
        </div>

        <div className="summary-grid">
          <div className="summary-item">
            <span className="label">請求対象者</span>
            <strong>{summary.target_users}<span>人</span></strong>
          </div>

          <div className="summary-item">
            <span className="label">サービス提供表</span>
            <strong>{summary.confirmed_count} / {summary.target_users}<span>人 確定</span></strong>
          </div>

          <div className="summary-item warning">
            <span className="label">未確定</span>
            <strong>{summary.unconfirmed_count}<span>人</span></strong>
          </div>

          <div className="summary-item">
            <span className="label">国保連請求総額</span>
            <strong>{summary.total_claim_amount.toLocaleString()}<span>円</span></strong>
          </div>
        </div>

        {summary.unconfirmed_count > 0 && (
          <div className="check-message warning-message">
            <strong>⚠ 国保連CSVを作成できません</strong>
            <p>未確定の利用者がいます。サービス提供表を確定してください。</p>
          </div>
        )}
      </section>

      {/* =========================
          3. 金額集計
      ========================= */}
      <section className="card">
        <div className="section-title">
          <h2>請求金額</h2>
        </div>

        <div className="amount-grid">
          <div className="amount-item">
            <span>総費用</span>
            <strong>{amounts.total_cost.toLocaleString()}円</strong>
          </div>

          <div className="amount-item">
            <span>保険請求額</span>
            <strong>{amounts.benefit_amount.toLocaleString()}円</strong>
          </div>

          <div className="amount-item">
            <span>公費請求額</span>
            <strong>{amounts.public_amount.toLocaleString()}円</strong>
          </div>

          <div className="amount-item">
            <span>利用者負担額</span>
            <strong>{amounts.user_share_amount.toLocaleString()}円</strong>
          </div>
        </div>
      </section>

      {/* =========================
          4. 請求チェック
      ========================= */}
      <section className="card">
        <div className="section-title">
          <h2>請求チェック</h2>
          <span className="check-count">{checks.total_items}項目中 {checks.ok_items}項目OK</span>
        </div>

        <div className="check-list">
          {checks.items.map((item, idx) => (
            <div key={idx} className={`check-row ${item.status}`}>
              <span className="check-icon">{item.status === "ok" ? "✓" : "!"}</span>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      {/* =========================
          5. 請求対象者一覧
      ========================= */}
      <section className="card">
        <div className="section-title">
          <h2>請求対象者</h2>
          <span className="section-note">{monthlyData.year}年{monthlyData.month}月</span>
        </div>

        <div className="table-wrapper">
          <table className="claim-table">
            <thead>
              <tr>
                <th>利用者</th>
                <th>確定</th>
                <th>総費用</th>
                <th>保険請求</th>
                <th>公費請求</th>
                <th>利用者負担</th>
              </tr>
            </thead>

            <tbody>
              {records.map((r, idx) => (
                <tr key={idx} className={r.confirmed ? "" : "row-warning"}>
                  <td>
                    {r.user}
                    {r.public_flag && <span className="public-badge">生活保護</span>}
                  </td>
                  <td>
                    <span className={`table-status ${r.confirmed ? "confirmed" : "unconfirmed"}`}>
                      {r.confirmed ? "✓" : "!"}
                    </span>
                  </td>
                  <td>{r.total_cost.toLocaleString()}円</td>
                  <td>{r.benefit_amount.toLocaleString()}円</td>
                  <td>{r.public_amount.toLocaleString()}円</td>
                  <td>{r.user_share_amount.toLocaleString()}円</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* =========================
          6. CSV作成
      ========================= */}
      <section className="card csv-section">
        <div className="section-title">
          <h2>国保連CSV</h2>
        </div>

        <div className="csv-status">
          <div>
            <span className="label">現在の状態</span>
            <strong>{csv.status === "not_created" ? "未作成" : "作成済み"}</strong>
          </div>

          <button type="button" className="csv-button" disabled={summary.unconfirmed_count > 0}>
            国保連CSVを作成
          </button>
        </div>

        <p className="csv-note">
          ※ 全対象者のサービス提供表が確定し、請求チェックがすべてOKになった後にCSVを作成できます。
        </p>
      </section>

      {/* =========================
          7. CSV作成履歴
      ========================= */}
      <section className="card">
        <div className="section-title">
          <h2>CSV作成履歴</h2>
        </div>

        {csv.history.length === 0 ? (
          <div className="empty-history">この月のCSV作成履歴はありません。</div>
        ) : (
          <ul>
            {csv.history.map((h, idx) => (
              <li key={idx}>{h}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
