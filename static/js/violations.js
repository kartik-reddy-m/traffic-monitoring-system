// Violations Stream & History Manager
let lastKnownViolationId = 0;

document.addEventListener("DOMContentLoaded", () => {
    loadActiveViolationsStream();
    loadViolationHistory();
    initViolationFilters();
    initClearAll();

    // Periodic stream check
    setInterval(loadActiveViolationsStream, 3000);
});

async function loadActiveViolationsStream() {
    try {
        const res = await fetch("/api/violations?limit=12");
        if (!res.ok) return;
        const violations = await res.json();

        const container = document.getElementById("violation-cards-stream");
        const countBadge = document.getElementById("live-violations-badge");
        if (!container) return;

        if (countBadge) countBadge.innerText = `${violations.length} Violations`;

        if (violations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#9989;</div>
                    <h4>No violations currently flagged</h4>
                    <p class="text-muted">When a vehicle runs a red light, drives wrong-way, or violates passenger/helmet rules, evidence will appear here immediately.</p>
                </div>
            `;
            return;
        }

        // Check for new violations to notify
        if (violations.length > 0 && violations[0].id > lastKnownViolationId) {
            if (lastKnownViolationId !== 0) {
                showToast(`New ${violations[0].violation_type} flagged! (#${violations[0].id})`, "danger");
            }
            lastKnownViolationId = violations[0].id;
        }

        container.innerHTML = violations.map(v => {
            const timeStr = v.timestamp ? new Date(v.timestamp).toLocaleString() : "-";
            const badgeClass = v.violation_type.includes("Red") ? "badge-red" :
                               v.violation_type.includes("Wrong") ? "badge-amber" :
                               v.violation_type.includes("Triple") ? "badge-purple" : "badge-orange";

            return `
                <div class="violation-card">
                    <img src="${v.evidence_path}" alt="${v.violation_type}"
                         onclick="openEvidenceModal('${v.evidence_path}', '${v.violation_type}', '${v.details}')" />
                    <div class="vcard-body">
                        <div class="vcard-header">
                            <span class="badge ${badgeClass}">${v.violation_type}</span>
                            <strong>#${v.id}</strong>
                        </div>
                        <div style="font-weight:600; font-size:13px; margin-top:4px;">
                            ${v.vehicle_type.toUpperCase()} #${v.vehicle_id} (Conf: ${Math.round(v.confidence * 100)}%)
                        </div>
                        <div class="vcard-meta">&#128337; ${timeStr}</div>
                        <div class="vcard-meta" style="margin-top:2px;">&#127909; Source: ${v.video_source || "Live Stream"}</div>
                        <button class="btn btn-secondary btn-sm btn-block mt-8"
                                onclick="openEvidenceModal('${v.evidence_path}', '${v.violation_type}', '${v.details}')">
                            &#128269; View Evidence Proof
                        </button>
                    </div>
                </div>
            `;
        }).join("");

    } catch (e) {
        console.error("Error loading active violations stream:", e);
    }
}

async function loadViolationHistory() {
    const type = document.getElementById("filter-violation-type")?.value || "all";
    const vehicle = document.getElementById("filter-vehicle-type")?.value || "all";
    const search = document.getElementById("filter-search")?.value || "";

    const params = new URLSearchParams();
    if (type !== "all") params.append("violation_type", type);
    if (vehicle !== "all") params.append("vehicle_type", vehicle);
    if (search.trim()) params.append("search", search.trim());
    params.append("limit", "100");

    try {
        const res = await fetch(`/api/violations?${params.toString()}`);
        if (!res.ok) return;
        const records = await res.json();

        const tbody = document.getElementById("history-table-body");
        if (!tbody) return;

        if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">No matching violation records found</td></tr>`;
            return;
        }

        tbody.innerHTML = records.map(r => {
            const timeStr = r.timestamp ? new Date(r.timestamp).toLocaleString() : "-";
            const badgeClass = r.violation_type.includes("Red") ? "badge-red" :
                               r.violation_type.includes("Wrong") ? "badge-amber" :
                               r.violation_type.includes("Triple") ? "badge-purple" : "badge-orange";

            return `
                <tr>
                    <td><strong>#${r.id}</strong></td>
                    <td>${timeStr}</td>
                    <td><span class="badge ${badgeClass}">${r.violation_type}</span></td>
                    <td>${r.vehicle_type.toUpperCase()}</td>
                    <td>#${r.vehicle_id}</td>
                    <td>${Math.round(r.confidence * 100)}%</td>
                    <td><span class="text-muted">${r.video_source || "Live"}</span></td>
                    <td>
                        <img src="${r.evidence_path}" class="table-thumb" alt="Proof"
                             onclick="openEvidenceModal('${r.evidence_path}', '${r.violation_type}', '${r.details}')" />
                    </td>
                    <td>
                        <button class="btn btn-danger btn-sm" onclick="deleteViolationRecord(${r.id})" title="Delete record">
                            &#128465;
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

    } catch (e) {
        console.error("Error loading violation history:", e);
    }
}

function initViolationFilters() {
    const btnFilter = document.getElementById("btn-apply-filters");
    if (btnFilter) {
        btnFilter.addEventListener("click", () => {
            loadViolationHistory();
        });
    }

    const typeSel = document.getElementById("filter-violation-type");
    const vehSel = document.getElementById("filter-vehicle-type");
    const searchInp = document.getElementById("filter-search");

    if (typeSel) typeSel.addEventListener("change", loadViolationHistory);
    if (vehSel) vehSel.addEventListener("change", loadViolationHistory);
    if (searchInp) {
        searchInp.addEventListener("keyup", (e) => {
            if (e.key === "Enter") loadViolationHistory();
        });
    }
}

async function deleteViolationRecord(id) {
    if (!confirm(`Are you sure you want to delete violation record #${id}?`)) return;

    try {
        const res = await fetch(`/api/violations/${id}`, { method: "DELETE" });
        if (res.ok) {
            showToast(`Record #${id} deleted`, "success");
            loadViolationHistory();
            loadActiveViolationsStream();
            if (typeof fetchDashboardStats === "function") fetchDashboardStats();
        } else {
            showToast("Failed to delete record", "danger");
        }
    } catch (e) {
        showToast("Error connecting to server", "danger");
    }
}

function initClearAll() {
    const btnClear = document.getElementById("btn-clear-violations");
    if (btnClear) {
        btnClear.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to clear ALL violation records and evidence?")) return;

            try {
                const res = await fetch("/api/violations/clear", { method: "POST" });
                if (res.ok) {
                    showToast("All violation records cleared", "success");
                    loadViolationHistory();
                    loadActiveViolationsStream();
                    if (typeof fetchDashboardStats === "function") fetchDashboardStats();
                }
            } catch (e) {
                showToast("Failed to clear records", "danger");
            }
        });
    }
}
