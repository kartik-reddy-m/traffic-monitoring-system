// Dashboard Real-Time Metrics Poller
document.addEventListener("DOMContentLoaded", () => {
    fetchDashboardStats();
    fetchRecentViolations();
    setInterval(fetchDashboardStats, 1500);
    setInterval(fetchRecentViolations, 3500);
});

async function fetchDashboardStats() {
    try {
        const res = await fetch("/api/monitoring/stats");
        if (!res.ok) return;
        const data = await res.json();

        // 1. KPI Cards
        const totalEl = document.getElementById("kpi-total-counted");
        const activeEl = document.getElementById("kpi-active-vehicles");
        const densityTextEl = document.getElementById("kpi-density-text");
        const densityBadgeEl = document.getElementById("kpi-density-badge");
        const densityRatioEl = document.getElementById("kpi-density-ratio");
        const violationsEl = document.getElementById("kpi-violations-count");
        const flowRateEl = document.getElementById("kpi-flow-rate");

        if (totalEl) totalEl.innerText = data.total_vehicles_counted || 0;
        if (activeEl) activeEl.innerText = data.active_vehicles_count || 0;
        if (densityTextEl) densityTextEl.innerText = data.density_level || "LOW";
        if (densityRatioEl) densityRatioEl.innerText = `${Math.round((data.density_ratio || 0) * 100)}%`;
        if (violationsEl) violationsEl.innerText = data.violations_count || 0;
        if (flowRateEl) flowRateEl.innerText = data.flow_rate_per_min || 0;

        // Density Badge Styles
        const densityColors = {
            "LOW": { text: "Density: LOW", class: "pill-green" },
            "MEDIUM": { text: "Density: MEDIUM", class: "pill-amber" },
            "HIGH": { text: "Density: HIGH", class: "pill-red" }
        };
        const dInfo = densityColors[data.density_level] || densityColors["LOW"];
        
        const topPill = document.getElementById("traffic-density-pill");
        if (topPill) {
            topPill.className = `pill ${dInfo.class}`;
            topPill.innerText = dInfo.text;
        }

        if (densityBadgeEl) {
            densityBadgeEl.innerText = `● ${data.density_level}`;
            densityBadgeEl.className = `stat-badge ${data.density_level === "HIGH" ? "badge-red" : data.density_level === "MEDIUM" ? "badge-amber" : "badge-green"}`;
        }

        // 2. Sidebar Meta
        const fpsSidebar = document.getElementById("sidebar-fps");
        if (fpsSidebar) fpsSidebar.innerText = data.fps || "0.0";

        const signalSidebar = document.getElementById("sidebar-signal-badge");
        if (signalSidebar) {
            signalSidebar.innerText = data.signal_state;
            signalSidebar.className = `badge ${data.signal_state === "RED" ? "badge-red" : data.signal_state === "YELLOW" ? "badge-amber" : "badge-green"}`;
        }

        // 3. Vehicle Categories
        const catCounts = data.counts_by_class || {};
        const carCountEl = document.getElementById("cat-car-count");
        const bikeCountEl = document.getElementById("cat-bike-count");
        const busCountEl = document.getElementById("cat-bus-count");
        const truckCountEl = document.getElementById("cat-truck-count");

        if (carCountEl) carCountEl.innerText = catCounts.car || 0;
        if (bikeCountEl) bikeCountEl.innerText = (catCounts.motorcycle || 0) + (catCounts.bicycle || 0);
        if (busCountEl) busCountEl.innerText = catCounts.bus || 0;
        if (truckCountEl) truckCountEl.innerText = catCounts.truck || 0;

        // 4. Violation Breakdown
        const vtypes = data.violations_by_type || {};
        const rlEl = document.getElementById("vtype-red-light");
        const wwEl = document.getElementById("vtype-wrong-way");
        const trEl = document.getElementById("vtype-triple-riding");
        const nhEl = document.getElementById("vtype-no-helmet");

        if (rlEl) rlEl.innerText = vtypes["Red Light Violation"] || 0;
        if (wwEl) wwEl.innerText = vtypes["Wrong-Way Driving"] || 0;
        if (trEl) trEl.innerText = vtypes["Triple Riding"] || 0;
        if (nhEl) nhEl.innerText = vtypes["No Helmet"] || 0;

        // 5. Live Monitor Header Elements
        const monitorFps = document.getElementById("monitor-fps");
        const monitorActive = document.getElementById("monitor-active-count");
        const monitorDensity = document.getElementById("monitor-density-badge");
        const monitorSignal = document.getElementById("monitor-signal-text");

        if (monitorFps) monitorFps.innerText = `FPS: ${data.fps || 0.0}`;
        if (monitorActive) monitorActive.innerText = `Active: ${data.active_vehicles_count || 0}`;
        if (monitorDensity) monitorDensity.innerText = `Density: ${data.density_level || 'LOW'}`;
        if (monitorSignal) {
            monitorSignal.innerText = data.signal_state;
            monitorSignal.className = data.signal_state === "RED" ? "text-danger" : data.signal_state === "YELLOW" ? "text-warning" : "text-success";
        }

    } catch (err) {
        console.error("Error fetching dashboard stats:", err);
    }
}

async function fetchRecentViolations() {
    try {
        const res = await fetch("/api/violations?limit=5");
        if (!res.ok) return;
        const violations = await res.json();

        const tbody = document.getElementById("dashboard-recent-violations-body");
        if (!tbody) return;

        if (violations.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No violations logged yet</td></tr>`;
            return;
        }

        tbody.innerHTML = violations.map(v => {
            const timeStr = v.timestamp ? new Date(v.timestamp).toLocaleTimeString() : "-";
            const badgeClass = v.violation_type.includes("Red") ? "badge-red" :
                               v.violation_type.includes("Wrong") ? "badge-amber" :
                               v.violation_type.includes("Triple") ? "badge-purple" : "badge-orange";

            return `
                <tr>
                    <td><strong>#${v.id}</strong></td>
                    <td>${timeStr}</td>
                    <td><span class="badge ${badgeClass}">${v.violation_type}</span></td>
                    <td>${v.vehicle_type.toUpperCase()} #${v.vehicle_id}</td>
                    <td>${Math.round(v.confidence * 100)}%</td>
                    <td>
                        <img src="${v.evidence_path}" class="table-thumb" alt="Proof"
                             onclick="openEvidenceModal('${v.evidence_path}', '${v.violation_type}', '${v.details}')" />
                    </td>
                </tr>
            `;
        }).join("");

    } catch (err) {
        console.error("Error fetching recent violations:", err);
    }
}
