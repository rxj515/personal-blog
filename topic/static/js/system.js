// =========================================================
// system.js
// 系统设置页面
// =========================================================


// =========================================================
// AI服务预设配置
// =========================================================

const AI_PROVIDERS = {

    ollama: {
        name: "Ollama (本地)",
        model: "qwen3:8b",
        base_url: "http://localhost:11434/v1",
        api_key: "",
        hint_model: "例如: qwen3:8b, llama3.1, deepseek-r1:7b",
        hint_url: "例如: http://localhost:11434/v1",
        show_api_key: false
    },

    deepseek: {
        name: "DeepSeek",
        model: "deepseek-chat",
        base_url: "https://api.deepseek.com/v1",
        api_key: "sk-...",
        hint_model: "例如: deepseek-chat, deepseek-reasoner",
        hint_url: "https://api.deepseek.com/v1",
        show_api_key: true
    },

    openai: {
        name: "OpenAI",
        model: "gpt-4o-mini",
        base_url: "https://api.openai.com/v1",
        api_key: "sk-...",
        hint_model: "例如: gpt-4o, gpt-4o-mini, gpt-3.5-turbo",
        hint_url: "https://api.openai.com/v1",
        show_api_key: true
    },

    qwen: {
        name: "通义千问 (Qwen)",
        model: "qwen-plus",
        base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key: "sk-...",
        hint_model: "例如: qwen-turbo, qwen-plus, qwen-max",
        hint_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
        show_api_key: true
    },

    zhipu: {
        name: "智谱AI (GLM)",
        model: "glm-4-plus",
        base_url: "https://open.bigmodel.cn/api/paas/v4",
        api_key: "...",
        hint_model: "例如: glm-4-plus, glm-4-air, glm-4-flash",
        hint_url: "https://open.bigmodel.cn/api/paas/v4",
        show_api_key: true
    },

    custom: {
        name: "自定义",
        model: "",
        base_url: "",
        api_key: "",
        hint_model: "请输入模型名称",
        hint_url: "请输入接口地址",
        show_api_key: true
    }

};



// =========================================================
// System 对象
// =========================================================

const System = {

    async init() {

        console.log("系统设置页面初始化");

        const providerElement =
            document.getElementById("ai-service");

        if (providerElement) {

            // 检查选项是否完整
            const options = providerElement.querySelectorAll('option');

            if (options.length < 6) {

                console.log("下拉框选项缺失，正在补充...");
                const currentValue = providerElement.value;

                providerElement.innerHTML = '';

                const optionData = [
                    { value: 'ollama', text: 'Ollama (本地)' },
                    { value: 'deepseek', text: 'DeepSeek' },
                    { value: 'openai', text: 'OpenAI' },
                    { value: 'qwen', text: '通义千问 (Qwen)' },
                    { value: 'zhipu', text: '智谱AI (GLM)' },
                    { value: 'custom', text: '自定义' }
                ];

                optionData.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.value;
                    option.textContent = item.text;
                    providerElement.appendChild(option);
                });

                if (currentValue) {
                    providerElement.value = currentValue;
                }

                console.log("✅ 下拉框选项已补充，共", providerElement.querySelectorAll('option').length, "项");
            }

            // 绑定切换事件
            providerElement.onchange = () => {
                this.changeAIProvider();
            };

        } else {
            console.error("❌ 找不到 #ai-service");
        }

        await this.loadSystemConfig();

    },


    async loadSystemConfig() {

        const statusDescription =
            document.getElementById("system-status-description");

        const statusBadge =
            document.getElementById("system-status");

        const aiStatus =
            document.getElementById("system-ai-status");


        try {

            console.log("正在读取 /api/config");

            const response =
                await window.AppAPI.get("/api/config");

            console.log("接口返回:", response);

            if (!response || !response.data) {
                throw new Error("接口返回数据为空");
            }

            const config = response.data;

            // Python版本
            const python = document.getElementById("system-python");
            if (python) {
                python.textContent = config.python || "--";
            }

            // AI服务
            const ai = document.getElementById("system-ai");
            if (ai) {
                const provider = config.provider || config.ai || "ollama";
                const preset = AI_PROVIDERS[provider];
                ai.textContent = preset?.name || provider;
            }

            // 模型
            const model = document.getElementById("system-model");
            if (model) {
                model.textContent = config.model || "--";
            }

            // 地址
            const url = document.getElementById("system-ollama");
            if (url) {
                url.textContent = config.base_url || config.url || "--";
            }

            // 项目路径
            const project = document.getElementById("system-project");
            if (project) {
                project.textContent = config.project_dir || config.project_path || "--";
            }

            // 填充表单
            const serviceSelect = document.getElementById("ai-service");
            if (serviceSelect) {

                // 确保选项存在
                if (serviceSelect.querySelectorAll('option').length < 6) {
                    const currentValue = serviceSelect.value;
                    serviceSelect.innerHTML = '';
                    const optionData = [
                        { value: 'ollama', text: 'Ollama (本地)' },
                        { value: 'deepseek', text: 'DeepSeek' },
                        { value: 'openai', text: 'OpenAI' },
                        { value: 'qwen', text: '通义千问 (Qwen)' },
                        { value: 'zhipu', text: '智谱AI (GLM)' },
                        { value: 'custom', text: '自定义' }
                    ];
                    optionData.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item.value;
                        option.textContent = item.text;
                        serviceSelect.appendChild(option);
                    });
                    if (currentValue) {
                        serviceSelect.value = currentValue;
                    }
                }

                const provider = config.provider || config.ai || "ollama";
                serviceSelect.value = provider;

                // 应用预设
                this.applyPreset(provider);
            }

            const modelInput = document.getElementById("ai-model");
            if (modelInput) {
                modelInput.value = config.model || "";
            }

            const urlInput = document.getElementById("ai-url");
            if (urlInput) {
                urlInput.value = config.base_url || config.url || "";
            }

            const apiKeyInput = document.getElementById("ai-api-key");
            if (apiKeyInput) {
                apiKeyInput.value = config.api_key || config.apiKey || "";
            }

            // AI配置卡片 - 当前服务
            const serviceDisplay = document.getElementById("system-ai-service");
            if (serviceDisplay) {
                const provider = config.provider || config.ai || "ollama";
                const preset = AI_PROVIDERS[provider];
                serviceDisplay.textContent = preset?.name || provider;
            }

            // AI配置卡片 - 当前模型
            const aiModel = document.getElementById("system-ai-model");
            if (aiModel) {
                aiModel.textContent = config.model || "--";
            }

            // AI配置卡片 - 服务状态
            if (statusBadge) {
                statusBadge.textContent = "运行正常";
                statusBadge.classList.remove("status-error");
                statusBadge.classList.add("status-success");
            }

            if (aiStatus) {
                aiStatus.textContent = "✅ 已配置";
                aiStatus.classList.remove("system-value-error");
                aiStatus.classList.add("system-value-success");
            }

            if (statusDescription) {
                statusDescription.textContent = "系统配置读取正常，AI服务运行正常";
            }

            console.log("系统配置加载完成");

        } catch (error) {

            console.error("读取系统配置失败:", error);

            if (statusBadge) {
                statusBadge.textContent = "读取失败";
                statusBadge.classList.add("status-error");
            }

            if (aiStatus) {
                aiStatus.textContent = "⚠️ 读取失败";
                aiStatus.classList.remove("system-value-success");
                aiStatus.classList.add("system-value-error");
            }

            if (statusDescription) {
                statusDescription.textContent = "系统配置读取失败，请检查后端服务";
            }

        }

    },


    applyPreset(provider) {

        console.log("✅ applyPreset 被调用，provider=", provider);

        const preset =
            AI_PROVIDERS[provider] ||
            AI_PROVIDERS.custom;

        console.log("✅ 预设配置：", preset);

        const modelInput =
            document.getElementById("ai-model");

        const urlInput =
            document.getElementById("ai-url");

        const apiKeyInput =
            document.getElementById("ai-api-key");

        const modelHint =
            document.getElementById("model-hint");

        const urlHint =
            document.getElementById("url-hint");

        const extraArea =
            document.getElementById("extra-config-area");

        // 模型
        if (modelInput) {
            modelInput.value = preset.model;
            modelInput.placeholder = preset.hint_model;
        }

        // 接口地址
        if (urlInput) {
            urlInput.value = preset.base_url;
            urlInput.placeholder = preset.hint_url;
        }

        // API Key
        if (apiKeyInput) {
            apiKeyInput.value = preset.api_key || "";
            apiKeyInput.placeholder = preset.api_key ?
                "已预设，可直接修改" :
                "请输入 API Key";
        }

        // 提示文字
        if (modelHint) {
            modelHint.textContent = `(${preset.hint_model})`;
        }

        if (urlHint) {
            urlHint.textContent = `(${preset.hint_url})`;
        }

        // 显示/隐藏 API Key 区域
        if (extraArea) {
            extraArea.style.display =
                preset.show_api_key && provider !== "custom" ?
                    "block" :
                    "none";
        }

        // 更新显示区域
        const systemAi = document.getElementById("system-ai");
        if (systemAi) {
            systemAi.textContent = preset.name || provider;
        }

        const serviceDisplay = document.getElementById("system-ai-service");
        if (serviceDisplay) {
            serviceDisplay.textContent = preset.name || provider;
        }

        const aiModel = document.getElementById("system-ai-model");
        if (aiModel) {
            aiModel.textContent = preset.model || "";
        }

        // 自定义模式
        if (provider === "custom") {
            if (modelInput) {
                modelInput.value = "";
                modelInput.placeholder = "请输入模型名称";
            }
            if (urlInput) {
                urlInput.value = "";
                urlInput.placeholder = "请输入接口地址";
            }
            if (apiKeyInput) {
                apiKeyInput.value = "";
                apiKeyInput.placeholder = "请输入 API Key (可选)";
            }
            if (extraArea) {
                extraArea.style.display = "block";
            }
            if (systemAi) {
                systemAi.textContent = "自定义";
            }
            if (serviceDisplay) {
                serviceDisplay.textContent = "自定义";
            }
            if (aiModel) {
                aiModel.textContent = "";
            }
        }

        console.log("✅ 应用预设完成");

    },


    changeAIProvider() {

        console.log("✅ changeAIProvider 被调用");

        const providerElement =
            document.getElementById("ai-service");

        if (!providerElement) {
            console.error("❌ 找不到 #ai-service");
            return;
        }

        const provider = providerElement.value;
        console.log("✅ 切换到服务：", provider);

        this.applyPreset(provider);

    },


    async saveAIConfig() {

        const saveBtn =
            document.getElementById("save-config-btn");

        try {

            const providerElement =
                document.getElementById("ai-service");

            const modelElement =
                document.getElementById("ai-model");

            const urlElement =
                document.getElementById("ai-url");

            const apiKeyElement =
                document.getElementById("ai-api-key");


            const provider = providerElement?.value || "ollama";
            const model = modelElement?.value?.trim();
            const baseUrl = urlElement?.value?.trim();
            const apiKey = apiKeyElement?.value?.trim() || "";


            if (!model) {
                alert("请输入模型名称");
                modelElement?.focus();
                return;
            }

            if (!baseUrl) {
                alert("请输入接口地址");
                urlElement?.focus();
                return;
            }


            const data = {
                provider: provider,
                model: model,
                base_url: baseUrl,
                api_key: apiKey
            };


            console.log("保存AI配置:", data);


            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = "保存中...";
            }


            const result =
                await window.AppAPI.post("/api/system/ai/config", data);


            console.log("保存返回:", result);


            if (result && result.success) {

                alert("AI配置保存成功！");

                // ✅ 只触发事件，不重新加载配置，由 app.js 处理页面刷新
                document.dispatchEvent(new CustomEvent("aiConfigChanged"));

            } else {
                alert(result?.message || "保存失败");
            }

        } catch (error) {

            console.error("保存AI配置失败:", error);
            alert("保存失败：" + (error.message || "未知错误"));

        } finally {

            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = "保存 AI 配置";
            }

        }

    }

};


// =========================================================
// 非模块项目必须挂全局
// =========================================================

window.System = System;


// =========================================================
// DOM加载完成后初始化
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        System.init();

    }
);