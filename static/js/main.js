/* ============================================================
   统一交互脚本
   ============================================================ */

function filterType(btn) {
    const buttons = document.querySelectorAll('.filter-btn');
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const selectedType = btn.innerText.trim();

    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        const cardType = card.getAttribute('data-type');
        if (cardType === selectedType) {
            card.classList.remove('hidden');
        } else {
            card.classList.add('hidden');
        }
    });
}

function copyUrl(btn, url) {
    navigator.clipboard.writeText(url).then(() => {
        showToast('已复制：' + url);
        const originalText = btn.innerText;
        btn.innerText = '已复制';
        btn.style.background = '#28a745';
        setTimeout(() => {
            btn.innerText = originalText;
            btn.style.background = '#3a7bd5';
        }, 2000);
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('复制失败，请手动复制');
    });
}

function copyVar(btn, text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板！');
        const originalText = btn.innerText;
        btn.innerText = '已复制';
        btn.style.background = '#28a745';
        setTimeout(() => {
            btn.innerText = originalText;
            btn.style.background = '#3a7bd5';
        }, 2000);
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('复制失败：' + err);
    });
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.innerText = msg;
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.display = 'none';
    }, 2000);
}
