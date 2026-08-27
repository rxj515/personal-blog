/*
 * =========================================================
 * dashboard.js
 * 工作台
 *
 * 负责：
 * 1. 获取法规知识库数量
 * 2. 获取题库数量
 * 3. 获取 AI 配置
 * 4. 更新工作台统计卡片
 *
 * 注意：
 * dashboard.js 只负责定义 Dashboard
 * 不在文件末尾自动执行 Dashboard.init()
 *
 * 页面初始化由 app.js 统一控制
 * =========================================================
 */

const Dashboard = {

    /*
     * =====================================================
     * 初始化
     * =====================================================
     */

    async init() {

        console.log('=================================');
        console.log('Dashboard 初始化开始');
        console.log('=================================');

        try {

            await Promise.all([
                this.loadKnowledgeCount(),
                this.loadQuestionCount(),
                this.loadAIConfig()
            ]);

            console.log(
                'Dashboard 初始化完成'
            );

            // ✅ 监听 AI 配置变化事件
            document.removeEventListener(
                "aiConfigChanged",
                this._handleConfigChange
            );

            this._handleConfigChange =
                this._handleConfigChange.bind(this);

            document.addEventListener(
                "aiConfigChanged",
                this._handleConfigChange
            );

        } catch (error) {

            console.error(
                'Dashboard 初始化失败：',
                error
            );

        }
    },


    /*
     * =====================================================
     * 处理配置变化事件
     * =====================================================
     */

    _handleConfigChange() {

        console.log(
            'Dashboard 检测到 AI 配置变化，重新加载...'
        );

        this.loadAIConfig();

    },


    /*
     * =====================================================
     * 获取法规知识库数量
     * =====================================================
     */

    async loadKnowledgeCount() {

        const element =
            document.getElementById(
                'article-count'
            );

        if (!element) {

            console.error(
                '找不到 #article-count'
            );

            return;
        }

        try {

            console.log(
                '正在请求法规知识库...'
            );

            const response =
                await fetch(
                    '/api/knowledge/statistics',
                    {
                        method: 'GET',

                        headers: {
                            'Accept':
                                'application/json'
                        },

                        cache: 'no-store'
                    }
                );

            if (!response.ok) {

                throw new Error(
                    `HTTP ${response.status} ${response.statusText}`
                );
            }

            const result =
                await response.json();

            console.log(
                '法规统计接口返回：',
                result
            );

            if (
                result.success &&
                result.data
            ) {

                const count =
                    Number(
                        result.data.total || 0
                    );

                element.textContent =
                    count.toLocaleString();

            } else {

                console.error(
                    '法规统计接口返回异常：',
                    result
                );

                element.textContent =
                    '--';
            }

        } catch (error) {

            console.error(
                '获取法规知识库数量失败：',
                error
            );

            element.textContent =
                '--';
        }
    },


    /*
     * =====================================================
     * 获取题库数量
     * =====================================================
     */

    async loadQuestionCount() {

        const element =
            document.getElementById(
                'question-count'
            );

        if (!element) {

            console.error(
                '找不到 #question-count'
            );

            return;
        }

        try {

            console.log(
                '正在请求题库统计...'
            );

            const response =
                await fetch(
                    '/api/questions/statistics',
                    {
                        method: 'GET',

                        headers: {
                            'Accept':
                                'application/json'
                        },

                        cache: 'no-store'
                    }
                );

            if (!response.ok) {

                throw new Error(
                    `HTTP ${response.status} ${response.statusText}`
                );
            }

            const result =
                await response.json();

            console.log(
                '题库统计接口返回：',
                result
            );

            if (
                result.success &&
                result.data
            ) {

                const count =
                    Number(
                        result.data.total || 0
                    );

                element.textContent =
                    count.toLocaleString();

            } else {

                console.error(
                    '题库统计接口返回异常：',
                    result
                );

                element.textContent =
                    '--';
            }

        } catch (error) {

            console.error(
                '获取题库数量失败：',
                error
            );

            element.textContent =
                '--';
        }
    },


    /*
     * =====================================================
     * 获取 AI 配置
     * =====================================================
     */

    async loadAIConfig() {

        try {

            console.log(
                '正在请求 AI 配置...'
            );

            const response =
                await fetch(
                    '/api/config',
                    {
                        method: 'GET',

                        headers: {
                            'Accept':
                                'application/json'
                        },

                        cache: 'no-store'
                    }
                );

            if (!response.ok) {

                throw new Error(
                    `HTTP ${response.status} ${response.statusText}`
                );
            }

            const result =
                await response.json();

            console.log(
                'AI 配置接口返回：',
                result
            );


            /*
             * =================================================
             * 获取配置
             * =================================================
             */

            const config =
                result.data || {};


            /*
             * =================================================
             * Provider / AI 类型
             * =================================================
             */

            const provider =
                config.provider ||
                config.ai ||
                'ollama';

            // ✅ AI 服务显示名称映射
            const names = {
                ollama: 'Ollama',
                deepseek: 'DeepSeek',
                openai: 'OpenAI',
                qwen: '通义千问',
                zhipu: '智谱AI',
                custom: '自定义'
            };

            const displayName =
                names[provider] || provider;


            /*
             * =================================================
             * 当前模型
             * =================================================
             */

            const model =
                config.model ||
                config.ai_model ||
                config.aiModel ||
                'qwen3:8b';


            /*
             * =================================================
             * AI 服务状态
             * =================================================
             */

            const aiStatus =
                document.getElementById(
                    'ai-service-status'
                );

            if (aiStatus) {

                aiStatus.textContent =
                    '在线';
            }


            /*
             * =================================================
             * 1. 更新统计卡片区域
             * =================================================
             */

            // AI 类型 (header-ai-name)
            const aiName =
                document.getElementById(
                    'header-ai-name'
                );

            if (aiName) {

                aiName.textContent =
                    displayName;
            }


            // 当前模型 (current-model)
            const modelElement =
                document.getElementById(
                    'current-model'
                );

            if (modelElement) {

                modelElement.textContent =
                    model;
            }


            // 模型类型 (current-model-type)
            const modelTypeElement =
                document.getElementById(
                    'current-model-type'
                );

            if (modelTypeElement) {

                modelTypeElement.textContent =
                    displayName;
            }


            /*
             * =================================================
             * 2. 更新系统说明区域
             * =================================================
             */

            // 当前 AI 服务 (ai-service)
            const aiService =
                document.getElementById(
                    'ai-service'
                );

            if (aiService) {

                aiService.textContent =
                    displayName;
            }


            // 当前模型 (ai-model-name)
            const aiModelName =
                document.getElementById(
                    'ai-model-name'
                );

            if (aiModelName) {

                aiModelName.textContent =
                    model;
            }


            console.log(
                'AI 服务：',
                displayName
            );

            console.log(
                'AI 模型：',
                model
            );

        } catch (error) {

            console.error(
                '获取 AI 配置失败：',
                error
            );

            // 出错时显示默认值
            const aiService =
                document.getElementById(
                    'ai-service'
                );

            if (aiService) {

                aiService.textContent =
                    'Ollama';
            }

            const aiModelName =
                document.getElementById(
                    'ai-model-name'
                );

            if (aiModelName) {

                aiModelName.textContent =
                    'qwen3:8b';
            }
        }
    }

};


/*
 * =========================================================
 * 注意
 *
 * 这里不要再写：
 *
 * Dashboard.init();
 *
 * Dashboard.init() 由 app.js 统一调用
 * =========================================================
 */