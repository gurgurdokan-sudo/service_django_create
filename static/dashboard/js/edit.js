const DEBUG = true;

// oxlint の no-console をこの1か所だけで許可する
function log(level, ...args) {
  if (level === 'debug' && !DEBUG) return;
  // oxlint-disable-next-line no-console
  console[level === 'debug' ? 'log' : level](...args);
}

// 集計サマリーを画面（React）に渡す
function dispatchSummary(summary) {
  if (!summary) return;

  window.dispatchEvent(
    new CustomEvent('service-summary:update', { detail: summary })
  );

  // 確定状態をサーバーの値にそろえる
  const status = document.getElementById('confirmed-status');
  if (status && summary.record) {
    status.dataset.confirmed = String(summary.record.confirmed);
  }
}

// レスポンスをJSONとして読む。HTMLのエラー画面でも中身を返す
async function readJsonResponse(response) {
  const body = await response.text();
  try {
    return { json: body ? JSON.parse(body) : {}, body };
  } catch {
    return { json: null, body };
  }
}

// 集計APIから最新のサマリーを取得する（初期表示用）
async function refreshSummary() {
  const root = document.querySelector('#service-summary-root');
  const { userId, year, month } = root?.dataset ?? {};

  if (!userId || !year || !month) {
    log('warn', '集計APIを呼べません: data属性を確認', { userId, year, month });
    return;
  }

  const url =
    `/api/users/${encodeURIComponent(userId)}/summary/` +
    `?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`;

  try {
    const response = await fetch(url, {
      headers: { Accept: 'application/json' },
    });
    const { json, body } = await readJsonResponse(response);

    if (!json) {
      log('error', '集計APIの応答がJSONではありません', {
        status: response.status,
        url,
        body: body.slice(0, 500),
      });
      return;
    }

    if (!response.ok || json.status !== 'ok') {
      log('error', '集計の取得に失敗しました', { status: response.status, json });
      return;
    }

    dispatchSummary(json.summary);
  } catch (error) {
    log('error', '集計APIへの通信に失敗しました', error);
  }
}

// クリックしたときの次の値
function getNextValue(rowType, currentValue) {
  if (rowType === 'schedule') {
    if (currentValue === '') return '1';
    if (currentValue === '1') return 'x';
    return '';
  }
  return currentValue === '' ? '1' : '';
}

// 送るデータを作る
function buildPayload(cell, rowType, day, newValue) {
  const payload = { day, row_type: rowType, value: newValue };

  if (rowType === 'actual_addon') {
    // addon_id を優先（無いときだけ名前で探される）
    if (cell.dataset.addonId) payload.addon_id = cell.dataset.addonId;
    payload.value = cell.dataset.addonName ?? '';
  }
  return payload;
}

function initializeEditPage() {
  let isFirstEdit = true;
  const status = document.getElementById('confirmed-status');

  if (!status) {
    log('warn', '#confirmed-status が見つかりません');
  }

  // 初期表示時にサマリーを取得
  void refreshSummary();

  document.querySelectorAll('.editable-cell').forEach((cell) => {
    cell.addEventListener('click', async function () {
      // 送信中なら何もしない（2回クリック対策）
      if (this.dataset.busy === '1') return;

      if (status?.dataset.confirmed?.toLowerCase() === 'true') {
        await Swal.fire({
          icon: 'warning',
          title: '確定済み',
          text: '確定済みのため編集できません',
          confirmButtonColor: '#3085d6',
        });
        return;
      }

      if (isFirstEdit) {
        const result = await Swal.fire({
            text: '編集を開始しますか？',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: '編集する',
            cancelButtonText: 'キャンセル',
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33'
        });
        // キャンセルされたら中断
        if (!result.isConfirmed) return;
        
        isFirstEdit = false;
      }

      const row = this.closest('tr');
      const planId = row?.dataset.planId;
      const rowType = this.parentElement?.dataset.rowType ?? row?.dataset.rowType;
      const day = this.dataset.day;
      const currentValue = this.innerText.trim();

      if (!planId || !rowType || !day) {
        log('error', '編集に必要な情報が見つかりません', { planId, rowType, day });
        return;
      }

      const newValue = getNextValue(rowType, currentValue);
      const totalCell =
        this.closest('.calendar-row')?.querySelector('.total-cell') ??
        this.parentElement?.querySelector('.total-cell');
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

      // 保存前に画面を更新
      this.dataset.busy = '1';
      this.innerText = newValue;

      try {
        const response = await fetch(`/api/plan/${planId}/update/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
          },
          body: JSON.stringify(buildPayload(this, rowType, day, newValue)),
        });

        const { json, body } = await readJsonResponse(response);

        if (!response.ok || !json || json.status !== 'ok') {
          this.innerText = currentValue;
          log('error', '予定・実績の保存に失敗しました', {
            status: response.status,
            json,
            body: body.slice(0, 500),
          });
          await Swal.fire({
            icon: 'error',
            title: '保存エラー',
            text: json?.message || '編集を保存できませんでした',
          });
          return;
        }

        // 回数はサーバーが数え直した値を使う
        if (json.total !== undefined && totalCell) {
          totalCell.innerText = json.total;
        }

        // PATCHの返事に入っているサマリーをそのまま使う
        dispatchSummary(json.summary);
      } catch (error) {
        log('error', '保存エラー', error);
        this.innerText = currentValue;
        await Swal.fire({
          icon: 'error',
          title: '通信エラー',
          text: '通信エラーが発生しました。ネットワーク状況を確認してください。',
        });
      } finally {
        delete this.dataset.busy;
      }
    });
  });
}

// DOMの読み込み状態に応じて初期化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeEditPage, { once: true });
} else {
  initializeEditPage();
}