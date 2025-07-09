// Main JavaScript file for Funerária Montserrat
document.addEventListener("DOMContentLoaded", function () {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]'),
    );
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize form validation
    const forms = document.querySelectorAll(".needs-validation");
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener(
            "submit",
            function (event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add("was-validated");
            },
            false,
        );
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener("click", function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute("href"));
            if (target) {
                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                });
            }
        });
    });

    // Loading state management
    const loadingElements = document.querySelectorAll("[data-loading]");
    loadingElements.forEach((element) => {
        element.addEventListener("click", function () {
            this.classList.add("loading");
            setTimeout(() => {
                this.classList.remove("loading");
            }, 3000);
        });
    });

    // Character counter for textareas
    const textareas = document.querySelectorAll("textarea[maxlength]");
    textareas.forEach((textarea) => {
        const maxLength = textarea.getAttribute("maxlength");
        const counter = document.createElement("small");
        counter.className = "text-muted";
        counter.textContent = `0/${maxLength} caracteres`;

        textarea.parentNode.appendChild(counter);

        textarea.addEventListener("input", function () {
            const currentLength = this.value.length;
            counter.textContent = `${currentLength}/${maxLength} caracteres`;

            if (currentLength > maxLength * 0.9) {
                counter.classList.add("text-warning");
            } else {
                counter.classList.remove("text-warning");
            }
        });
    });

    // Auto-hide alerts
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        if (alert.classList.contains("alert-success")) {
            setTimeout(() => {
                alert.style.opacity = "0";
                setTimeout(() => {
                    alert.remove();
                }, 300);
            }, 5000);
        }
    });

    // Image lazy loading
    const images = document.querySelectorAll("img[data-src]");
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove("loading");
                observer.unobserve(img);
            }
        });
    });

    images.forEach((img) => {
        imageObserver.observe(img);
    });

    // Mobile menu handling
    const navbarToggler = document.querySelector(".navbar-toggler");
    const navbarCollapse = document.querySelector(".navbar-collapse");

    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener("click", function () {
            navbarCollapse.classList.toggle("show");
        });
    }

    // Theme Toggle Functionality
    const themeToggle = document.getElementById("themeToggle");

    if (themeToggle) {
        const body = document.body;
        const icon = themeToggle.querySelector("i");

        // Load saved theme or default to dark
        const savedTheme = localStorage.getItem("theme") || "dark";
        body.setAttribute("data-theme", savedTheme);
        updateIcon(savedTheme);

        themeToggle.addEventListener("click", function () {
            const currentTheme = body.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";

            body.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
            updateIcon(newTheme);

            // Add a small animation feedback
            themeToggle.style.transform = "scale(0.9)";
            setTimeout(() => {
                themeToggle.style.transform = "scale(1)";
            }, 150);

            console.log("Theme changed to:", newTheme);
        });

        function updateIcon(theme) {
            if (theme === "light") {
                icon.className = "fas fa-moon";
                themeToggle.title = "Alternar para tema escuro";
            } else {
                icon.className = "fas fa-sun";
                themeToggle.title = "Alternar para tema claro";
            }
        }

        console.log("Theme toggle initialized with theme:", savedTheme);
    } else {
        console.error("Theme toggle button not found");
    }
});

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(date));
}

function showToast(message, type = "success") {
    const toastContainer =
        document.getElementById("toast-container") || createToastContainer();

    const iconMap = {
        success: '<i class="fas fa-check-circle me-2"></i>',
        danger: '<i class="fas fa-exclamation-triangle me-2"></i>',
        warning: '<i class="fas fa-exclamation-circle me-2"></i>',
        info: '<i class="fas fa-info-circle me-2"></i>',
    };

    const soundMap = {
        success: "/static/sounds/success.mp3",
        danger: "/static/sounds/error.mp3",
        warning: "/static/sounds/warning.mp3",
        info: "/static/sounds/info.mp3",
    };

    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-live", "assertive");
    toast.setAttribute("aria-atomic", "true");

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${iconMap[type] || ""}${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    const audio = new Audio(soundMap[type] || soundMap.info);
    audio.volume = 0.3;
    audio.play();

    const bsToast = new bootstrap.Toast(toast);
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

// Error handling
window.addEventListener("error", function (e) {
    console.error("JavaScript Error:", e.error);
    showToast("Ocorreu um erro inesperado. Tente novamente.", "danger");
});

// Performance monitoring
window.addEventListener("load", function () {
    if ("performance" in window) {
        const loadTime =
            performance.timing.loadEventEnd -
            performance.timing.navigationStart;
        console.log(`Page loaded in ${loadTime}ms`);
    }
});