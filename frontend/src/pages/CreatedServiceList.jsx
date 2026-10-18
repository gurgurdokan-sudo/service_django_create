import React, { useCallback, useEffect, useState } from "react";
import Swal from "sweetalert2";
const CSV_CREATE_URL = "/dashboard/create_kokuho_csv/";

const toMonthKey = (year, month) =>
  `${year}-${String(month).padStart(2, "0")}`;

const formatNumber = (value) =>
  Number(value ?? 0).toLocaleString("ja-JP");

export default function ClaimMonthly() {
  const today = new Date();
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1;

  const [selectedYearMonth, setSelectedYearMonth] = useState(() =>
    toMonthKey(currentYear, currentMonth)
  );
  const [monthlyData, setMonthlyData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [isCreatingCsv, setIsCreatingCsv] = useState(false);
  const [csvError, setCsvError] = useState("");

  const fetchMonthlyData = useCallback(async () => {
    setIsLoading(true);
    setLoadError("");
    setMonthlyData(null);

    try {
      const [year, month] = selectedYearMonth.split("-").map(Number);
      const response = await fetch(
        `/created_service_list/api/?year=${year}&month=${month}`,
        { headers: { Accept: "application/json" } }
      );

      if (!response.ok) {
        throw new Error(`月次データの取得に失敗しました（${response.status}）`);
      }

      const data = await response.json();
      setMonthlyData(data);
    } catch (error) {
      setLoadError(error.message || "月次データの取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  }, [selectedYearMonth]);
  useEffect(() => {
    fetchMonthlyData();
  }, [fetchMonthlyData]);

  if (isLoading && !monthlyData) {
    return <div className="container">読み込み中...</div>;
  }

  if (!monthlyData) {
    return (
      <div className="container">
        <p className="check-message warning-message">
          {loadError || "月次データを表示できませんでした。"}
        </p>
        <button
          type="button"
          className="btn btn-outline"
          onClick={fetchMonthlyData}
        >
          再読み込み
        </button>
      </div>
    );
  }

  const { summary, amounts, checks, records, csv } = monthlyData;

  const checkItems = Array.isArray(checks.items) ? checks.items : [];
  const hasBlockingError = checkItems.some(
    (item) => item.status === "error"
  );

  const targetUsers = Number(summary.target_users ?? 0);
  const confirmedCount = Number(summary.confirmed_count ?? 0);
  const unconfirmedCount = Number(summary.unconfirmed_count ?? 0);

  const canCreateCsv =
    targetUsers > 0 &&
    confirmedCount === targetUsers &&
    unconfirmedCount === 0 &&
    !hasBlockingError;

  const isCsvIssued = csv.is_issued ?? csv.status === "created";
  const csvHistory = Array.isArray(csv.history) ? csv.history : [];

  const handleYearMonthChange = (offset) => {
    const [year, month] = selectedYearMonth.split("-").map(Number);
    const next = new Date(year, month - 1 + offset, 1);
    const earliest = new Date(currentYear - 1, 0, 1);
    const latest = new Date(currentYear, currentMonth - 1, 1);

    if (next < earliest || next > latest) {
      return;
    }

    setSelectedYearMonth(toMonthKey(next.getFullYear(), next.getMonth() + 1));
  };

  const generateYearMonthOptions = () => {
    const options = [];

    for (let year = currentYear - 1; year <= currentYear; year += 1) {
      const lastMonth = year === currentYear ? currentMonth : 12;

      for (let month = 1; month <= lastMonth; month += 1) {
        options.push({
          value: toMonthKey(year, month),
          label: `${year}年 ${month}月`,
        });
      }
    }

    return options;
  };

  const checkStatusLabel = (status) => {
    if (status === "ok") return "OK";
    if (status === "error") return "要修正";
    return "要確認";
  };
  const getCsrfToken = () =>
    document.querySelector(
      '#csrf-token-form [name="csrfmiddlewaretoken"]'
    )?.value ?? "";
    
  const handleCreateCsv = async (event) => {
    event.preventDefault();
      event.preventDefault();
    if (!canCreateCsv || isCreatingCsv) return;

    if (isCsvIssued) {
      const result = await Swal.fire({
        title: "CSVの再作成",
        text: "CSVは作成済みです。再作成しますか？",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "再作成する",
        cancelButtonText: "キャンセル",
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
      });

      // キャンセルされたら中断
      if (!result.isConfirmed) {
        return;
      }
    }

    setIsCreatingCsv(true);
    setCsvError("");

    try {
      const [year, month] = selectedYearMonth.split("-").map(Number);

      // POST送信
      const response = await fetch(CSV_CREATE_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken() || "", // Django必須のCSRFトークン
        },
        body: JSON.stringify({
          year: year,
          month: month,
        }),
      });

      if (!response.ok) {
        throw new Error(`CSV作成に失敗しました（${response.status}）`);
      }
      const contentType = response.headers.get("content-type") || "";

      // 作成APIがJSONでダウンロードURLを返す場合
      if (contentType.includes("application/json")) {
        const result = await response.json();
        const downloadUrl = result.file_url || result.download_url;

        if (!downloadUrl) {
          throw new Error(result.error || "CSVのダウンロードURLがありません");
        }

        window.location.assign(downloadUrl);
      } else {
        // CSVファイルを直接返す場合
        if (contentType.includes("text/html")) {
          throw new Error("CSVではなくHTMLが返りました。URLやログイン状態を確認してください。");
        }

        const blob = await response.blob();
        const objectUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = objectUrl;
        link.download = `kokuho_${year}_${String(month).padStart(2, "0")}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();

        setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
      }

      await fetchMonthlyData();
      Swal.fire({
        icon: "success",
        title: "作成完了",
        text: "国保連CSVを作成しました。",
        timer: 2000,
        showConfirmButton: false,
      });
    } catch (error) {
      setCsvError(error.message || "CSV作成に失敗しました");
      Swal.fire({
        icon: "error",
        title: "エラー",
        text: error.message || "CSV作成に失敗しました",
      });
    } finally {
      setIsCreatingCsv(false);
    }
  };

  const claimStatus =
    targetUsers === 0
      ? { label: "対象者なし", className: "status-warning" }
      : hasBlockingError
        ? { label: "要修正", className: "status-warning" }
        : unconfirmedCount > 0
          ? { label: "確認中", className: "status-warning" }
          : { label: "OK", className: "status-ok" };

  return (
    <div className="container">
      {/* =========================
          1. ページヘッダー
      ========================= */}
      <div className="page-header">
        <div>
          <h2>国保連請求</h2>
          <span className={`status-badge ${claimStatus.className}`}>
            {claimStatus.label}
          </span>

        </div>

        <div className="month-selector" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button className="btn btn-outline" onClick={() => handleYearMonthChange(-1)}>&lt;</button>
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
          <button className="btn btn-outline" onClick={() => handleYearMonthChange(1)}>&gt;</button>
        </div>
      </div>

      {/* =========================
          2. 請求ステータス
      ========================= */}
      <section className="card">
        <div className="section-title">
          <h2>請求状況</h2>
          <span className={`status-badge ${claimStatus.className}`}>
            {claimStatus.label}
          </span>
        </div>

        <div className="summary-grid">
          <div className="summary-item">
            <span className="label">請求対象者</span>
            <strong>
              {formatNumber(targetUsers)}
              <span>人</span>
            </strong>
          </div>

          <div className="summary-item">
            <span className="label">サービス提供表</span>
            <strong>{formatNumber(summary.confirmed_count)} / {formatNumber(summary.target_users)}<span>人 確定</span></strong>
          </div>

          <div className="summary-item warning">
            <span className="label">未確定</span>
            <strong>{formatNumber(summary.unconfirmed_count)}<span>人</span></strong>
          </div>

          <div className="summary-item">
            <span className="label">国保連請求総額</span>
            <strong>{formatNumber(summary.total_claim_amount)}<span>円</span></strong>
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
            <strong>{formatNumber(amounts.total_cost)}円</strong>
          </div>

          <div className="amount-item">
            <span>保険請求額</span>
            <strong>{formatNumber(amounts.benefit_amount)}円</strong>
          </div>

          <div className="amount-item">
            <span>公費請求額</span>
            <strong>{formatNumber(amounts.public_amount)}円</strong>
          </div>

          <div className="amount-item">
            <span>利用者負担額</span>
            <strong>{formatNumber(amounts.user_share_amount)}円</strong>
          </div>
        </div>
      </section>

      {/* =========================
          4. 請求チェック
      ========================= */}
      <section className="card">
        <div className="section-title">
          <h2>請求チェック</h2>
          <span className="check-count">{checkItems.length}項目中{" "}
            {checkItems.filter(i => i.status === "ok").length}項目OK</span>
        </div>

        <div className="check-list">
          {checkItems.map((item, idx) => (
            <div key={`${item.label}-${idx}`} className={`check-row ${item.status}`}>
              <span className="check-icon">{item.status === "ok" ? "✓" : item.status === "error" ? "×" : "！"}</span>
              <span>{item.label}</span>
              <strong>{item.value || checkStatusLabel(item.status)}</strong>
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
                      {r.confirmed ? "✓" : "! "}
                    </span>
                  </td>
                  <td>{formatNumber(r.total_cost)}円</td>
                  <td>{formatNumber(r.benefit_amount)}円</td>
                  <td>{formatNumber(r.public_amount)}円</td>
                  <td>{formatNumber(r.user_share_amount)}円</td>
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
          <form onSubmit={handleCreateCsv}>
          <button
            type="submit"
            className={`btn ${canCreateCsv ? "btn-success" : "btn-danger"}`}
            disabled={!canCreateCsv || isCreatingCsv}
          >
            {isCreatingCsv
              ? "作成中..."
              : isCsvIssued
                ? "国保連CSVを再作成"
                : "国保連CSVを作成"}
          </button>
        </form>
        </div>
        {csvError && (
          <div className="check-message warning-message">
            <strong>CSV作成エラー</strong>
            <p>{csvError}</p>
          </div>
        )}

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
        {csvHistory.length === 0 ? (
          <div className="empty-history">
            この月のCSV作成履歴はありません。
          </div>
        ) : (
          <ul>
            {csvHistory.map((item, index) => (
              <li key={`${item.generated_at || "csv"}-${index}`}>
                {item.generated_at || "作成日時なし"}
                {item.file_url && (
                  <a href={item.file_url}> ダウンロード</a>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
