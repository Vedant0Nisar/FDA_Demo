const API_BASE = window.location.origin;

// Initialize role from window global if available, else default
let currentRole = window.currentRole || 'manufacturer';

// 1. Manufacturer: Create Batch
async function createBatch() {
    const batchIdDoc = document.getElementById('batchId');
    const mfgDateDoc = document.getElementById('mfgDate');
    const expDateDoc = document.getElementById('expDate');

    if (!batchIdDoc || !mfgDateDoc || !expDateDoc) return;

    const batchId = batchIdDoc.value;
    const mfgDate = mfgDateDoc.value;
    const expDate = expDateDoc.value;

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
        const resultDiv = document.getElementById('batchResult');
        if (resultDiv) resultDiv.innerHTML = "⏳ Minting on Blockchain...";

        const res = await fetch(`${API_BASE}/batches/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
            const qrImageHtml = data.qr_code_base64 ? `
                <div style="margin-top: 20px; text-align: center; background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0;">
                    <img src="data:image/png;base64,${data.qr_code_base64}" alt="Batch QR Code" style="width: 200px; height: 200px; border: 1px solid #eee;">
                    <br>
                    <a href="data:image/png;base64,${data.qr_code_base64}" download="${batchId}_QR.png" class="primary-btn" style="display: inline-block; margin-top: 15px; text-decoration: none; background: #000; color: #fff; padding: 10px 20px; border-radius: 8px;">
                        📥 Download QR Code
                    </a>
                </div>
            ` : '';

            if (resultDiv) resultDiv.innerHTML = `
                <div style="color:var(--success); padding: 20px; background: rgba(16, 185, 129, 0.05); border: 1px solid var(--success); border-radius: 12px;">
                    <div style="font-size: 1.2rem; margin-bottom: 10px;">✅ <strong>Batch Created & Minted Successfully!</strong></div>
                    <small>Blockchain Tx: <span style="font-family: monospace; color: #666;">${data.hash}</span></small>
                    ${qrImageHtml}
                </div>`;
        } else {
            if (resultDiv) resultDiv.innerHTML = `<div style="color:var(--danger); padding: 10px; background: rgba(239, 68, 68, 0.1); border: 1px solid var(--danger); border-radius: 8px;">❌ Error: ${data.detail}</div>`;
        }
    } catch (err) {
        const resultDiv = document.getElementById('batchResult');
        if (resultDiv) resultDiv.innerHTML = `<div style="color:var(--danger)">Network Error: ${err}</div>`;
    }
}

// 2. Worker: Submit Action
async function submitAction() {
    const scanInput = document.getElementById('scanInput');
    if (!scanInput) return;

    const batchId = scanInput.value;
    const action = document.getElementById('actionType').value;
    const note = document.getElementById('actionNote') ? document.getElementById('actionNote').value : '';

    if (!batchId) return alert("Please enter a Batch ID");

    const payload = {
        action_type: action,
        description: note || `Action by ${currentRole}`,
        user_id: 1, // Simulated System User
        department_id: 1
    };

    const tempInput = document.getElementById('logTemp');
    const vehicleInput = document.getElementById('logVehicle');
    const ingressInput = document.getElementById('logIngress');
    const egressInput = document.getElementById('logEgress');

    // Map available fields to payload (top-level as expected by BatchEventRequest)
    if (tempInput) payload.temperature = tempInput.value;
    if (vehicleInput) payload.vehicle_id = vehicleInput.value;
    if (ingressInput) payload.ingress_quality = ingressInput.value;
    if (egressInput) payload.egress_quality = egressInput.value;
    if (note) payload.notes = note;

    try {
        const resultDiv = document.getElementById('actionResult');
        const res = await fetch(`${API_BASE}/batches/${batchId}/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (res.ok) {
            if (resultDiv) resultDiv.innerHTML =
                `<div style="color:var(--success); padding: 10px; background: rgba(16, 185, 129, 0.1); border: 1px solid var(--success); border-radius: 8px;">✅ Status Updated to: <strong>${result.current_status}</strong></div>`;
        } else {
            if (resultDiv) resultDiv.innerHTML =
                `<div style="color:var(--danger); padding: 10px; background: rgba(239, 68, 68, 0.1); border: 1px solid var(--danger); border-radius: 8px;">❌ Error: ${result.detail}</div>`;
        }
    } catch (err) {
        alert("Error: " + err);
    }
}

// 3. Consumer: Verify
async function verifyProduct() {
    const verifyInput = document.getElementById('verifyInput');
    if (!verifyInput) return;

    const batchId = verifyInput.value;
    if (!batchId) return alert("Enter ID");

    const resDiv = document.getElementById('verificationResult');
    const timelineDiv = document.getElementById('timelineView');

    if (resDiv) resDiv.innerHTML = "⏳ Verifying...";
    if (timelineDiv) timelineDiv.innerHTML = "";

    try {
        // Verify Call
        const vRes = await fetch(`${API_BASE}/verify/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_id: batchId })
        });
        const vData = await vRes.json();

        if (vData.status === 'AUTHENTIC') {
            if (resDiv) resDiv.innerHTML = `<h3 style="color:var(--success)">✅ AUTHENTIC</h3><p>${vData.message}</p>`;

            // Fetch Timeline
            const tRes = await fetch(`${API_BASE}/batches/${batchId}/timeline`);
            if (tRes.ok) {
                const tData = await tRes.json();
                tData.events.forEach(ev => {
                    const el = document.createElement('div');
                    el.className = 'event-card';

                    let metaHtml = '';
                    if (ev.metadata) {
                        const m = ev.metadata;
                        if (m.location) metaHtml += `<div class="meta-row">📍 Loc: ${m.location.lat}, ${m.location.long}</div>`;
                        if (m.temp) metaHtml += `<div class="meta-row">🌡️ Temp: ${m.temp}°C</div>`;
                        if (m.notes) metaHtml += `<div class="meta-row">📝 Note: ${m.notes}</div>`;
                        if (m.vehicle_id) metaHtml += `<div class="meta-row">🚛 Vehicle: ${m.vehicle_id}</div>`;
                    }

                    const txHash = ev.blockchain_tx_id || (ev.metadata && ev.metadata.hash) || 'Pending Mining...';

                    el.innerHTML = `
                        <div class="event-title">${ev.action_type}</div>
                        <div>${ev.description}</div>
                        
                        <div style="margin: 8px 0; font-size: 0.85em; background: rgba(0,0,0,0.05); padding: 8px; border-radius: 8px; word-break: break-all; border: 1px solid var(--border);">
                            <strong>🔗 Blockchain Tx Hash:</strong><br>
                            <span style="font-family: monospace; color: var(--stat-blue);">${txHash}</span>
                        </div>

                        ${metaHtml}

                        <div class="event-meta">📅 ${new Date(ev.timestamp).toLocaleString()} • 👤 ${ev.username || 'System'}</div>
                    `;
                    if (timelineDiv) timelineDiv.appendChild(el);
                });
            }
        } else {
            if (resDiv) resDiv.innerHTML = `<h3 style="color:var(--danger)">⚠️ ${vData.status}</h3><p>${vData.message}</p>`;
        }
    } catch (err) {
        if (resDiv) resDiv.innerHTML = `<div style="color:var(--danger)">Error during verification: ${err}</div>`;
    }
}

// --- QR Scanning Logic ---
let currentScanTarget = null;

function triggerQRScan(targetId) {
    currentScanTarget = targetId;
    const fileInput = document.getElementById('qrFileInput');
    if (fileInput) fileInput.click();
}

async function handleQRUpload(input) {
    if (!input.files || !input.files[0]) return;

    const file = input.files[0];
    const reader = new FileReader();

    reader.onload = async (e) => {
        const image = new Image();
        image.src = e.target.result;
        image.onload = () => {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.width = image.width;
            canvas.height = image.height;
            context.drawImage(image, 0, 0);

            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(imageData.data, imageData.width, imageData.height);

            if (code) {
                console.log("QR Code Decoded:", code.data);
                const targetInput = document.getElementById(currentScanTarget);
                if (targetInput) {
                    targetInput.value = code.data;
                    targetInput.classList.add('highlight-flash');
                    setTimeout(() => targetInput.classList.remove('highlight-flash'), 1000);
                }
                // Clear input for next scan
                input.value = '';
            } else {
                alert("❌ Could not find a valid QR code in this image. Please try another one.");
                input.value = '';
            }
        };
    };
    reader.readAsDataURL(file);
}
