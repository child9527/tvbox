/* ============================================================
   统一交互脚本
   ============================================================ */

/* ---------- 密码门 ---------- */
(function () {
    const PASSWORD = 'YnVnbWVub3Q=';
    const STORAGE_KEY = 'child9527_auth';
    const EXPIRE_DAYS = 90;

    function isAuthed() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return false;
            const data = JSON.parse(raw);
            if (!data || !data.time) return false;
            const age = Date.now() - data.time;
            return age < EXPIRE_DAYS * 24 * 60 * 60 * 1000;
        } catch (e) {
            return false;
        }
    }

    function setAuthed() {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ time: Date.now() }));
    }

    function showGate() {
        const gate = document.getElementById('auth-gate');
        if (gate) gate.classList.remove('hidden');
    }

    function hideGate() {
        const gate = document.getElementById('auth-gate');
        if (gate) gate.classList.add('hidden');
    }

    function tryAuth() {
        const input = document.getElementById('auth-input');
        const error = document.getElementById('auth-error');
        const box = document.querySelector('.auth-box');
        if (!input) return;

        const encoded = btoa(input.value.trim());
        if (encoded === PASSWORD) {
            setAuthed();
            hideGate();
            if (error) error.textContent = '';
        } else {
            if (error) error.textContent = '密码错误';
            if (box) {
                box.classList.remove('shake');
                void box.offsetWidth;
                box.classList.add('shake');
            }
            input.value = '';
            input.focus();
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (isAuthed()) {
            hideGate();
            return;
        }
        showGate();
        const input = document.getElementById('auth-input');
        const btn = document.getElementById('auth-btn');
        if (input) {
            input.focus();
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') tryAuth();
            });
        }
        if (btn) btn.addEventListener('click', tryAuth);
    });
})();

/* ---------- 软件分类筛选 ---------- */
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

/* ---------- 音源分类筛选（guoyue2010 / pdone） ---------- */
function filterSourceType(btn) {
    const buttons = btn.parentElement.querySelectorAll('.filter-btn');
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const selectedType = btn.innerText.trim();
    const cards = document.querySelectorAll('.source-card');
    cards.forEach(card => {
        if (card.getAttribute('data-type') === selectedType) {
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
