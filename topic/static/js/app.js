/*
 * =========================================================
 * app.js
 * 通用法规 AI 系统
 *
 * 负责：
 * 1. 页面配置
 * 2. 菜单切换
 * 3. 动态加载 HTML
 * 4. 动态加载 CSS
 * 5. 动态加载页面 JS
 * 6. 页面初始化
 * 7. 顶部时间
 * 8. 提供统一 AppAPI
 * =========================================================
 */

const App = {

    /*
     * =====================================================
     * 页面配置
     * =====================================================
     */

    pages: {

        dashboard: {
            url: '/dashboard',
            title: '工作台',
            css: '/static/css/dashboard.css',
            js: '/static/js/dashboard.js'
        },

        knowledge: {
            url: '/knowledge',
            title: '法规知识库',
            css: '/static/css/knowledge.css',
            js: '/static/js/knowledge.js'
        },

        aiQuestion: {
            url: '/ai-question',
            title: 'AI智能出题',
            css: '/static/css/ai_question.css',
            js: '/static/js/ai_question.js'
        },

        questionBank: {
            url: '/question-bank',
            title: '题库管理',
            css: '/static/css/question_bank.css',
            js: '/static/js/question_bank.js'
        },

        system: {
            url: '/system',
            title: '系统设置',
            css: '/static/css/system.css',
            js: '/static/js/system.js'
        }
    },


    /*
     * =====================================================
     * 当前页面
     * =====================================================
     */

    currentPage: null,


    /*
     * =====================================================
     * 初始化
     * =====================================================
     */

    init() {

        console.log('App 初始化');

        this.bindMenu();

        this.updateTime();

        setInterval(() => {

            this.updateTime();

        }, 1000);

        // 加载AI配置
        this.loadAIStatus();

        this.loadGlobalAIConfig();

        this.loadPage('dashboard');
        this.updateKnowledgeCount();
        // ✅ 监听 AI 配置变化事件
        document.addEventListener(
            "aiConfigChanged",
            () => {

                console.log(
                    "App 收到配置变化事件，刷新侧边栏"
                );

                this.updateSidebarAI();

                // ✅ 如果当前在系统设置页面，重新加载页面内容
                if (this.currentPage === 'system') {

                    console.log(
                        "当前在系统设置页面，重新加载页面内容"
                    );

                    // 重新加载 system 页面
                    this.loadPage('system');

                }

            }
        );
        // ✅ 新增：监听知识库更新事件
    document.addEventListener('knowledgeUpdated', () => {
        console.log('📨 收到知识库更新通知，刷新侧边栏数量');
        this.updateKnowledgeCount();
    });

    },


    /*
     * =====================================================
     * 菜单事件
     * =====================================================
     */

    bindMenu() {

        document
            .querySelectorAll('[data-page]')
            .forEach(item => {

                item.addEventListener(
                    'click',
                    () => {

                        const page =
                            item.dataset.page;

                        console.log(
                            '点击菜单：',
                            page
                        );

                        this.loadPage(page);
                    }
                );

            });
    },


    /*
     * =====================================================
     * 加载页面
     * =====================================================
     */

    async loadPage(page) {

        console.log('====================================');
        console.log('开始加载页面：', page);
        console.log('====================================');

        /*
         * 页面配置
         */

        const config =
            this.pages[page];

        if (!config) {

            console.error(
                '不存在的页面：',
                page
            );

            return;
        }


        /*
         * 保存当前页面
         */

        this.currentPage =
            page;


        /*
         * 设置菜单状态
         */

        this.setActiveMenu(page);


        /*
         * 获取页面容器
         */

        const container =
            document.getElementById(
                'page-container'
            );

        if (!container) {

            console.error(
                '找不到 #page-container'
            );

            return;
        }


        /*
         * 显示加载状态
         */

        container.innerHTML = `
            <div class="page-loading">

                <div class="loading-spinner">
                </div>

                <div class="loading-text">
                    页面加载中...
                </div>

            </div>
        `;


        try {

            /*
             * =================================================
             * 1. 请求页面 HTML
             * =================================================
             */

            console.log(
                '请求页面 HTML：',
                config.url
            );

            const response =
                await fetch(
                    config.url,
                    {
                        method: 'GET',

                        headers: {
                            'X-Requested-With':
                                'XMLHttpRequest',

                            'Accept':
                                'text/html'
                        },

                        cache: 'no-store'
                    }
                );


            if (!response.ok) {

                throw new Error(
                    `页面请求失败：${response.status} ${response.statusText}`
                );
            }


            /*
             * 获取 HTML
             */

            const html =
                await response.text();

            console.log(
                '页面 HTML 获取成功：',
                config.url
            );


            /*
             * =================================================
             * 2. HTML 放入容器
             * =================================================
             */

            container.innerHTML =
                html;


            /*
             * =================================================
             * 3. 修改顶部标题
             * =================================================
             */

            const title =
                document.getElementById(
                    'page-title'
                );

            if (title) {

                title.textContent =
                    config.title;
            }


            /*
             * =================================================
             * 4. 加载 CSS
             * =================================================
             */

            await this.loadCss(
                config.css
            );


            /*
             * =================================================
             * 5. 加载页面 JS
             * =================================================
             */

            await this.loadPageScript(
                config.js
            );


            /*
             * =================================================
             * 6. 页面初始化
             *
             * 非常重要：
             *
             * 页面 JS 只负责定义：
             *
             * Dashboard
             * Knowledge
             * AIQuestion
             * QuestionBank
             * System
             *
             * 真正的 init()
             * 由这里统一调用。
             * =================================================
             */

            this.initPage(page);


            /*
             * =================================================
             * 7. 加载完成后更新侧边栏
             * =================================================
             */

            await this.updateSidebarAI();
            await this.updateKnowledgeCount();


            /*
             * =================================================
             * 8. 加载完成
             * =================================================
             */

            console.log(
                '===================================='
            );

            console.log(
                '页面加载完成：',
                page
            );

            console.log(
                '===================================='
            );

            // ✅ 触发页面加载完成事件
            document.dispatchEvent(
                new CustomEvent("pageLoaded", {
                    detail: {
                        page: page
                    }
                })
            );


        } catch (error) {

            console.error(
                '页面加载失败：',
                error
            );


            container.innerHTML = `
                <div class="page-error">

                    <div class="error-icon">
                        ⚠
                    </div>

                    <div class="error-title">
                        页面加载失败
                    </div>

                    <div class="error-message">
                        ${this.escapeHtml(error.message)}
                    </div>

                    <button
                        class="btn-primary"
                        onclick="App.loadPage('${page}')"
                    >
                        重新加载
                    </button>

                </div>
            `;
        }
    },


    /*
     * =====================================================
     * 页面初始化
     *
     * 统一负责调用各页面 init()
     * =====================================================
     */

    initPage(page) {

        console.log(
            '开始初始化页面：',
            page
        );


        switch (page) {


            /*
             * =================================================
             * 工作台
             * =================================================
             */

            case 'dashboard':

                if (
                    typeof Dashboard !== 'undefined' &&
                    typeof Dashboard.init === 'function'
                ) {

                    console.log(
                        '调用 Dashboard.init()'
                    );

                    Dashboard.init();

                } else {

                    console.error(
                        'Dashboard.init 不存在'
                    );
                }

                break;


            /*
             * =================================================
             * 法规知识库
             * =================================================
             */

            case 'knowledge':

                if (
                    typeof Knowledge !== 'undefined' &&
                    typeof Knowledge.init === 'function'
                ) {

                    console.log(
                        '调用 Knowledge.init()'
                    );

                    Knowledge.init();

                } else {

                    console.warn(
                        'Knowledge.init 不存在'
                    );
                }

                break;


            /*
             * =================================================
             * AI智能出题
             * =================================================
             */

            case 'aiQuestion':

                if (
                    typeof AIQuestion !== 'undefined' &&
                    typeof AIQuestion.init === 'function'
                ) {

                    console.log(
                        '调用 AIQuestion.init()'
                    );

                    AIQuestion.init();

                } else {

                    console.warn(
                        'AIQuestion.init 不存在'
                    );
                }

                break;


            /*
             * =================================================
             * 题库管理
             * =================================================
             */

            case 'questionBank':

                if (
                    typeof QuestionBank !== 'undefined' &&
                    typeof QuestionBank.init === 'function'
                ) {

                    console.log(
                        '调用 QuestionBank.init()'
                    );

                    QuestionBank.init();

                } else {

                    console.warn(
                        'QuestionBank.init 不存在'
                    );
                }

                break;


            /*
             * =================================================
             * 系统设置
             * =================================================
             */

            case 'system':

                if (
                    typeof System !== 'undefined' &&
                    typeof System.init === 'function'
                ) {

                    console.log(
                        '调用 System.init()'
                    );

                    System.init();

                } else {

                    console.warn(
                        'System.init 不存在'
                    );
                }

                break;


            /*
             * =================================================
             * 默认
             * =================================================
             */

            default:

                console.log(
                    '页面没有配置初始化函数：',
                    page
                );
        }
    },


    /*
     * =====================================================
     * 动态加载 CSS
     * =====================================================
     */

    loadCss(url) {

        return new Promise(
            (resolve, reject) => {

                if (!url) {

                    resolve();

                    return;
                }


                /*
                 * 删除旧页面 CSS
                 */

                document
                    .querySelectorAll(
                        'link[data-page-css]'
                    )
                    .forEach(link => {

                        if (
                            link.dataset.pageCss !== url
                        ) {

                            link.remove();
                        }

                    });


                /*
                 * 如果已经存在
                 */

                const oldLink =
                    document.querySelector(
                        `link[data-page-css="${url}"]`
                    );

                if (oldLink) {

                    resolve();

                    return;
                }


                /*
                 * 创建 CSS
                 */

                const link =
                    document.createElement(
                        'link'
                    );

                link.rel =
                    'stylesheet';

                link.href =
                    url;

                link.dataset.pageCss =
                    url;


                /*
                 * CSS 加载成功
                 */

                link.onload = () => {

                    console.log(
                        'CSS 加载成功：',
                        url
                    );

                    resolve();
                };


                /*
                 * CSS 加载失败
                 */

                link.onerror = () => {

                    console.error(
                        'CSS 加载失败：',
                        url
                    );

                    reject(
                        new Error(
                            `CSS 加载失败：${url}`
                        )
                    );
                };


                document.head.appendChild(
                    link
                );
            }
        );
    },


    /*
     * =====================================================
     * 动态加载页面 JS
     * =====================================================
     */

    loadPageScript(url) {
        return new Promise((resolve, reject) => {
    
            if (!url) {
                resolve();
                return;
            }
    
            // =====================================================
            // 如果已经加载过，不再重复加载
            // =====================================================
    
            const oldScript = document.querySelector(
                `script[data-page-script="${url}"]`
            );
    
            if (oldScript) {
                console.log(
                    '页面 JS 已经加载过，直接使用：',
                    url
                );
    
                resolve();
                return;
            }
    
            // =====================================================
            // 创建 script
            // =====================================================
    
            const script = document.createElement('script');
    
            script.src =
                url +
                '?t=' +
                Date.now();
    
            script.dataset.pageScript = url;
    
            // =====================================================
            // JS 加载成功
            // =====================================================
    
            script.onload = () => {
    
                console.log(
                    '页面 JS 加载成功：',
                    url
                );
    
                resolve();
            };
    
            // =====================================================
            // JS 加载失败
            // =====================================================
    
            script.onerror = () => {
    
                console.error(
                    '页面 JS 加载失败：',
                    url
                );
    
                reject(
                    new Error(
                        `JS 加载失败：${url}`
                    )
                );
            };
    
            document.body.appendChild(script);
        });
    },


    /*
     * =====================================================
     * 设置菜单状态
     * =====================================================
     */

    setActiveMenu(page) {

        document
            .querySelectorAll(
                '[data-page]'
            )
            .forEach(item => {

                item.classList.toggle(
                    'active',
                    item.dataset.page === page
                );

            });
    },


    /*
     * =====================================================
     * 更新时间
     * =====================================================
     */

    updateTime() {

        const element =
            document.getElementById(
                'current-time'
            );

        if (!element) {

            return;
        }


        const now =
            new Date();


        const pad =
            value =>
                String(value)
                    .padStart(2, '0');


        element.textContent =
            `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ` +
            `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    },


    /*
     * =====================================================
     * 更新侧边栏 AI 信息
     * =====================================================
     */

    async updateSidebarAI() {

        try {
    
            const result =
                await window.AppAPI.get(
                    "/api/config"
                );
    
            if (!result || !result.data) {
                return;
            }
    
            const config = result.data;
    
            const provider =
                config.provider ||
                config.ai ||
                "ollama";
    
            // AI 服务显示名称映射
            const names = {
                ollama: "Ollama",
                deepseek: "DeepSeek",
                openai: "OpenAI",
                qwen: "通义千问",
                zhipu: "智谱AI",
                custom: "自定义"
            };
    
            const displayName =
                names[provider] || provider;
    
            // 侧边栏 AI 服务
            const sidebarService =
                document.getElementById(
                    "sidebar-ai-service"
                );
    
            if (sidebarService) {
    
                sidebarService.textContent =
                    displayName;
            }
    
            // 侧边栏 AI 模型
            const sidebarModel =
                document.getElementById(
                    "sidebar-ai-model"
                );
    
            if (sidebarModel) {
    
                sidebarModel.textContent =
                    config.model || "--";
            }
    
            // 顶部 AI 名称
            const headerAiName =
                document.getElementById(
                    "header-ai-name"
                );
    
            if (headerAiName) {
    
                headerAiName.textContent =
                    displayName;
            }
    
            console.log(
                "侧边栏 AI 信息已更新：",
                displayName,
                config.model
            );
    
        } catch (error) {
    
            console.error(
                "更新侧边栏 AI 信息失败：",
                error
            );
        }
    
    },
    
    // ✅ 在这里加新方法（逗号后面）
    async updateKnowledgeCount() {
    
        try {
    
            const result = await window.AppAPI.get("/api/knowledge/statistics");
    
            if (!result || !result.success) {
                console.warn('获取知识库统计失败:', result?.message);
                return;
            }
    
            const total = result.data?.total;
    
            if (total !== undefined && total !== null) {
                const countEl = document.querySelector('.sidebar-footer .footer-row b');
                if (countEl) {
                    countEl.textContent = total + '条';
                    console.log('✅ 知识库数量已更新：', total);
                }
            }
    
        } catch (error) {
    
            console.error('更新知识库数量失败：', error);
        }
    },


    /*
     * =====================================================
     * 加载全局 AI 配置
     * =====================================================
     */

    async loadGlobalAIConfig() {

        try {

            const result =
                await window.AppAPI.get(
                    "/api/config"
                );

            console.log(
                "全局AI配置:",
                result
            );

            if (!result || !result.data) {
                return;
            }

            const config = result.data;

            const provider =
                config.provider ||
                config.ai ||
                "ollama";

            const names = {
                ollama: "Ollama",
                deepseek: "DeepSeek",
                openai: "OpenAI",
                qwen: "通义千问",
                zhipu: "智谱AI",
                custom: "自定义"
            };

            const displayName =
                names[provider] || provider;

            // 左侧AI服务
            const service =
                document.getElementById(
                    "sidebar-ai-service"
                );

            if (service) {

                service.textContent =
                    displayName;
            }

            // 左侧模型
            const model =
                document.getElementById(
                    "sidebar-ai-model"
                );

            if (model) {

                model.textContent =
                    config.model || "--";
            }

            // 顶部模型名称
            const header =
                document.getElementById(
                    "header-ai-name"
                );

            if (header) {

                header.textContent =
                    displayName;
            }

        } catch (error) {

            console.error(
                "读取全局AI配置失败",
                error
            );
        }

    },


    /*
     * =====================================================
     * 加载 AI 状态
     * =====================================================
     */

    async loadAIStatus() {

        try {

            const result =
                await window.AppAPI.get(
                    "/api/config"
                );

            console.log(
                "AI状态:",
                result
            );

            if (!result || !result.data) {
                return;
            }

            const config = result.data;

            const provider =
                config.provider ||
                config.ai ||
                "ollama";

            const names = {
                ollama: "Ollama",
                deepseek: "DeepSeek",
                openai: "OpenAI",
                qwen: "通义千问",
                zhipu: "智谱AI",
                custom: "自定义"
            };

            const displayName =
                names[provider] || provider;

            // 左侧AI服务
            const service =
                document.getElementById(
                    "sidebar-ai-service"
                );

            if (service) {

                service.textContent =
                    displayName;
            }

            // 左侧模型
            const model =
                document.getElementById(
                    "sidebar-ai-model"
                );

            if (model) {

                model.textContent =
                    config.model || "--";
            }

            // 顶部模型
            const header =
                document.getElementById(
                    "header-ai-name"
                );

            if (header) {

                header.textContent =
                    displayName;
            }

        } catch (e) {

            console.error(
                "加载AI状态失败",
                e
            );
        }

    },


    /*
     * =====================================================
     * HTML 转义
     * =====================================================
     */

    escapeHtml(value) {

        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

};


/*
 * =========================================================
 * AppAPI
 *
 * 给：
 * knowledge.js
 * ai_question.js
 * question_bank.js
 * system.js
 *
 * 等页面 JS 使用
 * =========================================================
 */

window.AppAPI = {

    /*
     * =====================================================
     * GET
     * =====================================================
     */

    async get(url, options = {}) {

        const response =
            await fetch(
                url,
                {
                    method: 'GET',

                    headers: {
                        'Accept':
                            'application/json',

                        ...(options.headers || {})
                    },

                    cache:
                        options.cache ||
                        'no-store'
                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status} ${response.statusText}`
            );
        }


        return await response.json();
    },


    /*
     * =====================================================
     * POST
     * =====================================================
     */

    async post(
        url,
        data = null,
        options = {}
    ) {

        const requestOptions = {

            method: 'POST',

            headers: {
                'Accept':
                    'application/json',

                ...(options.headers || {})
            },

            cache: 'no-store'
        };


        /*
         * 有数据才发送 body
         */

        if (data !== null) {

            requestOptions.headers[
                'Content-Type'
            ] =
                'application/json';

            requestOptions.body =
                JSON.stringify(data);
        }


        const response =
            await fetch(
                url,
                requestOptions
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status} ${response.statusText}`
            );
        }


        return await response.json();
    }

};


/*
 * =========================================================
 * 启动
 * =========================================================
 */

document.addEventListener(
    'DOMContentLoaded',
    () => {

        console.log(
            'DOM 加载完成，启动 App'
        );

        console.log(
            'AppAPI 已加载'
        );

        App.init();
    }
);


// =====================================================
// 暴露 App 给全局（供 system.js 调用）
// =====================================================

window.App = App;