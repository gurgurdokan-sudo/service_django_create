import { useEffect, useState } from "react";

function CreatedServiceList() {
  const [records, setRecords] = useState([]);

  useEffect(() => {
    fetch("/created_service_list/api/ ")
      .then(res => res.json())
      .then(data => setRecords(data.records));
  }, []);

  return (
    <div className="container">
      <div className="header-container">
        <h1 className="page-title">作成済みサービス提供表一覧</h1>
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
          {records.length === 0 && (
            <tr>
              <td colSpan="4">サービス提供表が登録されていません</td>
            </tr>
          )}

          {records.map((r, i) => (
            <tr key={i}>
              <td>{r.user}</td>
              <td>{r.date}</td>
              <td>{r.confirmed ? "☑" : ""}</td>
              <td>
                <button onClick={() => window.location.href = r.download_url}>
                  ダウンロード
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default CreatedServiceList;
