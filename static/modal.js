// edit.js
document.addEventListener('DOMContentLoaded', () => {
    const editableCells = document.querySelectorAll('.editable-cell');

    editableCells.forEach(cell => {
        cell.addEventListener('click', async function() {
            const planId = this.closest("tr").getAttribute("data-plan-id");
            const rowType = this.parentElement.getAttribute('data-row-type');
            const day = this.getAttribute('data-day');
            const currentValue = this.innerText.trim();

            // 値の切り替えロジック
            let newValue = "";
            if (rowType === 'schedule') {
                newValue = (currentValue === "") ? "1" : (currentValue === "1" ? "x" : "");
            } else {
                newValue = (currentValue === "") ? "1" : (currentValue === "1" ? "△" : "");
            }

            // UIを即座に更新（楽観的アップデート）
            this.innerText = newValue;

            // REST API へ送信
            try {
                const response = await fetch(`/api/plan/${planId}/update/`, {
                    method: "PATCH",
                    headers: { 
                        "Content-Type": "application/json",
                        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({ day, value: newValue, row_type: rowType })
                });
                const data = await response.json();
                
                // 合計値をAPIからの戻り値で更新
                this.parentElement.querySelector('.total-cell').innerText = data.new_total;
            } catch (err) {
                console.error("保存失敗", err);
                alert("通信エラーが発生しました");
            }
        });
    });
});