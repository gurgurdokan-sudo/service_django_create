/**
 * CSRFトークンを取得するヘルパー関数
 */
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

/**
 * 1. 基本プラン（行全体）の削除
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
 * 2. 加算（特定の加算名）の削除
 * 画面上の加算行は「その月のその加算全て」を指すため、
 * 全日程からその加算名を削除するリクエストを送ります。
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