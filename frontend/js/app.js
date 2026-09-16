document.addEventListener("DOMContentLoaded", () => {
    initRouter();
    initApiHealthCheck();
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

/* SPA Router */
function initRouter() {
    window.addEventListener("hashchange", handleRoute);
    // Initial route
    if (!window.location.hash) {
        window.location.hash = "#floor-view";
    } else {
        handleRoute();
    }
}

function handleRoute() {
    const hash = window.location.hash || "#floor-view";
    
    // Update active nav link
    document.querySelectorAll(".nav-link").forEach(link => {
        if (link.getAttribute("href") === hash) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });

    // Hide all views
    document.querySelectorAll(".app-view").forEach(view => {
        view.classList.remove("active");
    });

    // Show selected view or placeholder
    const targetViewId = `view-${hash.substring(1)}`;
    const targetView = document.getElementById(targetViewId);
    
    if (targetView) {
        targetView.classList.add("active");
    }
}

/* API Health Check */
function initApiHealthCheck() {
    checkApiHealth();
    // Poll every 15 seconds
    setInterval(checkApiHealth, 15000);
}

async function checkApiHealth() {
    try {
        const isBackendHealthy = await window.api.health();
        let isAiConnected = false;
        
        if (isBackendHealthy) {
            const cfg = await window.api.get("/ai/config");
            isAiConnected = cfg.configured;
        }

        const indicator = document.getElementById("nav-ai-config"); 
        
        if (indicator) {
            if (isAiConnected) {
                indicator.classList.add("is-connected");
            } else {
                indicator.classList.remove("is-connected");
            }
        }
    } catch (e) {
        const indicator = document.getElementById("nav-ai-config"); 
        if (indicator) indicator.classList.remove("is-connected");
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
                document.getElementById("nav-ai-config").classList.add("is-connected");
            } else {
                resultEl.textContent = res.message || "Connection Error";
                resultEl.className = "text-critical";
                document.getElementById("nav-ai-config").classList.remove("is-connected");
            }
        } catch (e) {
            resultEl.textContent = "Network Error";
            resultEl.className = "text-critical";
        }
    });

    // Initial check
    window.api.get("/ai/config").then(cfg => {
        if(cfg.configured) {
            document.getElementById("nav-ai-config").classList.add("is-connected");
        }
    }).catch(e => console.log("AI Config not available yet"));

    // Trigger Console Logic
    const btnTrigger = document.getElementById("btn-trigger");
    if (btnTrigger) {
        btnTrigger.addEventListener("click", async () => {
            const eventType = document.getElementById("trigger-event-type").value;
            const severity = document.getElementById("trigger-severity").value;
            const action = document.getElementById("trigger-action").value;
            const resultEl = document.getElementById("trigger-result");
            
            resultEl.textContent = "Triggering...";
            resultEl.style.color = "var(--color-text-muted)";
            
            try {
                const res = await window.api.post("/simulation/trigger", {
                    event_type: eventType,
                    category: "safety",
                    severity: severity,
                    proposed_action: action
                });
                
                if (res.success) {
                    resultEl.textContent = "Event triggered successfully! Event ID: " + res.event_id;
                    resultEl.style.color = "var(--status-success)";
                    refreshDashboard();
                    if(window.loadPendingActions) window.loadPendingActions();
                } else {
                    resultEl.textContent = "Failed to trigger event.";
                    resultEl.style.color = "var(--status-critical)";
                }
            } catch (e) {
                resultEl.textContent = "Network error.";
                resultEl.style.color = "var(--status-critical)";
            }
        });
    }

    // Pending Actions Logic
    window.loadPendingActions = async function() {
        const listEl = document.getElementById("pending-actions-list");
        if (!listEl) return;
        
        try {
            const data = await window.api.get("/events/pending");
            if (!data.events || data.events.length === 0) {
                listEl.innerHTML = '<p style="color: var(--color-text-secondary);">No pending actions.</p>';
                return;
            }
            
            listEl.innerHTML = "";
            data.events.forEach(e => {
                const row = document.createElement("div");
                row.style.border = "1px solid var(--color-border)";
                row.style.padding = "var(--space-4)";
                row.style.marginBottom = "var(--space-4)";
                row.style.borderRadius = "var(--radius-sm)";
                row.style.display = "flex";
                row.style.justifyContent = "space-between";
                row.style.alignItems = "center";
                
                row.innerHTML = `
                    <div>
                        <div style="font-weight: 600; margin-bottom: 4px;">Event #${e.event_id}: ${e.event_type}</div>
                        <div style="font-size: 0.875rem; color: var(--color-text-secondary); margin-bottom: 8px;">Severity: ${e.severity}</div>
                        <div style="font-size: 0.875rem; background: var(--color-surface-subtle); padding: 4px 8px; border-radius: 4px;">Proposed Action: <strong>${e.proposed_action || 'None'}</strong></div>
                    </div>
                    <div style="display: flex; gap: var(--space-2);">
                        <button class="btn btn-primary approve-btn" data-id="${e.event_id}">Approve</button>
                        <button class="btn btn-secondary deny-btn" data-id="${e.event_id}">Deny</button>
                    </div>
                `;
                listEl.appendChild(row);
            });
            
            document.querySelectorAll(".approve-btn").forEach(btn => {
                btn.addEventListener("click", (e) => processApproval(e.target.dataset.id, "APPROVE"));
            });
            document.querySelectorAll(".deny-btn").forEach(btn => {
                btn.addEventListener("click", (e) => processApproval(e.target.dataset.id, "DENY"));
            });
        } catch (err) {
            listEl.innerHTML = '<p style="color: var(--status-critical);">Unable to load pending actions.</p>';
        }
    };
    
    async function processApproval(eventId, action) {
        try {
            await window.api.post("/approvals", {
                event_id: parseInt(eventId),
                action: action,
                user: "Admin"
            });
            window.loadPendingActions();
            refreshDashboard();
        } catch (e) {
            console.error("Failed to process approval", e);
        }
    }
    
    window.loadPendingActions();

    // Reasoning Trail Logic
    const btnTestReasoning = document.getElementById("btn-test-reasoning");
    if (btnTestReasoning) {
        btnTestReasoning.addEventListener("click", async () => {
            const context = document.getElementById("reasoning-context").value;
            const action = document.getElementById("reasoning-action").value;
            const resultBox = document.getElementById("reasoning-result");
            const statusBadge = document.getElementById("reasoning-status");
            const jsonPre = document.getElementById("reasoning-json");
            
            resultBox.style.display = "block";
            statusBadge.textContent = "Processing...";
            statusBadge.className = "badge badge-neutral";
            jsonPre.textContent = "";
            
            try {
                const res = await window.api.post("/ai/reason", {
                    event_context: context,
                    proposed_action: action
                });
                
                jsonPre.textContent = JSON.stringify(res, null, 2);
                
                if (res.guardrail_status && res.guardrail_status.status === "validated") {
                    statusBadge.textContent = "ALLOWED BY GUARDRAIL";
                    statusBadge.className = "badge badge-success";
                } else if (res.guardrail_status === "BLOCKED") {
                    statusBadge.textContent = "BLOCKED BY POLICY";
                    statusBadge.className = "badge badge-critical";
                } else {
                    statusBadge.textContent = "UNKNOWN";
                    statusBadge.className = "badge badge-warning";
                }
            } catch (e) {
                statusBadge.textContent = "ERROR";
                statusBadge.className = "badge badge-critical";
                jsonPre.textContent = e.toString();
            }
        });
    }

    // Ask JARVIS Logic
    const chatInput = document.getElementById("chat-input");
    const chatSendBtn = document.getElementById("btn-chat-send");
    const chatHistory = document.getElementById("chat-history");

    if (chatSendBtn && chatInput) {
        chatSendBtn.addEventListener("click", handleChatSend);
        chatInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") handleChatSend();
        });
    }

    function handleChatSend() {
        const text = chatInput.value.trim();
        if (!text) return;
        
        // Add user message
        const userMsg = document.createElement("div");
        userMsg.style.marginBottom = "var(--space-4)";
        userMsg.style.display = "flex";
        userMsg.style.justifyContent = "flex-end";
        userMsg.innerHTML = `<div style="background: var(--color-clay); color: white; padding: var(--space-3); border-radius: var(--radius-md); font-size: 0.875rem; max-width: 80%;"><strong>You:</strong> ${text}</div>`;
        chatHistory.appendChild(userMsg);
        
        chatInput.value = "";
        chatHistory.scrollTop = chatHistory.scrollHeight;
        
        // Simulate delay then Guardrail blocked response
        setTimeout(() => {
            const aiMsg = document.createElement("div");
            aiMsg.style.marginBottom = "var(--space-4)";
            aiMsg.style.display = "flex";
            aiMsg.innerHTML = `<div style="background: var(--color-surface); padding: var(--space-3); border-radius: var(--radius-md); font-size: 0.875rem; max-width: 80%; border: 1px solid var(--status-critical);">
                <strong>JARVIS:</strong> <span class="text-critical">Action blocked by Guardrail: AI advisory currently disabled pending authorization.</span>
            </div>`;
            chatHistory.appendChild(aiMsg);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }, 800);
    }
});
