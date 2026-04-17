/**
 * ExpoBeton RDC - Widget Chatbot Autonome
 * Version: 2.0 - Optimisé pour serveur mutualisé
 * 
 * Installation: Ajoutez simplement ce script à votre page HTML:
 * <script src="https://expobetonrdc.com/chat/chat-widget-standalone.js"></script>
 */

(function() {
    'use strict';
    
    // ========================================
    // CONFIGURATION
    // ========================================
    
    // URL de votre backend (same origin)
    const RASA_SERVER_URL = window.location.origin;
    
    // Configuration du widget
    const CONFIG = {
        inactivityTimeout: 10 * 60 * 1000, // 10 minutes
        position: 'bottom-right', // bottom-right, bottom-left, top-right, top-left
        primaryColor: '#0A2A66',
        buttonText: '💬',
        greeting: 'Bonjour! Comment puis-je vous aider?'
    };
    
    // ========================================
    // ÉTAT DU CHAT
    // ========================================
    
    const chatState = {
        isOpen: false,
        userInfo: null,
        sessionId: generateSessionId(),
        messages: [],
        lastActivityTime: null,
        inactivityTimer: null
    };
    
    // ========================================
    // FONCTIONS UTILITAIRES
    // ========================================
    
    function generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // Collect device metadata for analytics
    function getDeviceMetadata() {
        const ua = navigator.userAgent;
        let deviceType = 'desktop';
        if (/Mobi|Android/i.test(ua)) deviceType = 'mobile';
        else if (/Tablet|iPad/i.test(ua)) deviceType = 'tablet';

        let browser = 'Unknown';
        if (ua.indexOf('Firefox') > -1) browser = 'Firefox';
        else if (ua.indexOf('Edg') > -1) browser = 'Edge';
        else if (ua.indexOf('Chrome') > -1) browser = 'Chrome';
        else if (ua.indexOf('Safari') > -1) browser = 'Safari';
        else if (ua.indexOf('Opera') > -1 || ua.indexOf('OPR') > -1) browser = 'Opera';

        let os = 'Unknown';
        if (ua.indexOf('Windows') > -1) os = 'Windows';
        else if (ua.indexOf('Mac OS') > -1) os = 'macOS';
        else if (ua.indexOf('Linux') > -1) os = 'Linux';
        else if (ua.indexOf('Android') > -1) os = 'Android';
        else if (ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) os = 'iOS';

        return {
            device_type: deviceType,
            browser: browser,
            os: os,
            screen_width: window.screen.width,
            screen_height: window.screen.height,
            language: navigator.language || 'unknown',
            referrer: document.referrer || '',
            user_agent: ua,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        };
    }

    const _deviceMetadata = getDeviceMetadata();
    
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Container principal */
            #expobeton-chat-container {
                position: fixed;
                ${CONFIG.position.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'}
                ${CONFIG.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                z-index: 99999;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            
            /* Bouton flottant */
            #expobeton-chat-button {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, ${CONFIG.primaryColor} 0%, #1e3a8a 100%);
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(10, 42, 102, 0.4);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                position: relative;
            }
            
            #expobeton-chat-button:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 20px rgba(10, 42, 102, 0.6);
            }
            
            #expobeton-chat-button.has-notification::after {
                content: '';
                position: absolute;
                top: 5px;
                right: 5px;
                width: 12px;
                height: 12px;
                background: #ef4444;
                border-radius: 50%;
                border: 2px solid white;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.2); opacity: 0.8; }
            }
            
            /* Fenêtre de chat */
            #expobeton-chat-window {
                display: none;
                position: fixed;
                ${CONFIG.position.includes('bottom') ? 'bottom: 90px;' : 'top: 90px;'}
                ${CONFIG.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                width: 380px;
                height: 600px;
                max-height: 80vh;
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                display: flex;
                flex-direction: column;
                overflow: hidden;
                z-index: 99998;
            }
            
            #expobeton-chat-window.open {
                display: flex;
                animation: slideUp 0.3s ease;
            }
            
            @keyframes slideUp {
                from {
                    transform: translateY(20px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }
            
            /* Header */
            .expobeton-chat-header {
                background: linear-gradient(135deg, ${CONFIG.primaryColor} 0%, #1e3a8a 100%);
                color: white;
                padding: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .expobeton-chat-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }
            
            .expobeton-chat-close {
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background 0.3s;
            }
            
            .expobeton-chat-close:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            
            /* Zone de messages */
            .expobeton-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: #f8fafc;
            }
            
            /* Messages */
            .expobeton-message {
                margin-bottom: 16px;
                display: flex;
                align-items: flex-start;
                gap: 10px;
                animation: fadeIn 0.3s ease;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .expobeton-message.user {
                flex-direction: row-reverse;
            }
            
            .expobeton-message-avatar {
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                flex-shrink: 0;
            }
            
            .expobeton-message-bubble {
                max-width: 75%;
                display: flex;
                flex-direction: column;
            }
            
            .expobeton-message-bubble .expobeton-message-content {
                max-width: 100%;
            }
            
            .expobeton-message-content {
                padding: 12px 16px;
                border-radius: 12px;
                line-height: 1.5;
                font-size: 14px;
            }
            
            .expobeton-message-time {
                font-size: 10px;
                color: #9ca3af;
                margin-top: 3px;
                padding: 0 4px;
            }
            
            .expobeton-message.user .expobeton-message-time {
                text-align: right;
            }
            
            .expobeton-message.bot .expobeton-message-time {
                text-align: left;
            }
            
            .expobeton-message.bot .expobeton-message-content {
                background: white;
                color: #1e293b;
                border: 1px solid #e2e8f0;
            }
            
            .expobeton-message.user .expobeton-message-content {
                background: ${CONFIG.primaryColor};
                color: white;
            }
            
            /* Formulaire */
            .expobeton-user-form {
                padding: 20px;
                background: white;
            }
            
            .expobeton-form-group {
                margin-bottom: 15px;
            }
            
            .expobeton-form-group label {
                display: block;
                margin-bottom: 5px;
                font-size: 14px;
                color: #475569;
                font-weight: 500;
            }
            
            .expobeton-form-group input {
                width: 100%;
                padding: 10px 12px;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            
            .expobeton-form-group input:focus {
                outline: none;
                border-color: ${CONFIG.primaryColor};
            }
            
            .expobeton-form-submit {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, ${CONFIG.primaryColor} 0%, #1e3a8a 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            
            .expobeton-form-submit:hover {
                transform: translateY(-2px);
            }
            
            /* Input zone */
            .expobeton-chat-input-container {
                padding: 15px;
                background: white;
                border-top: 1px solid #e2e8f0;
            }
            
            .expobeton-chat-input-wrapper {
                display: flex;
                gap: 10px;
            }
            
            .expobeton-chat-input {
                flex: 1;
                padding: 12px;
                border: 1px solid #cbd5e1;
                border-radius: 20px;
                font-size: 14px;
                outline: none;
            }
            
            .expobeton-chat-input:focus {
                border-color: ${CONFIG.primaryColor};
            }
            
            .expobeton-send-button {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: ${CONFIG.primaryColor};
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s;
            }
            
            .expobeton-send-button:hover {
                transform: scale(1.1);
            }
            
            .expobeton-end-conversation {
                margin-top: 10px;
                text-align: center;
            }
            
            .expobeton-end-button {
                padding: 8px 16px;
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            
            .expobeton-end-button:hover {
                transform: translateY(-2px);
            }
            
            /* Responsive */
            @media (max-width: 480px) {
                #expobeton-chat-window {
                    width: calc(100vw - 40px);
                    height: calc(100vh - 100px);
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // ========================================
    // CRÉATION DU HTML
    // ========================================
    
    function createChatWidget() {
        const container = document.createElement('div');
        container.id = 'expobeton-chat-container';
        
        container.innerHTML = `
            <button id="expobeton-chat-button" class="has-notification" title="Chatbot ExpoBeton RDC">
                ${CONFIG.buttonText}
            </button>
            
            <div id="expobeton-chat-window">
                <div class="expobeton-chat-header">
                    <div>
                        <h3>🏗️ ExpoBeton RDC</h3>
                        <small style="opacity: 0.9;">Assistant virtuel</small>
                    </div>
                    <button class="expobeton-chat-close" id="expobeton-close-chat">×</button>
                </div>
                
                <div id="expobeton-user-form" class="expobeton-user-form">
                    <h4 style="margin-top: 0;">Bienvenue! 👋</h4>
                    <p style="font-size: 14px; color: #64748b; margin-bottom: 20px;">
                        Pour mieux vous servir, veuillez vous présenter:
                    </p>
                    <div class="expobeton-form-group">
                        <label>Nom complet *</label>
                        <input type="text" id="expobeton-name" placeholder="Ex: Jean Dupont" required>
                    </div>
                    <div class="expobeton-form-group">
                        <label>Téléphone</label>
                        <input type="tel" id="expobeton-phone" placeholder="Ex: +243 123 456 789">
                    </div>
                    <div class="expobeton-form-group">
                        <label>Email</label>
                        <input type="email" id="expobeton-email" placeholder="Ex: jean@example.com">
                    </div>
                    <button class="expobeton-form-submit" id="expobeton-start-chat">
                        Commencer la discussion 💬
                    </button>
                </div>
                
                <div class="expobeton-chat-messages" id="expobeton-messages" style="display: none;"></div>
                
                <div class="expobeton-chat-input-container" id="expobeton-input-container" style="display: none;">
                    <div class="expobeton-chat-input-wrapper">
                        <input 
                            type="text" 
                            id="expobeton-chat-input" 
                            class="expobeton-chat-input"
                            placeholder="Tapez votre message..."
                            autocomplete="off"
                        >
                        <button class="expobeton-send-button" id="expobeton-send-button">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="20" height="20">
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                            </svg>
                        </button>
                    </div>
                    <div class="expobeton-end-conversation">
                        <button class="expobeton-end-button" id="expobeton-end-conversation">
                            🏁 Terminer la conversation
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(container);
    }
    
    // ========================================
    // FONCTIONS DE CHAT
    // ========================================
    
    function addMessage(text, sender) {
        const messagesDiv = document.getElementById('expobeton-messages');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `expobeton-message ${sender}`;
        
        const now = new Date();
        const timeStr = now.toLocaleString('fr-FR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="expobeton-message-avatar">${sender === 'bot' ? '🤖' : '👤'}</div>
            <div class="expobeton-message-bubble">
                <div class="expobeton-message-content">${escapeHtml(text)}</div>
                <div class="expobeton-message-time">${timeStr}</div>
            </div>
        `;
        
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        chatState.messages.push({
            text,
            sender,
            timestamp: new Date().toISOString()
        });
        
        resetInactivityTimer();
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/\n/g, '<br>');
    }
    
    async function sendMessage(message) {
        if (!message.trim()) return;
        
        addMessage(message, 'user');
        
        try {
            const response = await fetch(`${RASA_SERVER_URL}/webhooks/rest/webhook`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    sender: chatState.sessionId,
                    message: message,
                    metadata: Object.assign({}, chatState.userInfo, _deviceMetadata)
                })
            });
            
            if (!response.ok) {
                throw new Error('Erreur serveur');
            }
            
            const data = await response.json();
            
            if (data && data.length > 0) {
                let hasUploadSequence = false;
                for (const msg of data) {
                    if (msg.custom && msg.custom.upload_sequence) {
                        hasUploadSequence = true;
                        await startStandaloneUploadSequence(msg.custom.upload_sequence);
                    } else if (msg.custom && msg.custom.do_uploads) {
                        hasUploadSequence = true;
                        await doStandaloneActualUploads(msg.custom.do_uploads);
                    } else if (msg.custom && msg.custom.single_upload_card) {
                        hasUploadSequence = true;
                        const card = msg.custom.single_upload_card;
                        card.upload_url = null;
                        renderUploadCardStandalone(card);
                        standaloneUploadQueue = [];
                        standaloneSeqMeta = {
                            mode: card.mode || 'local_store',
                            on_complete_trigger: card.on_complete_trigger || '/registration_review',
                            upload_url_base: card.upload_url_base,
                            auth_header: card.auth_header,
                        };
                    } else if (msg.custom && msg.custom.trigger_message) {
                        hasUploadSequence = true;
                        await sendMessage(msg.custom.trigger_message);
                    } else if (msg.text) {
                        if (hasUploadSequence && (
                            msg.text.includes('upload_documents.php') ||
                            msg.text.includes('Documents a fournir') ||
                            msg.text.includes('Verification de vos informations')
                        )) { continue; }
                        await new Promise(resolve => setTimeout(resolve, 500));
                        addMessage(msg.text, 'bot');
                    }
                }
            } else {
                addMessage("Désolé, je n'ai pas compris. Pouvez-vous reformuler?", 'bot');
            }
            
        } catch (error) {
            console.error('Error:', error);
            addMessage('Désolé, une erreur est survenue. Veuillez réessayer.', 'bot');
        }
    }
    
    // ========================================
    // FILE UPLOAD SYSTEM (Standalone) — Sequential Queue
    // ========================================

    let standaloneUploadQueue = [];
    let standaloneSeqMeta = null;
    let pendingFiles = {};       // { type: File } - files stored locally until confirmed

    async function startStandaloneUploadSequence(seq) {
        standaloneSeqMeta = {
            ref: seq.ref || null,
            upload_url_base: seq.upload_url_base,
            auth_header: seq.auth_header,
            final_message: seq.final_message || null,
            closing: seq.closing || null,
            mode: seq.mode || 'upload',
            on_complete_trigger: seq.on_complete_trigger || null,
        };
        const allUploads = seq.uploads.map(u => ({
            ...u,
            ref: seq.ref || null,
            upload_url: seq.ref ? `${seq.upload_url_base}?ref=${seq.ref}&type=${u.type}` : null,
            auth_header: seq.auth_header,
            mode: seq.mode || 'upload',
        }));
        standaloneUploadQueue = allUploads.slice(1);
        if (allUploads.length > 0) {
            renderUploadCardStandalone(allUploads[0]);
        } else {
            finishStandaloneUploadSequence();
        }
    }

    function advanceStandaloneQueue() {
        if (standaloneUploadQueue.length > 0) {
            const next = standaloneUploadQueue.shift();
            setTimeout(() => renderUploadCardStandalone(next), 600);
        } else {
            setTimeout(() => finishStandaloneUploadSequence(), 400);
        }
    }

    function finishStandaloneUploadSequence() {
        if (standaloneSeqMeta) {
            // If local_store mode with trigger, send message to Rasa
            if (standaloneSeqMeta.mode === 'local_store' && standaloneSeqMeta.on_complete_trigger) {
                sendMessage(standaloneSeqMeta.on_complete_trigger);
                standaloneSeqMeta = null;
                return;
            }
            if (standaloneSeqMeta.final_message) {
                addMessage(standaloneSeqMeta.final_message, 'bot');
            }
            setTimeout(() => {
                if (standaloneSeqMeta && standaloneSeqMeta.closing) {
                    addMessage(standaloneSeqMeta.closing, 'bot');
                }
                standaloneSeqMeta = null;
            }, 400);
        }
    }

    function renderUploadCardStandalone(uploadReq) {
        const messagesDiv = document.getElementById('expobeton-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'expobeton-message bot';
        messageDiv.innerHTML = `
            <div class="expobeton-message-avatar">🤖</div>
            <div class="expobeton-upload-card">
                <div style="font-weight:700;color:#0A2A66;margin-bottom:6px;">${escapeHtml(uploadReq.label)}</div>
                <p style="font-size:12px;color:#6C757D;margin-bottom:10px;">${escapeHtml(uploadReq.description).replace(/<br>/g,'<br>')}</p>
                <div class="expobeton-drop-zone" id="sdz-${uploadReq.type}">
                    <div style="font-size:28px;">📁</div>
                    <p style="font-size:12px;color:#64748b;margin:4px 0 8px;">Glissez votre fichier ici ou</p>
                    <label style="display:inline-block;padding:8px 18px;background:linear-gradient(135deg,#0A2A66,#1e3a8a);color:white;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;" for="sfi-${uploadReq.type}">Choisir un fichier</label>
                    <input type="file" id="sfi-${uploadReq.type}" accept="${uploadReq.accept}" style="display:none">
                </div>
                <div id="sprogress-${uploadReq.type}" style="display:none;padding:10px 0;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span id="sfn-${uploadReq.type}" style="font-size:12px;font-weight:600;"></span><span id="sfs-${uploadReq.type}" style="font-size:11px;color:#6C757D;"></span></div>
                    <div style="width:100%;height:6px;background:#e5e7eb;border-radius:3px;overflow:hidden;"><div id="sfill-${uploadReq.type}" style="height:100%;width:0%;background:linear-gradient(135deg,#0A2A66,#3b82f6);border-radius:3px;transition:width 0.3s;"></div></div>
                    <span id="sstat-${uploadReq.type}" style="font-size:11px;color:#6C757D;">En cours...</span>
                </div>
                <div id="sresult-${uploadReq.type}" style="display:none;"></div>
                <p style="text-align:center;margin-top:8px;font-size:11px;color:#94a3b8;">
                    <a href="${uploadReq.upload_url}" target="_blank" style="color:#0A2A66;">Uploadez via le site web</a>
                    <span style="margin:0 4px;">|</span>
                    <a href="#" id="sskip-${uploadReq.type}" style="color:#0A2A66;">Passer cette étape</a>
                </p>
            </div>
        `;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        chatState.messages.push({text: `[Upload: ${uploadReq.label}]`, sender: 'bot', timestamp: new Date().toISOString()});

        const fileInput = document.getElementById(`sfi-${uploadReq.type}`);
        const dropZone = document.getElementById(`sdz-${uploadReq.type}`);

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) standaloneUpload(e.target.files[0], uploadReq);
        });
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = '#0A2A66'; dropZone.style.background = '#eef2ff'; });
        dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = '#cbd5e1'; dropZone.style.background = '#f8fafc'; });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault(); dropZone.style.borderColor = '#cbd5e1'; dropZone.style.background = '#f8fafc';
            if (e.dataTransfer.files.length > 0) standaloneUpload(e.dataTransfer.files[0], uploadReq);
        });
        // Skip button
        document.getElementById(`sskip-${uploadReq.type}`).addEventListener('click', (e) => {
            e.preventDefault();
            showStandaloneResult(uploadReq.type, true, `⏭️ Étape passée — vous pourrez envoyer le document plus tard.`);
            advanceStandaloneQueue();
        });
    }

    function standaloneUpload(file, uploadReq) {
        const maxBytes = uploadReq.max_size_mb * 1024 * 1024;
        const allowedExts = uploadReq.accept.split(',').map(e => e.trim().toLowerCase());
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        const t = uploadReq.type;

        if (!allowedExts.includes(ext)) {
            showStandaloneResult(t, false, `Format non accepté (${ext}). Formats : ${uploadReq.accept}`);
            return;
        }
        if (file.size > maxBytes) {
            showStandaloneResult(t, false, `Fichier trop volumineux. Max : ${uploadReq.max_size_mb} MB`);
            return;
        }

        document.getElementById(`sdz-${t}`).style.display = 'none';
        document.getElementById(`sprogress-${t}`).style.display = 'block';
        document.getElementById(`sfn-${t}`).textContent = file.name;
        document.getElementById(`sfs-${t}`).textContent = `(${(file.size/1024/1024).toFixed(1)} MB)`;

        // Local store mode: save file locally
        if (uploadReq.mode === 'local_store') {
            pendingFiles[t] = file;
            document.getElementById(`sfill-${t}`).style.width = '100%';
            document.getElementById(`sstat-${t}`).textContent = 'Fichier selectionne';
            setTimeout(() => {
                document.getElementById(`sprogress-${t}`).style.display = 'none';
                const label = t === 'logo' ? 'Logo' : 'Passeport';
                showStandaloneResult(t, true, `${label} selectionne !`);
                advanceStandaloneQueue();
            }, 500);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                document.getElementById(`sfill-${t}`).style.width = pct + '%';
                document.getElementById(`sstat-${t}`).textContent = `Envoi... ${pct}%`;
            }
        });

        xhr.addEventListener('load', () => {
            document.getElementById(`sprogress-${t}`).style.display = 'none';
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const res = JSON.parse(xhr.responseText);
                    if (res.success) {
                        showStandaloneResult(t, true, `✅ ${t === 'logo' ? 'Logo' : 'Passeport'} envoyé avec succès !`);
                        advanceStandaloneQueue();
                    } else { showStandaloneResult(t, false, res.error || 'Erreur.'); }
                } catch(e) { showStandaloneResult(t, false, 'Réponse invalide.'); }
            } else { showStandaloneResult(t, false, `Erreur serveur (${xhr.status}).`); }
        });
        xhr.addEventListener('error', () => {
            document.getElementById(`sprogress-${t}`).style.display = 'none';
            showStandaloneResult(t, false, 'Erreur de connexion.');
        });

        xhr.open('POST', uploadReq.upload_url);
        xhr.setRequestHeader('Authorization', uploadReq.auth_header);
        xhr.send(formData);
    }

    function showStandaloneResult(type, success, message) {
        const el = document.getElementById(`sresult-${type}`);
        el.style.display = 'block';
        el.style.padding = '10px 14px';
        el.style.borderRadius = '8px';
        el.style.fontSize = '13px';
        el.style.fontWeight = '500';
        el.style.marginTop = '8px';
        el.style.background = success ? '#ecfdf5' : '#fef2f2';
        el.style.color = success ? '#065f46' : '#991b1b';
        el.style.border = `1px solid ${success ? '#a7f3d0' : '#fecaca'}`;
        el.textContent = message;
        if (!success) setTimeout(() => { const dz = document.getElementById(`sdz-${type}`); if(dz) dz.style.display='block'; }, 2000);
    }

    // Upload stored files to server after API confirmation
    async function doStandaloneActualUploads(info) {
        for (const type of info.uploads) {
            const file = pendingFiles[type];
            if (!file) continue;
            const url = `${info.upload_url_base}?ref=${info.ref}&type=${type}`;
            try {
                const formData = new FormData();
                formData.append('file', file);
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: { 'Authorization': info.auth_header },
                    body: formData
                });
                const result = await resp.json();
                if (result.success) {
                    console.log(`[Upload] ${type} uploaded successfully`);
                } else {
                    console.error(`[Upload] ${type} failed:`, result.error);
                }
            } catch (e) {
                console.error(`[Upload] ${type} error:`, e);
            }
            delete pendingFiles[type];
        }
    }

    function resetInactivityTimer() {
        chatState.lastActivityTime = Date.now();
        
        if (chatState.inactivityTimer) {
            clearTimeout(chatState.inactivityTimer);
        }
        
        chatState.inactivityTimer = setTimeout(() => {
            showInactivityWarning();
        }, CONFIG.inactivityTimeout);
    }
    
    function showInactivityWarning() {
        addMessage(
            "Vous avez été inactif pendant 10 minutes. La conversation sera terminée automatiquement dans 2 minutes si vous ne répondez pas.",
            'bot'
        );
        
        chatState.inactivityTimer = setTimeout(() => {
            endConversation(true);
        }, 2 * 60 * 1000);
    }
    
    async function endConversation(isAuto = false) {
        if (chatState.inactivityTimer) {
            clearTimeout(chatState.inactivityTimer);
        }
        
        const endMessage = isAuto 
            ? "👋 Session terminée automatiquement après inactivité. Merci d'avoir utilisé notre chatbot ExpoBeton RDC!\n\n📧 Un email avec le transcript a été envoyé.\n\nÀ bientôt!"
            : "👋 Merci d'avoir utilisé notre chatbot ExpoBeton RDC!\n\n📧 Un email avec le transcript a été envoyé à notre équipe.\n\nSi vous avez d'autres questions, n'hésitez pas à nous recontacter!\n\nÀ bientôt!";
        
        addMessage(endMessage, 'bot');
        
        // Envoyer au backend pour email
        try {
            await fetch(`${RASA_SERVER_URL}/webhook`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    next_action: 'action_end_conversation',
                    sender_id: chatState.sessionId,
                    tracker: {
                        sender_id: chatState.sessionId,
                        latest_message: {
                            text: '/end_conversation',
                            metadata: {
                                ...chatState.userInfo,
                                ..._deviceMetadata,
                                messages: chatState.messages,
                                session_id: chatState.sessionId
                            }
                        }
                    }
                })
            });
        } catch (error) {
            console.error('Error sending conversation:', error);
        }
        
        // Désactiver l'input
        document.getElementById('expobeton-chat-input').disabled = true;
        document.getElementById('expobeton-send-button').disabled = true;
        document.getElementById('expobeton-end-conversation').style.display = 'none';
        
        // Bouton restart après 3 secondes
        setTimeout(() => {
            const inputContainer = document.getElementById('expobeton-input-container');
            const restartDiv = document.createElement('div');
            restartDiv.style.cssText = 'text-align: center; padding: 15px;';
            restartDiv.innerHTML = '<button onclick="location.reload()" style="padding: 10px 20px; background: linear-gradient(135deg, #0A2A66 0%, #1e3a8a 100%); color: white; border: none; border-radius: 20px; cursor: pointer; font-weight: 600;">🔄 Nouvelle conversation</button>';
            inputContainer.appendChild(restartDiv);
        }, 3000);
    }
    
    // ========================================
    // EVENT LISTENERS
    // ========================================
    
    function initializeEventListeners() {
        // Bouton principal
        document.getElementById('expobeton-chat-button').addEventListener('click', () => {
            const chatWindow = document.getElementById('expobeton-chat-window');
            chatWindow.classList.toggle('open');
            chatState.isOpen = !chatState.isOpen;
            
            // Enlever la notification
            document.getElementById('expobeton-chat-button').classList.remove('has-notification');
        });
        
        // Bouton fermer
        document.getElementById('expobeton-close-chat').addEventListener('click', () => {
            document.getElementById('expobeton-chat-window').classList.remove('open');
            chatState.isOpen = false;
        });
        
        // Formulaire de démarrage
        document.getElementById('expobeton-start-chat').addEventListener('click', () => {
            const name = document.getElementById('expobeton-name').value.trim();
            
            if (!name) {
                alert('Veuillez entrer votre nom');
                return;
            }
            
            chatState.userInfo = {
                name,
                phone: document.getElementById('expobeton-phone').value.trim(),
                email: document.getElementById('expobeton-email').value.trim()
            };
            
            // Masquer le formulaire, afficher le chat
            document.getElementById('expobeton-user-form').style.display = 'none';
            document.getElementById('expobeton-messages').style.display = 'block';
            document.getElementById('expobeton-input-container').style.display = 'block';
            
            // Message de bienvenue
            addMessage(`Bonjour ${name}! Je suis ravi de vous aider. Comment puis-je vous renseigner sur ExpoBeton RDC aujourd'hui?`, 'bot');
            
            // Suggestions
            setTimeout(() => {
                addMessage("💡 Vous pourriez me demander:\n• C'est quoi ExpoBeton?\n• Quelles sont les dates?\n• Comment devenir ambassadeur?", 'bot');
            }, 1000);
            
            resetInactivityTimer();
        });
        
        // Envoi de message
        document.getElementById('expobeton-send-button').addEventListener('click', () => {
            const input = document.getElementById('expobeton-chat-input');
            sendMessage(input.value);
            input.value = '';
        });
        
        document.getElementById('expobeton-chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const input = document.getElementById('expobeton-chat-input');
                sendMessage(input.value);
                input.value = '';
            }
        });
        
        // Terminer conversation
        document.getElementById('expobeton-end-conversation').addEventListener('click', () => {
            endConversation(false);
        });
    }
    
    // ========================================
    // INITIALISATION
    // ========================================
    
    function init() {
        // Attendre que le DOM soit chargé
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }
        
        // Injecter les styles
        injectStyles();
        
        // Créer le widget
        createChatWidget();
        
        // Initialiser les événements
        initializeEventListeners();
        
        console.log('ExpoBeton Chat Widget initialized');
    }
    
    // Démarrer l'initialisation
    init();
    
})();
