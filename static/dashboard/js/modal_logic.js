const hideAllBasicRows = () => {
    document.querySelectorAll('.basic-row').forEach(row => {
        row.style.display = 'none';
    });
};
document.addEventListener('DOMContentLoaded', () => {
    const modalOverlay = document.getElementById('serviceModalOverlay');
    const openBtn = document.getElementById('openServiceModal');
    const serviceBtn = document.getElementById('service-btn');
    const closeBtn = document.getElementById('closeBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    if (openBtn) {
        openBtn.addEventListener('click', () => {
            modalOverlay.style.display = 'flex';
            hideAllBasicRows(); // モーダルを開くたびに初期化（非表示）
        });
    }

    const hideModal = () => {
        modalOverlay.style.display = 'none';
    };
    if (closeBtn) closeBtn.addEventListener('click', hideModal);
    if (cancelBtn) cancelBtn.addEventListener('click', hideModal);

    const tabBtns =document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const searchBasic = document.getElementById('search-bar-basic');
    const searchAddon = document.getElementById('search-bar-addon');

    tabBtns.forEach(btn=>{
        btn.addEventListener('click',()=>{
            const target = btn.getAttribute('data-tab');
            tabBtns.forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            tabPanels.forEach(p=>p.classList.remove('active'));
            document.getElementById(target).classList.add('active');
            if(target==='tab-basic'){
                searchBasic.style.display = 'block';
                searchAddon.style.display = 'none';
                document.querySelectorAll('input[name="selected_addon"]').forEach(r => r.checked = false);
            } else {
                searchBasic.style.display = 'none';
                searchAddon.style.display = 'block';
                document.querySelectorAll('input[name="selected_basic"]').forEach(r => r.checked = false);
            }
        });
    });
    const btnFilterBasic = document.getElementById('btn_filter_service');
    if (btnFilterBasic) {
        btnFilterBasic.addEventListener('click', () => {
            // 選択されていたラジオボタンも解除
            document.querySelectorAll('input[name="selected_basic"]').forEach(radio => {
                radio.checked = false;
            });
            const start = document.getElementById('modal_start_time').value;
            const end = document.getElementById('modal_end_time').value;
            const [h1, m1] = start.split(':').map(Number);
            const [h2, m2] = end.split(':').map(Number);
            const diffHours = ((h2 * 60 + m2) - (h1 * 60 + m1)) / 60;
            if (diffHours <= 0) {
                Swal.fire({
                    icon: 'warning',
                    title: '時間の指定が不正です',
                    text: '終了時間は開始時間より後の時間を設定してください。'
                });
                hideAllBasicRows();
                return;
            }
            if (!start || !end || end === '00:00') {
                Swal.fire({
                    icon: 'warning',
                    title: '時間が未入力です',
                    text: '開始時間と終了時間を正しく設定してから検索してください。'
                });
                hideAllBasicRows(); // 一覧は隠したままにする
                return;
            }

            let targetCategory = "";
            if (diffHours < 0) targetCategory = "error";
            else if (diffHours < 3) targetCategory = "3時間以下";
            else if (diffHours < 4) targetCategory = "3以上-4未満";
            else if (diffHours < 5) targetCategory = "4以上-5未満";
            else if (diffHours < 6) targetCategory = "5以上-6未満";
            else if (diffHours < 7) targetCategory = "6以上-7未満";
            else if (diffHours < 8) targetCategory = "7以上-8未満";
            else if (diffHours < 9) targetCategory = "8以上-9未満";
           
            let matchCount = 0;
            document.querySelectorAll('.basic-row').forEach(row => {
                const stayTime = row.getAttribute('data-stay-time') || '';
                if (stayTime.includes(targetCategory)) {
                    row.style.display = '';
                    matchCount++;
                } else {
                    row.style.display = 'none';
                }
            });
            if (matchCount === 0) {
                Swal.fire({
                    icon: 'info',
                    text: '該当する時間のサービスが見つかりませんでした。'
                });
            }
            document.getElementById('btn_reset_basic')?.addEventListener('click', () => {
                hideAllBasicRows();
                const startInput = document.getElementById('modal_start_time');
                const endInput = document.getElementById('modal_end_time');
                if (startInput) startInput.value = '';
                if (endInput) endInput.value = '';

                // 選択されていたラジオボタンも解除
                document.querySelectorAll('input[name="selected_basic"]').forEach(radio => {
                    radio.checked = false;
                });
            });
        });
    }
    const btnFilterAddon = document.getElementById('btn_filter_addon');
    if (btnFilterAddon) {
        btnFilterAddon.addEventListener('click', () => {
            // 選択されていたラジオボタンも解除
            document.querySelectorAll('input[name="selected_addon"]').forEach(radio => {
                radio.checked = false;
            });
            const keyword = document.getElementById('addon_keyword').value.trim();

            document.querySelectorAll('.addon-row').forEach(row => {
                const name = row.dataset.addonName || row.getAttribute('data-addon-name') || '';

                // キーワードが含まれているか判定
                if (name.includes(keyword)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    document.getElementById('btn_reset_basic')?.addEventListener('click',()=>{
    document.querySelectorAll('.basic-row').forEach(row=> row.style.display = '');
    });

    // ここからフォーム送信処理
    if (serviceBtn) {
        serviceBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            console.log('POST START')
            const selectedBasic = document.querySelector('input[name="selected_basic"]:checked');
            const selectedAddon = document.querySelector('input[name="selected_addon"]:checked');
            const selected = selectedBasic || selectedAddon;
            if (!selected){
                 return Swal.fire({
                    icon: 'warning',
                    text: 'サービスを選択してください'
                });
            }
            const userId = document.getElementById('userid').getAttribute("data-user-id");
            const startTime = document.getElementById('modal_start_time').value;
            const endTime = document.getElementById('modal_end_time').value;
            if (selectedBasic) {
                if (endTime === '00:00'){
                    return Swal.fire({
                        icon: 'warning',
                        text: '時間を設定してください。'
                    });
                }
                const result = await Swal.fire({
                    title: 'サービスプランの追加',
                    html: `開始: <b>${startTime}</b><br />終了: <b>${endTime}</b><br /><br />この内容でサービスを追加しますか？`,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: '追加する',
                    cancelButtonText: 'キャンセル',
                    confirmButtonColor: '#3085d6',
                    cancelButtonColor: '#d33'
                });
                // キャンセルされたら中断
                if (!result.isConfirmed) return;
                // API送信
                    const year = document.getElementById("dis_year").value;
                    const month = document.getElementById("dis_month").value;
                    console.log(`${year} ${month}`)
                    const response = await fetch(`/api/plan/${userId}/create/`, {
                        method: "POST",
                        headers: { 
                            "Content-Type": "application/json",
                            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        body: JSON.stringify({
                            selected_service: selectedBasic.value.split('_')[1],
                            start_time: startTime,
                            end_time: endTime,
                            year: year,
                            month: month,
                        })
                    }); 
                if (response.ok) {
                    location.reload(); // 成功したら新しいPlanを表示する
                    console.log('POST RESPONSE OK');
                }
                return;
            }


            const planId = document.getElementById('main_plan_select').value;
            if (selectedAddon && !planId ) {
                 return Swal.fire({
                    icon: 'warning',
                    text: '加算を紐付ける予定サービスを選択してください'
                });
            }
            if(selectedAddon){
               // 1. 親の tr から加算名を取得
                const addonRow = selectedAddon.closest('tr');
                const addonName = addonRow ? addonRow.dataset.addonName : '選択した加算';
                window.console.log(`${addonName}を選択しました`)
                // 2. SweetAlert2 で確認ダイアログを表示
                const result = await Swal.fire({
                    title: '加算の登録',
                    html: `<b>${addonName}を</b><br />登録しますか？`,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: '登録する',
                    cancelButtonText: 'キャンセル',
                    confirmButtonColor: '#3085d6',
                    cancelButtonColor: '#d33'
                });

                // キャンセルされたら処理を中断
                if (!result.isConfirmed) return;


                // API送信
                const response = await fetch(`/api/plan/${planId}/update/`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        addon_id: selectedAddon.value.split('_')[1],
                        days: [1,], // mainのscheに合わせる
                        row_type: 'actual_full',
                    })
                });
                
                if (response.ok) {
                    location.reload(); // 成功したらリロードして新しい行を表示
                }else{
                    Swal.fire({
                        icon: 'error',
                        text: '更新に失敗しました'
                    });
                }
                return;
            }
        });
    }
    document.querySelectorAll('.selectable-row').forEach(row => {
        row.addEventListener('click', () => {
        const radio = row.querySelector('input[type="radio"]');
        radio.checked = true;
        });
    });

});