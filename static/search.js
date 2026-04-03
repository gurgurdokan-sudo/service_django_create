document.addEventListener('DOMContentLoaded', () => {
    // モーダル開閉ロジック
    const overlay = document.getElementById('serviceModalOverlay');
    const openBtn = document.getElementById('openServiceModal');
    const closeBtn = document.getElementById('closeBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const startTimeInput = document.getElementById('modal_start_time');
    const endTimeInput = document.getElementById('modal_end_time');
        // --- タブ切り替えロジック ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const searchBar = document.getElementById('search-bar-container');

    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-tab');

            // 1. ボタンの状態を更新
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // 2. パネルの表示を切り替え
            tabPanels.forEach(p => p.classList.remove('active'));
            document.getElementById(target).classList.add('active');

            // 3. 基本サービス以外のタブでは検索バーを隠す
            if (target === 'tab-basic') {
                searchBar.style.display = 'block';
            } else {
                searchBar.style.display = 'none';
            }
        });
    });
    openBtn.addEventListener('click', () => {
        startTimeInput.value = "09:00";
        endTimeInput.value = "18:00"; 
        overlay.style.display = 'flex'; 
    });
    const hideModal = () => { overlay.style.display = 'none'; };
    closeBtn.addEventListener('click', hideModal);
    cancelBtn.addEventListener('click', hideModal);

    // --- サービス絞り込み機能 ---
    const btnFilter = document.getElementById('btn_filter_service');
    const btnReset = document.getElementById('btn_reset_filter');
    const rows = document.querySelectorAll('.service-row');
    const nameSearchInput = document.getElementById('modal_name_search');

    btnFilter.addEventListener('click', () => {
        const start = document.getElementById('modal_start_time').value;
        const end = document.getElementById('modal_end_time').value;
        const searchName = nameSearchInput.value.toLowerCase();

        if (!start || !end) {
            alert('開始時間と終了時間の両方を入力してください。');
            return;
        }

        // 時間差（分）を計算
        const [h1, m1] = start.split(':').map(Number);
        const [h2, m2] = end.split(':').map(Number);
        const diffMinutes = (h2 * 60 + m2) - (h1 * 60 + m1);

        if (diffMinutes <= 0) {
            alert('終了時間は開始時間より後の時間を設定してください。');
            return;
        }

        const diffHours = diffMinutes / 60;

        // 滞在時間カテゴリの判定
        let targetCategory = "";
        if (diffHours < 3) targetCategory = "3時間以下";
        else if (diffHours < 4) targetCategory = "3以上-4未満";
        else if (diffHours < 5) targetCategory = "4以上-5未満";
        else if (diffHours < 6) targetCategory = "5以上-6未満";
        else if (diffHours < 7) targetCategory = "6以上-7未満";
        else if (diffHours < 8) targetCategory = "7以上-8未満";
        else if (diffHours < 9) targetCategory = "8以上-9未満";

        // 名称一致チェック (共通)
        const nameMatches = rowName.includes(searchName);

        // テーブル行の表示・非表示を切り替え
        rows.forEach(row => {
            const stayTimeText = row.getAttribute('data-stay-time');
            if (stayTimeText.includes(targetCategory)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });

    btnReset.addEventListener('click', () => {
        document.getElementById('modal_start_time').value = "";
        document.getElementById('modal_end_time').value = "";
        rows.forEach(row => row.style.display = '');
    });
});