// search.js
document.addEventListener('DOMContentLoaded', () => {
    const modalOverlay = document.getElementById('serviceModalOverlay');
    const openBtn = document.getElementById('openServiceModal');
    const serviceBtn = document.getElementById('service-btn');
    const closeBtn = document.getElementById('closeBtn');
    const cancelBtn = document.getElementById('cancelBtn');

    if (openBtn) {
        openBtn.addEventListener('click', () => {
            modalOverlay.style.display = 'flex';
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
            }else{
                searchBasic.style.display = 'none';
                searchAddon.style.display = 'block';
            }
        });
    });
    const btnFilterBasic = document.getElementById('btn_filter_service');
    if (btnFilterBasic) {
        btnFilterBasic.addEventListener('click', () => {
            const start = document.getElementById('modal_start_time').value;
            const end = document.getElementById('modal_end_time').value;
            const [h1, m1] = start.split(':').map(Number);
            const [h2, m2] = end.split(':').map(Number);
            const diffHours = ((h2 * 60 + m2) - (h1 * 60 + m1)) / 60;

            let targetCategory = "";
            if (diffHours < 0) targetCategory = "error";
            else if (diffHours < 3) targetCategory = "3時間以下";
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
    const btnFilterAddon = document.getElementById('btn_filter_addon');
    if(btnFilterAddon){
        btnFilterAddon.addEventListener('click',()=>{
            const keyword = document.getElementById('addon_keyword').value.toLowerCase();
            document.querySelectorAll('.addon-row').forEach(row=>{
            const name = row.getAttribute('data-name').toLowerCase();
            row.style.display = name.includes(keyword) ? '' : 'none';
            });
        });
    }

    document.getElementById('btn_reset_basic')?.addEventListener('click',()=>{
    document.querySelectorAll('.basic-row').forEach(row=> row.style.display = '');
    });

    // ここからフォーム送信処理
    if (serviceBtn) {
        serviceBtn.addEventListener('click', async (e) => {
            const selected = document.querySelector('input[name="selected_service"]:checked');
            if (!selected) return alert("サービスを選択してください");
            const isAddon = selected.value.startsWith('addon_');
            const user_id = document.getElementById('userid').getAttribute("data-user-id");
            const planId = document.getElementById('main_plan_select').value;
            const day = 1;
            const startTime = document.getElementById('modal_start_time').value;
            const endTime = document.getElementById('modal_end_time').value;
            if (!isAddon) {
                if (endTime === '00:00') return alert('時間を設定してください。');
                if (!confirm(`開始: ${startTime}\n終了: ${endTime}\nこの内容でサービスを追加しますか？`)) return;
                    // API送信
                    const response = await fetch(`/api/plan/${user_id}/create/`, {
                        method: "POST",
                        headers: { 
                            "Content-Type": "application/json",
                            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        body: JSON.stringify({
                            selected_service: selected.value.split('_')[1],
                            start_time: startTime,
                            end_time: endTime,
                            day: day
                        })
                    }); 
                if (response.ok) {
                    location.reload(); // 成功したら新しいPlanを表示する
                }
                return;
            }


            
            // バリデーション: 加算なのにプランが選ばれていない
            if (isAddon && !planId) {
                e.preventDefault();
                return alert("加算を紐付ける予定サービスを選択してください");
            }else if(isAddon){
                e.preventDefault(); // 通常の送信をキャンセル
                if (!confirm("この内容で登録しますか？")) return;
                // API送信
                const response = await fetch(`/api/plan/${user_id}/update/`, {
                    method: "PATCH",
                    headers: { 
                        "Content-Type": "application/json",
                        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        plan_id: planId,
                        service_id: selected.value.split('_')[1],
                        days: [1,2,3,4,5,6,7], // todo:mainの実績行に加算を追加する場合、全ての日にちに追加する仕様になっている。将来的にはUIで選択できるようにするかも
                        row_type: 'actual_addon'
                    })
                });
                
                if (response.ok) {
                    location.reload(); // 成功したらリロードして新しい行を表示
                }
                return;
            }
        });
    }
});