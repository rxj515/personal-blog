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
        this.bindDeleteEvents();
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
                    this.bindDeleteEvents();
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
                    this.bindDeleteEvents();
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

        // 删除选中按钮
        const deleteSelectedBtn = document.getElementById('delete-selected-btn');
        if (deleteSelectedBtn) {
            deleteSelectedBtn.onclick = () => this.deleteSelectedQuestions();
        }
    },

    // =====================================================
    // 绑定删除事件（事件委托）
    // =====================================================

    bindDeleteEvents() {
        const list = document.getElementById('question-list');
        if (!list) return;

        list.removeEventListener('click', this._deleteHandler);
        
        this._deleteHandler = (e) => {
            const deleteBtn = e.target.closest('.btn-delete-row');
            if (deleteBtn) {
                const row = deleteBtn.closest('tr');
                if (row) {
                    const index = parseInt(row.dataset.index);
                    if (!isNaN(index)) {
                        this.deleteSingleQuestion(index);
                    }
                }
            }
        };
        
        list.addEventListener('click', this._deleteHandler);
    },

    // =====================================================
    // 加载题库（同时加载历史题库和 _new.json）
    // =====================================================

    async loadQuestions() {
        const list = document.getElementById('question-list');
        if (!list) return;

        list.innerHTML = `<tr><td colspan="13" class="empty-cell">⏳ 正在读取题库...</td></tr>`;

        try {
            // 1. 加载历史题库
            const historyResult = await window.AppAPI.get('/api/questions/data');
            const historyQuestions = (historyResult?.success && Array.isArray(historyResult.data)) 
                ? historyResult.data 
                : [];

            // 2. 加载新生成的题目（_new.json）
            const newResult = await window.AppAPI.get('/api/questions/new-data');
            const newQuestions = (newResult?.success && Array.isArray(newResult.data)) 
                ? newResult.data 
                : [];

            // 3. 合并，并去重（使用 id 或 article+title）
            const allQuestions = [...historyQuestions];
            const existed = new Set();
            
            historyQuestions.forEach(q => {
                // 优先用 id，没有则用 article+title
                const key = q.id || `${q.article || ''}|${q.title || ''}`;
                existed.add(key);
            });
            
            let addedCount = 0;
            newQuestions.forEach(q => {
                const key = q.id || `${q.article || ''}|${q.title || ''}`;
                if (!existed.has(key)) {
                    allQuestions.push(q);
                    existed.add(key);
                    addedCount++;
                }
            });

            this.questions = allQuestions;
            this.filteredQuestions = [...this.questions];
            this.currentPage = 1;

            console.log(`✅ 题库读取成功：历史题库 ${historyQuestions.length} 道 + 新题 ${newQuestions.length} 道（新增 ${addedCount} 道）= 共 ${this.questions.length} 道`);
            this.updateTotal();
            this.renderQuestions();
            this.bindCheckboxEvents();
            this.bindDeleteEvents();

        } catch (error) {
            console.error('❌ 题库读取失败:', error);
            this.questions = [];
            this.filteredQuestions = [];
            list.innerHTML = `
                <tr>
                    <td colspan="13" class="empty-cell">
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
        this.bindDeleteEvents();
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

        const pageInfo = document.getElementById('question-page-info');
        if (pageInfo) pageInfo.textContent = `${this.currentPage} / ${totalPage}`;

        const prev = document.getElementById('question-prev');
        if (prev) prev.disabled = this.currentPage <= 1;

        const next = document.getElementById('question-next');
        if (next) next.disabled = this.currentPage >= totalPage;

        if (!data.length) {
            list.innerHTML = `
                <tr>
                    <td colspan="13" class="empty-cell">
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

        list.innerHTML = data.map((q, i) => this.createRow(q, start + i)).join('');
    },

    // =====================================================
    // 创建行（已加入删除按钮，存储 id）
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
        const questionId = q.id || '';

        return `
            <tr data-index="${index}" data-id="${questionId}">
                <td class="col-checkbox">
                    <input type="checkbox" class="row-checkbox" data-index="${index}" data-id="${questionId}">
                </td>
                <td class="question-index-cell">${index + 1}</td>
                <td><span class="question-type-tag">${esc(fields.type)}</span></td>
                <td class="question-title-cell" title="${esc(fields.title)}">${esc(fields.title)}</td>
                ${fields.options.map(opt => `<td class="question-option-cell">${esc(opt)}</td>`).join('')}
                <td class="question-answer-cell">${fields.answer ? `<span class="answer-tag">${esc(fields.answer)}</span>` : '-'}</td>
                <td class="question-analysis-cell" title="${esc(fields.analysis)}">${fields.analysis ? esc(fields.analysis) : '-'}</td>
                <td class="col-delete">
                    <button class="btn-delete-row" data-index="${index}" data-id="${questionId}" title="删除此题">删除</button>
                </td>
            </tr>
        `;
    },

    // =====================================================
    // ✅ 删除单道题（通过ID精确删除，修复筛选后删除问题）
    // =====================================================

    async deleteSingleQuestion(index) {
        if (!this.questions || this.questions.length === 0) {
            return;
        }

        // ✅ 关键修复：从 filteredQuestions 中获取题目（而不是 questions）
        if (index < 0 || index >= this.filteredQuestions.length) {
            console.warn('删除失败：索引超出范围', index);
            return;
        }

        // ✅ 从筛选后的列表中获取题目
        const question = this.filteredQuestions[index];
        const title = this.getQuestionTitle(question) || '未命名题目';
        const type = this.getQuestionType(question) || '未知题型';
        const questionId = question.id;
        
        // ✅ 如果没有ID，提示无法删除
        if (!questionId) {
            alert('❌ 该题目没有唯一ID，无法精确删除。请重新生成题目。');
            return;
        }
        
        if (!confirm(`确定要删除这道题吗？\n\n题型：${type}\n题目：${title.substring(0, 50)}...`)) {
            return;
        }

        try {
            // ✅ 通过ID删除
            const response = await fetch('/api/questions/delete-bank', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    id: questionId,
                    question: question
                })
            });

            const result = await response.json();

            if (!result.success) {
                alert('❌ 删除失败：' + (result.message || '未知错误'));
                return;
            }

            // ✅ 从完整列表中移除（使用ID过滤）
            this.questions = this.questions.filter(q => q.id !== questionId);
            
            // ✅ 从筛选列表中移除（使用ID过滤）
            this.filteredQuestions = this.filteredQuestions.filter(q => q.id !== questionId);
            
            // 重新渲染
            this.renderQuestions();
            this.updateTotal();
            this.bindCheckboxEvents();
            this.bindDeleteEvents();
            this.clearSelection();
            
            // 显示成功消息
            this.showMessage(`✅ 删除成功，剩余 ${this.questions.length} 道题`, 'success');

        } catch (e) {
            console.error('删除失败：', e);
            alert('❌ 删除失败：' + e.message);
        }
    },

    // =====================================================
    // ✅ 删除选中的多道题（修复筛选后删除问题）
    // =====================================================

    async deleteSelectedQuestions() {
        // ✅ 从筛选后的列表中获取选中的索引
        const selectedIndices = this.getSelectedIndices();
        
        if (selectedIndices.length === 0) {
            alert('请先选择要删除的题目！');
            return;
        }

        // ✅ 从 filteredQuestions 中获取选中的题目（而不是 questions）
        const selectedQuestions = selectedIndices
            .map(i => this.filteredQuestions[i])
            .filter(q => q && q.id);
        
        if (selectedQuestions.length === 0) {
            alert('❌ 选中的题目没有唯一ID，无法删除。请重新生成题目。');
            return;
        }

        const titles = selectedQuestions
            .map((q, idx) => {
                const title = this.getQuestionTitle(q) || '未命名';
                const type = this.getQuestionType(q) || '未知';
                return `${idx + 1}. [${type}] ${title.substring(0, 30)}...`;
            })
            .join('\n');

        if (!confirm(`⚠️ 确定要删除选中的 ${selectedQuestions.length} 道题吗？\n\n${titles}`)) {
            return;
        }

        const deleteBtn = document.getElementById('delete-selected-btn');
        if (deleteBtn) {
            deleteBtn.disabled = true;
            deleteBtn.textContent = '⏳ 删除中...';
        }

        try {
            let deletedCount = 0;
            let failedList = [];
            const deletedIds = new Set();

            for (const q of selectedQuestions) {
                const response = await fetch('/api/questions/delete-bank', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        id: q.id,
                        question: q
                    })
                });

                const result = await response.json();
                
                if (result.success) {
                    deletedCount++;
                    deletedIds.add(q.id);
                } else {
                    const title = this.getQuestionTitle(q) || '未命名';
                    failedList.push(`题目：${title.substring(0, 20)}...`);
                }
            }

            // ✅ 从完整列表中移除（使用ID过滤）
            this.questions = this.questions.filter(q => !deletedIds.has(q.id));
            
            // ✅ 从筛选列表中移除（使用ID过滤）
            this.filteredQuestions = this.filteredQuestions.filter(q => !deletedIds.has(q.id));
            
            this.renderQuestions();
            this.updateTotal();
            this.bindCheckboxEvents();
            this.bindDeleteEvents();
            this.clearSelection();
            
            if (failedList.length === 0) {
                this.showMessage(`✅ 成功删除 ${deletedCount} 道题，剩余 ${this.questions.length} 道`, 'success');
            } else {
                const msg = `⚠️ 部分删除成功：${deletedCount}/${selectedQuestions.length} 道\n\n失败：\n${failedList.join('\n')}`;
                this.showMessage(msg, 'warning');
            }

        } catch (e) {
            console.error('批量删除失败：', e);
            alert('❌ 删除失败：' + e.message);
        } finally {
            if (deleteBtn) {
                deleteBtn.disabled = false;
                deleteBtn.textContent = '🗑 删除选中 (0)';
            }
        }
    },

    // =====================================================
    // 获取选中的索引
    // =====================================================

    getSelectedIndices() {
        const checkboxes = document.querySelectorAll('#question-list .row-checkbox:checked');
        const indices = [];
        checkboxes.forEach(cb => {
            const idx = parseInt(cb.dataset.index);
            if (!isNaN(idx)) {
                indices.push(idx);
            }
        });
        return indices;
    },

    // =====================================================
    // 清除所有选中
    // =====================================================

    clearSelection() {
        document.querySelectorAll('#question-list .row-checkbox').forEach(cb => {
            cb.checked = false;
            cb.closest('tr')?.classList.remove('selected');
        });
        const selectAll = document.getElementById('select-all');
        if (selectAll) selectAll.checked = false;
        this.updateSelectedCount();
        this.updateSelectAllState();
    },

    // =====================================================
    // 显示消息
    // =====================================================

    showMessage(msg, type = 'info') {
        const oldMsg = document.getElementById('bank-message');
        if (oldMsg) oldMsg.remove();

        const messageEl = document.createElement('div');
        messageEl.id = 'bank-message';
        messageEl.style.cssText = `
            padding: 12px 20px;
            border-radius: 12px;
            margin-bottom: 16px;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
            animation: slideDown 0.3s ease;
        `;

        const colors = {
            success: { bg: '#dcfce7', color: '#166534', border: '#86efac' },
            error: { bg: '#fee2e2', color: '#991b1b', border: '#fca5a5' },
            warning: { bg: '#fef3c7', color: '#92400e', border: '#fcd34d' },
            info: { bg: '#dbeafe', color: '#1e40af', border: '#93c5fd' }
        };

        const style = colors[type] || colors.info;
        messageEl.style.background = style.bg;
        messageEl.style.color = style.color;
        messageEl.style.border = `1px solid ${style.border}`;
        messageEl.textContent = msg;

        const container = document.querySelector('.question-filter-card');
        if (container) {
            container.parentNode.insertBefore(messageEl, container);
        } else {
            const tableCard = document.querySelector('.question-table-card');
            if (tableCard) {
                tableCard.parentNode.insertBefore(messageEl, tableCard);
            }
        }

        clearTimeout(this._messageTimer);
        this._messageTimer = setTimeout(() => {
            messageEl.style.animation = 'slideUp 0.3s ease forwards';
            setTimeout(() => messageEl.remove(), 300);
        }, 5000);
    },

    // =====================================================
    // 复选框事件
    // =====================================================

    bindCheckboxEvents() {
        const selectAll = document.getElementById('select-all');
        if (selectAll) {
            selectAll.onchange = null;
            selectAll.onchange = () => {
                const checked = selectAll.checked;
                document.querySelectorAll('.row-checkbox').forEach(cb => {
                    cb.checked = checked;
                    cb.closest('tr')?.classList.toggle('selected', checked);
                });
                this.updateSelectedCount();
                this.updateSelectAllState();
            };
        }

        document.querySelectorAll('.row-checkbox').forEach(cb => {
            cb.onchange = null;
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
        const deleteCount = document.getElementById('delete-count');
        const importBtn = document.getElementById('import-selected-btn');
        const deleteBtn = document.getElementById('delete-selected-btn');

        if (selectedCount) selectedCount.textContent = count;
        if (importCount) importCount.textContent = count;
        if (deleteCount) deleteCount.textContent = count;
        
        if (importBtn) {
            importBtn.disabled = count === 0;
            importBtn.innerHTML = `⬆ 导入选中 (${count})`;
        }
        
        if (deleteBtn) {
            deleteBtn.disabled = count === 0;
            deleteBtn.innerHTML = `🗑 删除选中 (${count})`;
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
        document.querySelectorAll('.row-checkbox:checked').forEach(cb => {
            const id = cb.dataset.id;
            if (id) ids.add(id);
        });

        return this.filteredQuestions.filter(q => ids.has(q.id));
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