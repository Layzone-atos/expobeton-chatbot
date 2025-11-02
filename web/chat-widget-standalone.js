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
            
            .expobeton-message-content {
                max-width: 70%;
                padding: 12px 16px;
                border-radius: 12px;
                line-height: 1.5;
                font-size: 14px;
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
        
        messageDiv.innerHTML = `
            <div class="expobeton-message-avatar">${sender === 'bot' ? '🤖' : '👤'}</div>
            <div class="expobeton-message-content">${escapeHtml(text)}</div>
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
                    metadata: chatState.userInfo
                })
            });
            
            if (!response.ok) {
                throw new Error('Erreur serveur');
            }
            
            const data = await response.json();
            
            if (data && data.length > 0) {
                for (const msg of data) {
                    if (msg.text) {
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
