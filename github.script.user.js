// ==UserScript==
// @name         GitHub & Raw 镜像自动测速与重定向（v0.9.1 稳健修复版）
// @namespace    http://tampermonkey.net/
// @version      0.9.1
// @description  自动测速 + 手动切换镜像 + 浮窗增强（优雅兜底 + 稳健数据类型）
// @author       You
// @match        https://github.com/*
// @match        https://*.github.com/*
// @match        https://raw.githubusercontent.com/*
// @run-at       document-start
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @updateURL    https://web.ksx.qzz.io/https://raw.githubusercontent.com/child9527/mybox/main/github.script.user.js
// @downloadURL  https://web.ksx.qzz.io/https://raw.githubusercontent.com/child9527/mybox/main/github.script.user.js
// ==/UserScript==

(async function() {
    'use strict';

    const MIRROR_LIST = [
        "https://gh-proxy.org",
        "https://web.ksx.qzz.io",
        "https://ghproxy.net"
    ];

    const currentUrl = window.location.href;

    // 如果当前已经在镜像站里，直接放行
    for (const mirror of MIRROR_LIST) {
        if (currentUrl.startsWith(mirror)) return;
    }

    let fastestMirror = GM_getValue('fastest_mirror', '') || '';
    // 防御性初始化，确保始终是对象
    let latencyMap = GM_getValue('last_latency_map', null) || {}; 
    const lastTestTime = GM_getValue('last_test_time', 0) || 0;
    const now = Date.now();
    const CACHE_EXPIRE = 6 * 60 * 60 * 1000;

    // 缓存过期或缺失 → 重新测速
    if (!fastestMirror || (now - lastTestTime > CACHE_EXPIRE)) {
        const result = await getFastestMirror(MIRROR_LIST, currentUrl);
        if (result && result.mirror) {
            fastestMirror = result.mirror;
            latencyMap = result.latencyMap || {};
            GM_setValue('fastest_mirror', fastestMirror);
            GM_setValue('last_latency_map', latencyMap);
            GM_setValue('last_test_time', now);
        } else {
            console.warn("[镜像助手] 所有镜像测速失败，停留在原始地址，不进行重定向");
            // 测速全败时不执行后续重定向跳转
            fastestMirror = ''; 
        }
    }

    // 渲染齿轮按钮
    const renderGearButton = () => {
        const gear = document.createElement("div");
        gear.textContent = "⚙️";
        gear.style.position = "fixed";
        gear.style.bottom = "10px";
        gear.style.right = "10px";
        gear.style.fontSize = "18px";
        gear.style.cursor = "pointer";
        gear.style.zIndex = "999999";
        gear.style.opacity = "0.6";
        gear.onmouseover = () => gear.style.opacity = "1";
        gear.onmouseout = () => gear.style.opacity = "0.6";

        gear.onclick = () => {
            GM_setValue("float_hidden", false);
            gear.remove();
            showFloatingTip(fastestMirror, latencyMap, currentUrl);
        };

        document.body.appendChild(gear);
    };

    // DOM 加载完成后根据状态渲染 UI
    const initUI = () => {
        if (GM_getValue("float_hidden", false)) {
            renderGearButton();
        } else {
            showFloatingTip(fastestMirror, latencyMap, currentUrl);
        }
    };

    if (document.body) {
        initUI();
    } else {
        window.addEventListener('DOMContentLoaded', initUI);
    }

    // 核心兜底逻辑：只有找到有效最快镜像时才执行 Replace 重定向
    if (fastestMirror) {
        window.location.replace(fastestMirror + '/' + currentUrl);
    }

    // 并发测速函数
    function getFastestMirror(mirrors, testUrl) {
        return new Promise((resolve) => {
            let completed = 0;
            let bestMirror = null;
            let minTime = Infinity;
            let tempLatencyMap = {};

            mirrors.forEach(mirror => {
                const startTime = performance.now();
                GM_xmlhttpRequest({
                    method: "HEAD",
                    url: `${mirror}/${testUrl}`,
                    timeout: 3000,
                    onload: function(response) {
                        const duration = performance.now() - startTime;
                        if (response.status < 400) {
                            tempLatencyMap[mirror] = duration.toFixed(0);
                            if (duration < minTime) {
                                minTime = duration;
                                bestMirror = mirror;
                            }
                        }
                        checkFinish();
                    },
                    onerror: checkFinish,
                    ontimeout: checkFinish
                });
            });

            function checkFinish() {
                completed++;
                if (completed === mirrors.length) {
                    resolve(bestMirror ? { mirror: bestMirror, latencyMap: tempLatencyMap } : null);
                }
            }
        });
    }

    // 浮窗渲染函数
    function showFloatingTip(currentMirror, map, targetPath) {
        // 安全类型保证
        const safeMap = map || {};

        const githubTheme = document.documentElement.dataset.colorMode;
        const isGithubDark = githubTheme === "dark" ||
            (githubTheme === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);

        const floatTheme = isGithubDark ? "light" : "dark";

        const div = document.createElement('div');
        div.style.position = 'fixed';
        div.style.bottom = '10px';
        div.style.right = '10px';
        div.style.padding = '10px 14px';
        div.style.borderRadius = '6px';
        div.style.fontSize = '12px';
        div.style.zIndex = '999999';
        div.style.cursor = 'move';
        div.style.userSelect = 'none';
        div.style.boxShadow = floatTheme === "light"
            ? '0 4px 12px rgba(255,255,255,0.3)'
            : '0 4px 12px rgba(0,0,0,0.3)';
        div.style.background = floatTheme === "light"
            ? 'rgba(255,255,255,0.95)'
            : 'rgba(0,0,0,0.85)';
        div.style.color = floatTheme === "light" ? '#000' : '#fff';

        const savedX = GM_getValue("float_pos_x", 0) || 0;
        const savedY = GM_getValue("float_pos_y", 0) || 0;
        div.style.transform = `translate(${savedX}px, ${savedY}px)`;

        // 标题显示
        const title = document.createElement('span');
        title.textContent = currentMirror ? `当前镜像: ${currentMirror}` : "当前镜像: 官方原始地址(测速失败)";

        const toggleBtn = document.createElement('span');
        toggleBtn.textContent = ' ▼';
        toggleBtn.style.cursor = 'pointer';
        toggleBtn.style.marginLeft = '6px';

        const closeBtn = document.createElement('span');
        closeBtn.textContent = ' ✕';
        closeBtn.style.cursor = 'pointer';
        closeBtn.style.marginLeft = '10px';

        const detailDiv = document.createElement('div');
        detailDiv.style.marginTop = '6px';
        detailDiv.style.display = 'none';

        const refreshBtn = document.createElement('div');
        refreshBtn.textContent = '重新测速';
        refreshBtn.style.cursor = 'pointer';
        refreshBtn.style.marginBottom = '6px';
        refreshBtn.style.color = floatTheme === "light" ? '#0070f3' : '#90cdf4';

        refreshBtn.onclick = async (e) => {
            e.stopPropagation();
            refreshBtn.textContent = '测速中...';
            const result = await getFastestMirror(MIRROR_LIST, targetPath);
            if (result && result.mirror) {
                GM_setValue('fastest_mirror', result.mirror);
                GM_setValue('last_latency_map', result.latencyMap);
                GM_setValue('last_test_time', Date.now());
                latencyMap = result.latencyMap || {};
                fastestMirror = result.mirror;
                title.textContent = `当前镜像: ${fastestMirror}`;
                renderMirrorList(latencyMap);
            } else {
                refreshBtn.textContent = '测速全部失败';
                setTimeout(() => { refreshBtn.textContent = '重新测速'; }, 2000);
            }
        };

        const renderMirrorList = (currentLatencyData) => {
            detailDiv.innerHTML = '';
            detailDiv.appendChild(refreshBtn);

            const activeMap = currentLatencyData || {};
            const sorted = Object.entries(activeMap).sort((a, b) => a[1] - b[1]);

            if (sorted.length === 0) {
                const emptyTip = document.createElement('div');
                emptyTip.textContent = '暂无有效延迟数据';
                emptyTip.style.opacity = '0.6';
                detailDiv.appendChild(emptyTip);
                return;
            }

            sorted.forEach(([m, l]) => {
                const isCurrent = (m === currentMirror);

                let color = "#4ade80"; // green
                if (l > 150 && l <= 400) color = "#facc15"; // yellow
                if (l > 400) color = "#f87171"; // red

                const p = document.createElement('div');
                p.innerHTML = `<span style="color:${color}">${m} (${l}ms)</span>${isCurrent ? " ✔" : ""}`;
                p.style.cursor = 'pointer';
                p.style.padding = '2px 0';

                p.onmouseover = () => p.style.opacity = '0.7';
                p.onmouseout = () => p.style.opacity = '1';

                p.onclick = (e) => {
                    e.stopPropagation();
                    GM_setValue('fastest_mirror', m);
                    GM_setValue('last_test_time', Date.now());
                    window.location.replace(m + '/' + targetPath);
                };

                detailDiv.appendChild(p);
            });
        };

        renderMirrorList(safeMap);

        let expanded = false;
        toggleBtn.onclick = (e) => {
            e.stopPropagation();
            expanded = !expanded;
            detailDiv.style.display = expanded ? 'block' : 'none';
            toggleBtn.textContent = expanded ? ' ▲' : ' ▼';
        };

        let isDragging = false;
        let startX = 0, startY = 0;
        let currentX = savedX, currentY = savedY;

        const onMouseMove = (e) => {
            if (!isDragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            div.style.transform = `translate(${currentX + dx}px, ${currentY + dy}px)`;
        };

        const onMouseUp = () => {
            if (!isDragging) return;
            isDragging = false;

            const matrix = new DOMMatrixReadOnly(getComputedStyle(div).transform);
            currentX = matrix.m41;
            currentY = matrix.m42;

            GM_setValue("float_pos_x", currentX);
            GM_setValue("float_pos_y", currentY);
        };

        div.onmousedown = (e) => {
            if (e.target.closest('div') === detailDiv || detailDiv.contains(e.target)) return;
            if (e.target === toggleBtn || e.target === closeBtn || e.target === refreshBtn) return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;

            const matrix = new DOMMatrixReadOnly(getComputedStyle(div).transform);
            currentX = matrix.m41;
            currentY = matrix.m42;
        };

        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);

        closeBtn.onclick = (e) => {
            e.stopPropagation();
            GM_setValue("float_hidden", true);
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup", onMouseUp);
            div.remove();
            renderGearButton();
        };

        div.appendChild(title);
        div.appendChild(toggleBtn);
        div.appendChild(closeBtn);
        div.appendChild(detailDiv);
        document.body.appendChild(div);
    }
})();
