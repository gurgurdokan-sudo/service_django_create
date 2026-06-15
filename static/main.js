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
    let [year,month] = document.getElementById('month_selector').value.split('-');
    year = parseInt(year);
    month = parseInt(month);
    console.log(`${action}${year}${month}`);
    const today = new Date();
    const nowYear = today.getFullYear();
    const nowMonth = today.getMonth();
        try{
        if (action === 'current'){
            if ( nowYear === year && nowMonth === month){
                alert("既に今月を表示");
                return;
            }
            window.location.href = `/user/${userId}/service/?year=${nowYear}&month=${String(nowMonth).padStart(2, '0')}`;            
            return;
        }
        if(action === 'prev'){
            month -= 1;
            if (month === 0){
                month = 12;
                year -=1;
                window.location.href = `/user/${userId}/service/?year=${year}&month=${String(month).padStart(2,'0')}`;
                return;
            }
            window.location.href = `/user/${userId}/service/?year=${year}&month=${String(month).padStart(2,'0')}`;
            return;
        }
        if (action === 'next'){
            month += 1;
            if (month === 13){
                month = 1;
                year += 1;
                window.location.href = `/user/${userId}/service/?year=${year}&month=${String(month).padStart(2,'0')}`;
                return;
            }
            window.location.href = `/user/${userId}/service/?year=${year}&month=${String(month).padStart(2,'0')}`;
            return;
        }
        else{
            console.log(`${action}が押されました`)
        }
    } catch(error){
        alert(`${error}errorが発生`);
    }
}
function toExcel(userId){
    const thisYear = parseInt(document.getElementById('current_year').value);
    const thisMonth = parseInt(document.getElementById('current_month').value);
    window.location.href = `/user/${userId}/create_sheet/?year=${thisYear}&month=${String(thisMonth).padStart(2,'0')}`;
    return;
}
function exportExcl(userId){
    const thisYear = parseInt(document.getElementById('current_year').value);
    const thisMonth = parseInt(document.getElementById('current_month').value);
    window.location.href = `/user/${userId}/export/?year=${thisYear}&month=${String(thisMonth).padStart(2,'0')}`
}
