// ==UserScript==
// @name         GitHub & Raw 镜像自动测速与重定向
// @namespace    https://gitee.com/child9527
// @version      0.9.9
// @description  自动测速 + 手动切换镜像 + 浮窗增强
// @author       child9527
// @match        https://github.com/*
// @match        https://*.github.com/*
// @match        https://raw.githubusercontent.com/*
// @match        https://gh-proxy.org/*
// @match        https://ghproxy.net/*
// @match        https://web.ksx.qzz.io/*
// @connect      github.com
// @connect      raw.githubusercontent.com
// @connect      gh-proxy.org
// @connect      ghproxy.net
// @connect      web.ksx.qzz.io
// @connect      *
// @run-at       document-start
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @updateURL    https://raw.githubusercontent.com/child9527/tvbox/main/github.script.user.js
// @downloadURL  https://raw.githubusercontent.com/child9527/tvbox/main/github.script.user.js
// ==/UserScript==

(async function() {
    'use strict';

    const MIRROR_LIST = [
        "https://gh-proxy.com",
        "https://gh-proxy.org",
        "https://ghproxy.net",
        "https://web.ksx.qzz.io",
        "https://wget.la"
    ];

    const currentUrl = window.location.href;

    // 检查当前是否已经在某个镜像站中
    let currentInMirror = "";
    let rawPath = currentUrl;
    
    for (const mirror of MIRROR_LIST) {
        if (currentUrl.startsWith(mirror)) {
            currentInMirror = mirror;
            // 剥离镜像前缀及多余斜杠，精准还原原始请求 URL
            rawPath = currentUrl.substring(mirror.length).replace(/^\/+/, '');
            break;
        }
    }

    // 辅助工具：安全拼接镜像前缀与目标 URL
    function buildMirrorUrl(mirror, target) {
        if (!mirror || mirror === 'OFFICIAL') return target;
        const cleanTarget = target.replace(/^\/+/, '');
        return `${mirror.replace(/\/+$/, '')}/${cleanTarget}`;
    }

    let fastestMirror = GM_getValue('fastest_mirror', '') || '';
    let latencyMap = GM_getValue('last_latency_map', null) || {}; 
    const lastTestTime = GM_getValue('last_test_time', 0) || 0;
    const now = Date.now();
    const CACHE_EXPIRE = 6 * 60 * 60 * 1000;

    // 只有在未显式指定为 OFFICIAL，且缓存过期或未曾设置时，才自动测速
    if (fastestMirror !== 'OFFICIAL' && (!fastestMirror || (now - lastTestTime > CACHE_EXPIRE))) {
        const result = await getFastestMirror(MIRROR_LIST, rawPath);
        if (result && result.mirror) {
            fastestMirror = result.mirror;
            latencyMap = result.latencyMap || {};
            GM_setValue('fastest_mirror', fastestMirror);
            GM_setValue('last_latency_map', latencyMap);
            GM_setValue('last_test_time', now);
        } else {
            console.warn("[镜像助手] 所有镜像测速失败，保持当前地址");
            fastestMirror = 'OFFICIAL';
            latencyMap = result ? (result.latencyMap || {}) : {};
        }
    }

    // 重定向控制逻辑：只有当不在镜像站、且用户选定了有效镜像（非 OFFICIAL）时触发自动重定向
    if (!currentInMirror && fastestMirror && fastestMirror !== 'OFFICIAL') {
        const targetTarget = buildMirrorUrl(fastestMirror, rawPath);
        if (targetTarget !== currentUrl) {
            window.location.replace(targetTarget);
            return; // 阻断后续执行
        }
    }

    // 渲染齿轮按钮
    const renderGearButton = () => {
        if (document.getElementById("gh-mirror-gear")) return;
        const gear = document.createElement("div");
        gear.id = "gh-mirror-gear";
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
            showFloatingTip(currentInMirror || fastestMirror, latencyMap, rawPath);
        };

        (document.body || document.documentElement).appendChild(gear);
    };

    // DOM 安全挂载 UI
    const initUI = () => {
        if (GM_getValue("float_hidden", false)) {
            renderGearButton();
        } else {
            showFloatingTip(currentInMirror || fastestMirror, latencyMap, rawPath);
        }
    };

    if (document.readyState === 'loading') {
        window.addEventListener('DOMContentLoaded', initUI);
    } else {
        initUI();
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
                const testTarget = buildMirrorUrl(mirror, testUrl);
                GM_xmlhttpRequest({
                    method: "HEAD",
                    url: testTarget,
                    timeout: 3000,
                    onload: function(response) {
                        const duration = performance.now() - startTime;
                        if (response.status < 400) {
                            tempLatencyMap[mirror] = duration.toFixed(0);
                            if (duration < minTime) {
                                minTime = duration;
                                bestMirror = mirror;
                            }
                        } else {
                            tempLatencyMap[mirror] = "失败";
                        }
                        checkFinish();
                    },
                    onerror: function() {
                        tempLatencyMap[mirror] = "失败";
                        checkFinish();
                    },
                    ontimeout: function() {
                        tempLatencyMap[mirror] = "超时";
                        checkFinish();
                    }
                });
            });

            function checkFinish() {
                completed++;
                if (completed === mirrors.length) {
                    resolve({ mirror: bestMirror, latencyMap: tempLatencyMap });
                }
            }
        });
    }

    // 浮窗渲染函数
    function showFloatingTip(activeMirror, map, targetPath) {
        if (document.getElementById("gh-mirror-float")) return;
        const safeMap = map || {};

        const githubTheme = document.documentElement ? document.documentElement.dataset.colorMode : "light";
        const isGithubDark = githubTheme === "dark" ||
            (githubTheme === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);

        const floatTheme = isGithubDark ? "light" : "dark";

        const div = document.createElement('div');
        div.id = "gh-mirror-float";
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

        const isCurrentlyOfficial = !activeMirror || activeMirror === 'OFFICIAL';

        const title = document.createElement('span');
        title.textContent = isCurrentlyOfficial ? "当前: 官方原始地址" : `当前镜像: ${activeMirror}`;

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
            if (result) {
                if (result.mirror) {
                    GM_setValue('fastest_mirror', result.mirror);
                    fastestMirror = result.mirror;
                }
                GM_setValue('last_latency_map', result.latencyMap);
                GM_setValue('last_test_time', Date.now());
                latencyMap = result.latencyMap || {};
                renderMirrorList(latencyMap);
            }
            refreshBtn.textContent = '重新测速';
        };

        const renderMirrorList = (currentLatencyData) => {
            detailDiv.innerHTML = '';
            detailDiv.appendChild(refreshBtn);

            const activeMap = currentLatencyData || {};

            // 1. 官方原始地址选项
            const officialItem = document.createElement('div');
            officialItem.innerHTML = `<span style="color:${floatTheme === 'light' ? '#333' : '#ccc'}">🌐 官方原始地址</span>${isCurrentlyOfficial ? " ✔" : ""}`;
            officialItem.style.cursor = 'pointer';
            officialItem.style.padding = '2px 0';
            officialItem.style.fontWeight = isCurrentlyOfficial ? 'bold' : 'normal';

            officialItem.onmouseover = () => officialItem.style.opacity = '0.7';
            officialItem.onmouseout = () => officialItem.style.opacity = '1';

            officialItem.onclick = (e) => {
                e.stopPropagation();
                GM_setValue('fastest_mirror', 'OFFICIAL');
                window.location.replace(targetPath);
            };
            detailDiv.appendChild(officialItem);

            // 2. 镜像列表渲染
            MIRROR_LIST.forEach(m => {
                const l = activeMap[m];
                const isCurrent = (m === activeMirror);

                let color = "#4ade80";
                let statusText = "";

                if (typeof l === 'number' || (!isNaN(l) && l !== "")) {
                    const numL = Number(l);
                    if (numL > 150 && numL <= 400) color = "#facc15";
                    if (numL > 400) color = "#f87171";
                    statusText = ` (${numL}ms)`;
                } else if (l) {
                    color = "#9ca3af";
                    statusText = ` (${l})`;
                } else {
                    color = "#9ca3af";
                    statusText = ` (未测速)`;
                }

                const p = document.createElement('div');
                p.innerHTML = `<span style="color:${color}">${m}${statusText}</span>${isCurrent ? " ✔" : ""}`;
                p.style.cursor = 'pointer';
                p.style.padding = '2px 0';

                p.onmouseover = () => p.style.opacity = '0.7';
                p.onmouseout = () => p.style.opacity = '1';

                p.onclick = (e) => {
                    e.stopPropagation();
                    GM_setValue('fastest_mirror', m);
                    GM_setValue('last_test_time', Date.now());
                    window.location.replace(buildMirrorUrl(m, targetPath));
                };

                detailDiv.appendChild(p);
            });
        };

        renderMirrorList(safeMap);

        let expanded = false;

        const closeDropdown = () => {
            expanded = false;
            detailDiv.style.display = 'none';
            toggleBtn.textContent = ' ▼';
        };

        toggleBtn.onclick = (e) => {
            e.stopPropagation();
            expanded = !expanded;
            detailDiv.style.display = expanded ? 'block' : 'none';
            toggleBtn.textContent = expanded ? ' ▲' : ' ▼';
        };

        // 点击页面其他任何区域时自动收起列表
        const onDocumentClick = (e) => {
            if (expanded && !div.contains(e.target)) {
                closeDropdown();
            }
        };

        document.addEventListener('click', onDocumentClick);

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
            document.removeEventListener("click", onDocumentClick);
            div.remove();
            renderGearButton();
        };

        div.appendChild(title);
        div.appendChild(toggleBtn);
        div.appendChild(closeBtn);
        div.appendChild(detailDiv);
        (document.body || document.documentElement).appendChild(div);
    }
})();
