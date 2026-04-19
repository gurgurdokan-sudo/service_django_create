// edit.js
document.addEventListener('DOMContentLoaded', () => {
    let isFirstEdit = true;
    const editableCells = document.querySelectorAll('.editable-cell');

    editableCells.forEach(cell => {
        cell.addEventListener('click', async function() {
            if(isFirstEdit) {
                alert('編集を開始します');
                isFirstEdit = false;
            }
            const userId = document.getElementById("userid").getAttribute("data-user-id")
            const planId = this.closest("tr").getAttribute("data-plan-id");
            const rowType = this.parentElement.getAttribute('data-row-type');
            const day = this.getAttribute('data-day');
            const currentValue = this.innerText.trim();

            // 値の切り替えロジック
            let newValue = "";
            if (rowType === 'schedule') {
                newValue = (currentValue === "") ? "1" : (currentValue === "1" ? "x" : "");
            } else {
                newValue = (currentValue === "") ? "1" : "";
            }

            // UIを即座に更新（楽観的アップデート）
            this.innerText = newValue;

            // REST API へ送信
            if (rowType === 'actual_addon') newValue = this.getAttribute('data-addon-name');
            try {
                const response = await fetch(`/api/plan/${userId}/update/`, {
                    method: "PATCH",
                    headers: { 
                        "Content-Type": "application/json",
                        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({ day:day, value: newValue, row_type: rowType, plan_id:planId})
                });
                const data = await response.json();
                    // 応答がエラー（404や500）の場合は、JSONパース前にテキストとして確認
                if (!response.ok) {
                    const errorHtml = await response.text();
                    console.error("Server Error HTML:", errorHtml);
                    throw new Error("サーバーエラーが発生しました");
                }
                // 合計値をAPIからの戻り値で更新
                this.parentElement.querySelector('.total-cell').innerText = data.total;
            } catch (err) {
                console.error("保存失敗", err);
                alert("通信エラーが発生しました");
            }
        });
    });
});