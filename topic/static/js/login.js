// ========== 登录页面脚本 ==========
(function() {
    'use strict';

    // DOM 元素
    const form = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const loginBtn = document.getElementById('loginBtn');
    const togglePasswordBtn = document.getElementById('togglePassword');

    // ========== 显示密码切换 ==========
    if (togglePasswordBtn) {
        togglePasswordBtn.addEventListener('click', function() {
            const icon = this.querySelector('i');
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.className = 'fas fa-eye-slash';
            } else {
                passwordInput.type = 'password';
                icon.className = 'fas fa-eye';
            }
        });
    }

    // ========== 表单提交 ==========
    form.addEventListener('submit', function(e) {
        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        // 前端验证 - 只有验证失败才阻止提交
        if (!username) {
            e.preventDefault();
            alert('请输入手机号');
            usernameInput.focus();
            return;
        }

        if (!password) {
            e.preventDefault();
            alert('请输入密码');
            passwordInput.focus();
            return;
        }

        // ✅ 验证通过，显示加载状态，让表单正常提交
        loginBtn.disabled = true;
        loginBtn.innerHTML = '登录中...';
        // 不调用 e.preventDefault()，表单正常提交
    });

    // ========== 回车键提交 ==========
    passwordInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            form.submit();
        }
    });

    usernameInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            passwordInput.focus();
        }
    });

    // ========== 自动聚焦 ==========
    if (usernameInput.value) {
        passwordInput.focus();
    } else {
        usernameInput.focus();
    }

})();