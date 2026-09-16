const API_BASE = "http://localhost:8000/api";

const api = {
    async get(endpoint) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            throw error;
        }
    },
    
    async post(endpoint, data) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Error posting to ${endpoint}:`, error);
            throw error;
        }
    },
    
    async health() {
        try {
            const response = await fetch(`${API_BASE}/health`);
            return response.ok;
        } catch (e) {
            return false;
        }
    }
};

window.api = api;
