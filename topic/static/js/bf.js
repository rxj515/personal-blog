// =========================================================
// app.js
// 通用法规 AI 系统前端
// =========================================================


// =========================================================
// 页面标题
// =========================================================

const PAGE_INFO = {

    home: {
        title: "首页",
        description: "通用法规 AI 智能题库系统"
    },

    knowledge: {
        title: "法规知识库",
        description: "查看和更新法规知识库"
    },

    generate: {
        title: "AI 智能出题",
        description: "根据法规知识库自动生成考试题目"
    },

    questions: {
        title: "我的题库",
        description: "查看已经生成的题目"
    },

    settings: {
        title: "系统设置",
        description: "查看系统运行配置"
    }

};


// =========================================================
// 全局数据
// =========================================================

// 本次最新生成的题目
window.latestGeneratedQuestions = [];

// 当前整个题库
window.questionBankQuestions = [];


// =========================================================
// AI模型显示同步
// =========================================================
//
// 功能：
//
// 1. Ollama
//    顶部：Ollama | Qwen3:8B
//    首页：Qwen3:8B
//
// 2. DeepSeek
//    顶部：DeepSeek
//    首页：DeepSeek
//
// 3. OpenAI
//    顶部：OpenAI
//    首页：OpenAI
//
// 4. 自定义AI
//    顶部：自定义AI
//    首页：自定义AI
//
// 注意：
//
// 这个函数只负责“页面显示”。
// 真正调用哪个AI由后端 ai_client.py 决定。
// =========================================================

function updateModelDisplay() {

    const modelSelect =
        document.getElementById(
            "modelSelect"
        );


    // -----------------------------------------------------
    // 获取当前选择的模型
    // -----------------------------------------------------

    const model =
        modelSelect
            ? modelSelect.value
            : "ollama";


    // -----------------------------------------------------
    // 获取顶部显示元素
    // -----------------------------------------------------

    const topModelName =
        document.getElementById(
            "topModelName"
        );

    const topModelDivider =
        document.getElementById(
            "topModelDivider"
        );

    const topModelVersion =
        document.getElementById(
            "topModelVersion"
        );


    // -----------------------------------------------------
    // 获取首页模型显示元素
    // -----------------------------------------------------

    const homeModelName =
        document.getElementById(
            "homeModelName"
        );


    // =====================================================
    // Ollama
    // =====================================================

    if (model === "ollama") {

        if (topModelName) {

            topModelName.innerText =
                "Ollama";

        }


        if (topModelDivider) {

            topModelDivider.style.display =
                "";

        }


        if (topModelVersion) {

            topModelVersion.innerText =
                "Qwen3:8B";

        }


        if (homeModelName) {

            homeModelName.innerText =
                "Qwen3:8B";

        }

        return;
    }


    // =====================================================
    // DeepSeek
    // =====================================================

    if (model === "deepseek") {

        if (topModelName) {

            topModelName.innerText =
                "DeepSeek";

        }


        if (topModelDivider) {

            topModelDivider.style.display =
                "none";

        }


        if (topModelVersion) {

            topModelVersion.innerText =
                "";

        }


        if (homeModelName) {

            homeModelName.innerText =
                "DeepSeek";

        }

        return;
    }


    // =====================================================
    // OpenAI
    // =====================================================

    if (model === "openai") {

        if (topModelName) {

            topModelName.innerText =
                "OpenAI";

        }


        if (topModelDivider) {

            topModelDivider.style.display =
                "none";

        }


        if (topModelVersion) {

            topModelVersion.innerText =
                "";

        }


        if (homeModelName) {

            homeModelName.innerText =
                "OpenAI";

        }

        return;
    }


    // =====================================================
    // 自定义AI
    // =====================================================

    if (model === "custom") {

        if (topModelName) {

            topModelName.innerText =
                "自定义AI";

        }


        if (topModelDivider) {

            topModelDivider.style.display =
                "none";

        }


        if (topModelVersion) {

            topModelVersion.innerText =
                "";

        }


        if (homeModelName) {

            homeModelName.innerText =
                "自定义AI";

        }

        return;
    }

}


// =========================================================
// 初始化AI模型选择器
// =========================================================

function initModelSelector() {

    const modelSelect =
        document.getElementById(
            "modelSelect"
        );


    // -----------------------------------------------------
    // 如果页面没有模型选择框
    // -----------------------------------------------------

    if (!modelSelect) {
        return;
    }


    // -----------------------------------------------------
    // 监听模型切换
    // -----------------------------------------------------

    modelSelect.addEventListener(
        "change",
        function() {

            updateModelDisplay();

        }
    );


    // -----------------------------------------------------
    // 页面第一次打开时同步显示
    // -----------------------------------------------------

    updateModelDisplay();

}


// =========================================================
// 页面切换
// =========================================================

function switchPage(pageName) {


    // -----------------------------------------------------
    // 隐藏所有页面
    // -----------------------------------------------------

    document
        .querySelectorAll(".page")
        .forEach(function(page) {

            page.classList.remove(
                "active-page"
            );

        });


    // -----------------------------------------------------
    // 显示目标页面
    // -----------------------------------------------------

    const target =
        document.getElementById(
            "page-" + pageName
        );


    if (target) {

        target.classList.add(
            "active-page"
        );

    }


    // -----------------------------------------------------
    // 更新左侧菜单
    // -----------------------------------------------------

    document
        .querySelectorAll(".menu-item")
        .forEach(function(item) {

            item.classList.remove(
                "active"
            );

        });


    const activeMenu =
        document.querySelector(
            `.menu-item[data-page="${pageName}"]`
        );


    if (activeMenu) {

        activeMenu.classList.add(
            "active"
        );

    }


    // -----------------------------------------------------
    // 更新顶部标题
    // -----------------------------------------------------

    const info =
        PAGE_INFO[pageName];


    if (info) {

        const pageTitle =
            document.getElementById(
                "pageTitle"
            );

        const pageDescription =
            document.getElementById(
                "pageDescription"
            );


        if (pageTitle) {

            pageTitle.innerText =
                info.title;

        }


        if (pageDescription) {

            pageDescription.innerText =
                info.description;

        }

    }


    // -----------------------------------------------------
    // 进入我的题库
    // -----------------------------------------------------

    if (pageName === "questions") {

        viewQuestions();

    }


    // -----------------------------------------------------
    // 进入系统设置
    // -----------------------------------------------------

    if (pageName === "settings") {

        loadConfig();

    }

}


// =========================================================
// 更新法规知识库
// =========================================================

async function loadKnowledge() {

    const button =
        document.getElementById(
            "knowledgeBtn"
        );


    if (button) {

        button.disabled = true;

        button.innerText =
            "正在更新……";

    }


    const container =
        document.getElementById(
            "knowledgeContainer"
        );


    if (container) {

        container.innerHTML = `
            <div class="empty-state">
                正在更新法规知识库，请稍候……
            </div>
        `;

    }


    try {


        // -------------------------------------------------
        // 更新知识库
        // -------------------------------------------------

        const updateResponse =
            await fetch(
                "/api/knowledge/update",
                {
                    method: "POST"
                }
            );


        const updateData =
            await updateResponse.json();


        if (!updateResponse.ok) {

            throw new Error(
                updateData.message ||
                "法规知识库更新失败"
            );

        }


        if (!updateData.success) {

            throw new Error(
                updateData.message ||
                "法规知识库更新失败"
            );

        }


        // -------------------------------------------------
        // 读取知识库
        // -------------------------------------------------

        const response =
            await fetch(
                "/api/knowledge/data"
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "读取法规知识库失败"
            );

        }


        if (!data.success) {

            throw new Error(
                data.message ||
                "读取法规知识库失败"
            );

        }


        // -------------------------------------------------
        // 更新首页法规数量
        // -------------------------------------------------

        const homeKnowledgeCount =
            document.getElementById(
                "homeKnowledgeCount"
            );


        if (homeKnowledgeCount) {

            homeKnowledgeCount.innerText =
                data.count;

        }


        // -------------------------------------------------
        // 显示法规表格
        // -------------------------------------------------

        renderKnowledgeTable(
            data.data
        );


    } catch (error) {

        console.error(
            "法规知识库更新失败：",
            error
        );


        if (container) {

            container.innerHTML = `
                <div class="empty-state">
                    法规知识库更新失败：
                    ${escapeHtml(
                        error.message
                    )}
                </div>
            `;

        }


    } finally {

        if (button) {

            button.disabled = false;

            button.innerText =
                "🔄 更新法规知识库";

        }

    }

}


// =========================================================
// AI生成题目
// =========================================================

async function loadQuestions() {

    const button =
        document.getElementById(
            "questionBtn"
        );


    // -----------------------------------------------------
    // 获取模型
    // -----------------------------------------------------

    const modelElement =
        document.getElementById(
            "modelSelect"
        );


    const model =
        modelElement
            ? modelElement.value
            : "ollama";


    // -----------------------------------------------------
    // 获取题型
    // -----------------------------------------------------

    const typeElement =
        document.querySelector(
            'input[name="questionType"]:checked'
        );


    const questionType =
        typeElement
            ? typeElement.value
            : "单选题";


    // -----------------------------------------------------
    // 获取数量
    // -----------------------------------------------------

    const countElement =
        document.getElementById(
            "questionCount"
        );


    const count =
        countElement
            ? parseInt(
                countElement.value
            )
            : 0;


    // -----------------------------------------------------
    // 检查数量
    // -----------------------------------------------------

    if (!count || count < 1) {

        alert(
            "请输入正确的题目数量"
        );

        return;

    }


    if (count > 100) {

        alert(
            "一次最多生成100道题"
        );

        return;

    }


    // -----------------------------------------------------
    // 按钮状态
    // -----------------------------------------------------

    if (button) {

        button.disabled = true;

        button.innerText =
            "正在生成……";

    }


    // -----------------------------------------------------
    // 显示生成状态
    // -----------------------------------------------------

    const status =
        document.getElementById(
            "generateStatus"
        );


    if (status) {

        status.classList.remove(
            "hidden"
        );

        status.classList.remove(
            "success"
        );

        status.classList.remove(
            "error"
        );


        status.innerText =
            `AI正在使用 ${getModelDisplayName(model)} 生成 ${count} 道${questionType}，请稍候……`;

    }


    // -----------------------------------------------------
    // 隐藏上一次结果
    // -----------------------------------------------------

    const latestCard =
        document.getElementById(
            "latestQuestionsCard"
        );


    if (latestCard) {

        latestCard.classList.add(
            "hidden"
        );

    }


    try {


        // -------------------------------------------------
        // 调用后端
        // -------------------------------------------------

        const response =
            await fetch(
                "/api/questions/generate",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        model:
                            model,

                        question_type:
                            questionType,

                        count:
                            count

                    })

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "服务器请求失败"
            );

        }


        if (!data.success) {

            throw new Error(
                data.message ||
                "AI出题失败"
            );

        }


        // -------------------------------------------------
        // 获取本次生成的题目
        // -------------------------------------------------

        let latestQuestions =
            data.data ||
            data.questions ||
            [];


        // -------------------------------------------------
        // 如果后端没有直接返回题目
        // 就重新读取题库
        // -------------------------------------------------

        if (
            !Array.isArray(
                latestQuestions
            ) ||
            latestQuestions.length === 0
        ) {

            const questionResponse =
                await fetch(
                    "/api/questions/data"
                );


            const questionData =
                await questionResponse.json();


            if (
                questionData.success &&
                Array.isArray(
                    questionData.data
                )
            ) {

                latestQuestions =
                    questionData.data.slice(
                        -count
                    );

            }

        }


        // -------------------------------------------------
        // 确保是数组
        // -------------------------------------------------

        if (
            !Array.isArray(
                latestQuestions
            )
        ) {

            latestQuestions = [];

        }


        // -------------------------------------------------
        // 保存本次生成结果
        // -------------------------------------------------

        window.latestGeneratedQuestions =
            latestQuestions;


        // -------------------------------------------------
        // 同时更新当前题库
        // -------------------------------------------------

        try {

            const questionResponse =
                await fetch(
                    "/api/questions/data"
                );


            const questionData =
                await questionResponse.json();


            if (
                questionData.success &&
                Array.isArray(
                    questionData.data
                )
            ) {

                window.questionBankQuestions =
                    questionData.data;

            }

        } catch (e) {

            console.log(
                "刷新题库缓存失败：",
                e
            );

        }


        // -------------------------------------------------
        // 更新首页题目数量
        // -------------------------------------------------

        const totalCount =
            data.total_count !== undefined
                ? data.total_count
                : data.count !== undefined
                    ? data.count
                    : window.questionBankQuestions.length;


        const homeQuestionCount =
            document.getElementById(
                "homeQuestionCount"
            );


        if (homeQuestionCount) {

            homeQuestionCount.innerText =
                totalCount;

        }


        const questionCountDisplay =
            document.getElementById(
                "questionCountDisplay"
            );


        if (questionCountDisplay) {

            questionCountDisplay.innerText =
                totalCount;

        }


        // -------------------------------------------------
        // 生成成功
        // -------------------------------------------------

        if (status) {

            status.classList.add(
                "success"
            );

        }


        const realCount =
            latestQuestions.length > 0
                ? latestQuestions.length
                : count;


        if (status) {

            status.innerText =
                `生成完成，共生成 ${realCount} 道${questionType}`;

        }


        // -------------------------------------------------
        // 显示最新生成题目
        // -------------------------------------------------

        if (
            Array.isArray(
                latestQuestions
            ) &&
            latestQuestions.length > 0
        ) {

            renderLatestQuestionTable(
                latestQuestions
            );


            const latestQuestionSubtitle =
                document.getElementById(
                    "latestQuestionSubtitle"
                );


            if (latestQuestionSubtitle) {

                latestQuestionSubtitle.innerText =
                    `本次使用 ${getModelDisplayName(model)}，共生成 ${latestQuestions.length} 道${questionType}`;

            }


            if (latestCard) {

                latestCard.classList.remove(
                    "hidden"
                );

            }

        } else {

            const latestQuestionContainer =
                document.getElementById(
                    "latestQuestionContainer"
                );


            if (latestQuestionContainer) {

                latestQuestionContainer.innerHTML = `
                    <div class="empty-state">

                        题目已经生成，但后端没有返回题目数据。

                        <br>

                        请点击“我的题库”查看。

                    </div>
                `;

            }


            if (latestCard) {

                latestCard.classList.remove(
                    "hidden"
                );

            }

        }


        // -------------------------------------------------
        // 页面滚动到最新题目
        // -------------------------------------------------

        if (latestCard) {

            setTimeout(
                function() {

                    latestCard.scrollIntoView({

                        behavior:
                            "smooth",

                        block:
                            "start"

                    });

                },
                100
            );

        }


    } catch (error) {

        console.error(
            "AI出题失败：",
            error
        );


        if (status) {

            status.classList.add(
                "error"
            );


            status.innerText =
                "AI出题失败：" +
                error.message;

        }


    } finally {

        if (button) {

            button.disabled = false;

            button.innerText =
                "🚀 开始生成题目";

        }

    }

}


// =========================================================
// 获取模型显示名称
// =========================================================

function getModelDisplayName(model) {

    if (model === "ollama") {

        return "Ollama | Qwen3:8B";

    }

    if (model === "deepseek") {

        return "DeepSeek";

    }

    if (model === "openai") {

        return "OpenAI";

    }

    if (model === "custom") {

        return "自定义AI";

    }

    return model || "Ollama";

}


// =========================================================
// 导出最新生成题目
// =========================================================

async function exportQuestions() {

    const button =
        document.getElementById(
            "exportQuestionBtn"
        );


    if (!button) {
        return;
    }


    button.disabled = true;

    button.innerText =
        "正在导出……";


    try {


        // -------------------------------------------------
        // 优先使用本次生成的数据
        // -------------------------------------------------

        let questions =
            window.latestGeneratedQuestions || [];


        // -------------------------------------------------
        // 如果没有，就读取题库
        // -------------------------------------------------

        if (
            !Array.isArray(
                questions
            ) ||
            questions.length === 0
        ) {

            const response =
                await fetch(
                    "/api/questions/data"
                );


            const data =
                await response.json();


            if (
                !data.success ||
                !Array.isArray(
                    data.data
                )
            ) {

                throw new Error(
                    "没有可导出的题目"
                );

            }


            questions =
                data.data;

        }


        // -------------------------------------------------
        // 再次检查
        // -------------------------------------------------

        if (
            questions.length === 0
        ) {

            throw new Error(
                "没有可导出的题目"
            );

        }


        // -------------------------------------------------
        // 调用后端 Excel 导出
        // -------------------------------------------------

        const response =
            await fetch(
                "/api/questions/export",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        questions:
                            questions

                    })

                }
            );


        if (!response.ok) {

            let message =
                "Excel导出失败";


            try {

                const errorData =
                    await response.json();


                message =
                    errorData.message ||
                    message;

            } catch (e) {

                // 忽略 JSON 解析错误

            }


            throw new Error(
                message
            );

        }


        // -------------------------------------------------
        // 获取 Excel 文件
        // -------------------------------------------------

        const blob =
            await response.blob();


        const url =
            window.URL.createObjectURL(
                blob
            );


        const a =
            document.createElement(
                "a"
            );


        a.href =
            url;


        // -------------------------------------------------
        // 获取服务器返回的文件名
        // -------------------------------------------------

        const disposition =
            response.headers.get(
                "Content-Disposition"
            );


        let filename =
            "AI生成题目.xlsx";


        if (disposition) {

            const match =
                disposition.match(
                    /filename\*=UTF-8''([^;]+)/
                );


            if (match) {

                filename =
                    decodeURIComponent(
                        match[1]
                    );

            }

        }


        // -------------------------------------------------
        // 下载
        // -------------------------------------------------

        a.download =
            filename;


        document.body.appendChild(
            a
        );


        a.click();


        a.remove();


        window.URL.revokeObjectURL(
            url
        );


        // -------------------------------------------------
        // 成功提示
        // -------------------------------------------------

        button.innerText =
            "✅ 导出成功";


        setTimeout(
            function() {

                button.innerText =
                    "📥 导出 Excel";

            },
            1500
        );


    } catch (error) {

        console.error(
            "导出Excel失败：",
            error
        );


        alert(
            "导出Excel失败：" +
            error.message
        );


        button.innerText =
            "📥 导出 Excel";


    } finally {

        button.disabled =
            false;

    }

}


// =========================================================
// 导出我的题库
// =========================================================

async function exportQuestionLibrary() {

    const button =
        document.getElementById(
            "exportLibraryBtn"
        );


    if (!button) {

        console.error(
            "找不到 exportLibraryBtn 按钮"
        );

        return;

    }


    button.disabled = true;

    button.innerText =
        "正在导出……";


    try {


        // -------------------------------------------------
        // 读取当前题库
        // -------------------------------------------------

        const response =
            await fetch(
                "/api/questions/data"
            );


        if (!response.ok) {

            throw new Error(
                "读取题库失败，HTTP状态码：" +
                response.status
            );

        }


        const data =
            await response.json();


        // -------------------------------------------------
        // 判断题库数据
        // -------------------------------------------------

        if (
            !data.success ||
            !Array.isArray(data.data)
        ) {

            throw new Error(
                data.message ||
                "当前没有可导出的题目"
            );

        }


        const questions =
            data.data;


        if (
            questions.length === 0
        ) {

            throw new Error(
                "当前题库没有题目"
            );

        }


        console.log(
            "准备导出题目：",
            questions.length,
            "道"
        );


        // -------------------------------------------------
        // 调用后端 Excel 导出接口
        // -------------------------------------------------

        const exportResponse =
            await fetch(
                "/api/questions/export",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        questions:
                            questions

                    })

                }
            );


        // -------------------------------------------------
        // 检查后端返回
        // -------------------------------------------------

        if (!exportResponse.ok) {

            let message =
                "Excel导出失败";


            try {

                const errorData =
                    await exportResponse.json();


                message =
                    errorData.message ||
                    message;

            } catch (e) {

                console.error(
                    "解析错误信息失败：",
                    e
                );

            }


            throw new Error(
                message
            );

        }


        // -------------------------------------------------
        // 获取Excel文件
        // -------------------------------------------------

        const blob =
            await exportResponse.blob();


        if (
            !blob ||
            blob.size === 0
        ) {

            throw new Error(
                "后端返回的Excel文件为空"
            );

        }


        // -------------------------------------------------
        // 创建下载
        // -------------------------------------------------

        const url =
            window.URL.createObjectURL(
                blob
            );


        const a =
            document.createElement(
                "a"
            );


        a.href =
            url;


        // -------------------------------------------------
        // 获取文件名
        // -------------------------------------------------

        let filename =
            "我的题库.xlsx";


        const disposition =
            exportResponse.headers.get(
                "Content-Disposition"
            );


        if (disposition) {

            const utf8Match =
                disposition.match(
                    /filename\*=UTF-8''([^;]+)/i
                );


            if (utf8Match) {

                filename =
                    decodeURIComponent(
                        utf8Match[1]
                    );

            } else {

                const normalMatch =
                    disposition.match(
                        /filename="?([^"]+)"?/i
                    );


                if (normalMatch) {

                    filename =
                        normalMatch[1];

                }

            }

        }


        a.download =
            filename;


        document.body.appendChild(
            a
        );


        a.click();


        a.remove();


        window.URL.revokeObjectURL(
            url
        );


        // -------------------------------------------------
        // 成功提示
        // -------------------------------------------------

        button.innerText =
            "✅ 导出成功";


        setTimeout(
            function() {

                button.innerText =
                    "📥 导出 Excel";

            },
            1500
        );


    } catch (error) {

        console.error(
            "题库导出失败：",
            error
        );


        alert(
            "导出Excel失败：\n" +
            error.message
        );


        button.innerText =
            "📥 导出 Excel";


    } finally {

        button.disabled =
            false;

    }

}


// =========================================================
// 导出我的整个题库
// =========================================================

async function exportLibraryQuestions() {

    const button =
        document.getElementById(
            "exportLibraryQuestionBtn"
        );


    if (!button) {
        return;
    }


    button.disabled = true;

    button.innerText =
        "正在导出……";


    try {


        // -------------------------------------------------
        // 优先使用当前已经读取的整个题库
        // -------------------------------------------------

        let questions =
            window.questionBankQuestions || [];


        // -------------------------------------------------
        // 如果浏览器里面没有
        // 重新从后端读取完整题库
        // -------------------------------------------------

        if (
            !Array.isArray(
                questions
            ) ||
            questions.length === 0
        ) {

            const response =
                await fetch(
                    "/api/questions/data"
                );


            const data =
                await response.json();


            if (
                !data.success ||
                !Array.isArray(
                    data.data
                )
            ) {

                throw new Error(
                    "当前题库没有题目"
                );

            }


            questions =
                data.data;


            // 保存完整题库
            window.questionBankQuestions =
                questions;

        }


        // -------------------------------------------------
        // 检查题库是否为空
        // -------------------------------------------------

        if (
            questions.length === 0
        ) {

            throw new Error(
                "当前题库没有可导出的题目"
            );

        }


        // -------------------------------------------------
        // 调用后端 Excel 导出接口
        // -------------------------------------------------

        const response =
            await fetch(
                "/api/questions/export",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        questions:
                            questions

                    })

                }
            );


        // -------------------------------------------------
        // 检查服务器
        // -------------------------------------------------

        if (!response.ok) {

            let message =
                "Excel导出失败";


            try {

                const errorData =
                    await response.json();


                message =
                    errorData.message ||
                    message;

            } catch (e) {

                // 忽略 JSON 解析错误

            }


            throw new Error(
                message
            );

        }


        // -------------------------------------------------
        // 获取 Excel 文件
        // -------------------------------------------------

        const blob =
            await response.blob();


        const url =
            window.URL.createObjectURL(
                blob
            );


        const a =
            document.createElement(
                "a"
            );


        a.href =
            url;


        // -------------------------------------------------
        // 获取服务器文件名
        // -------------------------------------------------

        const disposition =
            response.headers.get(
                "Content-Disposition"
            );


        let filename =
            "我的题库.xlsx";


        if (disposition) {

            const match =
                disposition.match(
                    /filename\*=UTF-8''([^;]+)/
                );


            if (match) {

                filename =
                    decodeURIComponent(
                        match[1]
                    );

            }

        }


        // -------------------------------------------------
        // 下载文件
        // -------------------------------------------------

        a.download =
            filename;


        document.body.appendChild(
            a
        );


        a.click();


        a.remove();


        window.URL.revokeObjectURL(
            url
        );


        // -------------------------------------------------
        // 导出成功
        // -------------------------------------------------

        button.innerText =
            "✅ 导出成功";


        setTimeout(
            function() {

                button.innerText =
                    "📥 导出 Excel";

            },
            1500
        );


    } catch (error) {

        console.error(
            "题库导出失败：",
            error
        );


        alert(
            "导出Excel失败：" +
            error.message
        );


        button.innerText =
            "📥 导出 Excel";


    } finally {

        button.disabled =
            false;

    }

}


// =========================================================
// 查看已有题目
// =========================================================

async function viewQuestions() {

    const button =
        document.getElementById(
            "viewQuestionBtn"
        );


    if (button) {

        button.disabled = true;

        button.innerText =
            "正在读取……";

    }


    const container =
        document.getElementById(
            "questionContainer"
        );


    if (container) {

        container.innerHTML = `
            <div class="empty-state">
                正在读取已有题库……
            </div>
        `;

    }


    try {

        const response =
            await fetch(
                "/api/questions/data"
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "读取题库失败"
            );

        }


        if (!data.success) {

            if (container) {

                container.innerHTML = `
                    <div class="empty-state">
                        暂无已有题库
                    </div>
                `;

            }


            const homeQuestionCount =
                document.getElementById(
                    "homeQuestionCount"
                );


            if (homeQuestionCount) {

                homeQuestionCount.innerText =
                    "0";

            }


            const questionCountDisplay =
                document.getElementById(
                    "questionCountDisplay"
                );


            if (questionCountDisplay) {

                questionCountDisplay.innerText =
                    "0";

            }


            // 清空题库缓存
            window.questionBankQuestions =
                [];


            return;

        }


        // -------------------------------------------------
        // 保存整个题库
        // -------------------------------------------------

        window.questionBankQuestions =
            Array.isArray(data.data)
                ? data.data
                : [];


        // -------------------------------------------------
        // 更新首页数量
        // -------------------------------------------------

        const homeQuestionCount =
            document.getElementById(
                "homeQuestionCount"
            );


        if (homeQuestionCount) {

            homeQuestionCount.innerText =
                data.count;

        }


        // -------------------------------------------------
        // 更新题库页面数量
        // -------------------------------------------------

        const questionCountDisplay =
            document.getElementById(
                "questionCountDisplay"
            );


        if (questionCountDisplay) {

            questionCountDisplay.innerText =
                data.count;

        }


        // -------------------------------------------------
        // 显示题库
        // -------------------------------------------------

        renderQuestionTable(
            window.questionBankQuestions
        );


    } catch (error) {

        console.error(
            "读取题库失败：",
            error
        );


        if (container) {

            container.innerHTML = `
                <div class="empty-state">
                    读取题库失败：
                    ${escapeHtml(
                        error.message
                    )}
                </div>
            `;

        }

    } finally {

        if (button) {

            button.disabled = false;

            button.innerText =
                "🔄 刷新题库";

        }

    }

}


// =========================================================
// 法规表格
// =========================================================

function renderKnowledgeTable(data) {

    const container =
        document.getElementById(
            "knowledgeContainer"
        );


    if (!container) {
        return;
    }


    if (
        !data ||
        data.length === 0
    ) {

        container.innerHTML = `
            <div class="empty-state">
                法规知识库没有数据
            </div>
        `;

        return;

    }


    let html = `

        <table>

            <thead>

                <tr>

                    <th>序号</th>

                    <th>法规名称</th>

                    <th>条文</th>

                    <th>内容</th>

                </tr>

            </thead>

            <tbody>

    `;


    data.forEach(
        function(item, index) {

            html += `

                <tr>

                    <td>
                        ${index + 1}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.law_name || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.article || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.content || ""
                        )}
                    </td>

                </tr>

            `;

        }
    );


    html += `

            </tbody>

        </table>

    `;


    container.innerHTML =
        html;

}


// =========================================================
// 最新生成题目表格
// =========================================================

function renderLatestQuestionTable(data) {

    const container =
        document.getElementById(
            "latestQuestionContainer"
        );


    if (!container) {
        return;
    }


    if (
        !data ||
        data.length === 0
    ) {

        container.innerHTML = `
            <div class="empty-state">
                暂无生成结果
            </div>
        `;

        return;

    }


    let html = `

        <table class="question-table">

            <thead>

                <tr>

                    <th>序号</th>

                    <th>题型</th>

                    <th>题目</th>

                    <th>A</th>

                    <th>B</th>

                    <th>C</th>

                    <th>D</th>

                    <th>E</th>

                    <th>F</th>

                    <th>解析</th>

                    <th>答案</th>

                </tr>

            </thead>

            <tbody>

    `;


    data.forEach(
        function(item, index) {

            html += `

                <tr>

                    <td>
                        ${index + 1}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.title_category_name || ""
                        )}
                    </td>

                    <td class="question-subject">
                        ${escapeHtml(
                            item.subjects || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_a || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_b || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_c || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_d || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_e || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_f || ""
                        )}
                    </td>

                    <td class="question-analysis">
                        ${escapeHtml(
                            item.analysis || ""
                        )}
                    </td>

                    <td>

                        <strong class="answer-cell">

                            ${escapeHtml(
                                item.answer || ""
                            )}

                        </strong>

                    </td>

                </tr>

            `;

        }
    );


    html += `

            </tbody>

        </table>

    `;


    container.innerHTML =
        html;

}


// =========================================================
// 我的题库表格
// =========================================================

function renderQuestionTable(data) {

    const container =
        document.getElementById(
            "questionContainer"
        );


    if (!container) {
        return;
    }


    if (
        !data ||
        data.length === 0
    ) {

        container.innerHTML = `
            <div class="empty-state">
                暂无题目
            </div>
        `;

        return;

    }


    let html = `

        <table class="question-table">

            <thead>

                <tr>

                    <th>序号</th>

                    <th>题型</th>

                    <th>题目</th>

                    <th>A</th>

                    <th>B</th>

                    <th>C</th>

                    <th>D</th>

                    <th>E</th>

                    <th>F</th>

                    <th>解析</th>

                    <th>答案</th>

                </tr>

            </thead>

            <tbody>

    `;


    data.forEach(
        function(item, index) {

            html += `

                <tr>

                    <td>
                        ${index + 1}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.title_category_name || ""
                        )}
                    </td>

                    <td class="question-subject">
                        ${escapeHtml(
                            item.subjects || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_a || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_b || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_c || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_d || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_e || ""
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            item.plan_f || ""
                        )}
                    </td>

                    <td class="question-analysis">
                        ${escapeHtml(
                            item.analysis || ""
                        )}
                    </td>

                    <td>

                        <strong class="answer-cell">

                            ${escapeHtml(
                                item.answer || ""
                            )}

                        </strong>

                    </td>

                </tr>

            `;

        }
    );


    html += `

            </tbody>

        </table>

    `;


    container.innerHTML =
        html;

}


// =========================================================
// 系统配置
// =========================================================

async function loadConfig() {

    const container =
        document.getElementById(
            "configContainer"
        );


    if (!container) {
        return;
    }


    try {

        const response =
            await fetch(
                "/api/config"
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "获取系统配置失败"
            );

        }


        container.innerHTML = `

            <div class="config-item">

                <div class="config-label">
                    Python版本
                </div>

                <div class="config-value">

                    ${escapeHtml(
                        data.python || ""
                    )}

                </div>

            </div>



            <div class="config-item">

                <div class="config-label">
                    AI类型
                </div>

                <div class="config-value">

                    ${escapeHtml(
                        data.ai || ""
                    )}

                </div>

            </div>



            <div class="config-item">

                <div class="config-label">
                    AI模型
                </div>

                <div class="config-value">

                    ${escapeHtml(
                        data.model || ""
                    )}

                </div>

            </div>



            <div class="config-item">

                <div class="config-label">
                    Ollama地址
                </div>

                <div class="config-value">

                    ${escapeHtml(
                        data.ollama || ""
                    )}

                </div>

            </div>



            <div class="config-item">

                <div class="config-label">
                    项目目录
                </div>

                <div class="config-value">

                    ${escapeHtml(
                        data.project_dir || ""
                    )}

                </div>

            </div>

        `;


    } catch (error) {

        console.error(
            "获取系统配置失败：",
            error
        );


        container.innerHTML = `

            <div class="empty-state">

                获取系统配置失败：

                ${escapeHtml(
                    error.message
                )}

            </div>

        `;

    }

}


// =========================================================
// HTML安全处理
// =========================================================

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


// =========================================================
// 页面加载
// =========================================================

window.addEventListener(
    "DOMContentLoaded",
    async function() {


        // -------------------------------------------------
        // 初始化AI模型选择器
        // -------------------------------------------------

        initModelSelector();


        // -------------------------------------------------
        // 默认首页
        // -------------------------------------------------

        switchPage(
            "home"
        );


        // -------------------------------------------------
        // 自动读取题库
        // -------------------------------------------------

        try {

            const response =
                await fetch(
                    "/api/questions/data"
                );


            const data =
                await response.json();


            if (
                data.success &&
                Array.isArray(
                    data.data
                )
            ) {

                // 保存完整题库
                window.questionBankQuestions =
                    data.data;


                // 更新首页题目数量
                const homeQuestionCount =
                    document.getElementById(
                        "homeQuestionCount"
                    );


                if (homeQuestionCount) {

                    homeQuestionCount.innerText =
                        data.count;

                }


                // 更新题库页面数量
                const questionCountDisplay =
                    document.getElementById(
                        "questionCountDisplay"
                    );


                if (questionCountDisplay) {

                    questionCountDisplay.innerText =
                        data.count;

                }

            }

        } catch (error) {

            console.log(
                "暂时没有题库：",
                error
            );

        }


        // -------------------------------------------------
        // 自动读取法规数量
        // -------------------------------------------------

        try {

            const response =
                await fetch(
                    "/api/knowledge/data"
                );


            const data =
                await response.json();


            if (data.success) {

                const homeKnowledgeCount =
                    document.getElementById(
                        "homeKnowledgeCount"
                    );


                if (homeKnowledgeCount) {

                    homeKnowledgeCount.innerText =
                        data.count;

                }

            }

        } catch (error) {

            console.log(
                "暂时没有法规知识库：",
                error
            );

        }


        // -------------------------------------------------
        // 再次同步AI模型显示
        // -------------------------------------------------

        updateModelDisplay();

    }
);