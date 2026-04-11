document.addEventListener('DOMContentLoaded', () => {
    let isFirstEdit = true;

    const editableCells = document.querySelectorAll('.editable-cell');

    editableCells.forEach(cell => {
        cell.addEventListener('click', function() {

            if (isFirstEdit) {
                alert('編集を開始します');
                isFirstEdit = false;
            }

            // ① planId を tr から取得
            const planId = this.closest("tr").getAttribute("data-plan-id");

            // ② rowType と day を取得
            const rowType = this.parentElement.getAttribute('data-row-type');
            const day = this.getAttribute('data-day');

            // ③ newValue を決定
            const currentValue = this.innerText.trim();
            let newValue = "";

            if (rowType === 'schedule') {
                if (currentValue === "") newValue = "1";
                else if (currentValue === "1") newValue = "x";
                else newValue = "";
            } else {
                if (currentValue === "") newValue = "1";
                else if (currentValue === "1") newValue = "△";
                else newValue = "";
            }

            // 画面に反映
            this.innerText = newValue;

            // ④ REST API に保存
            fetch(`/api/plan/${planId}/update/`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    day: day,
                    value: newValue,
                    row_type: rowType
                })
            })
            .then(res => res.json())
            .then(data => console.log("Saved:", data));

            // ⑤ 合計更新
            updateRowTotal(this.parentElement);
        });
    });

    function updateRowTotal(rowElement) {
        const cells = rowElement.querySelectorAll('.editable-cell');
        const totalCell = rowElement.querySelector('.total-cell');
        let count = 0;
        cells.forEach(c => {
            if (c.innerText.trim() === "1") count++;
        });
        if (totalCell) totalCell.innerText = count;
    }
});
