
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('serviceModal');
    const openBtn = document.getElementById('openServiceModal');
    const closeBtn = document.getElementById('closeBtn');
    const cancelBtn = document.getElementById('cancelBtn');

    // 開くボタンのイベント
    openBtn.addEventListener('click', function() {
        modal.showModal(); // Dialog APIで開く
    });

    // 閉じる処理（共通）
    function hideModal() {
        console.log("Closing Modal");
        modal.close();
    }
    closeBtn.addEventListener('click', hideModal);
    cancelBtn.addEventListener('click', hideModal);

    // 背景クリックで閉じる
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            hideModal();
        }
    });
});