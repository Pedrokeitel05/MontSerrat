// Função para configurar um botão de troca de tema
function setupThemeToggle(buttonId, textElementClass) {
    const themeButton = document.getElementById(buttonId);
    if (!themeButton) return;

    const body = document.body;
    let icon = themeButton.querySelector("i");
    let textElement = textElementClass
        ? themeButton.querySelector(`.${textElementClass}`)
        : null;

    function updateThemeUI(theme) {
        if (theme === "light") {
            if (icon) icon.className = "fas fa-moon me-2";
            if (textElement) textElement.textContent = "Mudar para Tema Escuro";
            if (buttonId === "themeToggle") icon.className = "fas fa-moon"; // Caso especial para o botão público
        } else {
            if (icon) icon.className = "fas fa-sun me-2";
            if (textElement) textElement.textContent = "Mudar para Tema Claro";
            if (buttonId === "themeToggle") icon.className = "fas fa-sun"; // Caso especial para o botão público
        }
    }

    const savedTheme = localStorage.getItem("theme") || "dark";
    body.setAttribute("data-theme", savedTheme);
    updateThemeUI(savedTheme);

    themeButton.addEventListener("click", function (event) {
        event.stopPropagation(); // Impede o menu de fechar ao clicar
        const currentTheme = body.getAttribute("data-theme");
        const newTheme = currentTheme === "dark" ? "light" : "dark";

        body.setAttribute("data-theme", newTheme);
        localStorage.setItem("theme", newTheme);
        updateThemeUI(newTheme);
    });
}

document.addEventListener("DOMContentLoaded", function () {
    // Configura os dois botões de tema (público e admin)
    setupThemeToggle("themeToggle");
    setupThemeToggle("themeToggleAdmin", "theme-text");

    // O resto do seu código de inicialização...
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]'),
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// FUNÇÕES UTILITÁRIAS (showToast, etc.)
function showToast(message, type = "success") {
    const toastContainer =
        document.getElementById("toast-container") || createToastContainer();
    const iconMap = {
        success: '<i class="fas fa-check-circle"></i>',
        danger: '<i class="fas fa-exclamation-triangle"></i>',
        warning: '<i class="fas fa-exclamation-circle"></i>',
        info: '<i class="fas fa-info-circle"></i>',
    };
    const titleMap = {
        success: "Sucesso!",
        danger: "Erro!",
        warning: "Atenção!",
        info: "Informação",
    };
    const toast = document.createElement("div");
    toast.className = `toast toast-modern toast-${type}`;
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.setAttribute("aria-atomic", "true");
    toast.innerHTML = `
        <div class="toast-header">
            <span class="toast-icon me-2">${iconMap[type] || ""}</span>
            <strong class="me-auto">${titleMap[type] || "Notificação"}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
    bsToast.show();
    toast.addEventListener("hidden.bs.toast", function () {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement("div");
    container.id = "toast-container";
    container.className = "position-fixed bottom-0 end-0 p-3";
    container.style.zIndex = "1055";
    document.body.appendChild(container);
    return container;
}
