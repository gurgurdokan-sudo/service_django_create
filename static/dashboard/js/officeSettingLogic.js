async function archiveAddonSetting(button) {
  const confirmation = await Swal.fire({
    title: "加算を一覧から非表示にしますか？",
    text: "設定は削除されず、管理画面から再表示できます。",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "非表示にする",
    cancelButtonText: "キャンセル",
  });
  if (!confirmation.isConfirmed) return;

  const form = button.closest("form");
  const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]').value;
  const statusLabel = document.getElementById("addon-save-status");
  button.disabled = true;
  try {
    const response = await fetch(button.dataset.apiUrl, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        addon_id: button.dataset.addonId,
        is_archived: true,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.message || "非表示にできませんでした。");
    }
    button.closest("tr").remove();
    if (statusLabel) statusLabel.textContent = "加算を一覧から非表示にしました。";
  } catch (error) {
    button.disabled = false;
    await Swal.fire("エラー", error.message, "error");
  }
}

async function confirmAddAddon(event, form) {
  event.preventDefault();
  const result = await Swal.fire({
    title: "加算を追加しますか？",
    text: "事業所の設定に追加します。",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "追加する",
    cancelButtonText: "キャンセル",
  });

  if (result.isConfirmed) {
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
    form.submit();
  }
  return false;
}

async function saveAddonSetting(input) {
  const previousValue = !input.checked;
  const statusLabel = document.getElementById("addon-save-status");
  const csrfToken = input.form.querySelector('[name="csrfmiddlewaretoken"]').value;
  input.disabled = true;

  try {
    // ブラウザーのタブセッション中、最初の変更時だけ確認する。
    const confirmKey = "officeAddonSettingConfirmed";
    if (sessionStorage.getItem(confirmKey) !== "1") {
      const confirmation = await Swal.fire({
        title: "加算表示を変更しますか？",
        text: "変更はこの事業所の選択モーダルにすぐ反映されます。",
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "変更する",
        cancelButtonText: "キャンセル",
      });
      if (!confirmation.isConfirmed) {
        input.checked = previousValue;
        return;
      }
      sessionStorage.setItem(confirmKey, "1");
    }

    if (statusLabel) statusLabel.textContent = "保存中…";
    const response = await fetch(input.dataset.apiUrl, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        addon_id: input.value,
        is_enabled: input.checked,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.message || "保存に失敗しました。");
    }
    if (statusLabel) statusLabel.textContent = "保存しました。";
  } catch (error) {
    input.checked = previousValue;
    if (statusLabel) statusLabel.textContent = error.message;
  } finally {
    input.disabled = false;
  }
}