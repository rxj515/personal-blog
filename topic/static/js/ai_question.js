const AIQuestion = {

    // =====================================================
    // 当前题目数据
    // =====================================================
    currentQuestions: [],


    // =====================================================
    // 当前AI配置
    // =====================================================
    currentAIConfig: null,


    // =====================================================
    // ✅ 当前使用的 PDF 名称
    // （从 localStorage 读取，仅用于展示）
    // =====================================================
    currentPDFName: "",


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

        // ✅ 加载分类（工种）下拉框
        await this.loadAiDeptList();

        // ✅ 加载当前使用的 PDF
        this.loadCurrentPDF();

        // 加载上次生成的题目（从 _new.json）
        await this.loadNewQuestions();

        // 绑定按钮
        this.bindEvent();

        // ✅ 绑定删除事件（独立）
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

        // ✅ 监听当前 PDF 变化（跨页面同步）
        window.removeEventListener(
            "storage",
            this._handlePDFChange
        );

        this._handlePDFChange =
            this._handlePDFChange.bind(this);

        window.addEventListener(
            "storage",
            this._handlePDFChange
        );

    },


    // =====================================================
    // ✅ 加载分类（工种）下拉框
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
    // ✅ 加载当前使用的 PDF（只读展示）
    //
    // 数据来源：localStorage.currentPDFName
    // 由知识库页面写入
    // =====================================================
    loadCurrentPDF() {

        const el =
            document.getElementById(
                "current-pdf-name"
            );

        if (!el) {
            return;
        }

        const pdfName =
            localStorage.getItem(
                "currentPDFName"
            ) || "";

        this.currentPDFName =
            pdfName;

        el.textContent =
            pdfName || "未选择";

        el.title =
            pdfName || "未选择";

        console.log(
            "当前使用的 PDF：",
            pdfName || "未选择"
        );
    },


    // =====================================================
    // ✅ 处理跨页面 PDF 变化
    // =====================================================
    _handlePDFChange(event) {

        if (
            !event ||
            event.key !== "currentPDFName"
        ) {
            return;
        }

        const el =
            document.getElementById(
                "current-pdf-name"
            );

        if (!el) {
            return;
        }

        const pdfName =
            event.newValue || "";

        this.currentPDFName =
            pdfName;

        el.textContent =
            pdfName || "未选择";

        el.title =
            pdfName || "未选择";

        console.log(
            "检测到 PDF 变化：",
            pdfName || "未选择"
        );
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


            const response =
                await fetch(
                    "/api/system/ai/config?t=" +
                    Date.now(),
                    {
                        method: "GET",
                        cache: "no-store"
                    }
                );


            if (!response.ok) {

                throw new Error(
                    "读取AI配置失败，HTTP状态码：" +
                    response.status
                );
            }


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


            this.currentAIConfig =
                config;


            const displayName =
                this.getAIModelDisplayName(
                    config
                );


            modelElement.textContent =
                displayName;


            modelElement.dataset.model =
                config.model;


            modelElement.dataset.provider =
                config.provider || "";


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
    // ✅ AI模型显示名称
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

        if (
            provider &&
            model
        ) {

            return displayProvider + " - " + model;
        }

        if (model) {

            return model;
        }

        return "未知模型";
    },


    // =====================================================
    // 绑定事件
    // =====================================================
    bindEvent() {

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
    // ✅ 绑定删除事件
    // =====================================================
    bindDeleteEvents() {

        const tbody =
            document.getElementById(
                "question-table-body"
            );

        if (!tbody) {
            return;
        }

        if (this._deleteHandler) {
            tbody.removeEventListener(
                "click",
                this._deleteHandler
            );
            this._deleteHandler = null;
        }

        this._deleteHandler = (e) => {
            const deleteBtn =
                e.target.closest(".btn-delete-row");

            if (deleteBtn) {
                const row =
                    deleteBtn.closest("tr");

                if (row) {
                    const questionId =
                        row.dataset.id;

                    if (questionId) {
                        e.stopPropagation();
                        this.deleteQuestionById(questionId);
                    } else {
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

            this.currentQuestions = this.currentQuestions.filter(q => q.id !== questionId);

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
    // =====================================================
    async generateStream() {

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


        const questionType =
            typeElement.value;


        const count =
            Number(
                countElement.value
            );


        const deptSelect = document.getElementById("ai-dept-select");

        const selectedOption = deptSelect ? deptSelect.options[deptSelect.selectedIndex] : null;

        const deptInfo = {
            id: selectedOption ? selectedOption.value : "",
            fullName: selectedOption ? (selectedOption.dataset.fullName || "") : "",
            superiorName: selectedOption ? (selectedOption.dataset.superiorName || "") : "",
            subjectionId: selectedOption ? (selectedOption.dataset.subjectionId || "") : "",
            subjectionName: selectedOption ? (selectedOption.dataset.subjectionName || "") : ""
        };


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


        this.currentQuestions = [];


        const tbody =
            document.getElementById(
                "question-table-body"
            );

        if (tbody) {

            tbody.innerHTML = "";

        }


        if (status) {

            status.classList.remove(
                "hidden"
            );

        }

        if (message) {

            message.textContent =
                "正在生成题目... 0/" + count;

        }


        const generateBtn =
            document.getElementById(
                "generate-btn"
            );

        if (generateBtn) {

            generateBtn.disabled = true;
            generateBtn.textContent = "正在生成...";

        }


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

                if (message) {

                    message.textContent =
                        "正在生成题目... 0/" +
                        (data.total || "?");

                }

                break;


            case "progress":

                if (message) {

                    message.textContent =
                        "正在生成题目... " +
                        (data.success || 0) +
                        "/" +
                        (data.total || "?");

                }

                break;


            case "question":

                if (data.question) {

                    this.currentQuestions.push(
                        data.question
                    );

                    this.render(
                        this.currentQuestions
                    );

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

                if (message) {

                    const total =
                        data.total ||
                        this.currentQuestions.length;

                    message.textContent =
                        "✅ 生成完成，共 " +
                        total +
                        " 道题";

                }

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
    // ✅ 渲染题目
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

            this.bindDeleteEvents();
            return;
        }


        const fragment =
            document.createDocumentFragment();

        list.forEach((item, index) => {

            const tr =
                document.createElement("tr");

            tr.dataset.index = index;
            tr.dataset.id = item.id || '';

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

        tbody.innerHTML = "";
        tbody.appendChild(fragment);

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
// ✅ 跳转到「法规知识库」页面（tab 切换）
//
// 你项目里左侧菜单是用 data-page 标识页面的：
//   <div class="menu-item" data-page="knowledge">法规知识库</div>
//
// 所以这里直接模拟点击那一项，
// 就能触发项目里完整的页面切换逻辑。
// =========================================================
function goKnowledge() {

    // 方式1：找左侧菜单里 data-page="knowledge" 的项，模拟点击
    const menuItem =
        document.querySelector(
            '.menu-item[data-page="knowledge"]'
        );

    if (menuItem) {
        menuItem.click();
        return;
    }

    // 方式2：如果项目里有全局切换函数，也可以直接调用
    if (
        typeof window.App !== 'undefined' &&
        typeof window.App.switchPage === 'function'
    ) {
        window.App.switchPage('knowledge');
        return;
    }

    // 兜底
    alert('请从左侧菜单进入「法规知识库」');
}

window.goKnowledge = goKnowledge;


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