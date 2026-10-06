document.addEventListener("DOMContentLoaded", () => {
    initThemeToggle();
    initRouter();
    initApiHealthCheck();
    initDashboard();
});

function initThemeToggle() {
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    const syncToggle = () => {
        const isDay = document.documentElement.dataset.theme === "day";
        const nextTheme = isDay ? "night" : "day";
        toggle.setAttribute("aria-label", `Switch to ${nextTheme} theme`);
        toggle.setAttribute("title", `Switch to ${nextTheme} theme`);
        toggle.setAttribute("aria-pressed", String(isDay));
    };

    toggle.addEventListener("click", () => {
        const nextTheme = document.documentElement.dataset.theme === "day" ? "night" : "day";
        document.documentElement.dataset.theme = nextTheme;
        try {
            localStorage.setItem("jarvis-theme", nextTheme);
        } catch (_) {
            // The live preference still works when storage is unavailable.
        }
        syncToggle();
    });

    syncToggle();
}

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

    if (hash === "#pending-actions" && typeof window.loadPendingActions === "function") {
        window.loadPendingActions();
    }
    if (hash === "#risk-trends" && typeof window.loadRiskTrends === "function") {
        window.loadRiskTrends();
    }
    if (hash === "#worker-records" && typeof window.loadWorkerRecords === "function") {
        window.loadWorkerRecords();
    }
    if (hash === "#trigger-console" && typeof window.initTemperatureConsole === "function") {
        window.initTemperatureConsole();
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
    if (window.location.hash === "#trigger-console" && typeof window.refreshTemperatureConsole === "function") {
        window.refreshTemperatureConsole(false);
    }
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
            
            const tempLine = (m.temperature_c != null)
                ? `<div class="map-node-line">Simulated ${Number(m.temperature_c).toFixed(1)} °C · ${m.temperature_band || "nominal"}</div>`
                : "";
            node.innerHTML = `
                <div class="map-node-title">${m.name}</div>
                <div class="map-node-line">${m.line}</div>
                ${tempLine}
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

    window.initTemperatureConsole = async function() {
        const slider = document.getElementById("temp-slider");
        if (!slider || slider.dataset.bound === "1") {
            if (typeof window.refreshTemperatureConsole === "function") {
                window.refreshTemperatureConsole();
            }
            return;
        }
        slider.dataset.bound = "1";

        let debounceTimer = null;
        const applyValue = async (raw) => {
            const value = Number(raw);
            document.getElementById("temp-current-value").textContent = value.toFixed(1) + " °C";
            try {
                const res = await window.api.post("/simulation/temperature", {
                    temperature_c: value,
                    zone: "Zone 01"
                });
                renderTemperatureDecision(res);
                await window.refreshTemperatureConsole(false);
                refreshDashboard();
            } catch (e) {
                const box = document.getElementById("temp-dispatch");
                if (box) {
                    box.hidden = false;
                    box.innerHTML = `<span class="text-critical">Dispatch blocked: ${e.message}</span>`;
                }
            }
        };

        slider.addEventListener("input", () => {
            document.getElementById("temp-current-value").textContent = Number(slider.value).toFixed(1) + " °C";
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => applyValue(slider.value), 180);
        });

        await window.refreshTemperatureConsole(true);
    };

    window.initTemperatureConsole();

    window.refreshTemperatureConsole = async function(moveSlider) {
        const slider = document.getElementById("temp-slider");
        if (!slider) return;
        try {
            const data = await window.api.get("/simulation/temperature");
            if (moveSlider !== false) slider.value = data.temperature_c;
            slider.min = data.slider.min_c;
            slider.max = data.slider.max_c;
            document.getElementById("temp-slider-min").textContent = data.slider.min_c;
            document.getElementById("temp-slider-max").textContent = data.slider.max_c;
            document.getElementById("temp-current-value").textContent = Number(data.temperature_c).toFixed(1) + " °C";
            document.getElementById("temp-current-band").innerHTML = temperatureBandBadge(data.band.severity, data.band_range);
            renderTemperatureChart(data.history, data.routing_table);
            renderRoutingTable(data.routing_table);
        } catch (e) {
            console.error("Temperature console failed to load", e);
        }
    };

    function temperatureBandBadge(severity, range) {
        const cls = (severity === "critical" || severity === "high")
            ? "badge-critical"
            : (severity === "medium" ? "badge-warning" : "badge-neutral");
        return `<span class="badge ${cls}">${(severity || "nominal").toUpperCase()}</span> <span style="color:var(--color-text-muted); font-size:0.75rem;">${range || ""}</span>`;
    }

    function renderRoutingTable(rows) {
        const body = document.getElementById("temp-routing-body");
        if (!body || !rows) return;
        body.innerHTML = rows.map(r => `
            <tr>
                <td>${temperatureBandBadge(r.severity)}</td>
                <td>${r.range}</td>
                <td>${r.recipients}</td>
            </tr>
        `).join("");
    }

    function renderTemperatureDecision(res) {
        const last = document.getElementById("temp-last-decision");
        const box = document.getElementById("temp-dispatch");
        if (!last || !box) return;
        if (!res.fired) {
            last.textContent = `${res.previous_c.toFixed(1)} → ${res.temperature_c.toFixed(1)} °C · ${res.transition || "no band change"} · no event`;
            return;
        }
        const gate = res.gated
            ? "gated as PENDING (policy requires approval)"
            : `AUTO-DISPATCHED · ${res.sent} sent / ${res.failed} failed`;
        last.textContent = `Event #${res.event_id} · ${res.severity.toUpperCase()} · ${res.transition} · ${gate}`;
        const rows = (res.recipients || []).map(d => {
            const cls = d.status === "SENT" ? "badge-success" : "badge-critical";
            return `<tr>
                <td>${d.label}</td>
                <td>${d.email}</td>
                <td><span class="badge ${cls}">${d.status}</span></td>
                <td style="color:var(--color-text-muted);">${d.error || "—"}</td>
            </tr>`;
        }).join("");
        const reasoning = (res.decision && res.decision.reasoning) ? res.decision.reasoning : "";
        box.hidden = false;
        box.innerHTML = `
            <strong>Last autonomous decision</strong> — ${res.gated ? "held for approval" : "no approval step"}<br>
            ${reasoning}
            ${rows ? `<table class="temp-routing-table" style="margin-top:12px;"><thead><tr><th>Role</th><th>Address</th><th>Status</th><th>Detail</th></tr></thead><tbody>${rows}</tbody></table>` : ""}
        `;
    }

    function renderTemperatureChart(history, routing) {
        const el = document.getElementById("temp-chart");
        if (!el) return;
        const points = (history || []).map(h => ({
            t: new Date(h.timestamp).getTime(),
            y: Number(h.temperature_c)
        })).filter(p => !Number.isNaN(p.t) && !Number.isNaN(p.y));
        if (!points.length) {
            el.innerHTML = '<p style="color:var(--color-text-muted); font-size:0.8125rem;">No slider samples yet.</p>';
            return;
        }
        const now = Date.now();
        points.push({ t: now, y: points[points.length - 1].y });
        const width = 760;
        const height = 220;
        const pad = { top: 16, right: 16, bottom: 28, left: 40 };
        const w = width - pad.left - pad.right;
        const h = height - pad.top - pad.bottom;
        const minT = points[0].t;
        const maxT = points[points.length - 1].t || minT + 1;
        const minY = 20;
        const maxY = 150;
        const xOf = (t) => pad.left + ((t - minT) / Math.max(1, maxT - minT)) * w;
        const yOf = (y) => pad.top + (1 - (y - minY) / (maxY - minY)) * h;
        const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${xOf(p.t).toFixed(1)},${yOf(p.y).toFixed(1)}`).join(" ");
        const thresholds = [70, 85, 100, 120];
        const labels = { 70: "LOW", 85: "MED", 100: "HIGH", 120: "CRIT" };
        let rules = "";
        thresholds.forEach(th => {
            const y = yOf(th);
            rules += `<line x1="${pad.left}" y1="${y}" x2="${width - pad.right}" y2="${y}" stroke="var(--color-border-strong)" stroke-dasharray="4,4"/>`;
            rules += `<text x="${pad.left + 4}" y="${y - 4}" font-size="9" fill="var(--color-text-muted)">${labels[th]}</text>`;
        });
        const last = points[points.length - 1];
        const markerColor = last.y >= 100 ? "var(--status-critical)" : (last.y >= 85 ? "var(--status-warning)" : "var(--color-text-muted)");
        el.innerHTML = `<svg viewBox="0 0 ${width} ${height}" style="width:100%; height:auto;">
            ${rules}
            <path d="${path}" fill="none" stroke="var(--color-text-secondary)" stroke-width="2"/>
            <circle cx="${xOf(last.t)}" cy="${yOf(last.y)}" r="4" fill="${markerColor}"/>
            <text x="${pad.left}" y="${height - 8}" font-size="10" fill="var(--color-text-muted)">°C (simulated, slider-set)</text>
        </svg>`;
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
                row.className = "pending-action-card";
                row.style.border = "1px solid var(--color-border)";
                row.style.padding = "var(--space-4)";
                row.style.marginBottom = "var(--space-4)";
                row.style.borderRadius = "var(--radius-sm)";
                row.style.background = "var(--color-bg)";
                
                const sev = (e.severity || "NORMAL").toLowerCase();
                const badgeClass = sev === "critical" ? "badge-critical" : sev === "high" ? "badge-warning" : "badge-neutral";
                const location = e.source_file || "Line 1 (Industrial Floor)";

                row.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--space-2);">
                        <div>
                            <span class="badge ${badgeClass}" style="margin-right: 8px; font-weight: 600;">
                                ${sev.toUpperCase()} SEVERITY
                            </span>
                            <span style="font-weight: 600; font-size: 0.95rem;">Event #${e.event_id}: ${(e.event_type || '').toUpperCase()}</span>
                        </div>
                        <span style="font-size: 0.75rem; color: var(--color-text-muted);">${e.timestamp || ''}</span>
                    </div>
                    <div style="font-size: 0.8125rem; color: var(--color-text-secondary); margin-bottom: var(--space-2);">
                        <span>Location / Source: <strong>${location}</strong></span>
                    </div>
                    <div style="font-size: 0.875rem; background: var(--color-surface-subtle); padding: 8px 12px; border-radius: 4px; margin-bottom: var(--space-3); border-left: 3px solid var(--color-text);">
                        Proposed Action: <strong>${e.proposed_action || 'Immediate attention required'}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-2);">
                        <div class="email-status-feedback" id="email-feedback-${e.event_id}" style="font-size: 0.75rem;"></div>
                        <div style="display: flex; gap: var(--space-2);">
                            <button class="btn btn-secondary send-email-btn" data-id="${e.event_id}" style="font-size: 0.75rem; padding: 6px 12px; border: 1px solid var(--color-border); background: var(--color-surface); cursor: pointer;">
                                📧 Send Email Alert
                            </button>
                            <button class="btn btn-primary approve-btn" data-id="${e.event_id}">Approve</button>
                            <button class="btn btn-secondary deny-btn" data-id="${e.event_id}">Deny</button>
                        </div>
                    </div>
                `;
                listEl.appendChild(row);
            });
            
            // Wire Approval / Denial
            document.querySelectorAll(".approve-btn").forEach(btn => {
                btn.addEventListener("click", (e) => processApproval(e.target.dataset.id, "APPROVE"));
            });
            document.querySelectorAll(".deny-btn").forEach(btn => {
                btn.addEventListener("click", (e) => processApproval(e.target.dataset.id, "DENY"));
            });

            // Wire Manual Email Alert Button (Double-click protected, real SMTP dispatch)
            document.querySelectorAll(".send-email-btn").forEach(btn => {
                btn.addEventListener("click", async (ev) => {
                    const eventId = ev.currentTarget.dataset.id;
                    const button = ev.currentTarget;
                    const feedbackEl = document.getElementById(`email-feedback-${eventId}`);
                    
                    // Prevent duplicate clicks & show loading
                    button.disabled = true;
                    button.innerHTML = "⏳ Sending...";
                    if (feedbackEl) {
                        feedbackEl.textContent = "Connecting to Gmail SMTP...";
                        feedbackEl.style.color = "var(--color-text-muted)";
                    }
                    
                    try {
                        const resp = await window.api.post(`/alerts/${eventId}/email`, {
                            user: "Admin",
                            role: "Manager"
                        });
                        
                        if (resp && resp.success) {
                            button.innerHTML = "✓ Email Sent";
                            button.style.borderColor = "var(--status-success)";
                            button.style.color = "var(--status-success)";
                            if (feedbackEl) {
                                feedbackEl.textContent = `✓ Alert delivered to manager (${resp.recipient})`;
                                feedbackEl.style.color = "var(--status-success)";
                            }
                            if (typeof window.loadRiskTrends === "function") {
                                window.loadRiskTrends();
                            }
                        } else {
                            button.disabled = false;
                            button.innerHTML = "📧 Send Email Alert";
                            if (feedbackEl) {
                                feedbackEl.textContent = `⚠️ ${resp?.detail || 'Unable to deliver email alert.'}`;
                                feedbackEl.style.color = "var(--status-critical)";
                            }
                        }
                    } catch (err) {
                        button.disabled = false;
                        button.innerHTML = "📧 Send Email Alert";
                        if (feedbackEl) {
                            feedbackEl.textContent = "⚠️ Email failed: Server or SMTP error.";
                            feedbackEl.style.color = "var(--status-critical)";
                        }
                    }
                });
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
            if (typeof window.loadRiskTrends === "function") {
                window.loadRiskTrends();
            }
        } catch (e) {
            console.error("Failed to process approval", e);
        }
    }
    
    window.loadPendingActions();

    function workerStatusBadge(status) {
        const value = (status || "Clear").toLowerCase();
        if (value === "probation") return "badge-warning";
        if (value === "flagged") return "badge-critical";
        return "badge-success";
    }

    window.loadWorkerRecords = async function() {
        const body = document.getElementById("worker-records-body");
        if (!body) return;
        try {
            const data = await window.api.get("/workers");
            const workers = data.workers || [];
            if (!workers.length) {
                body.innerHTML = '<tr><td colspan="6" style="padding: var(--space-3);">No worker records found.</td></tr>';
                return;
            }
            body.innerHTML = workers.map(w => `
                <tr class="worker-row" data-code="${w.worker_code}" style="border-bottom: 1px solid var(--color-border);">
                    <td style="padding: var(--space-3); font-family: var(--font-mono);">${w.worker_code || ""}</td>
                    <td style="padding: var(--space-3); font-weight: 500;">${w.name || ""}</td>
                    <td style="padding: var(--space-3); color: var(--color-text-secondary);">${w.role || ""} · ${w.department || ""}</td>
                    <td style="padding: var(--space-3);">${w.incidents_count ?? 0}</td>
                    <td style="padding: var(--space-3);">${w.last_incident_date || "-"}</td>
                    <td style="padding: var(--space-3);"><span class="badge ${workerStatusBadge(w.status)}">${w.status || "Clear"}</span></td>
                </tr>
            `).join("");

            body.querySelectorAll(".worker-row").forEach(row => {
                row.addEventListener("click", async () => {
                    const code = row.dataset.code;
                    const card = document.getElementById("worker-detail-card");
                    const detail = document.getElementById("worker-detail-body");
                    try {
                        const payload = await window.api.get(`/workers/${encodeURIComponent(code)}`);
                        const worker = payload.worker || {};
                        const events = payload.events || [];
                        const eventHtml = events.length
                            ? events.map(e => `<li style="margin-bottom:8px;"><strong>Event #${e.event_id}</strong> (${(e.event_type || "").toUpperCase()} / ${(e.severity || "").toUpperCase()} / ${(e.approval_status || "").toUpperCase()}) — ${e.proposed_action || ""}</li>`).join("")
                            : "<li>No linked events.</li>";
                        detail.innerHTML = `
                            <p><strong>${worker.name}</strong> (${worker.worker_code}) · ${worker.shift || ""}</p>
                            <p>${worker.history_summary || "No written history on file."}</p>
                            <p style="margin-top: var(--space-3); font-size: 0.75rem; color: var(--color-text-muted);">Ask JARVIS: “What has ${worker.name} done?”</p>
                            <ul style="margin-top: var(--space-3); padding-left: 18px;">${eventHtml}</ul>
                        `;
                        card.style.display = "block";
                        card.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    } catch (err) {
                        detail.textContent = "Unable to load this worker’s history.";
                        card.style.display = "block";
                    }
                });
            });
        } catch (err) {
            body.innerHTML = '<tr><td colspan="6" style="padding: var(--space-3); color: var(--status-critical);">Unable to load worker records. Is the API running on port 8000?</td></tr>';
        }
    };

    (function initInspect() {
        const fileInput = document.getElementById("inspect-file");
        const dropzone = document.getElementById("inspect-dropzone");
        const fileLabel = document.getElementById("inspect-file-label");
        const preview = document.getElementById("inspect-preview");
        const analyzeBtn = document.getElementById("btn-inspect");
        const browseBtn = document.getElementById("btn-browse-inspect");
        const resultCard = document.getElementById("inspect-result-card");
        const resultEl = document.getElementById("inspect-result");
        const optionLabels = document.querySelectorAll(".inspect-option");
        const demoPpeBtn = document.getElementById("btn-demo-ppe");
        const demoFireBtn = document.getElementById("btn-demo-fire");
        if (!analyzeBtn || !fileInput) return;

        function selectedType() {
            const checked = document.querySelector('input[name="inspect-type"]:checked');
            return checked ? checked.value : "ppe";
        }

        function syncOptionStyles() {
            optionLabels.forEach(label => {
                const radio = label.querySelector('input[type="radio"]');
                const on = radio && radio.checked;
                label.style.border = on ? "2px solid var(--color-clay)" : "2px solid var(--color-border)";
                label.style.background = on ? "var(--color-clay-soft)" : "var(--color-surface)";
            });
        }

        optionLabels.forEach(label => {
            label.addEventListener("change", syncOptionStyles);
            label.addEventListener("click", syncOptionStyles);
        });

        function showSelectedFile(file) {
            if (!file) return;
            if (fileLabel) fileLabel.textContent = file.name;
            if (!preview) return;
            preview.style.display = "block";
            if (file.type && file.type.startsWith("image/")) {
                const url = URL.createObjectURL(file);
                preview.innerHTML = `<img src="${url}" alt="Upload preview" style="max-width:100%; max-height:220px; border-radius: 8px; border: 1px solid var(--color-border);">`;
            } else {
                preview.innerHTML = `<div style="font-size:0.875rem;">File selected: <strong>${file.name}</strong></div>`;
            }
        }

        function renderResult(data) {
            const detections = (data.detections || []).map(d => d.label || d.class).filter(Boolean).join(", ") || "none";
            const workerLine = data.worker ? `${data.worker.name} (${data.worker.worker_code})` : "Not attributed";
            const sev = (data.severity || "").toLowerCase();
            const badge = sev === "critical" || sev === "high" ? "badge-critical" : sev === "medium" ? "badge-warning" : "badge-success";
            resultEl.innerHTML = `
                <p><span class="badge ${badge}">${(data.inspection_type || "").toUpperCase()} · ${(data.severity || "").toUpperCase()}</span>
                <span class="badge badge-neutral" style="margin-left:8px;">${(data.mode || "simulated").toUpperCase()}</span></p>
                <p style="margin-top: var(--space-3);"><strong>Event ID:</strong> #${data.event_id}</p>
                <p><strong>Worker:</strong> ${workerLine}</p>
                <p><strong>Detections:</strong> ${detections}</p>
                <p><strong>Proposed action:</strong> ${data.proposed_action || ""}</p>
                <p style="color: var(--color-text-secondary);">${data.reasoning || ""}</p>
                <p style="font-size: 0.75rem; color: var(--color-text-muted); margin-top: var(--space-3);">${data.note || ""} This event is now in Pending Actions.</p>
            `;
            resultCard.style.display = "block";
            if (window.loadPendingActions) window.loadPendingActions();
        }

        fileInput.addEventListener("change", () => {
            if (fileInput.files && fileInput.files[0]) showSelectedFile(fileInput.files[0]);
        });

        if (browseBtn) {
            browseBtn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                fileInput.click();
            });
        }

        if (dropzone) {
            ["dragenter", "dragover"].forEach(ev => {
                dropzone.addEventListener(ev, (e) => {
                    e.preventDefault();
                    dropzone.classList.add("is-dragover");
                });
            });
            ["dragleave", "drop"].forEach(ev => {
                dropzone.addEventListener(ev, (e) => {
                    e.preventDefault();
                    dropzone.classList.remove("is-dragover");
                });
            });
            dropzone.addEventListener("drop", (e) => {
                const file = e.dataTransfer.files && e.dataTransfer.files[0];
                if (!file) return;
                try {
                    const transfer = new DataTransfer();
                    transfer.items.add(file);
                    fileInput.files = transfer.files;
                } catch (err) {
                    /* DataTransfer may be blocked; still preview */
                }
                showSelectedFile(file);
                window._inspectDroppedFile = file;
            });
        }

        analyzeBtn.addEventListener("click", async () => {
            const file = (fileInput.files && fileInput.files[0]) || window._inspectDroppedFile;
            if (!file) {
                resultCard.style.display = "block";
                resultEl.innerHTML = '<p style="color: var(--status-critical);">Select <strong>PPE</strong> or <strong>Fire &amp; Smoke</strong>, then choose an image with Browse files.</p>';
                return;
            }
            analyzeBtn.disabled = true;
            analyzeBtn.textContent = "Analyzing...";
            try {
                const form = new FormData();
                form.append("inspection_type", selectedType());
                form.append("file", file, file.name || "upload.jpg");
                const data = await window.api.upload("/inspect/upload", form);
                renderResult(data);
            } catch (err) {
                resultCard.style.display = "block";
                resultEl.innerHTML = `<p style="color: var(--status-critical);">Inspection failed: ${err.message || "API error. Is the backend running on port 8000?"}</p>`;
            } finally {
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = "Analyze Media";
            }
        });

        async function runDemo(kind) {
            const radio = document.querySelector(`input[name="inspect-type"][value="${kind}"]`);
            if (radio) {
                radio.checked = true;
                syncOptionStyles();
            }
            try {
                const data = await window.api.post("/inspect/demo", { inspection_type: kind });
                renderResult(data);
            } catch (err) {
                resultCard.style.display = "block";
                resultEl.innerHTML = `<p style="color: var(--status-critical);">Sample inspection failed: ${err.message || "API error"}</p>`;
            }
        }

        if (demoPpeBtn) demoPpeBtn.addEventListener("click", () => runDemo("ppe"));
        if (demoFireBtn) demoFireBtn.addEventListener("click", () => runDemo("fire"));
    })();

    // ── Webcam Inspect ──────────────────────────────────────────────────────
    (function initWebcam() {
        const tabUpload  = document.getElementById("tab-upload");
        const tabWebcam  = document.getElementById("tab-webcam");
        const panelUpload  = document.getElementById("panel-upload");
        const panelWebcam  = document.getElementById("panel-webcam");
        if (!tabUpload || !tabWebcam) return;

        // ── Tab switching ────────────────────────────────────────────────
        function activateTab(which) {
            const isWebcam = (which === "webcam");
            tabUpload.style.background  = isWebcam ? "var(--color-surface)"  : "var(--color-clay)";
            tabUpload.style.color       = isWebcam ? "var(--color-text-secondary)" : "#fff";
            tabWebcam.style.background  = isWebcam ? "var(--color-clay)"     : "var(--color-surface)";
            tabWebcam.style.color       = isWebcam ? "#fff" : "var(--color-text-secondary)";
            panelUpload.style.display  = isWebcam ? "none"  : "block";
            panelWebcam.style.display  = isWebcam ? "block" : "none";
            if (!isWebcam) stopCamera();
        }

        tabUpload.addEventListener("click", () => activateTab("upload"));
        tabWebcam.addEventListener("click", () => activateTab("webcam"));

        // ── DOM refs ────────────────────────────────────────────────────
        const video         = document.getElementById("webcam-video");
        const canvas        = document.getElementById("webcam-canvas");
        const placeholder   = document.getElementById("webcam-placeholder");
        const scanOverlay   = document.getElementById("webcam-scan-overlay");
        const snapshotRow   = document.getElementById("webcam-snapshot-row");
        const snapshotImg   = document.getElementById("webcam-snapshot-img");
        const btnStart      = document.getElementById("btn-webcam-start");
        const btnStop       = document.getElementById("btn-webcam-stop");
        const btnCapture    = document.getElementById("btn-webcam-capture");
        const btnAnalyze    = document.getElementById("btn-webcam-analyze");
        const resultCard    = document.getElementById("inspect-result-card");
        const resultEl      = document.getElementById("inspect-result");

        let stream = null;
        let capturedDataURL = null;
        let autoCaptureTimer = null;
        let isAnalyzing = false;

        function selectedType() {
            const checked = document.querySelector('input[name="inspect-type"]:checked');
            return checked ? checked.value : "ppe";
        }

        // ── Camera start/stop ───────────────────────────────────────────
        async function startCamera() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720, facingMode: "environment" }, audio: false });
                video.srcObject = stream;
                placeholder.style.display = "none";
                scanOverlay.style.display  = "block";
                btnStart.disabled   = true;
                btnStop.disabled    = false;
                btnCapture.disabled = false;
                
                // Start automatic capture loop
                autoCaptureLoop();
            } catch (err) {
                resultCard.style.display = "block";
                resultEl.innerHTML = `<p style="color:var(--status-critical);">Camera access denied or unavailable: <strong>${err.message}</strong>.<br>
                    Check browser permissions (the address bar padlock icon) and reload, then try again.</p>`;
            }
        }

        function stopCamera() {
            if (autoCaptureTimer) {
                clearTimeout(autoCaptureTimer);
                autoCaptureTimer = null;
            }
            if (stream) {
                stream.getTracks().forEach(t => t.stop());
                stream = null;
            }
            video.srcObject = null;
            placeholder.style.display = "flex";
            scanOverlay.style.display  = "none";
            btnStart.disabled   = false;
            btnStop.disabled    = true;
            btnCapture.disabled = true;
            btnAnalyze.disabled = true;
            capturedDataURL     = null;
            if (snapshotRow) snapshotRow.style.display = "none";
        }

        function captureFrame() {
            if (!stream || !video.videoWidth) return;
            canvas.width  = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0);
            capturedDataURL = canvas.toDataURL("image/jpeg", 0.9);
            snapshotImg.src = capturedDataURL;
            snapshotRow.style.display = "block";
            btnAnalyze.disabled = false;

            // Flash effect on the scan overlay
            scanOverlay.style.opacity = "0.3";
            setTimeout(() => { scanOverlay.style.opacity = "1"; }, 120);
        }

        // ── Analyze captured frame ───────────────────────────────────────
        async function analyzeFrame() {
            if (!capturedDataURL || isAnalyzing) return;
            isAnalyzing = true;
            btnAnalyze.disabled = true;
            btnAnalyze.textContent = "Analyzing...";
            try {
                // Convert dataURL → Blob → FormData so the backend gets a proper file upload
                const res = await fetch(capturedDataURL);
                const blob = await res.blob();
                const form = new FormData();
                const kind = selectedType();
                form.append("inspection_type", kind);
                form.append("file", blob, `webcam_${kind}_${Date.now()}.jpg`);

                const data = await window.api.upload("/inspect/upload", form);
                renderWebcamResult(data);
            } catch (err) {
                resultCard.style.display = "block";
                resultEl.innerHTML = `<p style="color:var(--status-critical);">Inspection failed: ${err.message || "API error. Is the backend running on port 8000?"}</p>`;
            } finally {
                btnAnalyze.disabled = false;
                btnAnalyze.textContent = "🔍 Analyze Captured Frame";
                isAnalyzing = false;
            }
        }
        
        async function autoCaptureLoop() {
            if (!stream) return;
            if (!isAnalyzing) {
                captureFrame();
                await analyzeFrame();
            }
            autoCaptureTimer = setTimeout(autoCaptureLoop, 2000); // Auto-capture every 2s
        }

        function renderWebcamResult(data) {
            const detections = (data.detections || []).map(d => d.label || d.class).filter(Boolean).join(", ") || "none";
            const workerLine = data.worker ? `${data.worker.name} (${data.worker.worker_code})` : "Not attributed";
            const sev = (data.severity || "").toLowerCase();
            const badge = sev === "critical" || sev === "high" ? "badge-critical" : sev === "medium" ? "badge-warning" : "badge-success";
            resultEl.innerHTML = `
                <div style="margin-bottom:10px;">
                    <span style="display:inline-block; padding:3px 8px; background:rgba(255,255,255,0.05); border-radius:6px; font-size:0.7rem; color:var(--color-text-muted); margin-bottom:6px;">📷 WEBCAM CAPTURE</span>
                </div>
                <p><span class="badge ${badge}">${(data.inspection_type || "").toUpperCase()} · ${(data.severity || "").toUpperCase()}</span>
                <span class="badge badge-neutral" style="margin-left:8px;">${(data.mode || "simulated").toUpperCase()}</span></p>
                <p style="margin-top: var(--space-3);"><strong>Event ID:</strong> #${data.event_id}</p>
                <p><strong>Worker:</strong> ${workerLine}</p>
                <p><strong>Detections:</strong> ${detections}</p>
                <p><strong>Proposed action:</strong> ${data.proposed_action || ""}</p>
                <p style="color: var(--color-text-secondary);">${data.reasoning || ""}</p>
                <p style="font-size: 0.75rem; color: var(--color-text-muted); margin-top: var(--space-3);">${data.note || ""} This event is now in Pending Actions.</p>
            `;
            resultCard.style.display = "block";
            if (window.loadPendingActions) window.loadPendingActions();
        }

        // ── Button listeners ─────────────────────────────────────────────
        if (btnStart)   btnStart.addEventListener("click", startCamera);
        if (btnStop)    btnStop.addEventListener("click", stopCamera);
        if (btnCapture) btnCapture.addEventListener("click", captureFrame);
        if (btnAnalyze) btnAnalyze.addEventListener("click", analyzeFrame);
    })();

    // Risk Trends & Analytics Logic (Real SVG Chart & Live Audit Trail)
    window.loadRiskTrends = async function() {
        const chartContainer = document.getElementById("trends-chart-container");
        const emailAuditList = document.getElementById("trends-email-audit-list");
        const ppeStat = document.getElementById("trends-stat-ppe");
        const mechStat = document.getElementById("trends-stat-mechanical");
        const resStat = document.getElementById("trends-stat-resolution");

        try {
            const trends = await window.api.get("/trends");
            if (ppeStat) ppeStat.textContent = trends.ppe_violations_30d || "+12%";
            if (mechStat) mechStat.textContent = trends.mechanical_faults_30d || "-5%";
            if (resStat) resStat.textContent = trends.avg_resolution_time || "4.2m";

            if (chartContainer && trends.timeline) {
                const timeline = trends.timeline;
                const width = 800;
                const height = 220;
                const padding = { top: 20, right: 20, bottom: 35, left: 35 };
                const chartW = width - padding.left - padding.right;
                const chartH = height - padding.top - padding.bottom;

                const maxVal = Math.max(4, ...timeline.map(d => Math.max(d.ppe || 0, d.mechanical || 0, d.fire || 0, d.total || 0)));
                const barGroupW = chartW / timeline.length;
                const singleBarW = Math.max(8, (barGroupW - 28) / 3);

                let svg = `<svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">`;

                // Horizontal dashed grid lines
                for (let step = 0; step <= 4; step++) {
                    const yVal = Math.round((maxVal / 4) * step);
                    const yPos = padding.top + chartH - (chartH / 4) * step;
                    svg += `<line x1="${padding.left}" y1="${yPos}" x2="${width - padding.right}" y2="${yPos}" stroke="var(--color-border)" stroke-dasharray="3,3" opacity="0.6"/>`;
                    svg += `<text x="${padding.left - 8}" y="${yPos + 4}" text-anchor="end" font-size="10" fill="var(--color-text-muted)">${yVal}</text>`;
                }

                // Render clustered bars
                timeline.forEach((d, idx) => {
                    const groupX = padding.left + idx * barGroupW + 14;
                    const ppeH = ((d.ppe || 0) / maxVal) * chartH;
                    const mechH = ((d.mechanical || 0) / maxVal) * chartH;
                    const fireH = ((d.fire || 0) / maxVal) * chartH;

                    // 1. Safety / PPE Bar (warning state)
                    const ppeY = padding.top + chartH - ppeH;
                    svg += `<rect x="${groupX}" y="${ppeY}" width="${singleBarW}" height="${Math.max(2, ppeH)}" fill="var(--signal-amber)" rx="2">
                        <title>${d.date}: ${d.ppe} Safety/PPE Incident(s)</title>
                    </rect>`;

                    // 2. Mechanical Bar (neutral operational series)
                    const mechX = groupX + singleBarW + 2;
                    const mechY = padding.top + chartH - mechH;
                    svg += `<rect x="${mechX}" y="${mechY}" width="${singleBarW}" height="${Math.max(2, mechH)}" fill="var(--mist)" rx="2">
                        <title>${d.date}: ${d.mechanical} Mechanical Fault(s)</title>
                    </rect>`;

                    // 3. Fire Bar (critical state)
                    const fireX = mechX + singleBarW + 2;
                    const fireY = padding.top + chartH - fireH;
                    svg += `<rect x="${fireX}" y="${fireY}" width="${singleBarW}" height="${Math.max(2, fireH)}" fill="var(--signal-red)" rx="2">
                        <title>${d.date}: ${d.fire} Fire Alert(s)</title>
                    </rect>`;

                    // X-axis label
                    const labelX = groupX + singleBarW * 1.5;
                    svg += `<text x="${labelX}" y="${height - 12}" text-anchor="middle" font-size="11" fill="var(--color-text-secondary)">${d.date}</text>`;
                });

                svg += `</svg>`;
                chartContainer.innerHTML = svg;
            }

            // Load live email audit trail
            if (emailAuditList) {
                const auditData = await window.api.get("/alerts/audit");
                if (!auditData.notifications || auditData.notifications.length === 0) {
                    emailAuditList.innerHTML = '<p style="color: var(--color-text-muted); font-size: 0.875rem;">No manual email alerts dispatched yet. Click "Send Email Alert" on any pending event to test escalation.</p>';
                } else {
                    let tableHtml = `
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.8125rem;">
                            <thead>
                                <tr style="border-bottom: 1px solid var(--color-border); text-align: left; color: var(--color-text-secondary);">
                                    <th style="padding: 8px 4px;">Log ID</th>
                                    <th style="padding: 8px 4px;">Event Ref</th>
                                    <th style="padding: 8px 4px;">Recipient</th>
                                    <th style="padding: 8px 4px;">Status</th>
                                    <th style="padding: 8px 4px;">Timestamp</th>
                                    <th style="padding: 8px 4px;">Dispatched By</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;
                    auditData.notifications.forEach(n => {
                        const badgeClass = n.status === "SENT" ? "badge-success" : "badge-critical";
                        tableHtml += `
                            <tr style="border-bottom: 1px solid var(--color-border);">
                                <td style="padding: 8px 4px; font-weight: 500;">#${n.notification_id}</td>
                                <td style="padding: 8px 4px;">Event #${n.event_id}</td>
                                <td style="padding: 8px 4px; color: var(--color-text-secondary);">${n.recipient}</td>
                                <td style="padding: 8px 4px;"><span class="badge ${badgeClass}">${n.status}</span></td>
                                <td style="padding: 8px 4px; font-size: 0.75rem;">${n.sent_at}</td>
                                <td style="padding: 8px 4px; color: var(--color-text-secondary);">${n.sent_by}</td>
                            </tr>
                        `;
                    });
                    tableHtml += `</tbody></table>`;
                    emailAuditList.innerHTML = tableHtml;
                }
            }
        } catch (e) {
            if (chartContainer) chartContainer.innerHTML = '<p style="color: var(--status-critical); font-size: 0.875rem;">Unable to load risk trends data.</p>';
        }
    };

    window.loadRiskTrends();

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

    // Ask JARVIS Logic (Guardrail Validation + LLM Response)
    const chatInput = document.getElementById("chat-input");
    const chatSendBtn = document.getElementById("btn-chat-send");
    const chatHistory = document.getElementById("chat-history");

    if (chatSendBtn && chatInput) {
        chatSendBtn.addEventListener("click", () => handleChatSend());
        chatInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") handleChatSend();
        });
    }

    // Quick Prompt Suggestion Chips
    document.querySelectorAll(".chip-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const prompt = btn.getAttribute("data-prompt");
            if (prompt && chatInput) {
                chatInput.value = prompt;
                handleChatSend();
            }
        });
    });

    function formatMarkdown(text) {
        if (!text) return "";
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code style="background:var(--inline-code-bg); padding:2px 5px; border-radius:3px; font-family:var(--font-mono); font-size:0.8em;">$1</code>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n• /g, '<br>• ')
            .replace(/\n- /g, '<br>• ')
            .replace(/\n/g, '<br>');
        return formatted;
    }

    async function handleChatSend() {
        const text = chatInput.value.trim();
        if (!text) return;
        
        // Add user message
        const userMsg = document.createElement("div");
        userMsg.style.marginBottom = "var(--space-4)";
        userMsg.style.display = "flex";
        userMsg.style.justifyContent = "flex-end";
        userMsg.innerHTML = `<div style="background: var(--color-clay); color: var(--color-on-accent); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); font-size: 0.875rem; max-width: 80%; box-shadow: var(--shadow-card);">
            <strong>You:</strong> ${text}
        </div>`;
        chatHistory.appendChild(userMsg);
        
        chatInput.value = "";
        chatHistory.scrollTop = chatHistory.scrollHeight;
        
        // Show temporary thinking indicator
        const thinkingId = "thinking-" + Date.now();
        const thinkingMsg = document.createElement("div");
        thinkingMsg.id = thinkingId;
        thinkingMsg.style.marginBottom = "var(--space-4)";
        thinkingMsg.style.display = "flex";
        thinkingMsg.innerHTML = `<div style="background: var(--color-surface); padding: var(--space-3); border-radius: var(--radius-md); font-size: 0.85rem; max-width: 85%; border: 1px dashed var(--color-border); color: var(--color-muted);">
            <span style="display:inline-block; animation: pulse 1.5s infinite;">🔍</span> Evaluating query via Safety Guardrails...
        </div>`;
        chatHistory.appendChild(thinkingMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        try {
            const data = await api.post("/ai/chat", { message: text, user: "Supervisor" });
            const loader = document.getElementById(thinkingId);
            if (loader) loader.remove();

            const aiMsg = document.createElement("div");
            aiMsg.style.marginBottom = "var(--space-4)";
            aiMsg.style.display = "flex";

            if (data.allowed) {
                // Guardrail passed: Project query answered by LLM / Local Reasoning
                aiMsg.innerHTML = `<div style="background: var(--color-surface); padding: var(--space-4); border-radius: var(--radius-md); font-size: 0.875rem; max-width: 85%; border: 1px solid var(--status-normal); box-shadow: var(--shadow-card); line-height: 1.55;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid var(--message-rule); padding-bottom:6px;">
                        <span class="badge badge-normal" style="font-size:0.7rem;">✓ GUARDRAIL: PASSED</span>
                        <span style="font-size:0.75rem; color:var(--color-muted); font-family:var(--font-mono);">${data.provider || 'JARVIS Reasoning Engine'}</span>
                    </div>
                    <div>${formatMarkdown(data.response)}</div>
                </div>`;
            } else {
                // Guardrail blocked: Dangerous / Out-of-scope action intercepted
                aiMsg.innerHTML = `<div style="background: var(--color-surface); padding: var(--space-4); border-radius: var(--radius-md); font-size: 0.875rem; max-width: 85%; border: 1px solid var(--status-critical); box-shadow: var(--shadow-card); line-height: 1.55;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid var(--critical-message-rule); padding-bottom:6px;">
                        <span class="badge badge-critical" style="font-size:0.7rem;">✕ GUARDRAIL: BLOCKED</span>
                        <span style="font-size:0.75rem; color:var(--status-critical); font-family:var(--font-mono);">POLICY: ${data.policy || 'SYSTEM_RESTRICTION'}</span>
                    </div>
                    <div>${formatMarkdown(data.response)}</div>
                </div>`;
            }

            chatHistory.appendChild(aiMsg);
            chatHistory.scrollTop = chatHistory.scrollHeight;

        } catch (error) {
            const loader = document.getElementById(thinkingId);
            if (loader) loader.remove();

            const errorMsg = document.createElement("div");
            errorMsg.style.marginBottom = "var(--space-4)";
            errorMsg.style.display = "flex";
            errorMsg.innerHTML = `<div style="background: var(--color-surface); padding: var(--space-3); border-radius: var(--radius-md); font-size: 0.875rem; max-width: 85%; border: 1px solid var(--status-critical); color: var(--status-critical);">
                <strong>Communication Error:</strong> Could not connect to JARVIS API at :8000. Please ensure the backend is running.
            </div>`;
            chatHistory.appendChild(errorMsg);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
    }

    if (window.location.hash === "#worker-records") {
        window.loadWorkerRecords();
    }
});
