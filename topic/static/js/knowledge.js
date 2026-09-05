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
    // 初始化
    // =====================================================


    async function init() {
        console.log('=================================');
        console.log('Knowledge 初始化开始');
        console.log('=================================');
    
        bindEvents();
        
        // ✅ 先加载当前 PDF
        await loadCurrentPDF();
        
        // ✅ 再加载 PDF 列表
        await loadPDFList();
        
        // ✅ 最后加载知识库（会根据当前 PDF 加载对应数据）
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
            ?.addEventListener(
                'input',
                handleSearch
            );


        // 下拉筛选
        document
            .getElementById('knowledge-filter')
            ?.addEventListener(
                'change',
                handleFilter
            );


        // 上一页
        document
            .getElementById('knowledge-prev')
            ?.addEventListener(
                'click',
                previousPage
            );


        // 下一页
        document
            .getElementById('knowledge-next')
            ?.addEventListener(
                'click',
                nextPage
            );


        // 更新知识库
        document
            .getElementById('update-knowledge-btn')
            ?.addEventListener(
                'click',
                updateKnowledge
            );

        // 打标签
        document
            .getElementById('tag-articles-btn')
            ?.addEventListener(
                'click',
                tagArticles
            );

        // =================================================
        // ✅ 新增：PDF 相关事件
        // =================================================

        // 显示上传按钮
        document
            .getElementById('show-upload-btn')
            ?.addEventListener(
                'click',
                function() {
                    const area = document.getElementById('pdfUploadArea');
                    if (area) {
                        area.scrollIntoView({ behavior: 'smooth' });
                        document.getElementById('pdfFileInput')?.click();
                    }
                }
            );

        // 切换 PDF 按钮
        document
            .getElementById('switch-pdf-btn')
            ?.addEventListener(
                'click',
                function() {
                    document.querySelector('.pdf-list-container')?.scrollIntoView({ behavior: 'smooth' });
                }
            );

        // 文件选择
        document
            .getElementById('pdfFileInput')
            ?.addEventListener(
                'change',
                function() {
                    if (this.files.length > 0) {
                        uploadPDFs();
                    }
                }
            );

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
    // ✅ 新增：加载 PDF 列表
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
    // ✅ 新增：加载当前使用的 PDF
    // =====================================================

    async function loadCurrentPDF() {
        try {
            const result = await window.AppAPI.get('/api/pdf/current');
            const nameEl = document.getElementById('current-pdf-name');

            if (nameEl) {
                if (result.success && result.data && result.data.current_pdf) {
                    nameEl.textContent = result.data.current_pdf;
                } else {
                    nameEl.textContent = '未选择';
                }
            }
        } catch (error) {
            console.error('加载当前 PDF 失败：', error);
        }
    }

    // =====================================================
    // ✅ 选择/切换 PDF
    // =====================================================

    async function selectPDF(filename) {
        try {
            const result = await window.AppAPI.post('/api/pdf/select', {
                filename: filename
            });

            if (result.success) {
                document.getElementById('current-pdf-name').textContent = filename;
                showToast('✅ 已切换到：' + filename, 'success');
                
                // ✅ 重新加载知识库（会根据当前选中的 PDF 加载对应数据）
                await loadKnowledge();
                
                // 刷新列表
                await loadPDFList();
            } else {
                showToast('❌ 切换失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            showToast('❌ 切换失败：' + error.message, 'error');
        }
    }


    // =====================================================
    // ✅ 新增：删除 PDF
    // =====================================================

    async function deletePDF(filename) {
        if (!confirm('确定要删除 ' + filename + ' 吗？')) return;

        try {
            const result = await window.AppAPI.delete('/api/pdf/delete?filename=' + encodeURIComponent(filename));

            if (result.success) {
                showToast('✅ ' + result.message, 'success');
                await loadPDFList();
                // 如果当前使用的是被删除的，重置
                const current = document.getElementById('current-pdf-name');
                if (current && current.textContent === filename) {
                    current.textContent = '未选择';
                }
            } else {
                showToast('❌ ' + (result.message || '删除失败'), 'error');
            }
        } catch (error) {
            showToast('❌ 删除失败：' + error.message, 'error');
        }
    }


    // =====================================================
    // ✅ 新增：上传 PDF
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

        // 显示进度
        const progress = document.getElementById('uploadProgress');
        const fill = document.getElementById('progressFill');
        const status = document.getElementById('uploadStatus');

        if (progress) progress.style.display = 'block';
        if (fill) fill.style.width = '50%';
        if (status) status.textContent = '上传中...';

        try {
            const response = await fetch('/api/pdf/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (fill) fill.style.width = '100%';

            if (result.success) {
                if (status) status.textContent = '✅ 成功上传 ' + result.data.length + ' 个文件';
                showToast('✅ 成功上传 ' + result.data.length + ' 个文件', 'success');
                input.value = '';
                await loadPDFList();
                // 自动使用第一个上传的
                if (result.data && result.data.length > 0) {
                    await selectPDF(result.data[0].filename);
                }
            } else {
                if (status) status.textContent = '❌ ' + (result.message || '上传失败');
                showToast('❌ 上传失败：' + (result.message || '未知错误'), 'error');
            }
        } catch (error) {
            if (status) status.textContent = '❌ ' + error.message;
            showToast('❌ 上传失败：' + error.message, 'error');
        }

        setTimeout(() => {
            if (progress) progress.style.display = 'none';
            if (fill) fill.style.width = '0%';
        }, 3000);
    }


    // =====================================================
    // 加载知识库
    // =====================================================

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

        // 获取当前选中的 PDF 名称
        const currentPdfElement = document.getElementById('current-pdf-name');
        let currentPdfName = '';
        if (currentPdfElement) {
            currentPdfName = currentPdfElement.textContent.trim();
            // ✅ 去掉 .pdf 后缀，匹配目录名
            if (currentPdfName.endsWith('.pdf')) {
                currentPdfName = currentPdfName.slice(0, -4);
            }
        }


        // ✅ 如果当前有选中的 PDF（不是"未选择"），就传 source 参数
        let source = '';
        if (currentPdfName && currentPdfName !== '未选择') {
            source = currentPdfName;
        }

        console.log('当前选中的 PDF：', source);

        // ✅ 调用 API 时带上 source 参数
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

        const select =
            document.getElementById(
                'knowledge-filter'
            );

        if (!select) {
            return;
        }


        // 保留全部
        select.innerHTML = `
            <option value="">
                全部
            </option>
        `;


        // =================================================
        // 优先使用 chapter / section 字段
        // =================================================

        const chapters =
            new Set();


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


        // =================================================
        // 如果数据里面存在章节
        // =================================================

        if (chapters.size > 0) {

            [...chapters]
                .sort((a, b) =>
                    a.localeCompare(
                        b,
                        'zh-CN',
                        {
                            numeric: true
                        }
                    )
                )
                .forEach(chapter => {

                    const option =
                        document.createElement(
                            'option'
                        );

                    option.value =
                        chapter;

                    option.textContent =
                        chapter;

                    select.appendChild(
                        option
                    );
                });

            return;
        }


        // =================================================
        // 如果没有 chapter 字段
        // 就按照 article 生成条款选项
        // =================================================

        knowledgeData.forEach(item => {

            const article =
                item.article ||
                '';


            if (!article) {
                return;
            }


            const exists =
                [...select.options]
                    .some(
                        option =>
                            option.value ===
                            String(article)
                    );


            if (!exists) {

                const option =
                    document.createElement(
                        'option'
                    );

                option.value =
                    String(article);

                option.textContent =
                    String(article);

                select.appendChild(
                    option
                );
            }

        });
    }


    // =====================================================
    // 下拉筛选
    // =====================================================

    function handleFilter() {

        const select =
            document.getElementById(
                'knowledge-filter'
            );

        if (!select) {
            return;
        }


        const value =
            select.value
                .trim()
                .toLowerCase();


        if (!value) {

            filteredData =
                [...knowledgeData];

        } else {

            filteredData =
                knowledgeData.filter(
                    item => {

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


                        return text.includes(
                            value
                        );
                    }
                );
        }


        currentPage = 1;

        renderList();
    }


    // =====================================================
    // 搜索
    // =====================================================

    function handleSearch() {

        const input =
            document.getElementById(
                'knowledge-search'
            );

        const select =
            document.getElementById(
                'knowledge-filter'
            );


        if (!input) {
            return;
        }


        const keyword =
            input.value
                .trim()
                .toLowerCase();


        const filterValue =
            select
                ? select.value
                    .trim()
                    .toLowerCase()
                : '';


        filteredData =
            knowledgeData.filter(
                item => {

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


                    const matchKeyword =
                        !keyword ||
                        text.includes(keyword);


                    const matchFilter =
                        !filterValue ||
                        text.includes(filterValue);


                    return (
                        matchKeyword &&
                        matchFilter
                    );
                }
            );


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

        const total =
            filteredData.length;


        const totalPage =
            Math.max(
                1,
                Math.ceil(
                    total /
                    PAGE_SIZE
                )
            );


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

        const list =
            document.getElementById(
                'knowledge-list'
            );


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

        const list =
            document.getElementById(
                'knowledge-list'
            );


        if (!list) {
            return;
        }


        const total =
            filteredData.length;


        // =================================================
        // 数量
        // =================================================

        const count =
            document.getElementById(
                'knowledge-count'
            );


        if (count) {

            count.textContent =
                total.toLocaleString();
        }


        // =================================================
        // 结果信息
        // =================================================

        const resultInfo =
            document.getElementById(
                'knowledge-result-info'
            );


        // =================================================
        // 没数据
        // =================================================

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

                resultInfo.textContent =
                    '共 0 条法规条文';
            }


            updatePagination(0);

            return;
        }


        // =================================================
        // 总页数
        // =================================================

        const totalPage =
            Math.max(
                1,
                Math.ceil(
                    total /
                    PAGE_SIZE
                )
            );


        if (
            currentPage >
            totalPage
        ) {

            currentPage =
                totalPage;
        }


        // =================================================
        // 当前页数据
        // =================================================

        const start =
            (currentPage - 1) *
            PAGE_SIZE;


        const pageData =
            filteredData.slice(
                start,
                start + PAGE_SIZE
            );


        // =================================================
        // 更新结果
        // =================================================

        if (resultInfo) {

            resultInfo.textContent =
                `共 ${total.toLocaleString()} 条法规条文，当前第 ${currentPage} / ${totalPage} 页`;
        }


        // =================================================
        // 渲染
        // =================================================

        list.innerHTML =
            pageData
                .map(
                    (item, index) =>
                        createArticleHtml(
                            item,
                            start + index
                        )
                )
                .join('');


        // =================================================
        // 更新分页
        // =================================================

        updatePagination(
            totalPage
        );
    }


    // =====================================================
    // 更新分页按钮
    // =====================================================

    function updatePagination(
        totalPage
    ) {

        const pageInfo =
            document.getElementById(
                'knowledge-page-info'
            );


        const prev =
            document.getElementById(
                'knowledge-prev'
            );


        const next =
            document.getElementById(
                'knowledge-next'
            );


        if (pageInfo) {

            pageInfo.textContent =
                `${currentPage} / ${totalPage || 1}`;
        }


        if (prev) {

            prev.disabled =
                currentPage <= 1 ||
                !totalPage;
        }


        if (next) {

            next.disabled =
                !totalPage ||
                currentPage >= totalPage;
        }
    }


    // =====================================================
    // 单条法规
    // =====================================================

    function createArticleHtml(
        item,
        index
    ) {

        const article =
            item.article ||
            `第 ${index + 1} 条`;


        const content =
            item.content ||
            '';


        const title =
            item.title ||
            item.name ||
            item.law_name ||
            '法规条文';


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
                                    ${escapeHtml(
                                        item.category
                                    )}
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

        const button =
            document.getElementById(
                'update-knowledge-btn'
            );

        if (!button) {
            return;
        }

        const oldText =
            button.textContent;

        button.disabled = true;
        button.textContent = '更新中...';

        try {

            const result =
                await window.AppAPI.post(
                    '/api/knowledge/update'
                );

            if (!result.success) {

                throw new Error(
                    result.message ||
                    '知识库更新失败'
                );
            }

            showToast(
                '✅ 知识库更新完成！',
                'success'
            );

            // ✅ 重新加载列表
            await loadKnowledge();

            // ✅ 触发自定义事件，通知 app.js 刷新侧边栏
            document.dispatchEvent(new CustomEvent('knowledgeUpdated'));

        } catch (error) {

            console.error(
                '知识库更新失败：',
                error
            );

            showToast(
                error.message,
                'error'
            );

        } finally {

            button.disabled = false;
            button.textContent = oldText;
        }
    }


    // =====================================================
    // 打标签
    // =====================================================

    async function tagArticles() {

        const button =
            document.getElementById(
                'tag-articles-btn'
            );

        if (!button) {
            return;
        }

        const oldText =
            button.textContent;

        button.disabled = true;
        button.textContent = '打标签中...';

        try {

            const result =
                await window.AppAPI.post(
                    '/api/tag/articles'
                );

            if (!result.success) {

                throw new Error(
                    result.message ||
                    '打标签失败'
                );
            }

            showToast(
                '✅ 打标签完成！',
                'success'
            );

            // 重新加载知识库（刷新列表）
            await loadKnowledge();

            // ✅ 触发自定义事件，通知 app.js 刷新侧边栏
            document.dispatchEvent(new CustomEvent('knowledgeUpdated'));

        } catch (error) {

            console.error(
                '打标签失败：',
                error
            );

            showToast(
                '❌ ' + error.message,
                'error'
            );

        } finally {

            button.disabled = false;
            button.textContent = oldText;
        }
    }


    // =====================================================
    // HTML 转义
    // =====================================================

    function escapeHtml(value) {

        return String(
            value ?? ''
        )
            .replace(
                /&/g,
                '&amp;'
            )
            .replace(
                /</g,
                '&lt;'
            )
            .replace(
                />/g,
                '&gt;'
            )
            .replace(
                /"/g,
                '&quot;'
            )
            .replace(
                /'/g,
                '&#039;'
            );
    }


    // =====================================================
    // Toast
    // =====================================================

    function showToast(
        message,
        type = 'success'
    ) {

        if (
            window.AppToast &&
            typeof window.AppToast ===
                'function'
        ) {

            window.AppToast(
                message,
                type
            );

            return;
        }


        alert(message);
    }


    // =====================================================
    // ✅ 对外暴露（增加 PDF 相关方法）
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