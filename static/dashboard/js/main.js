/**
 * CSRFトークンを取得するヘルパー関数
 */
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

/**
 * 基本プランの削除
 */
async function deletePlan(planId) {
    const status = document.getElementById('confirmed-status');
    const confirmed = status.dataset.confirmed === "True";

    if (confirmed) {
        Swal.fire({
            icon: 'warning',
            title: '確定済み',
            text: '確定済みのため消去できません'
        });
        return;
    }
    if (!confirm("このサービス予定および実績データをすべて削除しますか？\n(この操作は取り消せません)")) {
        return;
    }

    try {
        const response = await fetch(`/api/plan/${planId}/delete/`, {
            method: "DELETE",
            headers: {
                "X-CSRFToken": getCsrfToken(),
            }
        });

        if (response.ok) {
            await Swal.fire({
                icon: 'success',
                title: '削除完了',
                text: '削除しました',
                timer: 1500,
                showConfirmButton: false
            });

            location.reload(); // 画面を更新して行を消す
        } else {
            const data = await response.json();
            Swal.fire({
                icon: 'error',
                title: '削除失敗',
                text: '削除に失敗しました: ' + (data.message || "Unknown error")
            });
        }
    } catch (error) {
        console.error("Delete Plan Error:", error);
        Swal.fire({
            icon: 'error',
            title: '通信エラー',
            text: '通信エラーが発生しました'
        });
    }
}

/**
 * 加算行削除
 */
async function deleteAddon(planId, addonName) {
    const result = await Swal.fire({
        title: '加算の削除',
        text: `「${addonName}」をこのプランの実績からすべて削除しますか？`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '削除する',
        cancelButtonText: 'キャンセル',
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6'
    });
    // キャンセル時
    if (!result.isConfirmed) return;

    try {
        const response = await fetch(`/api/plan/${planId}/update/`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
                row_type: "actual_addon_remove",
                addon_name: addonName,
            })
        });

        if (response.ok) {
            location.reload();
        } else {
            alert("加算の削除に失敗しました");
        }
    } catch (error) {
        console.error("Delete Addon Error:", error);
        alert("通信ERORRが発生しました");
    }
}

/**
 * 月の切り替え
 */
async function nextMonth(userId,action) {
    let dis_year = parseInt(document.getElementById('dis_year').value);
    let dis_month = parseInt(document.getElementById('dis_month').value);
    console.log(`${action}${dis_year}${dis_month}`);
    const today = new Date();
    const nowYear = today.getFullYear();
    const nowMonth = today.getMonth()+1;
        try{
        if (action === 'current'){
            if ( nowYear === dis_year && nowMonth === dis_month){
                Swal.fire({
                    icon: 'info',
                    text: '既に今月を表示しています'
                });
                return;
            }
            window.location.href = `/user/${userId}/service/?year=${nowYear}&month=${String(nowMonth).padStart(2, '0')}`;            
            return;
        }
        if(action === 'prev'){
            dis_month -= 1;
            if (dis_month === 0){
                dis_month = 12;
                dis_year -=1;
                window.location.href = `/user/${userId}/service/?year=${dis_year}&month=${String(dis_month).padStart(2,'0')}`;
                return;
            }
            window.location.href = `/user/${userId}/service/?year=${dis_year}&month=${String(dis_month).padStart(2,'0')}`;
            return;
        }
        if (action === 'next'){
            dis_month += 1;
            if (dis_month === 13){
                dis_month = 1;
                dis_year += 1;
                window.location.href = `/user/${userId}/service/?year=${dis_year}&month=${String(dis_month).padStart(2,'0')}`;
                return;
            }
            window.location.href = `/user/${userId}/service/?year=${dis_year}&month=${String(dis_month).padStart(2,'0')}`;
            return;
        }
        else{
            console.log(`${action}が押されました`)
        }
    } catch(error){
        Swal.fire({
            icon: 'error',
            title: 'エラー',
            text: `${error} エラーが発生しました`
        });
    }
}

/**
 * 予定道りschedule = 実績
 */
function toAct(userId) {
    const btn = document.getElementById('copyPlannedToActual');
    btn.disabled = true;
    btn.style.opacity = 0.5;
    const thisYear = parseInt(document.getElementById('dis_year').value);
    const thisMonth = parseInt(document.getElementById('dis_month').value);
    console.log(`${thisYear} ${thisMonth} 予定で実績を作成`)
    window.location.href = `/user/${userId}/service_act?year=${thisYear}&month=${String(thisMonth).padStart(2,'0')}`
}
/**
 * Excel作成（実績確定）
 */
async function toExcel(userId){
    const btn = document.getElementById('btn-excel');
        const result = await Swal.fire({
        title: '実績の確定',
        html: '実績を確定します。<br><b>確定後は実績が変更できなくなります。</b><br>よろしいですか？',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: '確定して作成',
        cancelButtonText: 'キャンセル',
        confirmButtonColor: '#28a745',
        cancelButtonColor: '#6c757d'
    });
    // キャンセル時
    if (!result.isConfirmed) return;

    btn.disabled =true;
    btn.style.opacity = 0.5;
    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();
    animateProgressBar();
    const thisYear = parseInt(document.getElementById('dis_year').value);
    const thisMonth = parseInt(document.getElementById('dis_month').value);
    window.location.href = `/user/${userId}/create_sheet/?dis_year=${thisYear}&dis_month=${String(thisMonth).padStart(2,'0')}`;
    return;
}
function exportExcel(userId){
    const btn = document.getElementById('btn-export');
    btn.disabled = true;
    btn.style.opacity = 0.5;
    const thisYear = parseInt(document.getElementById('dis_year').value);
    const thisMonth = parseInt(document.getElementById('dis_month').value);
    console.log(`exportExcel${thisYear}${thisMonth}`);
    window.location.href = `/user/${userId}/export/?dis_year=${thisYear}&dis_month=${String(thisMonth).padStart(2,'0')}`
}
function animateProgressBar(){
    const bar = document.getElementById('loadingBar');
    let progress = 0;

    const timer = setInterval(() => {
        progress += 0.5;  
        if(progress >= 100){
            progress = 100;
            clearInterval(timer);
        }
        bar.style.width = progress + "%";
    }, 60); // 60msごとに更新
}