/**
 * =========================================================
 * knowledge.js
 * 法规知识库
 * =========================================================
 */

window.Knowledge = (function () {

    // =====================================================
    // 数据
    // =====================================================

    let knowledgeData = [];

    let filteredData = [];

    let currentPage = 1;

    const PAGE_SIZE = 10;


    // =====================================================
    // 进度浮层控制器（打标签 / 更新知识库 共用）
    // =====================================================

    function createTaskProgress(cfg) {
        let timer = null;
        let elapsedTimer = null;
        let elapsed = 0;

        const overlay   = document.getElementById(cfg.overlayId);
        const card      = document.getElementById(cfg.cardId);
        const bar       = document.getElementById(cfg.barId);
        const percentEl = document.getElementById(cfg.percentId);
        const countEl   = document.getElementById(cfg.countId);
        const msgEl     = document.getElementById(cfg.messageId);
        const closeBtn  = document.getElementById(cfg.closeId);

        const elapsedEl = cfg.elapsedId
            ? document.getElementById(cfg.elapsedId)
            : null;


        // ✅ 刷新拦截
        function beforeUnloadHandler(e) {
            e.preventDefault();
            e.returnValue = '任务正在执行中，刷新会中断，确定要离开吗？';
            return e.returnValue;
        }

        function bindBeforeUnload() {
            window.addEventListener('beforeunload', beforeUnloadHandler);
        }

        function unbindBeforeUnload() {
            window.removeEventListener('beforeunload', beforeUnloadHandler);
        }


        // ✅ 耗时计时器
        function startElapsed() {
            stopElapsed();
            elapsed = 0;
            if (elapsedEl) elapsedEl.textContent = '已耗时 0 秒';

            elapsedTimer = setInterval(function () {
                elapsed += 1;
                if (elapsedEl) {
                    elapsedEl.textContent = '已耗时 ' + elapsed + ' 秒';
                }
            }, 1000);
        }

        function stopElapsed() {
            if (elapsedTimer) {
                clearInterval(elapsedTimer);
                elapsedTimer = null;
            }
        }


        function show() {
            if (!overlay) return;
            overlay.style.display = 'flex';
            if (card) card.className = 'task-progress-card';
            if (bar) bar.style.width = '0%';
            if (percentEl) percentEl.textContent = '0%';
            if (countEl) countEl.textContent = '0 / 0';
            if (msgEl) msgEl.textContent = '准备中...';
            if (closeBtn) closeBtn.style.display = 'none';

            startElapsed();
            bindBeforeUnload();
        }

        function hide() {
            if (overlay) overlay.style.display = 'none';

            stopElapsed();
            unbindBeforeUnload();
        }

        function update(data) {
            if (!data) return;

            // 优先用后端算好的 overall_percent
            let percent = 0;

            if (typeof data.overall_percent === 'number') {
                percent = Math.min(100, Math.max(0, Math.round(data.overall_percent)));
            } else {
                const total = Number(data.total) || 0;
                const processed = Number(data.processed) || 0;
                percent = total > 0
                    ? Math.min(100, Math.round((processed / total) * 100))
                    : 0;
            }

            if (bar) bar.style.width = percent + '%';
            if (percentEl) percentEl.textContent = percent + '%';

            // 数字区：显示"分片 1/2 · 第 45/200 页"
            if (countEl) {
                const partTotal = Number(data.part_total) || 0;
                const partProcessed = Number(data.part_processed) || 0;
                const pageTotal = Number(data.page_total) || 0;
                const pageProcessed = Number(data.page_processed) || 0;

                if (partTotal > 0) {
                    let txt = '分片 ' + partProcessed + '/' + partTotal;
                    if (pageTotal > 0) {
                        txt += ' · 第 ' + pageProcessed + '/' + pageTotal + ' 页';
                    }
                    countEl.textContent = txt;
                } else {
                    const total = Number(data.total) || 0;
                    const processed = Number(data.processed) || 0;
                    countEl.textContent = processed + ' / ' + total;
                }
            }

            // 消息区
            if (msgEl) {
                const stage = data.stage ? '[' + data.stage + '] ' : '';
                msgEl.textContent = stage + (data.message || '处理中...');
            }

            // 完成
            if (data.status === 'done') {
                if (card) card.classList.add('is-done');
                if (bar) bar.style.width = '100%';
                if (percentEl) percentEl.textContent = '100%';
                stopPolling();

                unbindBeforeUnload();
                stopElapsed();

                if (closeBtn) closeBtn.style.display = 'block';

                setTimeout(function () {
                    hide();
                }, 3000);
            }

            // 出错
            if (data.status === 'error') {
                if (card) card.classList.add('is-error');
                stopPolling();

                unbindBeforeUnload();
                stopElapsed();

                if (closeBtn) closeBtn.style.display = 'block';
            }
        }

        function stopPolling() {
            if (timer) {
                clearInterval(timer);
                timer = null;
            }
        }

        function startPolling() {
            stopPolling();

            const poll = function () {
                fetch(cfg.progressUrl)
                    .then(function (res) { return res.json(); })
                    .then(function (data) { update(data); })
                    .catch(function (e) {
                        console.error('读取进度失败：', e);
                    });
            };

            poll(); // 立即拉一次
            timer = setInterval(poll, 1000); // 每秒一次
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', hide);
        }

        return {
            show: show,
            hide: hide,
            update: update,
            startPolling: startPolling,
            stopPolling: stopPolling
        };
    }

    // 打标签进度浮层
    const tagProgress = createTaskProgress({
        overlayId:   'tagProgressOverlay',
        cardId:      'tagProgressCard',
        barId:       'tagProgressBar',
        percentId:   'tagProgressPercent',
        countId:     'tagProgressCount',
        messageId:   'tagProgressMessage',
        closeId:     'tagProgressClose',
        elapsedId:   'tagProgressElapsed',
        progressUrl: '/api/tag/progress'
    });

    // 更新知识库进度浮层
    const updateProgress = createTaskProgress({
        overlayId:   'updateProgressOverlay',
        cardId:      'updateProgressCard',
        barId:       'updateProgressBar',
        percentId:   'updateProgressPercent',
        countId:     'updateProgressCount',
        messageId:   'updateProgressMessage',
        closeId:     'updateProgressClose',
        elapsedId:   'updateProgressElapsed',
        progressUrl: '/api/knowledge/update/progress'
    });


    // =====================================================
    // 初始化
    // =====================================================

    async function init() {
        console.log('=================================');
        console.log('Knowledge 初始化开始');
        console.log('=================================');

        bindEvents();

        await loadCurrentPDF();
        await loadPDFList();
        await loadKnowledge();

        console.log('Knowledge 初始化完成');
    }


    // =====================================================
    // 绑定事件
    // =====================================================

    function bindEvents() {

        // 搜索
        document
            .getElementById('knowledge-search')
            ?.addEventListener('input', handleSearch);

        // 下拉筛选
        document
            .getElementById('knowledge-filter')
            ?.addEventListener('change', handleFilter);

        // 上一页
        document
            .getElementById('knowledge-prev')
            ?.addEventListener('click', previousPage);

        // 下一页
        document
            .getElementById('knowledge-next')
            ?.addEventListener('click', nextPage);

        // 更新知识库
        document
            .getElementById('update-knowledge-btn')
            ?.addEventListener('click', updateKnowledge);

        // 打标签
        document
            .getElementById('tag-articles-btn')
            ?.addEventListener('click', tagArticles);

        // 显示上传按钮
        document
            .getElementById('show-upload-btn')
            ?.addEventListener('click', function() {
                const area = document.getElementById('pdfUploadArea');
                if (area) {
                    area.scrollIntoView({ behavior: 'smooth' });
                    document.getElementById('pdfFileInput')?.click();
                }
            });

        // 切换 PDF 按钮
        document
            .getElementById('switch-pdf-btn')
            ?.addEventListener('click', function() {
                document.querySelector('.pdf-list-container')?.scrollIntoView({ behavior: 'smooth' });
            });

        // 文件选择
        document
            .getElementById('pdfFileInput')
            ?.addEventListener('change', function() {
                if (this.files.length > 0) {
                    uploadPDFs();
                }
            });

        // 拖拽上传
        const dropZone = document.getElementById('dropZone');
        if (dropZone) {
            dropZone.addEventListener('dragover', function(e) {
                e.preventDefault();
                this.style.borderColor = '#2563eb';
                this.style.background = '#eff6ff';
            });

            dropZone.addEventListener('dragleave', function(e) {
                e.preventDefault();
                this.style.borderColor = '';
                this.style.background = '';
            });

            dropZone.addEventListener('drop', function(e) {
                e.preventDefault();
                this.style.borderColor = '';
                this.style.background = '';
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    document.getElementById('pdfFileInput').files = files;
                    uploadPDFs();
                }
            });

            dropZone.addEventListener('click', function() {
                document.getElementById('pdfFileInput').click();
            });
        }
    }


    // =====================================================
    // 加载 PDF 列表
    // =====================================================

    async function loadPDFList() {
        try {
            const result = await window.AppAPI.get('/api/pdf/list');
            const list = document.getElementById('pdfList');

            if (!list) return;

            if (result.success && result.data && result.data.length > 0) {
                list.innerHTML = result.data.map(pdf => `
                    <div class="pdf-item">
                        <span class="pdf-name">📄 ${escapeHtml(pdf.name)}</span>
                        <span class="pdf-size">${(pdf.size/1024).toFixed(1)} KB</span>
                        <div class="pdf-actions">
                            <button class="btn-sm btn-use" onclick="window.Knowledge.selectPDF('${escapeHtml(pdf.name)}')">使用</button>
                            <button class="btn-sm btn-delete" onclick="window.Knowledge.deletePDF('${escapeHtml(pdf.name)}')">删除</button>
                        </div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div class="empty-state" style="padding:20px;text-align:center;color:#999;">暂无 PDF 文件</div>';
            }
        } catch (error) {
            console.error('加载 PDF 列表失败：', error);
        }
    }


    // =====================================================
    // 加载当前使用的 PDF
    // =====================================================

    async function loadCurrentPDF() {
        try {
            const result = await window.AppAPI.get('/api/pdf/current');
            const nameEl = document.getElementById('current-pdf-name');

            let pdfName = '';

            if (result.success && result.data && result.data.current_pdf) {
                pdfName = result.data.current_pdf;
            }

            if (nameEl) {
                nameEl.textContent = pdfName || '未选择';
            }

            localStorage.setItem('currentPDFName', pdfName || '');

        } catch (error) {
            console.error('加载当前 PDF 失败：', error);
            localStorage.setItem('currentPDFName', '');
        }
    }

    // =====================================================
    // 选择/切换 PDF
    // =====================================================

    async function selectPDF(filename) {
        try {
            const result = await window.AppAPI.post('/api/pdf/select', {
                filename: filename
            });

            if (result.success) {
                document.getElementById('current-pdf-name').textContent = filename;

                localStorage.setItem('currentPDFName', filename || '');

                showToast('✅ 已切换到：' + filename, 'success');

                await loadKnowledge();
                await loadPDFList();
            } else {
                showToast('❌ 切换失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            showToast('❌ 切换失败：' + error.message, 'error');
        }
    }


    // =====================================================
    // 删除 PDF
    // =====================================================

    async function deletePDF(filename) {
        if (!confirm(`确定要删除 "${filename}" 吗？此操作不可恢复！`)) return;

        try {
            const response = await fetch(`/api/pdf/delete?filename=${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                showToast('✅ ' + result.message, 'success');

                await loadPDFList();

                const current = document.getElementById('current-pdf-name');
                if (current && current.textContent === filename) {
                    current.textContent = '未选择';

                    localStorage.setItem('currentPDFName', '');

                    await loadKnowledge();
                }
            } else {
                showToast('❌ ' + (result.message || '删除失败'), 'error');
            }
        } catch (error) {
            console.error('删除失败：', error);
            showToast('❌ 删除失败：' + error.message, 'error');
        }
    }


    // =====================================================
    // 上传 PDF
    // =====================================================

    async function uploadPDFs() {

        const input = document.getElementById('pdfFileInput');
        const files = input.files;

        if (files.length === 0) {
            showToast('请选择 PDF 文件', 'error');
            return;
        }

        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }

        const progress  = document.getElementById('uploadProgress');
        const fill      = document.getElementById('progressFill');
        const status    = document.getElementById('uploadStatus');
        const percentEl = document.getElementById('uploadPercent');
        const warning   = document.getElementById('uploadWarning');

        if (progress) progress.style.display = 'block';
        if (fill) fill.style.width = '0%';
        if (status) status.textContent = '正在上传...';
        if (percentEl) percentEl.textContent = '0%';
        if (warning) {
            warning.innerHTML = '⚠️ 正在上传文件，请勿刷新页面或关闭浏览器，否则上传会中断。';
            warning.style.background = '#fff7ed';
            warning.style.borderColor = '#fed7aa';
            warning.style.color = '#c2410c';
            warning.style.display = 'block';
        }

        const beforeUnloadHandler = function (e) {
            e.preventDefault();
            e.returnValue = '文件正在上传，确定要离开吗？';
            return e.returnValue;
        };
        window.addEventListener('beforeunload', beforeUnloadHandler);

        try {
            const result = await new Promise((resolve, reject) => {

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/pdf/upload');

                xhr.upload.onprogress = function (e) {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);

                        if (fill) fill.style.width = percent + '%';
                        if (percentEl) percentEl.textContent = percent + '%';
                        if (status) status.textContent = '正在上传... ' + percent + '%';

                        if (percent >= 100) {
                            if (status) status.textContent = '上传完成，服务器正在处理...';
                            if (warning) {
                                warning.innerHTML = '⏳ 文件已上传，服务器正在解析，请继续等待，勿刷新。';
                                warning.style.background = '#eff6ff';
                                warning.style.borderColor = '#bfdbfe';
                                warning.style.color = '#1d4ed8';
                            }
                        }
                    }
                };

                xhr.onload = function () {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            resolve(JSON.parse(xhr.responseText));
                        } catch (e) {
                            reject(new Error('服务器返回格式错误'));
                        }
                    } else {
                        reject(new Error('上传失败，HTTP状态码：' + xhr.status));
                    }
                };

                xhr.onerror = function () {
                    reject(new Error('网络错误，上传失败'));
                };

                xhr.send(formData);
            });

            if (fill) fill.style.width = '100%';
            if (percentEl) percentEl.textContent = '100%';

            if (result.success) {
                if (status) status.textContent = '✅ 成功上传 ' + result.data.length + ' 个文件';
                if (warning) {
                    warning.innerHTML = '✅ 上传完成，可以刷新或继续操作。';
                    warning.style.background = '#ecfdf5';
                    warning.style.borderColor = '#a7f3d0';
                    warning.style.color = '#047857';
                }

                showToast('✅ 成功上传 ' + result.data.length + ' 个文件', 'success');
                input.value = '';

                await loadPDFList();

                if (result.data && result.data.length > 0) {
                    await selectPDF(result.data[0].filename);
                }
            } else {
                if (status) status.textContent = '❌ ' + (result.message || '上传失败');
                if (warning) {
                    warning.innerHTML = '❌ 上传失败：' + (result.message || '未知错误');
                    warning.style.background = '#fef2f2';
                    warning.style.borderColor = '#fecaca';
                    warning.style.color = '#dc2626';
                }
                showToast('❌ 上传失败：' + (result.message || '未知错误'), 'error');
            }

        } catch (error) {
            if (status) status.textContent = '❌ ' + error.message;
            if (warning) {
                warning.innerHTML = '❌ 上传失败：' + error.message;
                warning.style.background = '#fef2f2';
                warning.style.borderColor = '#fecaca';
                warning.style.color = '#dc2626';
            }
            showToast('❌ 上传失败：' + error.message, 'error');

        } finally {
            window.removeEventListener('beforeunload', beforeUnloadHandler);

            setTimeout(() => {
                if (progress) progress.style.display = 'none';
                if (fill) fill.style.width = '0%';
                if (percentEl) percentEl.textContent = '0%';
            }, 3000);
        }
    }


    // =====================================================
    // 加载知识库
    // =====================================================

    async function loadKnowledge() {
        const list = document.getElementById('knowledge-list');
        if (!list) {
            console.error('找不到 #knowledge-list');
            return;
        }

        list.innerHTML = `
            <div class="list-loading">
                正在读取法规知识库...
            </div>
        `;

        try {

            const currentPdfElement = document.getElementById('current-pdf-name');
            let currentPdfName = '';
            if (currentPdfElement) {
                currentPdfName = currentPdfElement.textContent.trim();
                if (currentPdfName.endsWith('.pdf')) {
                    currentPdfName = currentPdfName.slice(0, -4);
                }
            }

            let source = '';
            if (currentPdfName && currentPdfName !== '未选择') {
                source = currentPdfName;
            }

            console.log('当前选中的 PDF：', source);

            const url = source ? `/api/knowledge/data?source=${encodeURIComponent(source)}` : '/api/knowledge/data';
            const result = await window.AppAPI.get(url);

            console.log('知识库接口返回：', result);

            if (!result.success) {
                throw new Error(result.message || '读取知识库失败');
            }

            knowledgeData = Array.isArray(result.data) ? result.data : [];
            console.log('知识库实际数量：', knowledgeData.length);

            filteredData = [...knowledgeData];
            currentPage = 1;

            buildFilter();
            renderList();

        } catch (error) {
            console.error('知识库读取失败：', error);
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">!</div>
                    <div class="empty-title">知识库读取失败</div>
                    <div class="empty-text">${escapeHtml(error.message)}</div>
                </div>
            `;
        }
    }

    // =====================================================
    // 创建章节/条款筛选
    // =====================================================

    function buildFilter() {

        const select = document.getElementById('knowledge-filter');

        if (!select) {
            return;
        }

        select.innerHTML = `
            <option value="">
                全部
            </option>
        `;

        const chapters = new Set();

        knowledgeData.forEach(item => {

            const chapter =
                item.chapter ||
                item.section ||
                item.chapter_name ||
                item.section_name ||
                '';

            if (chapter) {
                chapters.add(String(chapter));
            }

        });

        if (chapters.size > 0) {

            [...chapters]
                .sort((a, b) =>
                    a.localeCompare(b, 'zh-CN', { numeric: true })
                )
                .forEach(chapter => {

                    const option = document.createElement('option');

                    option.value = chapter;
                    option.textContent = chapter;

                    select.appendChild(option);
                });

            return;
        }

        knowledgeData.forEach(item => {

            const article = item.article || '';

            if (!article) {
                return;
            }

            const exists =
                [...select.options]
                    .some(option => option.value === String(article));

            if (!exists) {

                const option = document.createElement('option');

                option.value = String(article);
                option.textContent = String(article);

                select.appendChild(option);
            }

        });
    }


    // =====================================================
    // 下拉筛选
    // =====================================================

    function handleFilter() {

        const select = document.getElementById('knowledge-filter');

        if (!select) {
            return;
        }

        const value = select.value.trim().toLowerCase();

        if (!value) {

            filteredData = [...knowledgeData];

        } else {

            filteredData =
                knowledgeData.filter(item => {

                    const text = [
                        item.chapter,
                        item.section,
                        item.chapter_name,
                        item.section_name,
                        item.article
                    ]
                        .filter(Boolean)
                        .join(' ')
                        .toLowerCase();

                    return text.includes(value);
                });
        }

        currentPage = 1;

        renderList();
    }


    // =====================================================
    // 搜索
    // =====================================================

    function handleSearch() {

        const input = document.getElementById('knowledge-search');
        const select = document.getElementById('knowledge-filter');

        if (!input) {
            return;
        }

        const keyword = input.value.trim().toLowerCase();

        const filterValue =
            select
                ? select.value.trim().toLowerCase()
                : '';

        filteredData =
            knowledgeData.filter(item => {

                const text = [
                    item.article,
                    item.content,
                    item.title,
                    item.name,
                    item.law_name,
                    item.category,
                    item.chapter,
                    item.section,
                    item.chapter_name,
                    item.section_name
                ]
                    .filter(Boolean)
                    .join(' ')
                    .toLowerCase();

                const matchKeyword = !keyword || text.includes(keyword);

                const matchFilter = !filterValue || text.includes(filterValue);

                return matchKeyword && matchFilter;
            });

        currentPage = 1;

        renderList();
    }


    // =====================================================
    // 上一页
    // =====================================================

    function previousPage() {

        if (currentPage <= 1) {
            return;
        }

        currentPage--;

        renderList();

        scrollToTop();
    }


    // =====================================================
    // 下一页
    // =====================================================

    function nextPage() {

        const total = filteredData.length;

        const totalPage =
            Math.max(1, Math.ceil(total / PAGE_SIZE));

        if (currentPage >= totalPage) {
            return;
        }

        currentPage++;

        renderList();

        scrollToTop();
    }


    // =====================================================
    // 滚动到列表顶部
    // =====================================================

    function scrollToTop() {

        const list = document.getElementById('knowledge-list');

        if (list) {

            list.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }


    // =====================================================
    // 渲染列表
    // =====================================================

    function renderList() {

        const list = document.getElementById('knowledge-list');

        if (!list) {
            return;
        }

        const total = filteredData.length;

        const count = document.getElementById('knowledge-count');

        if (count) {
            count.textContent = total.toLocaleString();
        }

        const resultInfo =
            document.getElementById('knowledge-result-info');

        if (!total) {

            list.innerHTML = `
                <div class="empty-state">

                    <div class="empty-icon">
                        ▤
                    </div>

                    <div class="empty-title">
                        没有找到相关法规
                    </div>

                    <div class="empty-text">
                        请尝试其他关键词
                    </div>

                </div>
            `;

            if (resultInfo) {
                resultInfo.textContent = '共 0 条法规条文';
            }

            updatePagination(0);

            return;
        }

        const totalPage =
            Math.max(1, Math.ceil(total / PAGE_SIZE));

        if (currentPage > totalPage) {
            currentPage = totalPage;
        }

        const start = (currentPage - 1) * PAGE_SIZE;

        const pageData = filteredData.slice(start, start + PAGE_SIZE);

        if (resultInfo) {
            resultInfo.textContent =
                `共 ${total.toLocaleString()} 条法规条文，当前第 ${currentPage} / ${totalPage} 页`;
        }

        list.innerHTML =
            pageData
                .map((item, index) =>
                    createArticleHtml(item, start + index)
                )
                .join('');

        updatePagination(totalPage);
    }


    // =====================================================
    // 更新分页按钮
    // =====================================================

    function updatePagination(totalPage) {

        const pageInfo =
            document.getElementById('knowledge-page-info');

        const prev =
            document.getElementById('knowledge-prev');

        const next =
            document.getElementById('knowledge-next');

        if (pageInfo) {
            pageInfo.textContent = `${currentPage} / ${totalPage || 1}`;
        }

        if (prev) {
            prev.disabled = currentPage <= 1 || !totalPage;
        }

        if (next) {
            next.disabled = !totalPage || currentPage >= totalPage;
        }
    }


    // =====================================================
    // 单条法规
    // =====================================================

    function createArticleHtml(item, index) {

        const article = item.article || `第 ${index + 1} 条`;

        const content = item.content || '';

        const title =
            item.title || item.name || item.law_name || '法规条文';

        const chapter =
            item.chapter ||
            item.section ||
            item.chapter_name ||
            item.section_name ||
            '';

        return `
            <div class="article-item">

                <div class="article-header">

                    <div class="article-number">
                        ${escapeHtml(article)}
                    </div>

                    <div class="article-title">
                        ${escapeHtml(title)}
                    </div>

                </div>

                ${
                    chapter
                        ? `
                            <div class="article-chapter">
                                ${escapeHtml(chapter)}
                            </div>
                        `
                        : ''
                }

                <div class="article-content">
                    ${escapeHtml(content)}
                </div>

                <div class="article-footer">

                    <span>
                        法规条文
                    </span>

                    ${
                        item.category
                            ? `
                                <span>
                                    ${escapeHtml(item.category)}
                                </span>
                            `
                            : ''
                    }

                </div>

            </div>
        `;
    }

    // =====================================================
    // 更新知识库
    // =====================================================
    async function updateKnowledge() {
        const button = document.getElementById('update-knowledge-btn');

        if (!button) {
            return;
        }

        // =================================================
        // 1. 获取当前选中的 PDF
        // =================================================
        const currentPdfElement = document.getElementById('current-pdf-name');

        let sourceFile = '';

        if (currentPdfElement) {
            sourceFile = currentPdfElement.textContent.trim();
        }

        console.log('准备更新的 PDF：', sourceFile);

        // =================================================
        // 2. 检查是否选择了 PDF
        // =================================================
        if (!sourceFile || sourceFile === '未选择') {
            showToast('❌ 请先选择要更新的 PDF', 'error');
            return;
        }

        // =================================================
        // 3. 显示进度浮层（注意：这里先不启动轮询！）
        // =================================================
        updateProgress.show();

        // =================================================
        // 4. 保存按钮文字 + 禁用
        // =================================================
        const oldText = button.textContent;
        button.disabled = true;
        button.textContent = '更新中...';

        try {

            // =================================================
            // 5. 调用更新接口（后端会先 reset_progress，再启动后台任务）
            // =================================================
            const result = await window.AppAPI.post(
                '/api/knowledge/update',
                { source_file: sourceFile }
            );

            console.log('知识库更新接口返回：', result);

            // =================================================
            // 6. 接口返回失败 → 直接停止进度
            // =================================================
            if (!result.success) {
                updateProgress.stopPolling();
                updateProgress.update({
                    status: 'error',
                    message: result.message || '知识库更新失败',
                    total: 0,
                    processed: 0
                });
                return;
            }

            // =================================================
            // ⭐ 7. 关键：等后端 reset_progress 生效（约 300ms）
            //       然后才启动轮询，避免读到上一次任务的残留数据
            // =================================================
            await new Promise(resolve => setTimeout(resolve, 300));

            updateProgress.startPolling();

            // =================================================
            // 8. 监听 done 事件，完成后刷新知识库
            // =================================================
            waitProgressDone(
                '/api/knowledge/update/progress',
                function () {
                    loadKnowledge();
                    document.dispatchEvent(
                        new CustomEvent('knowledgeUpdated')
                    );
                }
            );

        } catch (error) {

            console.error('知识库更新失败：', error);

            updateProgress.stopPolling();
            updateProgress.update({
                status: 'error',
                message: error.message,
                total: 0,
                processed: 0
            });

        } finally {

            // =================================================
            // 9. 恢复按钮
            // =================================================
            button.disabled = false;
            button.textContent = oldText;
        }
    }


    // =====================================================
    // 给当前选中的 PDF 打工种标签
    // =====================================================
    async function tagArticles() {

        // =================================================
        // 1. 获取当前选中的 PDF
        // =================================================
        const currentPdfElement = document.getElementById('current-pdf-name');

        let sourceFile = '';

        if (currentPdfElement) {
            sourceFile = currentPdfElement.textContent.trim();
        }

        console.log('准备打标签的 PDF：', sourceFile);

        // =================================================
        // 2. 检查是否选择 PDF
        // =================================================
        if (!sourceFile || sourceFile === '未选择') {
            showToast('❌ 请先选择要打标签的 PDF', 'error');
            return;
        }

        // =================================================
        // 3. 找到打标签按钮
        // =================================================
        const button = document.getElementById('tag-articles-btn');

        const oldText = button ? button.textContent : '';

        // =================================================
        // 4. 显示进度浮层（先不启动轮询）
        // =================================================
        tagProgress.show();

        if (button) {
            button.disabled = true;
            button.textContent = '打标签中...';
        }

        try {

            // =================================================
            // 5. 调用打标签接口（后端先 reset，再启动任务）
            // =================================================
            const result = await window.AppAPI.post(
                '/api/tag/articles',
                { source_file: sourceFile }
            );

            console.log('打标签接口返回：', result);

            // =================================================
            // 6. 失败 → 停止进度
            // =================================================
            if (!result.success) {
                tagProgress.stopPolling();
                tagProgress.update({
                    status: 'error',
                    message: result.message || '打标签失败',
                    total: 0,
                    processed: 0
                });
                return;
            }

            // =================================================
            // ⭐ 7. 关键：等后端 reset 生效，再启动轮询
            // =================================================
            await new Promise(resolve => setTimeout(resolve, 300));

            tagProgress.startPolling();

            // =================================================
            // 8. 监听 done，完成后刷新知识库
            // =================================================
            waitProgressDone(
                '/api/tag/progress',
                function () {
                    loadKnowledge();
                    document.dispatchEvent(
                        new CustomEvent('knowledgeUpdated')
                    );
                }
            );

        } catch (error) {

            console.error('打标签失败：', error);

            tagProgress.stopPolling();
            tagProgress.update({
                status: 'error',
                message: error.message,
                total: 0,
                processed: 0
            });

        } finally {

            if (button) {
                button.disabled = false;
                button.textContent = oldText;
            }
        }
    }


    // =====================================================
    // 等待进度完成（轮询到 done 后执行回调）
    // =====================================================
    function waitProgressDone(progressUrl, onDone) {
        const timer = setInterval(function () {
            fetch(progressUrl)
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data && data.status === 'done') {
                        clearInterval(timer);
                        if (typeof onDone === 'function') {
                            onDone();
                        }
                    }
                    if (data && data.status === 'error') {
                        clearInterval(timer);
                    }
                })
                .catch(function () {
                    clearInterval(timer);
                });
        }, 1500);
    }


    // =====================================================
    // HTML 转义
    // =====================================================

    function escapeHtml(value) {

        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }


    // =====================================================
    // Toast
    // =====================================================

    function showToast(message, type = 'success') {

        if (window.AppToast && typeof window.AppToast === 'function') {
            window.AppToast(message, type);
            return;
        }

        alert(message);
    }


    // =====================================================
    // 对外暴露
    // =====================================================

    return {
        init,
        loadKnowledge,
        loadPDFList,
        loadCurrentPDF,
        selectPDF,
        deletePDF,
        uploadPDFs,
        handleSearch,
        nextPage,
        previousPage
    };

})();