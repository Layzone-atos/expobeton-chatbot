// Chat Widget Configuration
// Rasa Server URL - Auto-detect environment
const RASA_SERVER_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5005'
    : 'https://web-production-9f398e.up.railway.app';

const INACTIVITY_TIMEOUT = 10 * 60 * 1000; // 10 minutes in milliseconds

// Sound notification system using Web Audio API
let audioContext = null;

// Initialize audio context
function initAudio() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
}

// Play sound helper
function playSound(type) {
    try {
        initAudio();
        
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        if (type === 'botMessage') {
            // Bot message: pleasant notification (C5 note)
            oscillator.frequency.value = 523.25;
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        } else if (type === 'userMessage') {
            // User message: quick feedback (E5 note)
            oscillator.frequency.value = 659.25;
            gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.15);
        }
    } catch (error) {
        console.log('Sound notification failed:', error);
    }
}

// State Management
let chatState = {
    isOpen: false,
    userInfo: null,
    sessionId: null,
    messages: [],
    lastActivityTime: null,
    inactivityTimer: null
};

// DOM Elements
const chatButton = document.getElementById('chat-button');
const chatWindow = document.getElementById('chat-window');
const closeChat = document.getElementById('close-chat');
const userForm = document.getElementById('user-form');
const userInfoForm = document.getElementById('user-info-form');
const chatMessages = document.getElementById('chat-messages');
const chatInputContainer = document.getElementById('chat-input-container');
const messagesList = document.getElementById('messages-list');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const typingIndicator = document.getElementById('typing-indicator');
const notificationBadge = document.getElementById('notification-badge');
const endConversationButton = document.getElementById('end-conversation-button');

// Initialize
function init() {
    chatState.sessionId = generateSessionId();
    setupEventListeners();
    
    // Show notification badge after 3 seconds
    setTimeout(() => {
        if (!chatState.isOpen) {
            notificationBadge.style.display = 'flex';
        }
    }, 3000);
}

// Generate unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Event Listeners
function setupEventListeners() {
    chatButton.addEventListener('click', toggleChat);
    closeChat.addEventListener('click', toggleChat);
    userForm.addEventListener('submit', handleUserFormSubmit);
    sendButton.addEventListener('click', sendMessage);
    endConversationButton.addEventListener('click', endConversation);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Track activity
    chatInput.addEventListener('input', resetInactivityTimer);
    chatInput.addEventListener('focus', resetInactivityTimer);
}

// Toggle Chat Window
function toggleChat() {
    chatState.isOpen = !chatState.isOpen;
    
    if (chatState.isOpen) {
        chatWindow.style.display = 'flex';
        chatButton.style.display = 'none';
        notificationBadge.style.display = 'none';
        
        if (chatState.userInfo) {
            chatInput.focus();
        }
    } else {
        chatWindow.style.display = 'none';
        chatButton.style.display = 'flex';
    }
}

// Handle User Form Submission
async function handleUserFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(userForm);
    chatState.userInfo = {
        name: formData.get('name').trim(),
        phone: formData.get('phone').trim() || null,
        email: formData.get('email').trim() || null
    };
    
    // Hide form, show chat
    userInfoForm.style.display = 'none';
    chatMessages.style.display = 'block';
    chatInputContainer.style.display = 'block';
    
    // Send greeting message with user info
    await sendGreeting();
    
    // Focus on input
    chatInput.focus();
}

// Send Greeting
async function sendGreeting() {
    const greetingMessage = `Bonjour, je m'appelle ${chatState.userInfo.name}`;
    
    // Add user message to UI
    addMessage(greetingMessage, 'user');
    
    // Start inactivity timer
    resetInactivityTimer();
    
    // Send to Rasa
    await sendToRasa(greetingMessage);
}

// Send Message
async function sendMessage() {
    const message = chatInput.value.trim();
    
    if (!message) return;
    
    // Clear input
    chatInput.value = '';
    
    // Disable send button
    sendButton.disabled = true;
    
    // Add user message to UI
    addMessage(message, 'user');
    
    // Play user message sound
    playSound('userMessage');
    
    // Reset inactivity timer
    resetInactivityTimer();
    
    // Send to Rasa
    await sendToRasa(message);
    
    // Enable send button
    sendButton.disabled = false;
}

// Send Message to Rasa Server
async function sendToRasa(message) {
    showTypingIndicator();
    
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
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        hideTypingIndicator();
        
        // Add bot responses
        if (data && data.length > 0) {
            for (const msg of data) {
                await addMessage(msg.text, 'bot');
                await sleep(300); // Slight delay between multiple messages
            }
        } else {
            await addMessage("Désolé, je n'ai pas pu traiter votre message. Veuillez réessayer.", 'bot');
        }
        
    } catch (error) {
        console.error('Error sending message to Rasa:', error);
        hideTypingIndicator();
        
        await addMessage(
            "Désolé, une erreur s'est produite. Veuillez vérifier que le serveur Rasa est en cours d'exécution.",
            'bot'
        );
    }
}

// Add Message to UI
function addMessage(text, sender) {
    return new Promise((resolve) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.textContent = sender === 'bot' ? '🤖' : '👤';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        messagesList.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Play sound notification for bot messages
        if (sender === 'bot') {
            playSound('botMessage');
        }
        
        // Store message with ISO timestamp for backend
        chatState.messages.push({ 
            text, 
            sender, 
            timestamp: new Date().toISOString()
        });
        
        setTimeout(resolve, 100);
    });
}

// Show Typing Indicator
function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Hide Typing Indicator
function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

// Utility: Sleep
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Format Time
function formatTime(date) {
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

// Reset Inactivity Timer
function resetInactivityTimer() {
    chatState.lastActivityTime = Date.now();
    
    // Clear existing timer
    if (chatState.inactivityTimer) {
        clearTimeout(chatState.inactivityTimer);
    }
    
    // Set new timer
    chatState.inactivityTimer = setTimeout(() => {
        showInactivityWarning();
    }, INACTIVITY_TIMEOUT);
}

// Show Inactivity Warning
async function showInactivityWarning() {
    const warningMessage = "Vous avez été inactif pendant 10 minutes. Souhaitez-vous continuer la conversation ?\n\nSi vous ne répondez pas, la session sera terminée automatiquement et un email avec le transcript sera envoyé.";
    
    await addMessage(warningMessage, 'bot');
    
    // Wait 2 more minutes, then end conversation
    chatState.inactivityTimer = setTimeout(() => {
        endConversation(true); // Auto-end
    }, 2 * 60 * 1000);
}

// End Conversation
async function endConversation(isAuto = false) {
    // Clear inactivity timer
    if (chatState.inactivityTimer) {
        clearTimeout(chatState.inactivityTimer);
    }
    
    const endMessage = isAuto 
        ? "👋 Session terminée automatiquement après inactivité. Merci d'avoir utilisé notre chatbot ExpoBeton RDC!\n\n📧 Un email avec le transcript de notre conversation a été envoyé.\n\nÀ bientôt!"
        : "👋 Merci d'avoir utilisé notre chatbot ExpoBeton RDC!\n\n📧 Un email avec le transcript de notre conversation a été envoyé à notre équipe.\n\nSi vous avez d'autres questions, n'hésitez pas à nous recontacter!\n\nÀ bientôt!";
    
    await addMessage(endMessage, 'bot');
    
    // Send conversation to backend
    await sendConversationToBackend();
    
    // Disable input
    chatInput.disabled = true;
    sendButton.disabled = true;
    chatInput.placeholder = "Conversation terminée...";
    
    // Hide end conversation button
    endConversationButton.style.display = 'none';
    
    // Show restart option after 3 seconds
    setTimeout(() => {
        const restartDiv = document.createElement('div');
        restartDiv.style.cssText = 'text-align: center; padding: 15px;';
        restartDiv.innerHTML = '<button onclick="location.reload()" style="padding: 10px 20px; background: linear-gradient(135deg, #0A2A66 0%, #1e3a8a 100%); color: white; border: none; border-radius: 20px; cursor: pointer; font-weight: 600;">🔄 Nouvelle conversation</button>';
        document.getElementById('chat-input-container').appendChild(restartDiv);
    }, 3000);
}

// Send Conversation to Backend
async function sendConversationToBackend() {
    try {
        console.log('[END CONVERSATION] Sending conversation data to backend...');
        console.log('[END CONVERSATION] Session ID:', chatState.sessionId);
        console.log('[END CONVERSATION] User Info:', chatState.userInfo);
        console.log('[END CONVERSATION] Messages count:', chatState.messages.length);
        
        // Send via Rasa REST API with special intent
        const response = await fetch(`${RASA_SERVER_URL}/webhooks/rest/webhook`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sender: chatState.sessionId,
                message: '/end_conversation',
                metadata: {
                    messages: chatState.messages,
                    user_info: chatState.userInfo,
                    session_id: chatState.sessionId,
                    ended_at: new Date().toISOString(),
                    total_messages: chatState.messages.length
                }
            })
        });
        
        if (response.ok) {
            console.log('✅ [END CONVERSATION] Conversation data sent successfully');
        } else {
            console.error('❌ [END CONVERSATION] Failed to send:', response.status, response.statusText);
        }
        
    } catch (error) {
        console.error('❌ [END CONVERSATION] Error sending conversation to backend:', error);
        // Still mark as success since conversation is already displayed
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);
