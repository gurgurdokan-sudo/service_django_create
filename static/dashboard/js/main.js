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
            alert("削除しました");
            location.reload(); // 画面を更新して行を消す
        } else {
            const data = await response.json();
            alert("削除に失敗しました: " + (data.message || "Unknown error"));
        }
    } catch (error) {
        console.error("Delete Plan Error:", error);
        alert("通信エラーが発生しました");
    }
}

/**
 * 加算行削除
 */
async function deleteAddon(planId, addonName) {
    if (!confirm(`「${addonName}」をこのプランの実績からすべて削除しますか？`)) {
        return;
    }

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

function nextMonth(userId,action) {
    let dis_year = parseInt(document.getElementById('dis_year').value);
    let dis_month = parseInt(document.getElementById('dis_month').value);
    console.log(`${action}${dis_year}${dis_month}`);
    const today = new Date();
    const nowYear = today.getFullYear();
    const nowMonth = today.getMonth()+1;
        try{
        if (action === 'current'){
            if ( nowYear === dis_year && nowMonth === dis_month){
                alert("既に今月を表示");
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
        alert(`${error}errorが発生`);
    }
}
function toAct(userId) {
    const thisYear = parseInt(document.getElementById('dis_year').value);
    const thisMonth = parseInt(document.getElementById('dis_month').value);
    console.log(`${thisYear} ${thisMonth} 予定で実績を作成`)
    window.location.href = `/user/${userId}/service_act?year=${thisYear}&month=${String(thisMonth).padStart(2,'0')}`
}
function toExcel(userId){
    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();
    animateProgressBar();
    const thisYear = parseInt(document.getElementById('dis_year').value);
    const thisMonth = parseInt(document.getElementById('dis_month').value);
    window.location.href = `/user/${userId}/create_sheet/?dis_year=${thisYear}&dis_month=${String(thisMonth).padStart(2,'0')}`;
    return;
}
function exportExcel(userId){
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