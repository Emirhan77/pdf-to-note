/**
 * PDF Not — shared UI interactions
 */

function initFileDropzone() {
    const dropzone = document.getElementById("file-dropzone");
    const input = document.getElementById("pdf-file-input");
    const fileNameEl = document.getElementById("selected-file-name");
    if (!dropzone || !input) return;

    const showFile = (file) => {
        if (!file) return;
        if (fileNameEl) {
            fileNameEl.textContent = file.name;
            fileNameEl.hidden = false;
        }
        dropzone.classList.add("has-file");
    };

    dropzone.addEventListener("click", () => input.click());
    dropzone.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            input.click();
        }
    });

    input.addEventListener("change", () => {
        if (input.files?.[0]) showFile(input.files[0]);
    });

    ["dragenter", "dragover"].forEach((ev) => {
        dropzone.addEventListener(ev, (e) => {
            e.preventDefault();
            dropzone.classList.add("is-dragover");
        });
    });

    ["dragleave", "drop"].forEach((ev) => {
        dropzone.addEventListener(ev, (e) => {
            e.preventDefault();
            dropzone.classList.remove("is-dragover");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        const file = e.dataTransfer?.files?.[0];
        if (!file || file.type !== "application/pdf") return;
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        showFile(file);
    });
}

function initAnalysisLoading() {
    const form = document.getElementById("analysis-form");
    const submitButton = document.getElementById("analysis-submit");
    const overlay = document.getElementById("analysis-loading");
    const progress = document.getElementById("loading-progress");
    const percent = document.getElementById("loading-percent");
    const message = document.getElementById("loading-message");
    if (!form || !overlay) return;

    const loadingMessages = [
        "PDF metni okunuyor ve temizleniyor.",
        "Önemli başlıklar ve kavramlar seçiliyor.",
        "LLM için kaynak paketi hazırlanıyor.",
        "Ders notu ve sorular üretiliyor.",
        "Sonuç kaydediliyor, birazdan yönlendirileceksin."
    ];

    let loadingTimer = null;

    form.addEventListener("submit", () => {
        overlay.classList.add("is-visible");
        overlay.setAttribute("aria-hidden", "false");
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "Analiz Ediliyor…";
        }

        let value = 4;
        let messageIndex = 0;
        if (progress) progress.style.width = `${value}%`;
        if (percent) percent.textContent = `${value}%`;

        loadingTimer = window.setInterval(() => {
            const remaining = 96 - value;
            const step = Math.max(0.2, remaining * 0.055);
            value = Math.min(96, value + step);
            if (progress) progress.style.width = `${Math.round(value)}%`;
            if (percent) percent.textContent = `${Math.round(value)}%`;

            const nextIndex = Math.min(
                loadingMessages.length - 1,
                Math.floor((value / 100) * loadingMessages.length)
            );
            if (nextIndex !== messageIndex && message) {
                messageIndex = nextIndex;
                message.textContent = loadingMessages[messageIndex];
            }
        }, 900);
    });

    window.addEventListener("pageshow", () => {
        if (loadingTimer) window.clearInterval(loadingTimer);
        overlay.classList.remove("is-visible");
        overlay.setAttribute("aria-hidden", "true");
        if (progress) progress.style.width = "0%";
        if (percent) percent.textContent = "0%";
        if (message) message.textContent = loadingMessages[0];
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = "Analizi Başlat";
        }
    });
}

function markActiveNav() {
    const path = window.location.pathname.replace(/\/$/, "") || "/";
    document.querySelectorAll(".topbar nav a[data-nav]").forEach((link) => {
        const href = (link.getAttribute("href") || "").replace(/\/$/, "") || "/";
        const isHistory = href.includes("history") && path.includes("history");
        const isApp = href.includes("/app") && path.includes("/app");
        link.classList.toggle("is-active", isHistory || isApp);
    });
}

const EMAIL_PATTERN = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

function initLoginValidation() {
    const form = document.getElementById("login-form");
    const emailInput = document.getElementById("email");
    const errorEl = document.getElementById("email-error");
    if (!form || !emailInput || !errorEl) return;

    const setError = (message) => {
        if (message) {
            errorEl.textContent = message;
            errorEl.hidden = false;
            emailInput.classList.add("input-invalid");
            emailInput.setAttribute("aria-invalid", "true");
        } else {
            errorEl.textContent = "";
            errorEl.hidden = true;
            emailInput.classList.remove("input-invalid");
            emailInput.setAttribute("aria-invalid", "false");
        }
    };

    const validateEmail = () => {
        const value = emailInput.value.trim();
        if (!value) {
            setError("E-posta adresi gereklidir.");
            return false;
        }
        if (!EMAIL_PATTERN.test(value)) {
            setError("Geçerli bir e-posta adresi girin (örnek: ad@universite.edu.tr).");
            return false;
        }
        setError("");
        return true;
    };

    emailInput.addEventListener("input", () => {
        if (emailInput.classList.contains("input-invalid")) validateEmail();
    });

    emailInput.addEventListener("blur", validateEmail);

    form.addEventListener("submit", (e) => {
        if (!validateEmail()) {
            e.preventDefault();
            emailInput.focus();
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initLoginValidation();
    initFileDropzone();
    initAnalysisLoading();
    markActiveNav();
});
