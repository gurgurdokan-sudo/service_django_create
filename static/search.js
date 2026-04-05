document.addEventListener('DOMContentLoaded', () => {
    const modalOverlay = document.getElementById('serviceModalOverlay');
    const openBtn = document.getElementById('openServiceModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const closeBtn = document.getElementById('closeBtn');
    const submitBtnAddon = document.getElementById('footer-addon');
    const submitBtnBasic = document.getElementById('footer-basic');
    const serviceForm = document.getElementById('main-service-form');

    // 1. モーダル表示・非表示
    if (openBtn) {
        openBtn.addEventListener('click', () => {
            modalOverlay.style.display = 'flex';
        });
    }

    const hideModal = () => { modalOverlay.style.display = 'none'; };
    if (cancelBtn) cancelBtn.addEventListener('click', hideModal);
    if (closeBtn) closeBtn.addEventListener('click', hideModal);

    // 2. タブ切り替え
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const searchBasic = document.getElementById('search-bar-basic');
    const searchAddon = document.getElementById('search-bar-addon');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-tab');
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            tabPanels.forEach(p => p.classList.remove('active'));
            document.getElementById(target).classList.add('active');

            if (target === 'tab-basic') {
                searchBasic.style.display = 'block';
                searchAddon.style.display = 'none';
            } else {
                searchBasic.style.display = 'none';
                searchAddon.style.display = 'block';
            }
        });
    });

    // 3. 基本サービス検索 (時間)
    const btnFilterBasic = document.getElementById('btn_filter_service');
    if (btnFilterBasic) {
        btnFilterBasic.addEventListener('click', () => {
            const start = document.getElementById('modal_start_time').value;
            const end = document.getElementById('modal_end_time').value;
            const [h1, m1] = start.split(':').map(Number);
            const [h2, m2] = end.split(':').map(Number);
            const diffHours = ((h2 * 60 + m2) - (h1 * 60 + m1)) / 60;

            let targetCategory = "";
            if (diffHours < 3) targetCategory = "3時間以下";
            else if (diffHours < 4) targetCategory = "3以上-4未満";
            else if (diffHours < 5) targetCategory = "4以上-5未満";
            else if (diffHours < 6) targetCategory = "5以上-6未満";
            else if (diffHours < 7) targetCategory = "6以上-7未満";
            else if (diffHours < 8) targetCategory = "7以上-8未満";
            else if (diffHours < 9) targetCategory = "8以上-9未満";

            document.querySelectorAll('.basic-row').forEach(row => {
                const stayTime = row.getAttribute('data-stay-time');
                row.style.display = stayTime.includes(targetCategory) ? '' : 'none';
            });
        });
    }

    // 4. AddOnサービス検索 (名称)
    const btnFilterAddon = document.getElementById('btn_filter_addon');
    if (btnFilterAddon) {
        btnFilterAddon.addEventListener('click', () => {
            const keyword = document.getElementById('addon_keyword').value.toLowerCase();
            document.querySelectorAll('.addon-row').forEach(row => {
                const name = row.getAttribute('data-name').toLowerCase();
                row.style.display = name.includes(keyword) ? '' : 'none';
            });
        });
    }

    // 5. リセットボタン
    document.getElementById('btn_reset_basic')?.addEventListener('click', () => {
        document.querySelectorAll('.basic-row').forEach(row => row.style.display = '');
    });
    document.getElementById('btn_reset_addon')?.addEventListener('click', () => {
        document.getElementById('addon_keyword').value = "";
        document.querySelectorAll('.addon-row').forEach(row => row.style.display = '');
    });
    // 5. フォーム送信時の確認
    if (serviceForm) {
        serviceForm.addEventListener('submit', (e) => {
            // 送信のきっかけになったボタンを取得
            const triggerButton = e.submitter;

            if (triggerButton && triggerButton.closest('.modal-footer')) {
                const selected = serviceForm.querySelector('input[name="selected_service"]:checked');
                if (!selected) {
                    e.preventDefault();
                    alert('サービスを選択してください。');
                    return;
                }
                if (selected.value.startsWith('addon_')) {
                    // 確認ダイアログ
                    if (!confirm(`この内容で追加サービスを追加しますか？`)) {
                        e.preventDefault(); // キャンセル時は送信中止
                    }
                }
                const start = document.getElementById('modal_start_time')?.value;
                const end = document.getElementById('modal_end_time')?.value;
                if (selected.value.startsWith('basic_')) {
                    if (end === '00:00') {
                        e.preventDefault();
                        alert('時間を設定してください。');
                        return;
                    }
                    // 確認ダイアログ
                    if (end !== '00:00') {
                        if (!confirm(`開始: ${start}\n終了: ${end}\nこの内容でサービスを追加しますか？`)) {
                            e.preventDefault(); // キャンセル時は送信中止
                        }
                    }
                }
            }
        });
    }
});