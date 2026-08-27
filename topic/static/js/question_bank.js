/* =========================================================
 *
 * question_bank.js
 *
 * 题库管理
 *
 * ========================================================= */


const QuestionBank = {

    /* =====================================================
     * 当前全部题目
     * ===================================================== */

    questions: [],


    /* =====================================================
     * 当前筛选后的题目
     * ===================================================== */

    filteredQuestions: [],


    /* =====================================================
     * 当前页
     * ===================================================== */

    currentPage: 1,


    /* =====================================================
     * 每页数量
     * ===================================================== */

    pageSize: 10,


    /* =====================================================
     * 初始化
     * ===================================================== */

    async init() {

        console.log(
            "===================================="
        );

        console.log(
            "QuestionBank 初始化"
        );

        console.log(
            "===================================="
        );


        this.bindEvents();

        await this.loadQuestions();

    },


    /* =====================================================
     * 绑定事件
     * ===================================================== */

    bindEvents() {

        
        /* =================================================
        * ★ 新增：加载分类下拉框
        * ================================================= */
        this.loadDeptList();  // <--- 加上这一行！

        /* =================================================
         * 搜索
         * ================================================= */

        const search =
            document.getElementById(
                "question-search"
            );

        if (search) {

            search.oninput = () => {

                this.filterQuestions();

            };

        }


        /* =================================================
         * 题型筛选
         * ================================================= */

        const typeFilter =
            document.getElementById(
                "question-type-filter"
            );

        if (typeFilter) {

            typeFilter.onchange = () => {

                this.filterQuestions();

            };

        }


        /* =================================================
         * 上一页
         * ================================================= */

        const prev =
            document.getElementById(
                "question-prev"
            );

        if (prev) {

            prev.onclick = () => {

                if (this.currentPage > 1) {

                    this.currentPage--;

                    this.renderQuestions();

                }

            };

        }


        /* =================================================
         * 下一页
         * ================================================= */

        const next =
            document.getElementById(
                "question-next"
            );

        if (next) {

            next.onclick = () => {

                const totalPage =
                    Math.max(
                        1,
                        Math.ceil(
                            this.filteredQuestions.length /
                            this.pageSize
                        )
                    );


                if (
                    this.currentPage <
                    totalPage
                ) {

                    this.currentPage++;

                    this.renderQuestions();

                }

            };

        }


        /* =================================================
         * Excel 导出
         * ================================================= */

        const exportBtn =
            document.getElementById(
                "export-btn"
            );

        if (exportBtn) {

            exportBtn.onclick = () => {

                this.exportQuestions();

            };

        }


        /* =================================================
         * 导入数据库 (新增)
         * ================================================= */

        const importBtn =
            document.getElementById(
                "import-btn"
            );

        if (importBtn) {

            importBtn.onclick = () => {

                this.importQuestions();

            };

        }

    },


    /* =====================================================
     * 加载题库
     * ===================================================== */

    async loadQuestions() {

        const list =
            document.getElementById(
                "question-list"
            );


        if (!list) {

            console.error(
                "没有找到 #question-list"
            );

            return;

        }


        list.innerHTML = `

            <tr>

                <td
                    colspan="11"
                    class="empty-cell"
                >

                    正在读取题库...

                </td>

            </tr>

        `;


        try {

            console.log(
                "开始读取题库..."
            );


            const result =
                await window.AppAPI.get(
                    "/api/questions/data"
                );


            console.log(
                "题库接口返回：",
                result
            );


            if (
                !result ||
                !result.success
            ) {

                throw new Error(
                    result?.message ||
                    "读取题库失败"
                );

            }


            /* =================================================
             * 获取题目数据
             * ================================================= */

            let data = [];


            if (
                Array.isArray(
                    result.data
                )
            ) {

                data =
                    result.data;

            }

            else if (
                result.result &&
                Array.isArray(
                    result.result.data
                )
            ) {

                data =
                    result.result.data;

            }

            else if (
                result.questions &&
                Array.isArray(
                    result.questions
                )
            ) {

                data =
                    result.questions;

            }


            this.questions =
                Array.isArray(data)
                    ? data
                    : [];


            this.filteredQuestions =
                [...this.questions];


            this.currentPage = 1;


            console.log(
                "题库读取成功：",
                this.questions.length,
                "道"
            );


            this.updateTotal();


            this.renderQuestions();


        }
        catch (error) {

            console.error(
                "题库读取失败：",
                error
            );


            this.questions = [];

            this.filteredQuestions = [];


            list.innerHTML = `

                <tr>

                    <td
                        colspan="11"
                        class="empty-cell"
                    >

                        <div class="empty-state">

                            <div class="empty-icon">
                                ▦
                            </div>

                            <div class="empty-title">
                                题库读取失败
                            </div>

                            <div class="empty-text">
                                ${this.escapeHtml(
                                    error.message
                                )}
                            </div>

                        </div>

                    </td>

                </tr>

            `;


            this.updateTotal();

        }

    },


    /* =====================================================
     * 筛选题目
     * ===================================================== */

    filterQuestions() {

        const search =
            document.getElementById(
                "question-search"
            );


        const typeFilter =
            document.getElementById(
                "question-type-filter"
            );


        const keyword =
            search
                ? search.value
                    .trim()
                    .toLowerCase()
                : "";


        const type =
            typeFilter
                ? typeFilter.value
                : "";


        this.filteredQuestions =
            this.questions.filter(
                question => {


                    /* =====================================
                     * 搜索
                     * ===================================== */

                    const text =
                        JSON.stringify(
                            question
                        )
                        .toLowerCase();


                    const keywordMatch =
                        !keyword ||
                        text.includes(
                            keyword
                        );


                    /* =====================================
                     * 题型
                     * ===================================== */

                    const questionType =
                        this.getQuestionType(
                            question
                        );


                    const typeMatch =
                        !type ||
                        questionType === type;


                    return (
                        keywordMatch &&
                        typeMatch
                    );

                }
            );


        this.currentPage = 1;


        this.updateTotal();


        this.renderQuestions();

    },


    /* =====================================================
     * 获取题型
     * ===================================================== */

    getQuestionType(question) {

        return (
            question.question_type ||
            question.type ||
            question.title_category_name ||
            "未知题型"
        );

    },


    /* =====================================================
     * 获取题目内容
     * ===================================================== */

    getQuestionTitle(question) {

        return (
            question.title ||
            question.subjects ||
            question.question ||
            question.content ||
            ""
        );

    },


    /* =====================================================
     * 获取选项
     *
     * 兼容：
     *
     * plan_a
     * plan_b
     * ...
     *
     * options
     * ===================================================== */

    getOption(question, letter) {

        const key =
            "plan_" +
            letter.toLowerCase();


        /* =============================================
         * AI当前数据格式
         * ============================================= */

        if (
            question[key] !== undefined &&
            question[key] !== null
        ) {

            return String(
                question[key]
            );

        }


        /* =============================================
         * 兼容 options 数组
         * ============================================= */

        if (
            Array.isArray(
                question.options
            )
        ) {

            const index =
                letter.charCodeAt(0) -
                65;


            return (
                question.options[index] || ""
            );

        }


        /* =============================================
         * 兼容 options 对象
         * ============================================= */

        if (
            question.options &&
            typeof question.options === "object"
        ) {

            return (
                question.options[letter] ||
                question.options[
                    letter.toLowerCase()
                ] ||
                ""
            );

        }


        return "";

    },


    /* =====================================================
     * 获取答案
     * ===================================================== */

    getAnswer(question) {

        return (
            question.answer ||
            question.correct_answer ||
            question.correctAnswer ||
            ""
        );

    },


    /* =====================================================
     * 获取解析
     * ===================================================== */

    getAnalysis(question) {

        return (
            question.analysis ||
            question.explanation ||
            question.explain ||
            ""
        );

    },


    /* =====================================================
     * 更新总数
     * ===================================================== */

    updateTotal() {

        const total =
            document.getElementById(
                "question-total"
            );


        if (!total) {

            return;

        }


        total.textContent =
            `${this.filteredQuestions.length} 题`;

    },


    /* =====================================================
     * 渲染题目
     * ===================================================== */

    renderQuestions() {

        const list =
            document.getElementById(
                "question-list"
            );


        if (!list) {

            console.error(
                "没有找到 #question-list"
            );

            return;

        }


        const total =
            this.filteredQuestions.length;


        const totalPage =
            Math.max(
                1,
                Math.ceil(
                    total /
                    this.pageSize
                )
            );


        if (
            this.currentPage >
            totalPage
        ) {

            this.currentPage =
                totalPage;

        }


        const start =
            (
                this.currentPage -
                1
            ) *
            this.pageSize;


        const end =
            start +
            this.pageSize;


        const data =
            this.filteredQuestions.slice(
                start,
                end
            );


        /* =================================================
         * 更新分页
         * ================================================= */

        const pageInfo =
            document.getElementById(
                "question-page-info"
            );


        if (pageInfo) {

            pageInfo.textContent =
                `${this.currentPage} / ${totalPage}`;

        }


        const prev =
            document.getElementById(
                "question-prev"
            );


        if (prev) {

            prev.disabled =
                this.currentPage <= 1;

        }


        const next =
            document.getElementById(
                "question-next"
            );


        if (next) {

            next.disabled =
                this.currentPage >= totalPage;

        }


        /* =================================================
         * 没有数据
         * ================================================= */

        if (!data.length) {

            list.innerHTML = `

                <tr>

                    <td
                        colspan="11"
                        class="empty-cell"
                    >

                        <div class="empty-state">

                            <div class="empty-icon">
                                ▦
                            </div>

                            <div class="empty-title">
                                暂无题目
                            </div>

                            <div class="empty-text">
                                当前筛选条件下没有题目
                            </div>

                        </div>

                    </td>

                </tr>

            `;

            return;

        }


        /* =================================================
         * 渲染表格
         * ================================================= */

        list.innerHTML =
            data
                .map(
                    (question, index) =>
                        this.createQuestionRow(
                            question,
                            start + index
                        )
                )
                .join("");

    },


    /* =====================================================
     * 创建题目行
     * ===================================================== */

    createQuestionRow(
        question,
        index
    ) {

        const title =
            this.getQuestionTitle(
                question
            );


        const type =
            this.getQuestionType(
                question
            );


        const answer =
            this.getAnswer(
                question
            );


        const analysis =
            this.getAnalysis(
                question
            );


        const optionA =
            this.getOption(
                question,
                "A"
            );


        const optionB =
            this.getOption(
                question,
                "B"
            );


        const optionC =
            this.getOption(
                question,
                "C"
            );


        const optionD =
            this.getOption(
                question,
                "D"
            );


        const optionE =
            this.getOption(
                question,
                "E"
            );


        const optionF =
            this.getOption(
                question,
                "F"
            );


        return `

            <tr>

                <!-- 序号 -->

                <td
                    class="question-index-cell"
                >

                    ${index + 1}

                </td>


                <!-- 题型 -->

                <td>

                    <span
                        class="question-type-tag"
                    >

                        ${this.escapeHtml(
                            type
                        )}

                    </span>

                </td>


                <!-- 题目 -->

                <td
                    class="question-title-cell"
                    title="${this.escapeHtml(
                        title
                    )}"
                >

                    ${this.escapeHtml(
                        title
                    )}

                </td>


                <!-- A -->

                <td
                    class="question-option-cell"
                >

                    ${this.escapeHtml(
                        optionA
                    )}

                </td>


                <!-- B -->

                <td
                    class="question-option-cell"
                >

                    ${this.escapeHtml(
                        optionB
                    )}

                </td>


                <!-- C -->

                <td
                    class="question-option-cell"
                >

                    ${this.escapeHtml(
                        optionC
                    )}

                </td>


                <!-- D -->

                <td
                    class="question-option-cell"
                >

                    ${this.escapeHtml(
                        optionD
                    )}

                </td>


                <!-- E -->

                <td
                    class="question-option-cell"
                >

                    ${this.escapeHtml(
                        optionE
                    )}

                </td>


                <!-- F -->

                <td
                    class="question-option-cell"
                >

                    ${this.escapeHtml(
                        optionF
                    )}

                </td>


                <!-- 答案 -->

                <td
                    class="question-answer-cell"
                >

                    ${
                        answer
                            ? `
                                <span
                                    class="answer-tag"
                                >
                                    ${this.escapeHtml(
                                        answer
                                    )}
                                </span>
                              `
                            : "-"
                    }

                </td>


                <!-- 解析 -->

                <td
                    class="question-analysis-cell"
                    title="${this.escapeHtml(
                        analysis
                    )}"
                >

                    ${
                        analysis
                            ? this.escapeHtml(
                                analysis
                            )
                            : "-"
                    }

                </td>

            </tr>

        `;

    },


    /* =====================================================
     * 导入到数据库 (新增方法)
     * ===================================================== */

    async importQuestions() {

        /* =================================================
         * 1. 检查是否有数据
         * ================================================= */
    
        if (!Array.isArray(this.filteredQuestions) || this.filteredQuestions.length === 0) {
            alert("当前没有可导入的题目");
            return;
        }
    
        /* =================================================
         * 2. 获取当前选中的分类
         * ================================================= */
    
        const deptSelect = document.getElementById('import-dept-select');
        const selectedOption = deptSelect ? deptSelect.options[deptSelect.selectedIndex] : null;
        
        if (!selectedOption || selectedOption.value === "") {
            alert("请先选择所属分类！");
            return;
        }
    
        // 获取分类信息
        const deptInfo = {
            id: selectedOption.value,                 // 分类 ID
            name: selectedOption.textContent.trim(),  // 分类名称（含缩进，需要处理）
            fullName: selectedOption.dataset.fullName || '',       // 完整分类名
            subjectionId: selectedOption.dataset.subjectionId || '',   // 所属单位 ID
            subjectionName: selectedOption.dataset.subjectionName || '' // 所属单位名称
        };
    
        /* =================================================
         * 3. 确认导入
         * ================================================= */
    
        const confirmMessage = 
            `确认将 ${this.filteredQuestions.length} 道题导入到【${deptInfo.fullName}】吗？\n\n` +
            `⚠️ 提示：重复的题目（相同标题和答案）将被跳过。`;
    
        if (!confirm(confirmMessage)) {
            return;
        }
    
        /* =================================================
         * 4. 发送请求
         * ================================================= */
    
        const button = document.getElementById("import-btn");
        const oldText = button ? button.textContent : "";
    
        if (button) {
            button.disabled = true;
            button.textContent = "⏳ 导入中...";
        }
    
        try {
            console.log("开始导入题库：", this.filteredQuestions.length, "道，分类:", deptInfo);
    
            const response = await fetch(
                "/api/questions/import",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        questions: this.filteredQuestions,
                        dept: deptInfo  // ★★★ 把分类信息一起传过去 ★★★
                    })
                }
            );
    
            if (!response.ok) {
                let message = "导入数据库失败";
                try {
                    const error = await response.json();
                    message = error.message || message;
                } catch (_) {}
                throw new Error(message);
            }
    
            const result = await response.json();
    
            if (!result.success) {
                throw new Error(result.message || "导入失败");
            }
    
            // 显示结果
            const inserted = result.data?.inserted || result.inserted || this.filteredQuestions.length;
            const skipped = result.data?.skipped || 0;
    
            let message = 
                `✅ 导入成功！\n` +
                `分类：${deptInfo.fullName}\n` +
                `共处理 ${this.filteredQuestions.length} 道题\n` +
                `成功导入 ${inserted} 道\n`;
    
            if (skipped > 0) {
                message += `跳过 ${skipped} 道（已存在）`;
            }
    
            alert(message);
    
        } catch (error) {
            console.error("导入数据库失败：", error);
            alert("❌ 导入失败：\n" + error.message);
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = oldText || "⬆ 导入数据库";
            }
        }
    },


    // =====================================================
    // 加载部门分类（树形结构，带缩进）
    // =====================================================

    async loadDeptList() {
        try {
            const response = await fetch('/api/dept/list');
            const result = await response.json();
            
            const select = document.getElementById('import-dept-select');
            if (!select) return;
            
            // 清空
            select.innerHTML = '<option value="">请选择分类</option>';
            
            if (result.success && result.data.length > 0) {
                // 扁平化树形结构（带缩进）
                const flattenTree = (nodes, prefix = '') => {
                    nodes.forEach(node => {
                        const option = document.createElement('option');
                        option.value = node.id;
                        option.textContent = prefix + node.name;
                        // 存储完整路径（用于导入时显示完整分类名）
                        option.dataset.fullName = node.name;
                        option.dataset.subjectionId = node.subjectionId || '';
                        option.dataset.subjectionName = node.subjectionName || '';
                        select.appendChild(option);
                        
                        if (node.children && node.children.length > 0) {
                            flattenTree(node.children, prefix + '　　');
                        }
                    });
                };
                
                flattenTree(result.data);
            } else {
                // 如果没有分类数据，使用默认选项
                const defaultDepts = [
                    { id: '1', name: '安全管理人员' },
                    { id: '2', name: '运输队' },
                    { id: '3', name: '机电队' },
                    { id: '4', name: '通风队' }
                ];
                defaultDepts.forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept.id;
                    option.textContent = dept.name;
                    select.appendChild(option);
                });
            }
            
        } catch (error) {
            console.error('加载部门分类失败:', error);
            // 加载失败时使用默认选项
            const select = document.getElementById('import-dept-select');
            if (select) {
                select.innerHTML = `
                    <option value="">请选择分类</option>
                    <option value="1">安全管理人员</option>
                    <option value="2">运输队</option>
                    <option value="3">机电队</option>
                    <option value="4">通风队</option>
                `;
            }
        }
    },



    /* =====================================================
     * 导出 Excel
     * ===================================================== */

    async exportQuestions() {

        if (
            !Array.isArray(
                this.filteredQuestions
            ) ||
            this.filteredQuestions.length === 0
        ) {

            alert(
                "当前没有可导出的题目"
            );

            return;

        }


        const button =
            document.getElementById(
                "export-btn"
            );


        const oldText =
            button
                ? button.textContent
                : "";


        if (button) {

            button.disabled = true;

            button.textContent =
                "正在导出...";

        }


        try {

            console.log(
                "开始导出题库：",
                this.filteredQuestions.length,
                "道"
            );


            const response =
                await fetch(
                    "/api/questions/export",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify({
                                questions:
                                    this.filteredQuestions
                            })
                    }
                );


            if (!response.ok) {

                let message =
                    "Excel 导出失败";


                try {

                    const error =
                        await response.json();


                    message =
                        error.message ||
                        message;

                }
                catch (_) {}


                throw new Error(
                    message
                );

            }


            const blob =
                await response.blob();


            if (
                !blob ||
                blob.size === 0
            ) {

                throw new Error(
                    "导出的Excel文件为空"
                );

            }


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


            a.download =
                `法规题库_${this.formatDate(
                    new Date()
                )}.xlsx`;


            document.body.appendChild(
                a
            );


            a.click();


            a.remove();


            window.URL.revokeObjectURL(
                url
            );


            alert(
                `Excel 导出成功，共 ${this.filteredQuestions.length} 道题。`
            );

        }
        catch (error) {

            console.error(
                "Excel导出失败：",
                error
            );


            alert(
                "导出失败：" +
                error.message
            );

        }
        finally {

            if (button) {

                button.disabled = false;

                button.textContent =
                    oldText ||
                    "↓ 导出 Excel";

            }

        }

    },


    /* =====================================================
     * 日期
     * ===================================================== */

    formatDate(date) {

        const year =
            date.getFullYear();


        const month =
            String(
                date.getMonth() + 1
            ).padStart(
                2,
                "0"
            );


        const day =
            String(
                date.getDate()
            ).padStart(
                2,
                "0"
            );


        return (
            year +
            month +
            day
        );

    },


    /* =====================================================
     * HTML 转义
     * ===================================================== */

    escapeHtml(value) {

        return String(
            value ?? ""
        )
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

};


/* =========================================================
 *
 * 给 App.js 使用
 *
 * App.js 会执行：
 *
 * QuestionBank.init()
 *
 * ========================================================= */

window.QuestionBank =
    QuestionBank;