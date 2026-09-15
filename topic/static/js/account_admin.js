/**
 * =========================================================
 * account_admin.js
 * 系统账户管理
 *
 * 功能：
 * 1. 真实读取 data/users.json
 * 2. 创建账户
 * 3. 修改密码
 * 4. 启用 / 禁用账户
 * 5. 删除账户
 * 6. 搜索 / 筛选 / 分页
 * =========================================================
 */

window.AccountAdmin = (function () {

    // =====================================================
    // 账户数据
    // =====================================================

    let accountData = [];

    let filteredData = [];

    let currentPage = 1;

    const PAGE_SIZE = 10;

    // 当前修改密码的账户
    let passwordUserId = null;


    // =====================================================
    // 初始化
    // =====================================================

    async function init() {

        console.log("=================================");
        console.log("AccountAdmin 初始化");
        console.log("=================================");

        bindEvents();

        await loadAccounts();

        console.log("AccountAdmin 初始化完成");
    }


    // =====================================================
    // 从后端加载账户
    // =====================================================

    async function loadAccounts() {

        const loading = document.getElementById(
            "account-loading"
        );

        if (loading) {
            loading.style.display = "flex";
        }

        try {

            console.log("正在加载账户列表...");

            const result =
                await window.AppAPI.get(
                    "/api/account/list"
                );

            console.log(
                "账户列表接口返回：",
                result
            );

            if (
                !result ||
                !result.success
            ) {

                throw new Error(
                    result?.message ||
                    "获取账户列表失败"
                );
            }

            accountData =
                Array.isArray(result.data)
                    ? result.data
                    : [];

            currentPage = 1;

            applyFilters();

            console.log(
                "✅ 账户列表加载完成，共",
                accountData.length,
                "个账户"
            );

        } catch (error) {

            console.error(
                "❌ 获取账户列表失败：",
                error
            );

            accountData = [];

            filteredData = [];

            render();

            showToast(
                error.message ||
                "获取账户列表失败",
                "error"
            );

        } finally {

            if (loading) {
                loading.style.display = "none";
            }

        }
    }


    // =====================================================
    // 绑定事件
    // =====================================================

    function bindEvents() {

        // 搜索
        document
            .getElementById("account-search")
            ?.addEventListener(
                "input",
                function () {

                    currentPage = 1;

                    applyFilters();
                }
            );


        // 角色筛选
        document
            .getElementById("account-role-filter")
            ?.addEventListener(
                "change",
                function () {

                    currentPage = 1;

                    applyFilters();
                }
            );


        // 状态筛选
        document
            .getElementById("account-status-filter")
            ?.addEventListener(
                "change",
                function () {

                    currentPage = 1;

                    applyFilters();
                }
            );


        // 刷新
        document
            .getElementById("account-refresh-btn")
            ?.addEventListener(
                "click",
                async function () {

                    await loadAccounts();
                }
            );


        // 上一页
        document
            .getElementById("account-prev")
            ?.addEventListener(
                "click",
                previousPage
            );


        // 下一页
        document
            .getElementById("account-next")
            ?.addEventListener(
                "click",
                nextPage
            );


        // =================================================
        // 创建账户
        // =================================================

        document
            .getElementById("account-create-btn")
            ?.addEventListener(
                "click",
                openCreateModal
            );


        document
            .getElementById("account-create-close")
            ?.addEventListener(
                "click",
                closeCreateModal
            );


        document
            .getElementById("account-create-cancel")
            ?.addEventListener(
                "click",
                closeCreateModal
            );


        document
            .getElementById("account-create-form")
            ?.addEventListener(
                "submit",
                handleCreate
            );


        // =================================================
        // 修改密码
        // =================================================

        document
            .getElementById("account-password-close")
            ?.addEventListener(
                "click",
                closePasswordModal
            );


        document
            .getElementById("account-password-cancel")
            ?.addEventListener(
                "click",
                closePasswordModal
            );


        document
            .getElementById("account-password-form")
            ?.addEventListener(
                "submit",
                handlePasswordChange
            );


        // =================================================
        // 点击遮罩关闭
        // =================================================

        document
            .getElementById("account-create-modal")
            ?.addEventListener(
                "click",
                function (event) {

                    if (
                        event.target === this
                    ) {

                        closeCreateModal();
                    }
                }
            );


        document
            .getElementById("account-password-modal")
            ?.addEventListener(
                "click",
                function (event) {

                    if (
                        event.target === this
                    ) {

                        closePasswordModal();
                    }
                }
            );
    }


    // =====================================================
    // 筛选
    // =====================================================

    function applyFilters() {

        const searchInput =
            document.getElementById(
                "account-search"
            );

        const roleSelect =
            document.getElementById(
                "account-role-filter"
            );

        const statusSelect =
            document.getElementById(
                "account-status-filter"
            );


        const keyword =
            searchInput
                ? searchInput.value
                    .trim()
                    .toLowerCase()
                : "";


        const role =
            roleSelect
                ? roleSelect.value
                : "";


        const status =
            statusSelect
                ? statusSelect.value
                : "";


        filteredData =
            accountData.filter(function (user) {

                const username =
                    String(
                        user.username || ""
                    ).toLowerCase();


                const userId =
                    String(
                        user.user_id || ""
                    ).toLowerCase();


                const matchSearch =
                    !keyword ||
                    username.includes(keyword) ||
                    userId.includes(keyword);


                const matchRole =
                    !role ||
                    user.role === role;


                let matchStatus = true;


                if (
                    status === "enabled"
                ) {

                    matchStatus =
                        user.enabled === true;
                }


                if (
                    status === "disabled"
                ) {

                    matchStatus =
                        user.enabled === false;
                }


                return (
                    matchSearch &&
                    matchRole &&
                    matchStatus
                );
            });


        render();
    }


    // =====================================================
    // 渲染
    // =====================================================

    function render() {

        updateStatistics();

        renderTable();

        updatePagination();
    }


    // =====================================================
    // 统计
    // =====================================================

    function updateStatistics() {

        const total =
            accountData.length;


        const enabled =
            accountData.filter(
                user => user.enabled
            ).length;


        const disabled =
            accountData.filter(
                user => !user.enabled
            ).length;


        const admins =
            accountData.filter(
                user =>
                    user.role === "管理员"
            ).length;


        setText(
            "account-total-count",
            total
        );


        setText(
            "account-enabled-count",
            enabled
        );


        setText(
            "account-disabled-count",
            disabled
        );


        setText(
            "account-admin-count",
            admins
        );
    }


    // =====================================================
    // 表格
    // =====================================================

    function renderTable() {

        const list =
            document.getElementById(
                "account-list"
            );


        const empty =
            document.getElementById(
                "account-empty-state"
            );


        const loading =
            document.getElementById(
                "account-loading"
            );


        if (!list) {
            return;
        }


        if (loading) {
            loading.style.display = "none";
        }


        const total =
            filteredData.length;


        setText(
            "account-result-count",
            `${total} 个账户`
        );


        if (!total) {

            list.innerHTML = "";


            if (empty) {
                empty.style.display = "flex";
            }


            return;
        }


        if (empty) {
            empty.style.display = "none";
        }


        const start =
            (currentPage - 1) *
            PAGE_SIZE;


        const pageData =
            filteredData.slice(
                start,
                start + PAGE_SIZE
            );


        list.innerHTML =
            pageData
                .map(createRow)
                .join("");
    }


    // =====================================================
    // 单行
    // =====================================================

    function createRow(user) {

        const avatar =
            getAvatar(
                user.username
            );


        const roleClass =
            user.role === "管理员"
                ? "account-tag-admin"
                : "account-tag-user";


        const statusClass =
            user.enabled
                ? "account-tag-enabled"
                : "account-tag-disabled";


        const statusText =
            user.enabled
                ? "正常"
                : "已禁用";


        // 管理员不允许禁用
        const toggleButton =
            user.role === "管理员"
                ? ""
                : user.enabled
                    ? `
                        <button
                            type="button"
                            class="account-action-btn account-action-disable"
                            onclick="window.AccountAdmin.toggleStatus('${escapeHtml(user.user_id)}')"
                        >
                            禁用
                        </button>
                    `
                    : `
                        <button
                            type="button"
                            class="account-action-btn account-action-enable"
                            onclick="window.AccountAdmin.toggleStatus('${escapeHtml(user.user_id)}')"
                        >
                            启用
                        </button>
                    `;


        // 管理员不能删除
        const deleteButton =
            user.role === "管理员"
                ? ""
                : `
                    <button
                        type="button"
                        class="account-action-btn account-action-delete"
                        onclick="window.AccountAdmin.deleteUser('${escapeHtml(user.user_id)}')"
                    >
                        删除
                    </button>
                `;


        return `
            <tr>

                <td>

                    <div class="account-user-info">

                        <div class="account-avatar">
                            ${avatar}
                        </div>

                        <div>

                            <div class="account-user-name">
                                ${escapeHtml(user.username)}
                            </div>

                            <div class="account-user-id">
                                ${escapeHtml(user.user_id)}
                            </div>

                        </div>

                    </div>

                </td>


                <td>

                    <span
                        class="account-tag ${roleClass}"
                    >
                        ${escapeHtml(user.role)}
                    </span>

                </td>


                <td>

                    <span
                        class="account-tag ${statusClass}"
                    >
                        ${statusText}
                    </span>

                </td>


                <td>
                    ${escapeHtml(
                        user.created_at || "-"
                    )}
                </td>


                <td>
                    ${escapeHtml(
                        user.last_login || "暂无"
                    )}
                </td>


                <td>

                    <div class="account-actions">

                        <button
                            type="button"
                            class="account-action-btn account-action-password"
                            onclick="window.AccountAdmin.openPasswordModal('${escapeHtml(user.user_id)}')"
                        >
                            修改密码
                        </button>

                        ${toggleButton}

                        ${deleteButton}

                    </div>

                </td>

            </tr>
        `;
    }


    // =====================================================
    // 创建账户
    // =====================================================

    function openCreateModal() {

        const modal =
            document.getElementById(
                "account-create-modal"
            );


        const form =
            document.getElementById(
                "account-create-form"
            );


        if (form) {
            form.reset();
        }


        const enabled =
            document.getElementById(
                "account-enabled"
            );


        if (enabled) {
            enabled.checked = true;
        }


        if (modal) {
            modal.style.display = "flex";
        }


        setTimeout(function () {

            document
                .getElementById(
                    "account-username"
                )
                ?.focus();

        }, 50);
    }


    function closeCreateModal() {

        const modal =
            document.getElementById(
                "account-create-modal"
            );


        if (modal) {
            modal.style.display = "none";
        }
    }


    // =====================================================
    // 创建账户
    // =====================================================

    async function handleCreate(event) {

        event.preventDefault();


        const username =
            document
                .getElementById(
                    "account-username"
                )
                .value
                .trim();


        const password =
            document
                .getElementById(
                    "account-password"
                )
                .value;


        const confirmPassword =
            document
                .getElementById(
                    "account-password-confirm"
                )
                .value;


        const enabled =
            document
                .getElementById(
                    "account-enabled"
                )
                .checked;


        // =================================================
        // 前端校验
        // =================================================

        if (username.length < 2) {

            showToast(
                "❌ 用户名至少 2 个字符",
                "error"
            );

            return;
        }


        if (/\s/.test(username)) {

            showToast(
                "❌ 用户名不能包含空格",
                "error"
            );

            return;
        }


        if (password.length < 12) {

            showToast(
                "❌ 密码至少 12 位",
                "error"
            );

            return;
        }


        if (
            password !== confirmPassword
        ) {

            showToast(
                "❌ 两次密码不一致",
                "error"
            );

            return;
        }


        // =================================================
        // 调用后端
        // =================================================

        try {

            console.log(
                "正在创建账户：",
                username
            );


            const result =
                await window.AppAPI.post(
                    "/api/account/create",
                    {
                        username: username,
                        password: password,
                        enabled: enabled
                    }
                );


            console.log(
                "创建账户接口返回：",
                result
            );


            if (
                !result ||
                !result.success
            ) {

                throw new Error(
                    result?.message ||
                    "账户创建失败"
                );
            }


            closeCreateModal();


            await loadAccounts();


            showToast(
                "✅ 账户创建成功",
                "success"
            );


        } catch (error) {

            console.error(
                "❌ 创建账户失败：",
                error
            );


            showToast(
                error.message ||
                "账户创建失败",
                "error"
            );
        }
    }


    // =====================================================
    // 修改密码
    // =====================================================

    function openPasswordModal(userId) {

        const user =
            accountData.find(
                item =>
                    item.user_id === userId
            );


        if (!user) {
            return;
        }


        passwordUserId =
            userId;


        setText(
            "account-password-username",
            `修改 ${user.username} 的登录密码`
        );


        const form =
            document.getElementById(
                "account-password-form"
            );


        if (form) {
            form.reset();
        }


        const modal =
            document.getElementById(
                "account-password-modal"
            );


        if (modal) {
            modal.style.display = "flex";
        }


        setTimeout(function () {

            document
                .getElementById(
                    "account-new-password"
                )
                ?.focus();

        }, 50);
    }


    function closePasswordModal() {

        const modal =
            document.getElementById(
                "account-password-modal"
            );


        if (modal) {
            modal.style.display = "none";
        }


        passwordUserId = null;
    }


    async function handlePasswordChange(event) {

        event.preventDefault();


        if (!passwordUserId) {

            showToast(
                "❌ 未找到目标账户",
                "error"
            );

            return;
        }


        const password =
            document
                .getElementById(
                    "account-new-password"
                )
                .value;


        const confirmPassword =
            document
                .getElementById(
                    "account-new-password-confirm"
                )
                .value;


        if (password.length < 12) {

            showToast(
                "❌ 密码至少 12 位",
                "error"
            );

            return;
        }


        if (
            password !== confirmPassword
        ) {

            showToast(
                "❌ 两次密码不一致",
                "error"
            );

            return;
        }


        try {

            const result =
                await window.AppAPI.post(
                    "/api/account/password",
                    {
                        user_id: passwordUserId,
                        password: password
                    }
                );


            if (
                !result ||
                !result.success
            ) {

                throw new Error(
                    result?.message ||
                    "密码修改失败"
                );
            }


            closePasswordModal();


            await loadAccounts();


            showToast(
                "✅ 密码修改成功",
                "success"
            );


        } catch (error) {

            console.error(
                "❌ 修改密码失败：",
                error
            );


            showToast(
                error.message ||
                "密码修改失败",
                "error"
            );
        }
    }


    // =====================================================
    // 启用 / 禁用
    // =====================================================

    async function toggleStatus(userId) {

        const user =
            accountData.find(
                item =>
                    item.user_id === userId
            );


        if (!user) {
            return;
        }


        if (
            user.role === "管理员"
        ) {

            showToast(
                "⚠️ 管理员账户暂不允许通过此页面禁用",
                "error"
            );

            return;
        }


        const action =
            user.enabled
                ? "禁用"
                : "启用";


        if (
            !confirm(
                `确定要${action}账户「${user.username}」吗？`
            )
        ) {

            return;
        }


        try {

            const result =
                await window.AppAPI.post(
                    "/api/account/status",
                    {
                        user_id: userId,
                        enabled: !user.enabled
                    }
                );


            if (
                !result ||
                !result.success
            ) {

                throw new Error(
                    result?.message ||
                    `${action}账户失败`
                );
            }


            await loadAccounts();


            showToast(
                user.enabled
                    ? "✅ 账户已禁用"
                    : "✅ 账户已启用",
                "success"
            );


        } catch (error) {

            console.error(
                `❌ ${action}账户失败：`,
                error
            );


            showToast(
                error.message ||
                `${action}账户失败`,
                "error"
            );
        }
    }


    // =====================================================
    // 删除
    // =====================================================

    async function deleteUser(userId) {

        const user =
            accountData.find(
                item =>
                    item.user_id === userId
            );


        if (!user) {
            return;
        }


        if (
            user.role === "管理员"
        ) {

            showToast(
                "❌ 管理员账户不能删除",
                "error"
            );

            return;
        }


        if (
            !confirm(
                `确定要删除账户「${user.username}」吗？\n\n删除后该账户将无法登录。`
            )
        ) {

            return;
        }


        try {

            const result =
                await window.AppAPI.post(
                    "/api/account/delete",
                    {
                        user_id: userId
                    }
                );


            if (
                !result ||
                !result.success
            ) {

                throw new Error(
                    result?.message ||
                    "账户删除失败"
                );
            }


            await loadAccounts();


            showToast(
                "✅ 账户已删除",
                "success"
            );


        } catch (error) {

            console.error(
                "❌ 删除账户失败：",
                error
            );


            showToast(
                error.message ||
                "账户删除失败",
                "error"
            );
        }
    }


    // =====================================================
    // 分页
    // =====================================================

    function previousPage() {

        if (
            currentPage <= 1
        ) {
            return;
        }


        currentPage--;


        render();
    }


    function nextPage() {

        const totalPage =
            Math.max(
                1,
                Math.ceil(
                    filteredData.length /
                    PAGE_SIZE
                )
            );


        if (
            currentPage >= totalPage
        ) {
            return;
        }


        currentPage++;


        render();
    }


    function updatePagination() {

        const totalPage =
            Math.max(
                1,
                Math.ceil(
                    filteredData.length /
                    PAGE_SIZE
                )
            );


        if (
            currentPage > totalPage
        ) {
            currentPage = totalPage;
        }


        setText(
            "account-page-info",
            `${currentPage} / ${totalPage}`
        );


        const prev =
            document.getElementById(
                "account-prev"
            );


        const next =
            document.getElementById(
                "account-next"
            );


        if (prev) {

            prev.disabled =
                currentPage <= 1;
        }


        if (next) {

            next.disabled =
                currentPage >= totalPage;
        }
    }


    // =====================================================
    // 工具
    // =====================================================

    function getAvatar(username) {

        if (!username) {
            return "👤";
        }


        return username
            .charAt(0)
            .toUpperCase();
    }


    function setText(id, value) {

        const element =
            document.getElementById(id);


        if (element) {

            element.textContent =
                String(value);
        }
    }


    function escapeHtml(value) {

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


    function showToast(
        message,
        type = "success"
    ) {

        if (
            window.AppToast &&
            typeof window.AppToast ===
                "function"
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

        openPasswordModal,

        toggleStatus,

        deleteUser

    };

})();