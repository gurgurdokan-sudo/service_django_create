document.addEventListener('DOMContentLoaded', () => {
    let isFirstEdit = true;

    // JSON文字列をオブジェクトに変換（失敗したら空オブジェクト）
    let scheduleData = window.initialSchedule || {};
    let actualData = window.initialActual || {};
    console.log("Initial Schedule Data:", scheduleData);
    // JSONをHidden Inputに反映させる関数
    function syncJson() {
        scheduleInput.value = JSON.stringify(scheduleData);
        actualInput.value = JSON.stringify(actualData);
        console.log("JSON Synced");
    }

    // 初期表示処理: 保存されているデータをセルに反映する
    function initCells() {
        const rows = document.querySelectorAll('.data-row');
        rows.forEach(row => {
            const rowType = row.getAttribute('data-row-type');
            const dataObj = (rowType === 'schedule') ? scheduleData : actualData;
            const cells = row.querySelectorAll('.editable-cell');

            cells.forEach(cell => {
                const day = cell.getAttribute('data-day');
                // オブジェクトにデータがあれば表示、なければ空
                if (dataObj[day]) {
                    cell.innerText = dataObj[day];
                }
            });
            // 初期表示後の合計計算
            updateRowTotal(row);
        });
    }

    // 初期実行
    initCells();

    // 3. 編集イベント（クリック処理）
    const editableCells = document.querySelectorAll('.editable-cell');
    editableCells.forEach(cell => {
        cell.addEventListener('click', function() {
            if (isFirstEdit) {
                alert('編集を開始します');
                isFirstEdit = false;
            }

            const rowType = this.parentElement.getAttribute('data-row-type');
            const day = this.getAttribute('data-day');
            const currentValue = this.innerText.trim();
            
            let newValue = "";

            if (rowType === 'schedule') {
                if (currentValue === "") newValue = "1";
                else if (currentValue === "1") newValue = "x";
                else newValue = "";
                scheduleData[day] = newValue;
            } else {
                if (currentValue === "") newValue = "1";
                else if (currentValue === "1") newValue = "△";
                else newValue = "";
                actualData[day] = newValue;
            }

            this.innerText = newValue;

            // データの同期
            syncJson();
            // 合計計算
            updateRowTotal(this.parentElement);
        });
    });

    // 合計計算関数
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