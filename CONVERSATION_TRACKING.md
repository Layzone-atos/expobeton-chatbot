# 📧 Conversation Email Tracking - ExpoBeton RDC

## ✅ Feature Overview

**ALL conversations** with the chatbot are now automatically tracked and sent via email to **bot@expobetonrdc.com**.

### What Gets Sent:

1. **Complete Conversation Transcript** - Every message exchange
2. **User Information** - Name, phone, email (from web form)
3. **Session Details** - Session ID, timestamp, message count
4. **Metadata** - All conversation context

---

## 📋 When Emails Are Sent:

Conversation emails are sent automatically when:

1. **After 4+ messages** - Once a conversation has at least 4 messages (2 from user, 2 from bot)
2. **When fallback is triggered** - When the bot can't answer a question
3. **Unanswered questions** - Separate email for questions the bot couldn't answer

---

## 📧 Email Format:

### **Subject:**
```
[Bot] Conversation - [User Name] - 2025-10-25 15:42
```

### **Email Body:**
```
Bonjour,

Voici le transcript d'une conversation avec le chatbot ExpoBeton RDC.

=== INFORMATIONS UTILISATEUR ===
Nom: Jean Dupont
Téléphone: +243 XX XXX XXXX
Email: jean@example.com
Session ID: session_1234567890_abc123

=== CONVERSATION ===
[15:30:45] Utilisateur: Bonjour, je m'appelle Jean Dupont

[15:30:47] Bot: Bonjour Jean! Comment puis-je vous aider aujourd'hui?

[15:31:02] Utilisateur: C'est quoi ExpoBeton?

[15:31:04] Bot: ExpoBeton RDC est le salon international de la construction...

=== FIN DE CONVERSATION ===

Date: 2025-10-25 15:31:04
Nombre de messages: 4

Cordialement,
Bot ExpoBeton RDC
```

---

## 🔧 How It Works:

### 1. **Message Logging**
Every message (user & bot) is stored in memory with:
- Sender (user/bot)
- Text content
- Timestamp
- User metadata

### 2. **Conversation Tracking**
Each session is tracked by:
- Session ID (unique per user)
- User information
- Message history
- Last activity timestamp

### 3. **Email Trigger**
Emails are sent when:
- Message count reaches 4 or more
- Fallback is triggered
- Conversation ends

---

## 📁 Backup Logging:

If SMTP email fails, conversations are logged to:
```
conversations.log
```

This file contains the same information as the email.

---

## 🎯 Benefits:

✅ **Track all customer interactions**  
✅ **Monitor bot performance**  
✅ **Identify knowledge gaps**  
✅ **Follow up with users**  
✅ **Analyze common questions**  
✅ **Improve bot responses**  

---

## 🔍 Monitoring:

Check your **bot@expobetonrdc.com** inbox to see:

1. **Real-time conversations** as they happen
2. **User contact information** for follow-ups
3. **Questions the bot couldn't answer**
4. **Complete conversation context**

---

## 📊 Data Collected:

### From Web Form:
- Full name (required)
- Phone number (optional)
- Email (optional)

### From Conversation:
- All messages exchanged
- Timestamps
- Session duration
- Bot responses
- User questions

---

## 🔐 Privacy:

- User data is only sent to bot@expobetonrdc.com
- SMTP credentials are securely stored in `.env` file
- Conversations are logged locally as backup
- No third-party services used

---

## 🚀 Testing:

1. Open the web chat interface
2. Fill in the user form
3. Have a conversation (ask 2-3 questions)
4. Check **bot@expobetonrdc.com** inbox
5. You should receive an email with the full transcript!

---

## 📞 Support:

For questions about conversation tracking:
- Email: info@expobetonrdc.com
- Check logs: `conversations.log` and `unanswered_questions.log`

---

**Developed for ExpoBeton RDC** 🏗️🇨🇩
