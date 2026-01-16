const API_BASE = window.location.origin;

let currentRole = 'manufacturer';

// Role Configuration
const ROLE_CONFIG = {
    'cnf': { title: "C&F Agent Portal", actions: ["RECEIVED_AT_CNF", "DISPATCHED_TO_DISTRIBUTOR"] },
    'distributor': { title: "Distributor Portal", actions: ["RECEIVED_AT_DISTRIBUTOR", "DISPATCHED_TO_RETAILER"] },
    'retailer': { title: "Retailer Portal", actions: ["RECEIVED_AT_STORE", "SOLD_TO_CONSUMER"] }
};

function switchRole(role) {
    currentRole = role;

    // Update Sidebar
    document.querySelectorAll('.role-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`button[onclick="switchRole('${role}')"]`).classList.add('active');

    // Update Sections
    document.querySelectorAll('.section').forEach(sec => sec.classList.remove('active'));

    if (role === 'manufacturer') {
        document.getElementById('manufacturer').classList.add('active');
    } else if (role === 'consumer') {
        document.getElementById('consumer').classList.add('active');
    } else {
        // Shared Worker View
        document.getElementById('supply-worker').classList.add('active');
        const config = ROLE_CONFIG[role];
        document.getElementById('workerTitle').innerText = config.title;

        // Populate Actions
        const select = document.getElementById('actionType');
        select.innerHTML = '';
        config.actions.forEach(action => {
            const opt = document.createElement('option');
            opt.value = action;
            opt.innerText = action.replace(/_/g, ' ');
            select.appendChild(opt);
        });
    }
}

// 1. Manufacturer: Create Batch

async function createBatch() {
    const batchId = document.getElementById('batchId').value;
    const mfgDate = document.getElementById('mfgDate').value;
    const expDate = document.getElementById('expDate').value;

    if (!batchId || !mfgDate || !expDate) return alert("Please fill all fields");

    const payload = {
        batch_id: batchId,
        product_gtin: document.getElementById('gtin').value,
        manufacturer_license: document.getElementById('license').value,
        mfg_date: mfgDate,
        exp_date: expDate,
        batch_size: parseInt(document.getElementById('size').value)
    };

    try {
        document.getElementById('batchResult').innerHTML = "⏳ Minting on Blockchain...";

        const res = await fetch(`${API_BASE}/batches/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
            document.getElementById('batchResult').innerHTML = `
                <div style="color:var(--success); padding: 10px; background: rgba(0,255,0,0.1); border-radius: 8px;">
                    <strong>✅ Batch Created Successfully!</strong><br>
                    <small>Tx Hash: ${data.hash}</small>
                </div>`;

            // Auto-fill for convenience
            lastGeneratedBatchId = data.batch_id;
        } else {
            document.getElementById('batchResult').innerHTML = `<div style="color:var(--danger)">❌ Error: ${data.detail}</div>`;
        }
    } catch (err) {
        document.getElementById('batchResult').innerHTML = `<div style="color:var(--danger)">Network Error: ${err}</div>`;
    }
}

let lastGeneratedBatchId = "";



// 2. Worker: Submit Action
async function submitAction() {
    const batchId = document.getElementById('scanInput').value;
    const action = document.getElementById('actionType').value;
    const note = document.getElementById('actionNote').value;

    if (!batchId) return alert("Please enter a Batch ID");

    const payload = {
        action_type: action,
        description: note || `Action by ${currentRole}`,
        user_id: 1, // Simulated System User
        department_id: 1
    };

    try {
        const res = await fetch(`${API_BASE}/batches/${batchId}/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (res.ok) {
            document.getElementById('actionResult').innerHTML =
                `<div style="color:var(--success)">✅ Status Updated to: <strong>${result.current_status}</strong></div>`;
        } else {
            document.getElementById('actionResult').innerHTML =
                `<div style="color:var(--danger)">❌ Error: ${result.detail}</div>`;
        }
    } catch (err) {
        alert("Error: " + err);
    }
}

// 3. Consumer: Verify
async function verifyProduct() {
    const batchId = document.getElementById('verifyInput').value;
    if (!batchId) return alert("Enter ID");

    const resDiv = document.getElementById('verificationResult');
    const timelineDiv = document.getElementById('timelineView');

    resDiv.innerHTML = "Verifying...";
    timelineDiv.innerHTML = "";

    // Verify Call
    const vRes = await fetch(`${API_BASE}/verify/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id: batchId })
    });
    const vData = await vRes.json();

    if (vData.status === 'AUTHENTIC') {
        resDiv.innerHTML = `<h3 style="color:var(--success)">✅ AUTHENTIC</h3><p>${vData.message}</p>`;

        // Fetch Timeline
        const tRes = await fetch(`${API_BASE}/batches/${batchId}/timeline`);
        if (tRes.ok) {
            const tData = await tRes.json();
            tData.events.forEach(ev => {
                const el = document.createElement('div');
                el.className = 'event-card';

                let metaHtml = '';
                if (ev.metadata) {
                    // Check for common metadata fields we can show
                    const m = ev.metadata;
                    if (m.location) metaHtml += `<div class="meta-row">📍 Loc: ${m.location.lat}, ${m.location.long}</div>`;
                    if (m.temp) metaHtml += `<div class="meta-row">🌡️ Temp: ${m.temp}°C</div>`;
                    if (m.notes) metaHtml += `<div class="meta-row">📝 Note: ${m.notes}</div>`;
                }

                // Use blockchain_tx_id if available, otherwise check metadata.hash, otherwise 'Pending'
                const txHash = ev.blockchain_tx_id || (ev.metadata && ev.metadata.hash) || 'Pending Mining...';

                el.innerHTML = `
                    <div class="event-title">${ev.action_type}</div>
                    <div>${ev.description}</div>
                    
                    <div style="margin: 8px 0; font-size: 0.85em; background: rgba(0,0,0,0.05); padding: 5px; border-radius: 4px; word-break: break-all;">
                        <strong>🔗 Blockchain Tx Hash:</strong><br>
                        <span style="font-family: monospace; color: var(--primary);">${txHash}</span>
                    </div>

                    ${metaHtml}

                    <div class="event-meta">📅 ${new Date(ev.timestamp).toLocaleString()} • 👤 ${ev.username || 'System'}</div>
                `;
                timelineDiv.appendChild(el);
            });
        }
    } else {
        resDiv.innerHTML = `<h3 style="color:var(--danger)">⚠️ ${vData.status}</h3><p>${vData.message}</p>`;
    }
}
