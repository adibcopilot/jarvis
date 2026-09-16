document.addEventListener("DOMContentLoaded", () => {
    initDashboard();
});

async function initDashboard() {
    try {
        await refreshDashboard();
        // Refresh every 5 seconds
        setInterval(refreshDashboard, 5000);
    } catch (e) {
        console.error("Failed to initialize dashboard", e);
    }
}

async function refreshDashboard() {
    const statusData = await window.api.get("/status");
    const machineData = await window.api.get("/machines");
    
    updateSummary(statusData);
    updateFacilityMap(machineData.machines);
}

function updateSummary(data) {
    const overallEl = document.getElementById("summary-overall");
    const alertsEl = document.getElementById("summary-alerts");
    const approvalsEl = document.getElementById("summary-approvals");
    
    if (overallEl) {
        overallEl.textContent = data.overall;
        overallEl.className = "summary-value " + getStatusColorClass(data.overall);
    }
    
    if (alertsEl) alertsEl.textContent = data.active_alerts;
    if (approvalsEl) approvalsEl.textContent = data.pending_approvals;
}

function updateFacilityMap(machines) {
    const mapEl = document.getElementById("facility-map-container");
    if (!mapEl) return;
    
    mapEl.innerHTML = ""; // Clear
    
    machines.forEach(m => {
        const node = document.createElement("div");
        node.className = "map-node";
        
        node.innerHTML = `
            <div class="map-node-title">${m.name}</div>
            <div class="map-node-line">${m.line}</div>
            <div class="badge ${getBadgeClass(m.state)}">${m.state}</div>
            ${m.simulated ? '<div style="margin-top:8px; font-size:10px; color:var(--color-text-muted);">SIMULATED</div>' : ''}
        `;
        
        mapEl.appendChild(node);
    });
}

function getStatusColorClass(status) {
    if (status === "CRITICAL") return "text-critical";
    if (status === "WARNING") return "text-warning";
    return "text-success"; // NORMAL
}

function getBadgeClass(state) {
    if (state === "RUNNING") return "badge-success";
    if (state === "STOPPED" || state === "FAULTED") return "badge-critical";
    if (state === "UNKNOWN") return "badge-neutral";
    return "badge-info";
}

// AI Config Logic
document.addEventListener("DOMContentLoaded", () => {
    const aiNav = document.getElementById("nav-ai-config");
    const aiModal = document.getElementById("ai-modal");
    const aiModalClose = document.getElementById("ai-modal-close");
    const testBtn = document.getElementById("ai-test-btn");

    aiNav.addEventListener("click", (e) => {
        e.preventDefault();
        aiModal.style.display = "flex";
    });

    aiModalClose.addEventListener("click", () => {
        aiModal.style.display = "none";
    });

    testBtn.addEventListener("click", async () => {
        const provider = document.getElementById("ai-provider").value;
        const model = document.getElementById("ai-model").value;
        const key = document.getElementById("ai-key").value;
        const resultEl = document.getElementById("ai-test-result");

        resultEl.textContent = "Testing...";
        resultEl.className = "";

        try {
            const res = await window.api.post("/ai/test", {
                provider: provider,
                model: model,
                api_key: key
            });

            if (res.success) {
                resultEl.textContent = res.message;
                resultEl.className = "text-success";
                document.getElementById("ai-status-dot").style.color = "var(--status-success)";
                document.getElementById("ai-status-text").textContent = "Connected";
            } else {
                resultEl.textContent = res.message || "Connection Error";
                resultEl.className = "text-critical";
                document.getElementById("ai-status-dot").style.color = "var(--status-critical)";
                document.getElementById("ai-status-text").textContent = "Error";
            }
        } catch (e) {
            resultEl.textContent = "Network Error";
            resultEl.className = "text-critical";
        }
    });

    // Initial check
    window.api.get("/ai/config").then(cfg => {
        if(cfg.configured) {
            document.getElementById("ai-status-dot").style.color = "var(--status-success)";
            document.getElementById("ai-status-text").textContent = "Connected";
        }
    }).catch(e => console.log("AI Config not available yet"));
});
