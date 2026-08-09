import { useEffect, useState } from "react";
import React from "react";

export default function CreatedServiceList() {
  const today = new Date();
  const initialYear = today.getFullYear();
  const initialMonth = today.getMonth() + 1;
  // 初期値を "2024-5" のような形式にする
  const [selectedYearMonth, setSelectedYearMonth] = useState(`${initialYear}-${initialMonth}`);
  const [records, setRecords] = useState([]);

  // セレクトボックスの選択肢を作る関数
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

  const fetchRecords = async () => {
    try {
      const [year, month] = selectedYearMonth.split('-').map(Number);
      const response = await fetch(`/created_service_list/api/?year=${year}&month=${month}`);
      const data = await response.json();
      
      // DjangoのAPIが { "records": [...] } で返している場合は data.records をセット
      // 直接 [...] で返している場合は data をセット
      const result = data.records || data;
      setRecords(Array.isArray(result) ? result : []);
      
      console.log("届いたデータ:", result);
    } catch (e) {
      console.error("データ取得エラー:", e);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [selectedYearMonth]);

  return (
    <div className="container">
      <div className="header-container">
        <h1 className="page-title">作成済みサービス提供表一覧</h1>

        <div className="filter-controls" style={{ marginBottom: "20px" }}>
          <label>表示月：</label>
          {/* 年月プルダウン */}
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

      <table className="data-table">
        <thead>
          <tr>
            <th>利用者</th>
            <th>作成月</th>
            <th>確定済み</th>
            <th>ダウンロード</th>
          </tr>
        </thead>

        <tbody>
          {records.length === 0 ? (
            <tr>
              <td colSpan="4" style={{ textAlign: "center" }}>
                サービス提供表が作成されていません
              </td>
            </tr>
          ) : (
            records.map((r, idx) => (
              <tr key={idx}>
                <td>{r.user}</td>
                <td>{r.date ? `${r.date.split('-')[0]}年 ${r.date.split('-')[1]}月 ` : ''}</td>
                <td>{r.confirmed ? "☑" : ""}</td>
                <td>
                  <button
                    onClick={() =>
                      (window.location.href = `/dashboard/download_service_sheet/${r.user_id}?dis_year=${r.year}&dis_month=${r.month}`)
                    }
                  >
                    ダウンロード
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}