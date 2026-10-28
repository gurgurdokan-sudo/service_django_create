/**
 * CSRFトークンを取得するヘルパー関数
 */
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

/**
 * 基本プランの削除
 */
const deletingPlanIds = new Set();
async function deletePlan(planId) {
    const planKey = String(planId);
    if (deletingPlanIds.has(planKey)) return;

    const status = document.getElementById("confirmed-status");
    if (!status) {
        await Swal.fire({
            icon: "error",
            title: "削除できません",
            text: "確定状態を確認できません。ページを再読み込みしてください。"
        });
        return;
    }

    const confirmed = String(status.dataset.confirmed).toLowerCase() === "true";
    if (confirmed) {
        await Swal.fire({
            icon: "warning",
            title: "確定済み",
            text: "確定済みのため消去できません"
        });
        return;
    }

    deletingPlanIds.add(planKey);
    try {
        const result = await Swal.fire({
            icon: "warning",
            title: "削除確認",
            text: "このサービス予定および実績データをすべて削除しますか？\n(この操作は取り消せません)",
            showCancelButton: true,
            confirmButtonText: "削除する",
            cancelButtonText: "キャンセル",
            confirmButtonColor: "#d33",
            reverseButtons: true,
            focusCancel: true
        });
        if (!result.isConfirmed) return;

        const response = await fetch(`/api/plan/${encodeURIComponent(planKey)}/delete/`, {
            method: "DELETE",
            headers: {
                "X-CSRFToken": getCsrfToken(),
                "Accept": "application/json"
            }
        });

        let data = {};
        try {
            data = await response.json();
        } catch {
            console.log('想定外のresponse')
        }

        if (!response.ok) {
            if (response.status === 409 && data.code === "ADDON_REASSIGN_FAILED") {
                // await Swal.fire({
                //     icon: "warning",
                //     title: "加算を自動付け替えできません",
                //     text: data.message || "付け替え先を一意に決められませんでした。データは変更されていません。残りのPlanと加算を確認してください。"
                // });
                console.log('付け替え先を一意に決められませんでした。データは変更されていません。');
                return;
            }
            throw new Error(data.message || `削除に失敗しました (HTTP ${response.status})`);
        }

        const successMessages = ["基本プランを削除しました。"];
        const movedAddonCount = Number(data.reassigned_addon_count || 0);
        if (movedAddonCount > 0) {
            successMessages.push(`加算データ${movedAddonCount}件を別の基本サービスへ付け替えました。`);
        }
        if (data.record_deleted) {
            successMessages.push("基本サービス作成画面に遷移します。");
        }

        await Swal.fire({
            icon: "success",
            title: "削除完了",
            text: successMessages.join("\n"),
            timer: 2500,
            showConfirmButton: false
        });

        window.location.reload();
    } catch (error) {
        console.error("Delete Plan Error:", error);
        await Swal.fire({
            icon: "error",
            title: "削除失敗",
            text: error.message || "通信エラーが発生しました"
        });
    } finally {
        deletingPlanIds.delete(planKey);
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
const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));

function toListHtml(items) {
  return `<ul style="text-align:left">${items
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("")}</ul>`;
}

async function toExcel(userId){
    const btn = document.getElementById('btn-excel');
    let started = false;
    btn.disabled =true;
    btn.style.opacity = 0.5;

    const thisYear = Number(document.getElementById('dis_year').value);
    const thisMonth = Number(document.getElementById('dis_month').value);
    const params = new URLSearchParams({
                                          year: String(thisYear),
                                          month: String(thisMonth).padStart(2, "0"),
                                        });
    try {
        console.log(params.toString())
        const response = await fetch(
          `/api/user/${userId}/validate/?${params.toString()}`,
          { headers: { Accept: "application/json" } }
        );
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const modal = new bootstrap.Modal(document.getElementById("loadingModal"));
        modal.show();
        const validation = await response.json();
        const errors = Array.isArray(validation.errors) ? validation.errors : [];
        const warnings = Array.isArray(validation.warnings) ? validation.warnings : [];

        if (errors.length) {
            await Swal.fire({
                icon: "error",
                title: "Excelを作成できません",
                html: `<ul style="text-align:left">${errors.map((item) =>
                    `<li>${escapeHtml(item)}</li>`).join("")}</ul>`,
            });
        }
        // Errorがあれば中止
        if (errors.length > 0) {
          await Swal.fire({
            icon: "error",
            title: "Excelを作成できません",
            html: toListHtml(errors),
          });
          return;
        }

        // Warningがあれば確認
        if (warnings.length > 0) {
          const warnResult = await Swal.fire({
            icon: "warning",
            title: "確認してください",
            html: toListHtml(warnings),
            showCancelButton: true,
            confirmButtonText: "確認して続行",
            cancelButtonText: "戻る",
          });
          if (!warnResult.isConfirmed) return;
        }

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
        if (!result.isConfirmed){
            return;
        }else{
            animateProgressBar();
            started = true;
            modal.show();
        }
    const createParams = new URLSearchParams({
      year: thisYear,
      month: String(thisMonth).padStart(2, "0"),
    });
    console.log(createParams);
    window.location.href = `/user/${userId}/create_sheet/?${createParams.toString()}`;

    }catch (e){
        console.error(e);
        await Swal.fire("通信エラー", "入力チェック/Excel作成に失敗しました。", "error");
    } finally {
    if (!started) {
      btn.disabled = false;
      btn.style.opacity = 1;
      location.reload();
    }
  }
}
function exportExcel(userId){
    const btn = document.getElementById('btn-export');
    btn.disabled = true;
    btn.style.opacity = 0.5;
    const thisYear = Number(document.getElementById('dis_year').value);
    const thisMonth = Number(document.getElementById('dis_month').value);
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
document.addEventListener('DOMContentLoaded', () => {
    const btnValidate = document.getElementById('btn_validate');

    if (btnValidate) {
        btnValidate.addEventListener('click', async () => {
            const userId = document.getElementById('userid').dataset.userId;
            const year = document.getElementById('dis_year').value;
            const month = document.getElementById('dis_month').value;

            try {
                // チェック中はローディング
                Swal.fire({
                    title: 'チェック中...',
                    text: '算定ルールを検証しています',
                    allowOutsideClick: false,
                    didOpen: () => { Swal.showLoading(); }
                });

                const response = await fetch(`/api/user/${userId}/validate/?year=${year}&month=${month}`);
                const data = await response.json();

                if (data.status === "ok") {
                    // エラーなし
                    Swal.fire({
                        icon: 'success',
                        title: 'チェック完了',
                        text: '算定ルール上のエラーは見つかりませんでした。',
                        confirmButtonColor: '#2c3e50'
                    });
                } else {
                    let htmlContent = '<div style="text-align:left; font-size: 0.9rem; max-height: 300px; overflow-y: auto;">';

                    if (data.errors && data.errors.length > 0) {
                        htmlContent += '<h5 style="color:#d32f2f; font-weight:bold;"> エラー（修正必須）</h5><ul style="color:#d32f2f;">';
                        data.errors.forEach(err => { htmlContent += `<li>${err}</li>`; });
                        htmlContent += '</ul>';
                    }

                    if (data.warnings && data.warnings.length > 0) {
                        htmlContent += '<h5 style="color:#f39c12; font-weight:bold; margin-top:15px;"> 確認（必要に応じて）</h5><ul>';
                        data.warnings.forEach(warn => { htmlContent += `<li>${warn}</li>`; });
                        htmlContent += '</ul>';
                    }

                    htmlContent += '</div>';

                    Swal.fire({
                        icon: data.errors.length > 0 ? 'error' : 'warning',
                        title: '入力チェック結果',
                        html: htmlContent,
                        width: '600px',
                        confirmButtonColor: '#2c3e50'
                    });
                }
            } catch (error) {
                console.error(error);
                Swal.fire('通信エラー', 'チェック処理に失敗しました', 'error');
            }
        });
    }
});