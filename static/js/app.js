// Global App State & Navigation
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initGlobalRefresh();
});

function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.getAttribute("data-tab");
            navigateToTab(targetTab);
        });
    });
}

function navigateToTab(tabId) {
    // Update active nav button
    document.querySelectorAll(".nav-item").forEach(btn => {
        if (btn.getAttribute("data-tab") === tabId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Update active pane
    document.querySelectorAll(".tab-pane").forEach(pane => {
        if (pane.id === `tab-${tabId}`) {
            pane.classList.add("active");
        } else {
            pane.classList.remove("active");
        }
    });

    // Update Header Titles
    const titleMap = {
        "dashboard": { title: "Dashboard Overview", desc: "Comprehensive real-time traffic statistics and violation metrics" },
        "live-monitor": { title: "Live Traffic Surveillance", desc: "Real-time AI vehicle detection, tracking, and virtual signal calibration" },
        "active-violations": { title: "Violation Detection Feed", desc: "Instant visual alert stream of safety infractions detected on feed" },
        "violation-history": { title: "Violation History Archive", desc: "Searchable database of recorded incidents with visual snapshot evidence" },
        "about": { title: "About System", desc: "System architecture, computer vision models, and methodology documentation" }
    };

    if (titleMap[tabId]) {
        document.getElementById("page-title").innerText = titleMap[tabId].title;
        document.getElementById("page-desc").innerText = titleMap[tabId].desc;
    }

    // Tab specific refreshes
    if (tabId === "violation-history") {
        if (typeof loadViolationHistory === "function") loadViolationHistory();
    } else if (tabId === "active-violations") {
        if (typeof loadActiveViolationsStream === "function") loadActiveViolationsStream();
    }
}

function initGlobalRefresh() {
    const btnRefresh = document.getElementById("btn-refresh-all");
    if (btnRefresh) {
        btnRefresh.addEventListener("click", () => {
            showToast("Refreshing data...", "info");
            if (typeof fetchDashboardStats === "function") fetchDashboardStats();
            if (typeof loadViolationHistory === "function") loadViolationHistory();
            if (typeof loadActiveViolationsStream === "function") loadActiveViolationsStream();
        });
    }
}

// Modal handling
function openEvidenceModal(imagePath, title, details) {
    const modal = document.getElementById("evidence-modal");
    const modalImg = document.getElementById("modal-img");
    const modalTitle = document.getElementById("modal-title");
    const modalDetails = document.getElementById("modal-details");
    const downloadBtn = document.getElementById("modal-download-btn");

    modalImg.src = imagePath;
    modalTitle.innerText = title || "Violation Evidence Snapshot";
    modalDetails.innerHTML = `<p>${details || ""}</p>`;
    downloadBtn.href = imagePath;

    modal.classList.add("active");
}

function closeEvidenceModal() {
    const modal = document.getElementById("evidence-modal");
    if (modal) modal.classList.remove("active");
}

// Close modal when clicking outside modal-content
window.addEventListener("click", (e) => {
    const modal = document.getElementById("evidence-modal");
    if (e.target === modal) {
        closeEvidenceModal();
    }
});

// Toast Notifications
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type === "danger" ? "toast-danger" : type === "success" ? "toast-success" : ""}`;
    toast.innerHTML = `<span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 250);
    }, 3200);
}
