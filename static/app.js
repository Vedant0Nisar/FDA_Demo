const API_BASE = window.location.origin;

// Initialize role from window global if available, else default
let currentRole = window.currentRole || 'manufacturer';

// 1. Manufacturer: Create Batch
// Global Live Location
let liveLocation = null;

function initLiveLocation() {
    if (!navigator.geolocation) return;

    const latFields = document.querySelectorAll('#geoLat');
    const longFields = document.querySelectorAll('#geoLong');

    latFields.forEach(f => f.placeholder = "Locating...");
    longFields.forEach(f => f.placeholder = "Locating...");

    navigator.geolocation.watchPosition(
        (pos) => {
            liveLocation = { lat: pos.coords.latitude, long: pos.coords.longitude };

            // Update all UI fields automatically
            latFields.forEach(f => f.value = liveLocation.lat);
            longFields.forEach(f => f.value = liveLocation.long);
        },
        (err) => console.warn("Live Geo Error:", err),
        { enableHighAccuracy: true, maximumAge: 0 }
    );
}

// Initialize immediately
initLiveLocation();

// Helper for Geolocation (Returns cached or fresh)
function getGeoLocation() {
    return new Promise((resolve, reject) => {
        if (liveLocation) {
            resolve(liveLocation);
            return;
        }
        if (!navigator.geolocation) {
            console.warn("Geolocation not supported");
            resolve(null);
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                liveLocation = { lat: pos.coords.latitude, long: pos.coords.longitude };
                resolve(liveLocation);
            },
            (err) => {
                console.warn("Geo error:", err);
                resolve(null);
            }
        );
    });
}

function printQR(base64Img) {
    const win = window.open('', '_blank');
    win.document.write(`
        <html>
            <head><title>Print QR</title></head>
            <body style="text-align:center; padding: 50px;">
                <img src="data:image/png;base64,${base64Img}" style="width: 300px; height: 300px; border: 1px solid #ccc;">
                <br><br>
                <script>
                    window.onload = function() { window.print(); window.close(); }
                </script>
            </body>
        </html>
    `);
    win.document.close();
}

// 1. Manufacturer: Create Batch
async function createBatch() {
    const batchIdDoc = document.getElementById('batchId');
    const mfgDateDoc = document.getElementById('mfgDate');
    const expDateDoc = document.getElementById('expDate');
    const opNameDoc = document.getElementById('operatorName');

    if (!batchIdDoc || !mfgDateDoc || !expDateDoc) return;

    const batchId = batchIdDoc.value;
    const mfgDate = mfgDateDoc.value;
    const expDate = expDateDoc.value;

    if (!batchId || !mfgDate || !expDate) return alert("Please fill all fields");

    const resultDiv = document.getElementById('batchResult');
    if (resultDiv) resultDiv.innerHTML = "⏳ Getting Location & Minting...";

    const location = await getGeoLocation();

    const payload = {
        batch_id: batchId,
        product_gtin: document.getElementById('gtin').value,
        manufacturer_license: document.getElementById('license').value,
        mfg_date: mfgDate,
        exp_date: expDate,
        batch_size: parseInt(document.getElementById('size').value),
        operator_name: opNameDoc ? opNameDoc.value : null,
        location: location
    };

    try {
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
                        📥 Download QR
                    </a>
                    <button onclick="printQR('${data.qr_code_base64}')" class="primary-btn" style="display: inline-block; margin-left: 10px; margin-top: 15px; background: #2563eb; color: #fff; padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer;">
                        🖨️ Print
                    </button>
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

    const resultDiv = document.getElementById('actionResult');
    if (resultDiv) resultDiv.innerHTML = "⏳ Getting Location & Mining...";

    const location = await getGeoLocation();

    const payload = {
        action_type: action,
        description: note || `Action by ${currentRole}`,
        user_id: 1, // Simulated System User
        department_id: 1,
        location: location
    };

    const vehicleInput = document.getElementById('logVehicle');
    const ingressInput = document.getElementById('logIngress');
    const egressInput = document.getElementById('logEgress');
    const quantityInput = document.getElementById('logQuantity');
    const opIdInput = document.getElementById('logOperatorId');
    const opNameInput = document.getElementById('logOperatorName');

    if (vehicleInput) payload.vehicle_id = vehicleInput.value;
    if (ingressInput) payload.ingress_quality = ingressInput.value;
    if (egressInput) payload.egress_quality = egressInput.value;
    if (quantityInput && quantityInput.value) payload.quantity = parseInt(quantityInput.value);
    if (note) payload.notes = note;
    if (opIdInput) payload.operator_id = opIdInput.value;
    if (opNameInput) payload.operator_name = opNameInput.value;

    try {
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

// 3. Consumer: Verify
async function verifyProduct() {
    const verifyInput = document.getElementById('verifyInput');
    if (!verifyInput) return;

    const batchId = verifyInput.value;
    if (!batchId) return alert("Enter ID");

    const resDiv = document.getElementById('verificationResult');
    const timelineDiv = document.getElementById('timelineView');
    const treeDiv = document.getElementById('treeContainer');
    const mermaidDiv = document.getElementById('mermaidTree');
    const treeAlerts = document.getElementById('treeAlerts');

    if (resDiv) resDiv.innerHTML = "⏳ Verifying...";
    if (timelineDiv) timelineDiv.innerHTML = "";
    if (treeDiv) treeDiv.style.display = 'none';

    try {
        // Verify Call
        const vRes = await fetch(`${API_BASE}/verify/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batch_id: batchId, location: await getGeoLocation() }) // Send verify loc too
        });
        const vData = await vRes.json();

        if (vData.status === 'AUTHENTIC') {
            if (resDiv) {
                let detailsHtml = `
                    <div style="margin-top: 15px; text-align: left; background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
                        <p><strong>📦 Product:</strong> ${vData.product_name || 'N/A'}</p>
                        <p><strong>📅 Expiry:</strong> ${vData.exp_date || 'N/A'}</p>
                        <p><strong>🆔 Batch ID:</strong> ${batchId}</p>
                        <p><strong>✅ Status:</strong> <span style="color:var(--success); font-weight:bold;">${vData.status}</span></p>
                    </div>
                `;
                resDiv.innerHTML = `<h3 style="color:var(--success)">✅ AUTHENTIC</h3><p>${vData.message}</p>${detailsHtml}`;
            }
        } else if (vData.status === 'TAMPERED') {
            if (resDiv) {
                let detailsHtml = `
                    <div style="margin-top: 15px; text-align: left; background: #fff5f5; padding: 15px; border-radius: 8px; border: 1px solid #fca5a5;">
                        <p><strong>📦 Product:</strong> ${vData.product_name || 'Unknown'}</p>
                        <p><strong>📅 Expiry:</strong> ${vData.exp_date || 'Unknown'}</p>
                         <p><strong>🆔 Batch ID:</strong> ${batchId}</p>
                    </div>
                `;
                resDiv.innerHTML = `
                <div style="background: #fee2e2; border: 2px solid #ef4444; padding: 20px; border-radius: 12px; text-align: center;">
                    <h1 style="color: #b91c1c; margin: 0; font-size: 2rem;">⛔ SECURITY ALERT ⛔</h1>
                    <h2 style="color: #ef4444; margin: 10px 0;">DATABASE TAMPER DETECTED</h2>
                    <p style="font-size: 1.1rem; color: #7f1d1d; margin-bottom: 10px;">${vData.message}</p>
                    ${detailsHtml}
                    <div style="margin-top: 15px; font-weight: bold; color: #b91c1c;">DO NOT ACCEPT THIS PRODUCT.</div>
                    <div style="margin-top: 10px; font-size: 0.9rem;">Incident logged in Audit Trail below.</div>
                </div>
             `;
            }
        } else {
            if (resDiv) resDiv.innerHTML = `<h3 style="color:var(--danger)">⚠️ ${vData.status}</h3><p>${vData.message}</p>`;
        }

        // Fetch Timeline (Run for Authentic AND Tampered to show the trail)
        if (vData.status === 'AUTHENTIC' || vData.status === 'TAMPERED') {
            const tRes = await fetch(`${API_BASE}/batches/${batchId}/timeline`);
            if (tRes.ok) {
                const tData = await tRes.json();
                tData.events.forEach(ev => {
                    const el = document.createElement('div');
                    el.className = 'event-card';

                    // Custom Style for Tamper Alert in Timeline
                    if (ev.action_type === 'TAMPER_ALERT') {
                        el.style.border = '2px solid #ef4444';
                        el.style.backgroundColor = '#fef2f2';
                    }

                    let metaHtml = '';
                    if (ev.metadata) {
                        const m = ev.metadata;
                        if (m.location) metaHtml += `<div class="meta-row">📍 Loc: ${m.location.lat}, ${m.location.long}</div>`;
                        // Temp removed
                        if (m.notes) metaHtml += `<div class="meta-row">📝 Note: ${m.notes}</div>`;

                        if (m.vehicle_id) metaHtml += `<div class="meta-row">🚛 Vehicle: ${m.vehicle_id}</div>`;
                        if (m.quantity) metaHtml += `<div class="meta-row">📦 Quantity: <strong>${m.quantity}</strong></div>`;

                        // New Fields
                        if (m.operator_name) metaHtml += `<div class="meta-row">👤 Op Name: <strong>${m.operator_name}</strong></div>`;
                        if (m.operator_id) metaHtml += `<div class="meta-row">🆔 Op ID: <strong>${m.operator_id}</strong></div>`;
                    }

                    const txHash = ev.blockchain_tx_id || (ev.metadata && ev.metadata.hash) || 'Pending Mining...';

                    let icon = ev.action_type === 'TAMPER_ALERT' ? '⛔' : '⛓️';

                    el.innerHTML = `
                        <div class="event-title" style="${ev.action_type === 'TAMPER_ALERT' ? 'color:#b91c1c;' : ''}">
                            ${ev.action_type}
                        </div>
                        <div>${ev.description}</div>
                        
                        <div style="margin: 8px 0; font-size: 0.85em; background: rgba(0,0,0,0.05); padding: 8px; border-radius: 8px; word-break: break-all; border: 1px solid var(--border);">
                            <strong>${icon} Blockchain Tx Hash:</strong><br>
                            <span style="font-family: monospace; color: ${ev.action_type === 'TAMPER_ALERT' ? '#b91c1c' : 'var(--stat-blue)'};">${txHash}</span>
                        </div>

                        ${metaHtml}

                        <div class="event-meta">📅 ${new Date(ev.timestamp).toLocaleString()} • 👤 ${ev.username || 'System'}</div>
                    `;
                    if (timelineDiv) timelineDiv.appendChild(el);
                });
            }
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
