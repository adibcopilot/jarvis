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

    // Define spatial layout zones (hardcoded based on deep instruction for the 3 known machines)
    const zones = [
        { id: "ZONE 01 · PROCESSING", machines: ["machine-01"] },
        { id: "ZONE 02 · ASSEMBLY", machines: ["machine-02"] },
        { id: "ZONE 03 · PACKAGING", machines: ["machine-03"] }
    ];

    let lastNodeRect = null;

    zones.forEach((zone, index) => {
        const zoneEl = document.createElement("div");
        zoneEl.className = "map-zone";
        
        const labelEl = document.createElement("div");
        labelEl.className = "map-zone-label";
        labelEl.textContent = zone.id;
        zoneEl.appendChild(labelEl);

        const contentEl = document.createElement("div");
        contentEl.className = "map-zone-content";
        zoneEl.appendChild(contentEl);

        // Find machines for this zone
        const zoneMachines = machines.filter(m => zone.machines.includes(m.id));
        
        zoneMachines.forEach(m => {
            const node = document.createElement("div");
            node.className = "map-node";
            node.dataset.machineId = m.id;
            
            node.innerHTML = `
                <div class="map-node-title">${m.name}</div>
                <div class="map-node-line">${m.line}</div>
                <div class="badge ${getBadgeClass(m.state)}">● ${m.state}</div>
            `;
            
            // Add connector if not the first zone
            if (index > 0) {
                const connector = document.createElement("div");
                connector.className = "map-connector";
                // Approx height based on margins (8 spaces = 2rem = 32px + padding)
                connector.style.height = "64px";
                connector.style.top = "-64px";
                node.appendChild(connector);
            }

            // Interactive Click
            node.addEventListener("click", () => {
                document.querySelectorAll(".map-node").forEach(n => n.classList.remove("active"));
                node.classList.add("active");
                showMachineDetails(m);
            });

            contentEl.appendChild(node);
        });

        mapEl.appendChild(zoneEl);
    });
}

function showMachineDetails(machine) {
    const panel = document.getElementById("machine-details-panel");
    if (!panel) return;
    
    panel.style.display = "block";
    document.getElementById("detail-name").textContent = machine.name;
    document.getElementById("detail-line").textContent = machine.line;
    
    const statusEl = document.getElementById("detail-status");
    statusEl.textContent = machine.state;
    statusEl.className = `badge ${getBadgeClass(machine.state)}`;

    // Mocking an event if FAULTED for demonstration
    const eventsContainer = document.getElementById("detail-events-container");
    const eventText = document.getElementById("detail-event-text");
    
    if (machine.state === "FAULTED" || machine.state === "STOPPED") {
        eventsContainer.style.display = "block";
        eventText.textContent = "Sensor mismatch detected at joint 4.";
    } else {
        eventsContainer.style.display = "none";
    }
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
