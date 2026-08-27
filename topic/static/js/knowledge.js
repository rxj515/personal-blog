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
    }


    // =====================================================
    // 加载知识库
    // =====================================================

    async function loadKnowledge() {

        const list =
            document.getElementById(
                'knowledge-list'
            );

        if (!list) {
            console.error(
                '找不到 #knowledge-list'
            );
            return;
        }


        list.innerHTML = `
            <div class="list-loading">
                正在读取法规知识库...
            </div>
        `;


        try {

            const result =
                await window.AppAPI.get(
                    '/api/knowledge/data'
                );


            console.log(
                '知识库接口返回：',
                result
            );


            if (!result.success) {

                throw new Error(
                    result.message ||
                    '读取知识库失败'
                );
            }


            knowledgeData =
                Array.isArray(result.data)
                    ? result.data
                    : [];


            console.log(
                '知识库实际数量：',
                knowledgeData.length
            );


            filteredData =
                [...knowledgeData];


            currentPage = 1;


            // =================================================
            // 生成筛选下拉框
            // =================================================

            buildFilter();


            // =================================================
            // 渲染
            // =================================================

            renderList();


        } catch (error) {

            console.error(
                '知识库读取失败：',
                error
            );


            list.innerHTML = `
                <div class="empty-state">

                    <div class="empty-icon">
                        !
                    </div>

                    <div class="empty-title">
                        知识库读取失败
                    </div>

                    <div class="empty-text">
                        ${escapeHtml(error.message)}
                    </div>

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

        button.textContent =
            '更新中...';


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
                result.message ||
                '法规知识库更新完成',
                'success'
            );


            await loadKnowledge();


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

            button.textContent =
                oldText;
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
    // 对外暴露
    // =====================================================

    return {

        init,

        loadKnowledge,

        handleSearch,

        nextPage,

        previousPage

    };

})();