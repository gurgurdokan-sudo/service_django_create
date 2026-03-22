    document.addEventListener('DOMContentLoaded', () => {
        console.log("DOM Fully Loaded");
        // 編集モードに入ったかどうかのフラグ
        let isFirstEdit = true;

    // すべての編集可能セルを取得
    const editableCells = document.querySelectorAll('.editable-cell');

    editableCells.forEach(cell => {
        cell.addEventListener('click', function() {
            // 初回クリック時のみアラートを表示
            if (isFirstEdit) {
                alert('編集します');
                isFirstEdit = false;
            }

            // 親要素の属性から「予定(schedule)」か「実績(actual)」かを判定
            const rowType = this.parentElement.getAttribute('data-row-type');
            const currentValue = this.innerText.trim();
            
            let newValue = "";

            if (rowType === 'schedule') {
                // 予定の切り替え: 空白 -> 1 -> x -> 空白
                if (currentValue === "") newValue = "1";
                else if (currentValue === "1") newValue = "x";
                else newValue = "";
            } else {
                // 実績の切り替え: 空白 -> 1 -> △ -> 空白
                if (currentValue === "") newValue = "1";
                else if (currentValue === "1") newValue = "△";
                else newValue = "";
            }

            // 値を書き換え
            this.innerText = newValue;

            // 合計値の再計算（オプション）
            updateRowTotal(this.parentElement);
        });
    });

    // 行の合計（1の数）を計算する関数
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