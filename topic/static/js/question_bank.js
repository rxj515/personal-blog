/* =========================================================
 * question_bank.js - 题库管理
 * ========================================================= */

const QuestionBank = {

    // =====================================================
    // 状态
    // =====================================================

    questions: [],
    filteredQuestions: [],
    currentPage: 1,
    pageSize: 10,

    // =====================================================
    // 初始化
    // =====================================================

    async init() {
        console.log("📚 QuestionBank 初始化");
        this.bindEvents();
        await this.loadQuestions();
        this.bindCheckboxEvents();
    },

    // =====================================================
    // 绑定事件
    // =====================================================

    bindEvents() {
        // 加载分类（不阻塞主流程）
        this.loadDeptList().catch(err => {
            console.warn('加载分类失败:', err);
        });

        // 搜索（防抖）
        const search = document.getElementById('question-search');
        if (search) {
            let timer;
            search.oninput = () => {
                clearTimeout(timer);
                timer = setTimeout(() => this.filterQuestions(), 300);
            };
        }

        // 题型筛选
        const typeFilter = document.getElementById('question-type-filter');
        if (typeFilter) {
            typeFilter.onchange = () => this.filterQuestions();
        }

        // 分页
        const prev = document.getElementById('question-prev');
        if (prev) {
            prev.onclick = () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.renderQuestions();
                    this.bindCheckboxEvents();
                }
            };
        }

        const next = document.getElementById('question-next');
        if (next) {
            next.onclick = () => {
                const totalPage = Math.max(1, Math.ceil(this.filteredQuestions.length / this.pageSize));
                if (this.currentPage < totalPage) {
                    this.currentPage++;
                    this.renderQuestions();
                    this.bindCheckboxEvents();
                }
            };
        }

        // 导出
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.onclick = () => this.exportQuestions();
        }

        // 导入选中
        const importSelectedBtn = document.getElementById('import-selected-btn');
        if (importSelectedBtn) {
            importSelectedBtn.onclick = () => this.importSelectedQuestions();
        }

        // 导入全部
        const importAllBtn = document.getElementById('import-all-btn');
        if (importAllBtn) {
            importAllBtn.onclick = () => this.importAllQuestions();
        }
    },

    // =====================================================
    // 加载题库
    // =====================================================

    async loadQuestions() {
        const list = document.getElementById('question-list');
        if (!list) return;

        list.innerHTML = `<tr><td colspan="12" class="empty-cell">⏳ 正在读取题库...</td></tr>`;

        try {
            const result = await window.AppAPI.get('/api/questions/data');

            if (!result?.success) {
                throw new Error(result?.message || '读取题库失败');
            }

            this.questions = Array.isArray(result.data) ? result.data : [];
            this.filteredQuestions = [...this.questions];
            this.currentPage = 1;

            console.log(`✅ 题库读取成功：${this.questions.length} 道`);
            this.updateTotal();
            this.renderQuestions();
            this.bindCheckboxEvents();

        } catch (error) {
            console.error('❌ 题库读取失败:', error);
            this.questions = [];
            this.filteredQuestions = [];
            list.innerHTML = `
                <tr>
                    <td colspan="12" class="empty-cell">
                        <div class="empty-state">
                            <div class="empty-icon">❌</div>
                            <div class="empty-title">题库读取失败</div>
                            <div class="empty-text">${this.escapeHtml(error.message)}</div>
                        </div>
                    </td>
                </tr>
            `;
            this.updateTotal();
        }
    },

    // =====================================================
    // 筛选题目
    // =====================================================

    filterQuestions() {
        const keyword = document.getElementById('question-search')?.value.trim().toLowerCase() || '';
        const type = document.getElementById('question-type-filter')?.value || '';

        this.filteredQuestions = this.questions.filter(q => {
            const text = JSON.stringify(q).toLowerCase();
            const keywordMatch = !keyword || text.includes(keyword);
            const typeMatch = !type || this.getQuestionType(q) === type;
            return keywordMatch && typeMatch;
        });

        this.currentPage = 1;
        this.updateTotal();
        this.renderQuestions();
        this.bindCheckboxEvents();
    },

    // =====================================================
    // 获取字段（兼容多种数据格式）
    // =====================================================

    getQuestionType(q) {
        return q.question_type || q.type || q.title_category_name || '未知题型';
    },

    getQuestionTitle(q) {
        return q.title || q.subjects || q.question || q.content || '';
    },

    getOption(q, letter) {
        const key = 'plan_' + letter.toLowerCase();
        if (q[key] !== undefined && q[key] !== null) return String(q[key]);

        if (Array.isArray(q.options)) {
            const idx = letter.charCodeAt(0) - 65;
            return q.options[idx] || '';
        }

        if (q.options && typeof q.options === 'object') {
            return q.options[letter] || q.options[letter.toLowerCase()] || '';
        }

        return '';
    },

    getAnswer(q) {
        return q.answer || q.correct_answer || q.correctAnswer || '';
    },

    getAnalysis(q) {
        return q.analysis || q.explanation || q.explain || '';
    },

    // =====================================================
    // 更新总数
    // =====================================================

    updateTotal() {
        const el = document.getElementById('question-total');
        if (el) el.textContent = `${this.filteredQuestions.length} 题`;
    },

    // =====================================================
    // 渲染表格
    // =====================================================

    renderQuestions() {
        const list = document.getElementById('question-list');
        if (!list) return;

        const total = this.filteredQuestions.length;
        const totalPage = Math.max(1, Math.ceil(total / this.pageSize));

        if (this.currentPage > totalPage) this.currentPage = totalPage;

        const start = (this.currentPage - 1) * this.pageSize;
        const data = this.filteredQuestions.slice(start, start + this.pageSize);

        // 更新分页
        const pageInfo = document.getElementById('question-page-info');
        if (pageInfo) pageInfo.textContent = `${this.currentPage} / ${totalPage}`;

        const prev = document.getElementById('question-prev');
        if (prev) prev.disabled = this.currentPage <= 1;

        const next = document.getElementById('question-next');
        if (next) next.disabled = this.currentPage >= totalPage;

        // 空数据
        if (!data.length) {
            list.innerHTML = `
                <tr>
                    <td colspan="12" class="empty-cell">
                        <div class="empty-state">
                            <div class="empty-icon">📭</div>
                            <div class="empty-title">暂无题目</div>
                            <div class="empty-text">当前筛选条件下没有题目</div>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        // 渲染
        list.innerHTML = data.map((q, i) => this.createRow(q, start + i)).join('');
    },

    // =====================================================
    // 创建行
    // =====================================================

    createRow(q, index) {
        const fields = {
            title: this.getQuestionTitle(q),
            type: this.getQuestionType(q),
            answer: this.getAnswer(q),
            analysis: this.getAnalysis(q),
            options: ['A', 'B', 'C', 'D', 'E', 'F'].map(letter => this.getOption(q, letter))
        };

        const esc = this.escapeHtml;

        return `
            <tr>
                <td class="col-checkbox">
                    <input type="checkbox" class="row-checkbox" data-id="${q.id || index}">
                </td>
                <td class="question-index-cell">${index + 1}</td>
                <td><span class="question-type-tag">${esc(fields.type)}</span></td>
                <td class="question-title-cell" title="${esc(fields.title)}">${esc(fields.title)}</td>
                ${fields.options.map(opt => `<td class="question-option-cell">${esc(opt)}</td>`).join('')}
                <td class="question-answer-cell">${fields.answer ? `<span class="answer-tag">${esc(fields.answer)}</span>` : '-'}</td>
                <td class="question-analysis-cell" title="${esc(fields.analysis)}">${fields.analysis ? esc(fields.analysis) : '-'}</td>
            </tr>
        `;
    },

    // =====================================================
    // 复选框事件
    // =====================================================

    bindCheckboxEvents() {
        const selectAll = document.getElementById('select-all');
        if (selectAll) {
            selectAll.onchange = () => {
                const checked = selectAll.checked;
                document.querySelectorAll('.row-checkbox').forEach(cb => {
                    cb.checked = checked;
                    cb.closest('tr')?.classList.toggle('selected', checked);
                });
                this.updateSelectedCount();
            };
        }

        document.querySelectorAll('.row-checkbox').forEach(cb => {
            cb.onchange = () => {
                cb.closest('tr')?.classList.toggle('selected', cb.checked);
                this.updateSelectedCount();
                this.updateSelectAllState();
            };
        });

        this.updateSelectedCount();
        this.updateSelectAllState();
    },

    updateSelectedCount() {
        const count = document.querySelectorAll('.row-checkbox:checked').length;
        const selectedCount = document.getElementById('selected-count');
        const importCount = document.getElementById('import-count');
        const importBtn = document.getElementById('import-selected-btn');

        if (selectedCount) selectedCount.textContent = count;
        if (importCount) importCount.textContent = count;
        if (importBtn) {
            importBtn.disabled = count === 0;
            importBtn.innerHTML = `⬆ 导入选中 (${count})`;
        }
    },

    updateSelectAllState() {
        const selectAll = document.getElementById('select-all');
        if (!selectAll) return;

        const checkboxes = document.querySelectorAll('.row-checkbox');
        if (!checkboxes.length) {
            selectAll.checked = false;
            selectAll.indeterminate = false;
            return;
        }

        const checked = document.querySelectorAll('.row-checkbox:checked');
        selectAll.checked = checked.length === checkboxes.length;
        selectAll.indeterminate = checked.length > 0 && checked.length < checkboxes.length;
    },

    // =====================================================
    // 获取选中的题目
    // =====================================================

    getSelectedQuestions() {
        const ids = new Set();
        document.querySelectorAll('.row-checkbox:checked').forEach(cb => ids.add(cb.dataset.id));

        return this.filteredQuestions.filter((q, i) => {
            const id = String(q.id ?? i);
            return ids.has(id);
        });
    },

    // =====================================================
    // 导入
    // =====================================================

    async importSelectedQuestions() {
        const questions = this.getSelectedQuestions();
        if (!questions.length) {
            alert('请先选择要导入的题目！');
            return;
        }
        await this.doImport(questions);
    },

    async importAllQuestions() {
        if (!this.filteredQuestions.length) {
            alert('当前没有可导入的题目');
            return;
        }
        await this.doImport(this.filteredQuestions);
    },

    async doImport(questions) {
        const select = document.getElementById('import-target-select');
        const option = select?.options[select.selectedIndex];

        if (!option?.value) {
            alert('请先选择目标分类！');
            select?.focus();
            return;
        }

        const deptInfo = {
            id: option.value,
            fullName: option.dataset.fullName || option.textContent.trim(),
            superiorId: option.dataset.superiorId || '',
            superiorName: option.dataset.superiorName || ''
        };

        if (!confirm(`确认将 ${questions.length} 道题导入到【${deptInfo.fullName}】吗？`)) {
            return;
        }

        const btn = document.getElementById('import-selected-btn');
        const allBtn = document.getElementById('import-all-btn');

        try {
            if (btn) { btn.disabled = true; btn.textContent = '⏳ 导入中...'; }
            if (allBtn) allBtn.disabled = true;

            const res = await fetch('/api/questions/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ questions, dept: deptInfo })
            });

            const result = await res.json();

            if (result.success) {
                const inserted = result.data?.inserted ?? questions.length;
                alert(`✅ 导入成功！\n共处理 ${questions.length} 道\n成功导入 ${inserted} 道`);
                // 清空选中
                document.querySelectorAll('.row-checkbox:checked').forEach(cb => {
                    cb.checked = false;
                    cb.closest('tr')?.classList.remove('selected');
                });
                this.updateSelectedCount();
                this.updateSelectAllState();
            } else {
                alert(`❌ 导入失败：${result.message}`);
            }
        } catch (err) {
            alert(`❌ 导入失败：${err.message}`);
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '⬆ 导入选中 (0)'; }
            if (allBtn) allBtn.disabled = false;
        }
    },

    // =====================================================
    // 加载分类
    // =====================================================

    async loadDeptList() {
        try {
            const res = await window.AppAPI.get('/api/dept/list');
            const select = document.getElementById('import-target-select');
            if (!select) return;

            select.innerHTML = '<option value="">-- 请选择目标分类 --</option>';

            if (res?.success && res.data?.length) {
                const flatten = (nodes, prefix = '') => {
                    nodes.forEach(node => {
                        const opt = document.createElement('option');
                        opt.value = node.id;
                        opt.textContent = prefix + node.name;
                        opt.dataset.fullName = node.name;
                        opt.dataset.superiorId = node.superiorId || '';
                        opt.dataset.superiorName = node.superiorName || '';
                        select.appendChild(opt);
                        if (node.children?.length) flatten(node.children, prefix + '　　');
                    });
                };
                flatten(res.data);
            }
        } catch (err) {
            console.error('加载分类失败:', err);
        }
    },

    // =====================================================
    // 导出 Excel
    // =====================================================

    async exportQuestions() {
        if (!this.filteredQuestions.length) {
            alert('当前没有可导出的题目');
            return;
        }

        const btn = document.getElementById('export-btn');
        const oldText = btn?.textContent || '';

        try {
            if (btn) { btn.disabled = true; btn.textContent = '⏳ 导出中...'; }

            const res = await fetch('/api/questions/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ questions: this.filteredQuestions })
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.message || '导出失败');
            }

            const blob = await res.blob();
            if (!blob?.size) throw new Error('导出的Excel文件为空');

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `法规题库_${this.formatDate(new Date())}.xlsx`;
            a.click();
            a.remove();
            URL.revokeObjectURL(url);

            alert(`✅ Excel 导出成功，共 ${this.filteredQuestions.length} 道题`);

        } catch (err) {
            alert(`❌ 导出失败：${err.message}`);
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = oldText || '↓ 导出 Excel'; }
        }
    },

    // =====================================================
    // 工具
    // =====================================================

    formatDate(date) {
        return [
            date.getFullYear(),
            String(date.getMonth() + 1).padStart(2, '0'),
            String(date.getDate()).padStart(2, '0')
        ].join('');
    },

    escapeHtml(str) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return String(str ?? '').replace(/[&<>"']/g, m => map[m]);
    }

};

window.QuestionBank = QuestionBank;