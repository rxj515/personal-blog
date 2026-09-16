const AIQuestion = {

    // =====================================================
    // 当前题目数据
    //
    // 这里只保存"本次AI生成"的题目
    // 页面显示和Excel导出都使用这里的数据
    // =====================================================
    currentQuestions: [],


    // =====================================================
    // 当前AI配置
    // =====================================================
    currentAIConfig: null,


    // =====================================================
    // 是否正在生成中
    // =====================================================
    isGenerating: false,


    // =====================================================
    // 删除事件处理器引用（用于移除监听器）
    // =====================================================
    _deleteHandler: null,


    // =====================================================
    // 初始化
    // =====================================================
    async init() {

        console.log("================================");
        console.log("AIQuestion 初始化");
        console.log("================================");

        // 读取当前系统AI配置
        await this.loadAIConfig();

        // ✅ 新增：加载分类（工种）下拉框
        await this.loadAiDeptList();

        // 加载上次生成的题目（从 _new.json）
        await this.loadNewQuestions();

        // 绑定按钮
        this.bindEvent();

        // ✅ 新增：绑定删除事件（独立）
        this.bindDeleteEvents();

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

    },


    // =====================================================
    // ✅ 新增：加载分类（工种）下拉框
    // =====================================================
    async loadAiDeptList() {

        try {
    
            const response = await fetch("/api/dept/list?t=" + Date.now(), {
                method: "GET",
                cache: "no-store"
            });
    
            const result = await response.json();
    
            const select = document.getElementById("ai-dept-select");
    
            if (!select) return;
    
            // 清空
            select.innerHTML = '<option value="">全部工种</option>';
    
            if (result.success && result.data.length > 0) {
    
                // 扁平化树形结构（带缩进）
                const flattenTree = (nodes, prefix = '', parentName = '') => {
                    nodes.forEach(node => {
                        const option = document.createElement('option');
                        option.value = node.id;
                        option.textContent = prefix + node.name;
    
                        // 存储完整路径
                        const fullPath = parentName ? `${parentName} / ${node.name}` : node.name;
                        option.dataset.fullName = fullPath;
                        option.dataset.superiorName = node.superiorName || '';
                        option.dataset.subjectionId = node.subjectionId || '';
                        option.dataset.subjectionName = node.subjectionName || '';
    
                        select.appendChild(option);
    
                        if (node.children && node.children.length > 0) {
                            flattenTree(node.children, prefix + '　　', fullPath);
                        }
                    });
                };
    
                flattenTree(result.data);
    
            }
    
        }
        catch (e) {
            console.error("加载分类失败:", e);
        }
    },


    
    // =====================================================
    // 处理配置变化事件
    // =====================================================
    _handleConfigChange() {

        console.log(
            'AIQuestion 检测到 AI 配置变化，重新加载...'
        );

        this.loadAIConfig();

    },


    // =====================================================
    // 加载本次新题（从 _new.json）
    // =====================================================
    async loadNewQuestions() {

        try {

            console.log(
                "正在加载上次生成的题目..."
            );

            const response =
                await fetch(
                    "/api/questions/new-data?t=" +
                    Date.now(),
                    {
                        method: "GET",
                        cache: "no-store"
                    }
                );

            if (!response.ok) {

                console.log(
                    "没有找到上次生成的题目（HTTP " +
                    response.status +
                    "）"
                );

                return;
            }

            const result =
                await response.json();

            console.log(
                "加载新题接口返回：",
                result
            );

            if (
                result &&
                result.success &&
                Array.isArray(result.data) &&
                result.data.length > 0
            ) {

                this.currentQuestions =
                    result.data;

                this.render(
                    this.currentQuestions
                );

                const message =
                    document.getElementById(
                        "generate-message"
                    );

                if (message) {

                    message.textContent =
                        "已加载上次生成的 " +
                        this.currentQuestions.length +
                        " 道题";

                }

                console.log(
                    "已加载上次生成的题目：",
                    this.currentQuestions.length,
                    "道"
                );

            }
            else {

                console.log(
                    "没有找到上次生成的题目"
                );

            }

        }
        catch (e) {

            console.log(
                "加载上次生成的题目失败：",
                e
            );

        }
    },


    // =====================================================
    // 读取当前AI模型配置
    //
    // 使用后端已经存在的接口：
    //
    // GET /api/system/ai/config
    //
    // 不再直接读取 aiconfig.json
    // =====================================================
    async loadAIConfig() {

        const modelElement =
            document.getElementById("ai-model");


        if (!modelElement) {

            console.error(
                "没有找到 ai-model 元素"
            );

            return null;
        }


        try {

            console.log(
                "正在读取当前AI模型配置..."
            );


            // =================================================
            // 调用现有后端接口
            // =================================================
            const response =
                await fetch(
                    "/api/system/ai/config?t=" +
                    Date.now(),
                    {
                        method: "GET",
                        cache: "no-store"
                    }
                );


            // =================================================
            // HTTP错误
            // =================================================
            if (!response.ok) {

                throw new Error(
                    "读取AI配置失败，HTTP状态码：" +
                    response.status
                );
            }


            // =================================================
            // 读取JSON
            // =================================================
            const result =
                await response.json();


            console.log(
                "================================"
            );

            console.log(
                "AI配置接口返回：",
                result
            );

            console.log(
                "================================"
            );


            // =================================================
            // 兼容不同返回结构
            // =================================================

            let config = null;


            if (
                result &&
                result.config &&
                typeof result.config === "object"
            ) {

                config =
                    result.config;

            }
            else if (
                result &&
                result.data &&
                typeof result.data === "object"
            ) {

                config =
                    result.data;

            }
            else if (
                result &&
                typeof result === "object" &&
                (
                    result.model ||
                    result.provider
                )
            ) {

                config =
                    result;

            }


            if (!config) {

                throw new Error(
                    "AI配置接口没有返回有效配置"
                );

            }


            if (!config.model) {

                throw new Error(
                    "AI配置中没有 model"
                );

            }


            // =================================================
            // 保存配置
            // =================================================
            this.currentAIConfig =
                config;


            // =================================================
            // ✅ 获取显示名称（改进版）
            // =================================================
            const displayName =
                this.getAIModelDisplayName(
                    config
                );


            // =================================================
            // 页面显示
            // =================================================
            modelElement.textContent =
                displayName;


            // =================================================
            // 保存真实模型名称
            // =================================================
            modelElement.dataset.model =
                config.model;


            modelElement.dataset.provider =
                config.provider || "";


            // =================================================
            // 状态样式
            // =================================================
            modelElement.classList.remove(
                "model-error"
            );


            modelElement.classList.add(
                "model-loaded"
            );


            console.log(
                "当前使用AI模型：",
                displayName
            );


            console.log(
                "Provider：",
                config.provider
            );


            console.log(
                "Model：",
                config.model
            );


            return config;

        }
        catch (e) {

            console.error(
                "================================"
            );

            console.error(
                "读取AI模型配置失败：",
                e
            );

            console.error(
                "================================"
            );


            // =================================================
            // 页面显示错误
            // =================================================
            modelElement.textContent =
                "读取模型失败";


            modelElement.title =
                e.message ||
                "无法读取当前AI模型配置";


            modelElement.classList.add(
                "model-error"
            );


            this.currentAIConfig =
                null;


            return null;
        }
    },


    // =====================================================
    // ✅ AI模型显示名称（改进版）
    // =====================================================
    getAIModelDisplayName(config) {

        const provider =
            String(
                config.provider || ""
            )
            .trim()
            .toLowerCase();

        const model =
            String(
                config.model || ""
            )
            .trim();

        // 显示名称映射
        const providerNames = {
            ollama: "Ollama",
            deepseek: "DeepSeek",
            openai: "OpenAI",
            qwen: "通义千问",
            zhipu: "智谱AI",
            custom: "自定义"
        };

        const displayProvider =
            providerNames[provider] || provider;

        // =================================================
        // 如果有 provider 和 model
        // =================================================
        if (
            provider &&
            model
        ) {

            return displayProvider + " - " + model;
        }

        // =================================================
        // 只有模型
        // =================================================
        if (model) {

            return model;
        }

        return "未知模型";
    },


    // =====================================================
    // 绑定事件
    // =====================================================
    bindEvent() {

        // =================================================
        // AI出题按钮
        // =================================================
        const btn =
            document.getElementById(
                "generate-btn"
            );

        if (btn) {

            btn.onclick = () => {

                this.generateStream();

            };

        }
        else {

            console.error(
                "没有找到生成按钮"
            );
        }


        // =================================================
        // Excel导出按钮
        // =================================================
        const exportBtn =
            document.getElementById(
                "export-btn"
            );

        if (exportBtn) {

            exportBtn.onclick = () => {

                this.exportExcel();

            };

        }
        else {

            console.error(
                "没有找到Excel导出按钮"
            );
        }

    },


    // =====================================================
    // ✅ 新增：绑定删除事件（独立方法，防止重复绑定）
    // =====================================================
    bindDeleteEvents() {

        const tbody =
            document.getElementById(
                "question-table-body"
            );

        if (!tbody) {
            return;
        }

        // 移除旧监听器
        if (this._deleteHandler) {
            tbody.removeEventListener(
                "click",
                this._deleteHandler
            );
            this._deleteHandler = null;
        }

        // 创建新监听器
        this._deleteHandler = (e) => {
            const deleteBtn =
                e.target.closest(".btn-delete-row");

            if (deleteBtn) {
                const row =
                    deleteBtn.closest("tr");

                if (row) {
                    // ✅ 获取存储的ID
                    const questionId =
                        row.dataset.id;

                    if (questionId) {
                        // 阻止事件冒泡
                        e.stopPropagation();
                        // ✅ 通过ID删除
                        this.deleteQuestionById(questionId);
                    } else {
                        // 兼容旧数据：如果没有ID，使用索引
                        const index =
                            parseInt(
                                row.dataset.index
                            );
                        if (!isNaN(index)) {
                            e.stopPropagation();
                            this.deleteQuestion(index);
                        }
                    }
                }
            }
        };

        tbody.addEventListener(
            "click",
            this._deleteHandler
        );
    },


    // =====================================================
    // ✅ 删除单道题（通过ID）
    // =====================================================
    async deleteQuestionById(questionId) {

        if (
            !Array.isArray(this.currentQuestions) ||
            this.currentQuestions.length === 0
        ) {
            return;
        }

        // 查找题目
        const question = this.currentQuestions.find(q => q.id === questionId);
        if (!question) {
            console.warn("删除失败：未找到ID为", questionId, "的题目");
            return;
        }

        const title = question.title || question.subjects || '未命名题目';
        const type = question.title_category_name || '未知题型';
        
        if (
            !confirm(
                "确定要删除这道题吗？\n\n题型：" + type + "\n题目：" + title.substring(0, 50) + "..."
            )
        ) {
            return;
        }

        // =================================================
        // ✅ 调用后端接口删除（通过ID）
        // =================================================
        try {
            const response = await fetch(
                "/api/questions/delete-new",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ id: questionId })
                }
            );

            const result = await response.json();

            if (!result.success) {
                alert("删除失败：" + (result.message || "未知错误"));
                return;
            }

            // =================================================
            // 从数组中移除（通过ID过滤）
            // =================================================
            this.currentQuestions = this.currentQuestions.filter(q => q.id !== questionId);

            // 重新渲染
            this.render(this.currentQuestions);

            // 更新消息
            const message =
                document.getElementById(
                    "generate-message"
                );

            if (message) {
                message.textContent =
                    "✅ 已删除，剩余 " +
                    this.currentQuestions.length +
                    " 道题";
            }

            console.log(
                "已删除ID：",
                questionId,
                "剩余",
                this.currentQuestions.length,
                "道"
            );

        } catch (e) {
            console.error("删除失败：", e);
            alert("删除失败：" + e.message);
        }
    },


    // =====================================================
    // ✅ 删除单道题（通过索引，兼容旧数据）
    // =====================================================
    async deleteQuestion(index) {

        if (
            !Array.isArray(this.currentQuestions) ||
            this.currentQuestions.length === 0
        ) {
            return;
        }

        if (
            index < 0 ||
            index >= this.currentQuestions.length
        ) {
            console.warn("删除失败：索引超出范围", index);
            return;
        }

        const question = this.currentQuestions[index];
        const title = question.title || question.subjects || '未命名题目';
        const type = question.title_category_name || '未知题型';
        
        // 如果题目有ID，用ID删除
        if (question.id) {
            await this.deleteQuestionById(question.id);
            return;
        }

        if (
            !confirm(
                "确定要删除第 " +
                (index + 1) +
                " 道题吗？\n\n题型：" + type + "\n题目：" + title.substring(0, 50) + "..."
            )
        ) {
            return;
        }

        try {
            const response = await fetch(
                "/api/questions/delete-new",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ index: index })
                }
            );

            const result = await response.json();

            if (!result.success) {
                alert("删除失败：" + (result.message || "未知错误"));
                return;
            }

            this.currentQuestions.splice(index, 1);
            this.render(this.currentQuestions);

            const message =
                document.getElementById(
                    "generate-message"
                );

            if (message) {
                message.textContent =
                    "✅ 已删除，剩余 " +
                    this.currentQuestions.length +
                    " 道题";
            }

            console.log(
                "已删除第",
                index + 1,
                "道题，剩余",
                this.currentQuestions.length,
                "道"
            );

        } catch (e) {
            console.error("删除失败：", e);
            alert("删除失败：" + e.message);
        }
    },


    // =====================================================
    // AI生成题目（流式模式 - SSE）
    //
    // 每生成一道题就立即显示在页面上
    // =====================================================
    async generateStream() {

        // =================================================
        // 防止重复点击
        // =================================================
        if (this.isGenerating) {

            console.log("正在生成中，请勿重复点击");
            return;
        }


        const modelElement =
            document.getElementById(
                "ai-model"
            );


        const typeElement =
            document.getElementById(
                "question-type"
            );


        const countElement =
            document.getElementById(
                "question-count"
            );


        const status =
            document.getElementById(
                "generate-status"
            );


        const message =
            document.getElementById(
                "generate-message"
            );


        // =================================================
        // 检查配置控件
        // =================================================
        if (
            !modelElement ||
            !typeElement ||
            !countElement
        ) {

            alert(
                "出题配置控件不存在"
            );

            return;
        }


        // =================================================
        // 如果初始化时没有读取到配置
        // 再读取一次
        // =================================================
        if (!this.currentAIConfig) {

            console.log(
                "当前没有AI配置，重新读取..."
            );

            await this.loadAIConfig();

            if (!this.currentAIConfig) {

                alert(
                    "无法读取当前AI模型配置，请检查系统AI配置"
                );

                return;
            }
        }


        // =================================================
        // 获取题型
        // =================================================
        const questionType =
            typeElement.value;


        // =================================================
        // 获取数量
        // =================================================
        const count =
            Number(
                countElement.value
            );


        // =================================================
        // ✅ 获取分类（工种）信息
        // =================================================
        const deptSelect = document.getElementById("ai-dept-select");

        const selectedOption = deptSelect ? deptSelect.options[deptSelect.selectedIndex] : null;

        const deptInfo = {
            id: selectedOption ? selectedOption.value : "",
            fullName: selectedOption ? (selectedOption.dataset.fullName || "") : "",
            superiorName: selectedOption ? (selectedOption.dataset.superiorName || "") : "",
            subjectionId: selectedOption ? (selectedOption.dataset.subjectionId || "") : "",
            subjectionName: selectedOption ? (selectedOption.dataset.subjectionName || "") : ""
        };

        // =================================================
        // 数量校验
        // =================================================
        if (
            !count ||
            count < 1 ||
            count > 100
        ) {

            alert(
                "题目数量必须在1～100之间"
            );

            return;
        }


        // =================================================
        // 每次生成之前清空上一次
        // =================================================
        this.currentQuestions = [];


        // =================================================
        // 清空页面
        // =================================================
        const tbody =
            document.getElementById(
                "question-table-body"
            );

        if (tbody) {

            tbody.innerHTML = "";

        }


        // =================================================
        // 显示生成状态
        // =================================================
        if (status) {

            status.classList.remove(
                "hidden"
            );

        }

        if (message) {

            message.textContent =
                "正在生成题目... 0/" + count;

        }


        // =================================================
        // 禁用按钮
        // =================================================
        const generateBtn =
            document.getElementById(
                "generate-btn"
            );

        if (generateBtn) {

            generateBtn.disabled = true;
            generateBtn.textContent = "正在生成...";

        }


        // =================================================
        // 设置生成状态
        // =================================================
        this.isGenerating = true;


        try {

            console.log(
                "================================"
            );

            console.log(
                "开始AI生成（流式）"
            );

            console.log(
                "Provider：",
                this.currentAIConfig.provider
            );

            console.log(
                "题型：",
                questionType
            );

            console.log(
                "要求数量：",
                count
            );

            console.log(
                "分类：",
                deptInfo
            );

            console.log(
                "================================"
            );


            // =================================================
            // 调用 SSE 流式接口
            // =================================================
            const response =
                await fetch(
                    "/api/questions/generate-stream",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            question_type: questionType,
                            count: count,
                            dept: deptInfo
                        })
                    }
                );


            // =================================================
            // HTTP错误
            // =================================================
            if (!response.ok) {

                let errorMessage =
                    "AI出题失败";

                try {

                    const errorData =
                        await response.json();

                    errorMessage =
                        errorData.message ||
                        errorMessage;

                }
                catch (e) {

                    errorMessage +=
                        "，HTTP状态码：" +
                        response.status;

                }

                throw new Error(errorMessage);

            }


            // =================================================
            // 读取 SSE 流
            // =================================================
            const reader =
                response.body.getReader();

            const decoder =
                new TextDecoder();

            let buffer = "";

            while (true) {

                const { done, value } =
                    await reader.read();

                if (done) break;

                buffer +=
                    decoder.decode(value, { stream: true });

                // 按 \n\n 分割 SSE 事件
                const events =
                    buffer.split("\n\n");

                buffer =
                    events.pop() || "";

                for (const event of events) {

                    if (!event.trim()) continue;

                    const lines =
                        event.split("\n");

                    for (const line of lines) {

                        if (line.startsWith("data: ")) {

                            try {

                                const data =
                                    JSON.parse(
                                        line.slice(6)
                                    );

                                this.handleSSEEvent(
                                    data,
                                    message,
                                    tbody
                                );

                            }
                            catch (parseError) {

                                console.error(
                                    "解析SSE数据失败：",
                                    parseError,
                                    line
                                );

                            }

                        }

                    }

                }

            }


            // =================================================
            // 最终刷新一次（确保所有题目都显示了）
            // =================================================
            this.render(this.currentQuestions);

        }
        catch (e) {

            console.error(
                "AI出题失败：",
                e
            );

            this.currentQuestions = [];

            if (tbody) {

                tbody.innerHTML = "";

            }

            if (message) {

                message.textContent =
                    "生成失败：" +
                    (e.message || "未知错误");

            }

            alert(
                "生成失败：" +
                (e.message || "未知错误")
            );

        }
        finally {

            // =================================================
            // 恢复状态
            // =================================================
            this.isGenerating = false;

            if (status) {

                status.classList.add("hidden");

            }

            if (generateBtn) {

                generateBtn.disabled = false;
                generateBtn.textContent =
                    generateBtn.dataset.oldText ||
                    "✦ 开始AI出题";

            }

        }
    },


    // =====================================================
    // 处理 SSE 事件
    // =====================================================
    handleSSEEvent(data, message, tbody) {

        console.log("收到SSE事件：", data);

        switch (data.type) {

            case "start":

                // 开始生成
                if (message) {

                    message.textContent =
                        "正在生成题目... 0/" +
                        (data.total || "?");

                }

                break;


            case "progress":

                // 进度更新
                if (message) {

                    message.textContent =
                        "正在生成题目... " +
                        (data.success || 0) +
                        "/" +
                        (data.total || "?");

                }

                break;


            case "question":

                // 收到一道新题，立即显示
                if (data.question) {

                    // 追加到当前列表
                    this.currentQuestions.push(
                        data.question
                    );

                    // 重新渲染
                    this.render(
                        this.currentQuestions
                    );

                    // 更新进度
                    if (message) {

                        message.textContent =
                            "已生成 " +
                            (data.index || this.currentQuestions.length) +
                            "/" +
                            (data.total || "?") +
                            " 道题";

                    }

                    console.log(
                        "收到第 " +
                        (data.index || this.currentQuestions.length) +
                        " 道题"
                    );

                }

                break;


            case "warning":

                // 警告信息
                console.warn(
                    "SSE警告：",
                    data.message
                );

                if (message) {

                    message.textContent =
                        "⚠️ " + data.message;

                }

                break;


            case "end":

                // 生成完成
                if (message) {

                    const total =
                        data.total ||
                        this.currentQuestions.length;

                    message.textContent =
                        "✅ 生成完成，共 " +
                        total +
                        " 道题";

                }

                // 如果 data.questions 存在，用它覆盖
                if (
                    data.questions &&
                    Array.isArray(data.questions) &&
                    data.questions.length > 0
                ) {

                    this.currentQuestions =
                        data.questions;

                    this.render(
                        this.currentQuestions
                    );

                }

                console.log(
                    "生成完成，共 " +
                    this.currentQuestions.length +
                    " 道题"
                );

                break;


            case "error":

                // 错误
                console.error(
                    "SSE错误：",
                    data.message
                );

                if (message) {

                    message.textContent =
                        "❌ 错误：" + data.message;

                }

                throw new Error(data.message);

                break;


            default:

                console.log(
                    "未知SSE事件类型：",
                    data.type,
                    data
                );

                break;

        }

    },


    // =====================================================
    // ✅ 渲染题目（已加入删除按钮，并在渲染后重新绑定删除事件）
    // =====================================================
    render(list) {

        const tbody =
            document.getElementById(
                "question-table-body"
            );

        if (!tbody) {

            console.error(
                "没有找到 question-table-body"
            );

            return;
        }


        if (
            !Array.isArray(list) ||
            list.length === 0
        ) {

            tbody.innerHTML = `

                <tr>
                    <td
                        colspan="11"
                        style="
                            text-align:center;
                            padding:40px;
                            color:#94a3b8;
                        "
                    >
                        暂无题目
                    </td>
                </tr>

            `;

            // 重新绑定删除事件
            this.bindDeleteEvents();
            return;
        }


        // =================================================
        // 使用 DocumentFragment 提高性能
        // =================================================
        const fragment =
            document.createDocumentFragment();

        list.forEach((item, index) => {

            const tr =
                document.createElement("tr");

            // 存储索引和ID到 data 属性，方便删除
            tr.dataset.index = index;
            tr.dataset.id = item.id || '';  // ✅ 存储ID

            tr.innerHTML = `

                <td>${index + 1}</td>

                <td class="question-title">
                    ${item.title || item.subjects || ""}
                </td>

                <td>${item.plan_a || ""}</td>
                <td>${item.plan_b || ""}</td>
                <td>${item.plan_c || ""}</td>
                <td>${item.plan_d || ""}</td>
                <td>${item.plan_e || ""}</td>
                <td>${item.plan_f || ""}</td>
                <td>${item.answer || ""}</td>
                <td>${item.analysis || ""}</td>
                <td>
                    <button 
                        class="btn-delete-row" 
                        data-index="${index}"
                        data-id="${item.id || ''}"
                        title="删除此题"
                    >
                        删除
                    </button>
                </td>

            `;

            fragment.appendChild(tr);

        });

        // 替换整个 tbody 内容
        tbody.innerHTML = "";
        tbody.appendChild(fragment);

        // =================================================
        // ✅ 重新绑定删除事件
        // =================================================
        this.bindDeleteEvents();

    },


    // =====================================================
    // 导出Excel
    // =====================================================
    async exportExcel() {

        const btn =
            document.getElementById(
                "export-btn"
            );


        try {

            // =================================================
            // 检查题目
            // =================================================
            if (
                !Array.isArray(
                    this.currentQuestions
                ) ||
                this.currentQuestions.length === 0
            ) {

                alert(
                    "当前没有可导出的题目，请先生成题目。"
                );

                return;
            }


            // =================================================
            // 按钮状态
            // =================================================
            if (btn) {

                btn.disabled = true;
                btn.textContent = "正在导出...";

            }


            console.log(
                "开始导出Excel"
            );

            console.log(
                "本次导出题目数量：",
                this.currentQuestions.length
            );


            // =================================================
            // 调用原来的导出接口
            // =================================================
            const response =
                await fetch(
                    "/api/questions/export",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            questions: this.currentQuestions
                        })
                    }
                );


            // =================================================
            // HTTP错误
            // =================================================
            if (!response.ok) {

                let errorMessage =
                    "Excel导出失败";

                try {

                    const errorData =
                        await response.json();

                    errorMessage =
                        errorData.message ||
                        errorMessage;

                }
                catch (jsonError) {

                    errorMessage +=
                        "，HTTP状态码：" +
                        response.status;

                }

                throw new Error(errorMessage);

            }


            // =================================================
            // 获取Excel
            // =================================================
            const blob =
                await response.blob();

            if (!blob || blob.size === 0) {

                throw new Error(
                    "导出的Excel文件为空"
                );

            }


            console.log(
                "Excel文件大小：",
                blob.size,
                "bytes"
            );


            // =================================================
            // 创建下载
            // =================================================
            const url =
                window.URL.createObjectURL(blob);

            const a =
                document.createElement("a");

            a.href = url;
            a.download = "AI生成题目.xlsx";

            document.body.appendChild(a);
            a.click();
            a.remove();

            window.URL.revokeObjectURL(url);


            console.log(
                "Excel导出成功"
            );

            alert(
                "Excel导出成功，共 " +
                this.currentQuestions.length +
                " 道题。"
            );

        }
        catch (e) {

            console.error(
                "Excel导出失败：",
                e
            );

            alert(
                "导出失败：" +
                (e.message || "未知错误")
            );

        }
        finally {

            if (btn) {

                btn.disabled = false;
                btn.textContent = "↓ 导出Excel";

            }

        }
    }
};


// =========================================================
// 页面初始化
// =========================================================
if (
    document.readyState === "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        () => {

            AIQuestion.init();

        }
    );

}
else {

    AIQuestion.init();

}


// =========================================================
// 暴露给全局
// =========================================================
window.AIQuestion = AIQuestion;