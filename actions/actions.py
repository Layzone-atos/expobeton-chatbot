# actions/actions.py

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import os
import glob
import cohere
import numpy as np
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, environment variables must be set manually
    pass

# Initialize Cohere client
COHERE_API_KEY = os.getenv('COHERE_API_KEY', 'qvXFOdNWBqKm3BTibge6Ssic9OTWmlsLxh0MaMng')
co = cohere.Client(COHERE_API_KEY)

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')  # Default to Gmail
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')  # Set this in environment
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')  # Set this in environment
NOTIFICATION_EMAIL = 'bot@expobetonrdc.com'

# Cache for document embeddings
DOCS_CACHE = None
EMBEDDINGS_CACHE = None

# Conversation tracking
CONVERSATION_LOGS = {}
SESSION_LANGUAGES = {}  # Track detected language per session for consistency

def send_conversation_email(session_id: str, user_info: dict, messages: list):
    """Send complete conversation transcript via email"""
    try:
        # Debug: Print SMTP configuration
        print(f"[EMAIL DEBUG] SMTP_SERVER: {SMTP_SERVER}")
        print(f"[EMAIL DEBUG] SMTP_PORT: {SMTP_PORT}")
        print(f"[EMAIL DEBUG] SMTP_USERNAME: {SMTP_USERNAME}")
        print(f"[EMAIL DEBUG] SMTP_PASSWORD: {'***' if SMTP_PASSWORD else 'NOT SET'}")
        print(f"[EMAIL DEBUG] NOTIFICATION_EMAIL: {NOTIFICATION_EMAIL}")
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME or 'noreply@expobetonrdc.com'
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = f'[Bot] Conversation - {user_info.get("name", "Utilisateur")} - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        
        # Build conversation transcript
        transcript = ""
        for msg_data in messages:
            sender = "Utilisateur" if msg_data['sender'] == 'user' else "Bot"
            
            # Handle timestamp - peut être datetime ou string ISO
            timestamp = msg_data.get('timestamp')
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now()
            
            time_str = timestamp.strftime("%H:%M:%S")
            transcript += f"[{time_str}] {sender}: {msg_data['text']}\n\n"
        
        # Email body
        body = f"""
Bonjour,

Voici le transcript d'une conversation avec le chatbot ExpoBeton RDC.

=== INFORMATIONS UTILISATEUR ===
Nom: {user_info.get('name', 'Non fourni')}
Téléphone: {user_info.get('phone', 'Non fourni')}
Email: {user_info.get('email', 'Non fourni')}
Session ID: {session_id}

=== CONVERSATION ===
{transcript}
=== FIN DE CONVERSATION ===

Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Nombre de messages: {len(messages)}

Cordialement,
Bot ExpoBeton RDC
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        if SMTP_USERNAME and SMTP_PASSWORD:
            print(f"[EMAIL DEBUG] Attempting to connect to {SMTP_SERVER}:{SMTP_PORT}")
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            print(f"[EMAIL DEBUG] TLS started, logging in as {SMTP_USERNAME}")
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            print(f"[EMAIL DEBUG] Logged in, sending email to {NOTIFICATION_EMAIL}")
            server.send_message(msg)
            server.quit()
            print(f"✅ [SUCCESS] Conversation email sent for session: {session_id}")
        else:
            print(f"⚠️ [WARNING] SMTP not configured. Email not sent for session: {session_id}")
            print(f"[CONVERSATION LOG] Logging to file instead...")
            log_file = Path(__file__).parent.parent / 'conversations.log'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(body)
                f.write(f"\n{'='*50}\n")
    except Exception as e:
        print(f"❌ [ERROR] Error sending conversation email: {e}")
        import traceback
        traceback.print_exc()

def log_conversation_message(session_id: str, sender: str, text: str, user_info: dict = None):
    """Log a message in the conversation"""
    if session_id not in CONVERSATION_LOGS:
        CONVERSATION_LOGS[session_id] = {
            'messages': [],
            'user_info': user_info or {},
            'started_at': datetime.now(),
            'last_activity': datetime.now()
        }
    
    CONVERSATION_LOGS[session_id]['messages'].append({
        'sender': sender,
        'text': text,
        'timestamp': datetime.now()
    })
    CONVERSATION_LOGS[session_id]['last_activity'] = datetime.now()
    CONVERSATION_LOGS[session_id]['user_info'] = user_info or CONVERSATION_LOGS[session_id]['user_info']

def send_unanswered_question_email(user_question: str):
    """Send email notification for unanswered questions"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME or 'noreply@expobetonrdc.com'
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = f'[Bot] Question sans réponse - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        
        # Email body
        body = f"""
        Bonjour,
        
        Le chatbot ExpoBeton RDC a reçu une question à laquelle il n'a pas pu répondre.
        
        Question de l'utilisateur:
        "{user_question}"
        
        Date et heure: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        Veuillez envisager d'ajouter cette information à la base de connaissances du bot.
        
        Cordialement,
        Bot ExpoBeton RDC
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email only if SMTP is configured
        if SMTP_USERNAME and SMTP_PASSWORD:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"Email sent for unanswered question: {user_question}")
        else:
            # Log to console if email not configured
            print(f"[UNANSWERED QUESTION] Email not configured. Question logged: {user_question}")
            # Optionally, write to a file
            log_file = Path(__file__).parent.parent / 'unanswered_questions.log'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {user_question}\n")
            
    except Exception as e:
        print(f"Error sending email: {e}")
        # Still log to file as backup
        try:
            log_file = Path(__file__).parent.parent / 'unanswered_questions.log'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {user_question}\n")
        except:
            pass

def load_and_embed_docs():
    """Load all docs and create Cohere embeddings"""
    global DOCS_CACHE, EMBEDDINGS_CACHE
    
    if DOCS_CACHE is not None:
        return DOCS_CACHE, EMBEDDINGS_CACHE
    
    docs_path = Path(__file__).parent.parent / 'docs'
    documents = []
    
    # Read all .txt files
    for file_path in docs_path.glob('*.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            documents.append({
                'filename': file_path.name,
                'content': content
            })
    
    if not documents:
        return [], []
    
    # Create embeddings with Cohere
    texts = [doc['content'] for doc in documents]
    try:
        response = co.embed(
            texts=texts,
            model='embed-multilingual-v3.0',
            input_type='search_document'
        )
        embeddings = response.embeddings
        
        DOCS_CACHE = documents
        EMBEDDINGS_CACHE = np.array(embeddings)
        
        return documents, embeddings
    except Exception as e:
        print(f"Error creating embeddings: {e}")
        return documents, []

def find_relevant_docs(query: str, top_k: int = 2):
    """Find most relevant documents using Cohere embeddings"""
    documents, doc_embeddings = load_and_embed_docs()
    
    if not documents or len(doc_embeddings) == 0:
        return []
    
    try:
        # Create embedding for query
        query_response = co.embed(
            texts=[query],
            model='embed-multilingual-v3.0',
            input_type='search_query'
        )
        query_embedding = np.array(query_response.embeddings[0])
        
        # Calculate cosine similarity
        doc_embeddings_array = np.array(doc_embeddings)
        similarities = np.dot(doc_embeddings_array, query_embedding) / (
            np.linalg.norm(doc_embeddings_array, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top_k most relevant docs
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        relevant_docs = [documents[i] for i in top_indices]
        
        return relevant_docs
    except Exception as e:
        print(f"Error finding relevant docs: {e}")
        return []

# Multilingual content dictionary
MULTILINGUAL_CONTENT = {
    'greeting': {
        'fr': "Bonjour! Je suis ravi de vous aider. Comment puis-je vous renseigner sur ExpoBeton RDC aujourd'hui?",
        'en': "Hello! I'm delighted to help you. How can I assist you with ExpoBeton RDC today?",
        'zh': "您好！我很高兴为您提供帮助。我能为您提供有关ExpoBeton RDC的哪些信息？",
        'ru': "Здравствуйте! Рад помочь вам. Как я могу помочь вам с ExpoBeton RDC сегодня?",
        'es': "¡Hola! Estoy encantado de ayudarle. ¿Cómo puedo ayudarle con ExpoBeton RDC hoy?",
        'ar': "مرحباً! يسعدني مساعدتك. كيف يمكنني مساعدتك بخصوص ExpoBeton RDC اليوم؟"
    },
    'how_are_you': {
        'fr': "Je vais très bien, merci de demander! 😊 Que souhaitez-vous savoir sur ExpoBeton RDC?",
        'en': "I'm doing great, thanks for asking! 😊 What would you like to know about ExpoBeton RDC?",
        'zh': "我很好，谢谢关心！😊 您想了解关于ExpoBeton RDC的什么信息？",
        'ru': "У меня все отлично, спасибо, что спросили! 😊 Что вы хотите узнать о ExpoBeton RDC?",
        'es': "¡Estoy muy bien, gracias por preguntar! 😊 ¿Qué le gustaría saber sobre ExpoBeton RDC?",
        'ar': "أنا بخير، شكراً لسؤالك! 😊 ماذا تريد أن تعرف عن ExpoBeton RDC؟"
    },
    'what_is_expobeton': {
        'fr': "ExpoBeton RDC est le salon international de la construction, des infrastructures et du développement urbain en République Démocratique du Congo. C'est un forum annuel qui crée un espace de réflexion et de partenariat pour rebâtir les villes congolaises et soutenir la croissance économique.",
        'en': "ExpoBeton RDC is the international construction, infrastructure and urban development fair in the Democratic Republic of Congo. It's an annual forum that creates a space for reflection and partnership to rebuild Congolese cities and support economic growth.",
        'zh': "ExpoBeton RDC是刚果民主共和国的国际建筑、基础设施和城市发展博览会。这是一个年度论坛,为重建刚果城市和支持经济增长创造了一个反思和伙伴关系的空间。",
        'ru': "ExpoBeton RDC - это международная выставка строительства, инфраструктуры и городского развития в Демократической Республике Конго. Это ежегодный форум, который создает пространство для размышлений и партнерства по восстановлению конголезских городов и поддержке экономического роста.",
        'es': "ExpoBeton RDC es la feria internacional de construcción, infraestructura y desarrollo urbano en la República Democrática del Congo. Es un foro anual que crea un espacio de reflexión y asociación para reconstruir las ciudades congoleñas y apoyar el crecimiento económico.",
        'ar': "ExpoBeton RDC هو المعرض الدولي للبناء والبنية التحتية والتنمية الحضرية في جمهورية الكونغو الديمقراطية. إنه منتدى سنوي يخلق مساحة للتفكير والشراكة لإعادة بناء المدن الكونغولية ودعم النمو الاقتصادي."
    },
    'dates': {
        'fr': "L'édition 2025 d'ExpoBeton RDC aura lieu du 8 au 11 octobre 2025 à Kinshasa, au Centre Culturel et Artistique pour les Pays de l'Afrique Centrale.",
        'en': "The 2025 edition of ExpoBeton RDC will take place from October 8-11, 2025 in Kinshasa, at the Cultural and Artistic Center for Central African Countries.",
        'zh': "ExpoBeton RDC 2025年版将于2025年10月8日至11日在金沙萨中非国家文化艺术中心举行。",
        'ru': "Выпуск ExpoBeton RDC 2025 года состоится с 8 по 11 октября 2025 года в Киншасе, в Культурно-художественном центре для стран Центральной Африки.",
        'es': "La edición 2025 de ExpoBeton RDC tendrá lugar del 8 al 11 de octubre de 2025 en Kinshasa, en el Centro Cultural y Artístico para los Países de África Central.",
        'ar': "ستقام نسخة 2025 من ExpoBeton RDC من 8 إلى 11 أكتوبر 2025 في كينشاسا، في المركز الثقافي والفني لبلدان أفريقيا الوسطى."
    },
    'location': {
        'fr': "ExpoBeton RDC se tiendra à Kinshasa, au Centre Culturel et Artistique pour les Pays de l'Afrique Centrale.",
        'en': "ExpoBeton RDC will be held in Kinshasa, at the Cultural and Artistic Center for Central African Countries.",
        'zh': "ExpoBeton RDC将在金沙萨中非国家文化艺术中心举行。",
        'ru': "ExpoBeton RDC будет проходить в Киншасе, в Культурно-художественном центре для стран Центральной Африки.",
        'es': "ExpoBeton RDC se celebrará en Kinshasa, en el Centro Cultural y Artístico para los Países de África Central.",
        'ar': "سيقام ExpoBeton RDC في كينشاسا، في المركز الثقافي والفني لبلدان أفريقيا الوسطى."
    },
    'thank_you': {
        'fr': "De rien! C'est avec plaisir! 😊\n\nSi vous avez d'autres questions sur ExpoBeton RDC, n'hésitez pas à me demander!",
        'en': "You're welcome! My pleasure! 😊\n\nIf you have any other questions about ExpoBeton RDC, don't hesitate to ask!",
        'zh': "不客气！很高兴为您服务！😊\n\n如果您对ExpoBeton RDC有任何其他问题，请随时提问！",
        'ru': "Пожалуйста! С удовольствием! 😊\n\nЕсли у вас есть другие вопросы о ExpoBeton RDC, не стесняйтесь спрашивать!",
        'es': "¡De nada! ¡Un plaisir! 😊\n\nSi tiene otras preguntas sobre ExpoBeton RDC, ¡no dude en preguntar!",
        'ar': "على الرحب والسعة! بكل سرور! 😊\n\nإذا كان لديك أي أسئلة أخرى حول ExpoBeton RDC، لا تتردد في السؤال!"
    },
    'goodbye': {
        'fr': "Au revoir! Merci d'avoir utilisé notre chatbot ExpoBeton RDC! 👋\n\nÀ très bientôt! N'hésitez pas à revenir si vous avez d'autres questions.",
        'en': "Goodbye! Thank you for using our ExpoBeton RDC chatbot! 👋\n\nSee you soon! Don't hesitate to come back if you have other questions.",
        'zh': "再见！感谢您使用我们的ExpoBeton RDC聊天机器人！👋\n\n很快见！如果您有其他问题，请随时回来。",
        'ru': "До свидания! Спасибо за использование нашего чат-бота ExpoBeton RDC! 👋\n\nДо скорой встречи! Не стесняйтесь вернуться, если у вас есть другие вопросы.",
        'es': "¡Adiós! ¡Gracias por usar nuestro chatbot ExpoBeton RDC! 👋\n\n¡Hasta pronto! No dude en volver si tiene otras preguntas.",
        'ar': "وداعاً! شكراً لاستخدامك روبوت الدردشة ExpoBeton RDC! 👋\n\nإلى اللقاء قريباً! لا تتردد في العودة إذا كان لديك أسئلة أخرى."
    },
    'fallback': {
        'fr': "Concernant cette question, je ne peux pas vous fournir de réponse pour le moment. Je vous suggère de contacter notre équipe par email à info@expobetonrdc.com.\n\n💡 Voici ce que je peux vous renseigner :\n• L'événement ExpoBeton\n• Les dates et le lieu\n• Le thème\n• Les fondateurs\n• Comment participer\n• Devenir ambassadeur",
        'en': "Regarding this question, I cannot provide an answer at the moment. I suggest you contact our team by email at info@expobetonrdc.com.\n\n💡 Here's what I can help you with:\n• The ExpoBeton event\n• Dates and location\n• The theme\n• The founders\n• How to participate\n• Becoming an ambassador",
        'zh': "关于这个问题，我暂时无法提供答案。我建议您通过电子邮件info@expobetonrdc.com联系我们的团队。\n\n💡 以下是我可以为您提供信息的内容：\n• ExpoBeton活动\n• 日期和地点\n• 主题\n• 创始人\n• 如何参加\n• 成为大使",
        'ru': "Относительно этого вопроса я не могу дать ответ в данный момент. Я предлагаю вам связаться с нашей командой по электронной почте info@expobetonrdc.com.\n\n💡 Вот с чем я могу вам помочь:\n• Мероприятие ExpoBeton\n• Даты и местоположение\n• Тема\n• Основатели\n• Как принять участие\n• Стать послом",
        'es': "Con respecto a esta pregunta, no puedo proporcionar una respuesta en este momento. Le sugiero que se ponga en contacto con nuestro equipo por correo electrónico a info@expobetonrdc.com.\n\n💡 Esto es lo que puedo ayudarle:\n• El evento ExpoBeton\n• Fechas y ubicación\n• El tema\n• Los fundadores\n• Cómo participar\n• Convertirse en embajador",
        'ar': "فيما يتعلق بهذا السؤال، لا يمكنني تقديم إجابة في الوقت الحالي. أقترح عليك الاتصال بفريقنا عبر البريد الإلكتروني info@expobetonrdc.com.\n\n💡 إليك ما يمكنني مساعدتك به:\n• حدث ExpoBeton\n• التواريخ والموقع\n• الموضوع\n• المؤسسون\n• كيفية المشاركة\n• أن تصبح سفيراً"
    },
    'registration': {
        'fr': "Pour participer à ExpoBeton RDC 2025, inscrivez-vous en ligne sur https://expobetonrdc.com/#tg_register.\n\n💡 Vous pourriez aussi demander :\n• Quelles sont les dates ?\n• Comment devenir ambassadeur ?\n• Quel est le thème ?",
        'en': "To participate in ExpoBeton RDC 2025, register online at https://expobetonrdc.com/#tg_register.\n\n💡 You might also ask:\n• What are the dates?\n• How to become an ambassador?\n• What is the theme?",
        'zh': "要参加ExpoBeton RDC 2025，请在https://expobetonrdc.com/#tg_register在线注册。\n\n💡 您还可以问：\n• 日期是什么时候？\n• 如何成为大使？\n• 主题是什么？",
        'ru': "Чтобы принять участие в ExpoBeton RDC 2025, зарегистрируйтесь онлайн на https://expobetonrdc.com/#tg_register.\n\n💡 Вы также можете спросить:\n• Какие даты?\n• Как стать послом?\n• Какая тема?",
        'es': "Para participar en ExpoBeton RDC 2025, regístrese en línea en https://expobetonrdc.com/#tg_register.\n\n💡 También podría preguntar:\n• ¿Cuáles son las fechas?\n• ¿Cómo convertirse en embajador?\n• ¿Cuál es el tema?",
        'ar': "للمشاركة في ExpoBeton RDC 2025، سجل عبر الإنترنت على https://expobetonrdc.com/#tg_register.\n\n💡 قد تسأل أيضاً:\n• ما هي التواريخ؟\n• كيف تصبح سفيراً؟\n• ما هو الموضوع؟"
    }
}

def detect_language(text: str) -> str:
    """Detect language from user text. Returns language code."""
    text_lower = text.lower()
    
    # French keywords
    french_keywords = ['bonjour', 'salut', 'merci', 'quoi', 'comment', 'pourquoi', 'quand', 'où', 'est-ce', 'c\'est', 'quelles', 'quel', 'quelle']
    # English keywords  
    english_keywords = ['hello', 'hi', 'thank', 'what', 'how', 'why', 'when', 'where', 'is', 'are', 'can', 'could', 'would']
    # Spanish keywords
    spanish_keywords = ['hola', 'gracias', 'qué', 'cómo', 'cuándo', 'dónde', 'por qué', 'buenos', 'días']
    # Russian keywords (Cyrillic)
    russian_keywords = ['привет', 'спасибо', 'что', 'как', 'когда', 'где', 'почему', 'здравствуй']
    # Chinese characters detection
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
    # Arabic characters detection
    has_arabic = any('\u0600' <= char <= '\u06ff' for char in text)
    
    # Count matches
    french_score = sum(1 for keyword in french_keywords if keyword in text_lower)
    english_score = sum(1 for keyword in english_keywords if keyword in text_lower)
    spanish_score = sum(1 for keyword in spanish_keywords if keyword in text_lower)
    russian_score = sum(1 for keyword in russian_keywords if keyword in text_lower)
    
    if has_chinese:
        return 'zh'
    if has_arabic:
        return 'ar'
    if russian_score > 0:
        return 'ru'
    if spanish_score > english_score and spanish_score > french_score:
        return 'es'
    if english_score > french_score:
        return 'en'
    if french_score > 0:
        return 'fr'
    
    # Default to French
    return 'fr'

def get_multilingual_response(key: str, lang: str = 'fr') -> str:
    """Get response in the specified language."""
    if key in MULTILINGUAL_CONTENT and lang in MULTILINGUAL_CONTENT[key]:
        return MULTILINGUAL_CONTENT[key][lang]
    # Fallback to French
    if key in MULTILINGUAL_CONTENT and 'fr' in MULTILINGUAL_CONTENT[key]:
        return MULTILINGUAL_CONTENT[key]['fr']
    return ""

class ActionGreetPersonalized(Action):
    """Custom action for personalized greeting with name extraction"""
    
    def name(self) -> Text:
        return "action_greet_personalized"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get person entity
        person = next(tracker.get_latest_entity_values("person"), None)
        
        # Detect language
        user_message = tracker.latest_message.get('text', '')
        detected_lang = detect_language(user_message)
        
        if person:
            # Personalized greeting with name
            if detected_lang == 'fr':
                message = f"Bonjour {person}! 😊 Ravi de faire votre connaissance! Comment puis-je vous aider aujourd'hui avec ExpoBeton RDC?"
            elif detected_lang == 'en':
                message = f"Hello {person}! 😊 Nice to meet you! How can I assist you today with ExpoBeton RDC?"
            else:
                message = f"Bonjour {person}! 😊 Ravi de faire votre connaissance! Comment puis-je vous aider aujourd'hui avec ExpoBeton RDC?"
        else:
            # Generic greeting
            message = get_multilingual_response('greeting', detected_lang)
            if detected_lang == 'fr':
                message = message.replace("Bonjour!", "Bonjour! 😊")
            elif detected_lang == 'en':
                message = message.replace("Hello!", "Hello! 😊")
        
        dispatcher.utter_message(text=message)
        return []

class ActionAnswerExpoBeton(Action):
    def name(self) -> Text:
        return "action_answer_expobeton"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_question = tracker.latest_message.get('text', '').lower()
        user_message_original = tracker.latest_message.get('text', '')
        session_id = tracker.sender_id
        metadata = tracker.latest_message.get('metadata', {})
        
        # Detect user's language for EACH message (not session-based)
        detected_lang = detect_language(user_message_original)
        print(f"[MULTILINGUAL] Detected language: {detected_lang} for message: {user_message_original[:50]}")
        
        # Log user message
        log_conversation_message(session_id, 'user', user_message_original, metadata)
        
        bot_response = ""
        
        # How are you? responses (CHECK FIRST - more specific than greeting, more friendly)
        user_question_clean = user_question.replace('?', '').replace('!', '').strip()
        if any(phrase in user_question_clean for phrase in ['how are you', 'comment allez-vous', 'comment vas-tu', 'comment allez vous', 'comment vas tu', 'ça va', 'ca va', 'cómo estás', '如何', 'как дела', 'كيف حالك']):
            # Friendly response with emoji
            if detected_lang == 'fr':
                answer = "Je vais très bien, merci de demander! 😊 Et vous, comment allez-vous? Que souhaitez-vous savoir sur ExpoBeton RDC?"
            elif detected_lang == 'en':
                answer = "I'm doing great, thanks for asking! 😊 And you, how are you? What would you like to know about ExpoBeton RDC?"
            elif detected_lang == 'zh':
                answer = "我很好，谢谢关心！😊 您呢，您好吗？您想了解关于ExpoBeton RDC的什么信息？"
            elif detected_lang == 'ru':
                answer = "У меня все отлично, спасибо, что спросили! 😊 А у вас как дела? Что вы хотите узнать о ExpoBeton RDC?"
            elif detected_lang == 'es':
                answer = "¡Estoy muy bien, gracias por preguntar! 😊 ¿Y usted, cómo está? ¿Qué le gustaría saber sobre ExpoBeton RDC?"
            elif detected_lang == 'ar':
                answer = "أنا بخير، شكراً لسؤالك! 😊 وأنت، كيف حالك؟ ماذا تريد أن تعرف عن ExpoBeton RDC؟"
            else:
                answer = get_multilingual_response('how_are_you', detected_lang)
            
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Greetings and politeness responses (FRIENDLY with emojis)
        if any(word in user_question for word in ['bonjour', 'salut', 'hello', 'hi', 'bonsoir', 'hola', 'привет', '你好', 'مرحبا']):
            # Extract user's name if provided
            user_name = None
            import re
            name_patterns = [
                r"je m['\u2019]appelle\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)*)",  # French - capture name with spaces
                r"my name is\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",  # English - capture name with spaces
                r"i['\u2019]m\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",  # English - capture name with spaces
                r"me llamo\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",  # Spanish - capture name with spaces
            ]
            for pattern in name_patterns:
                match = re.search(pattern, user_message_original, re.IGNORECASE)
                if match:
                    user_name = match.group(1).strip().title()
                    break
            
            # Build personalized greeting with FRIENDLY tone and emoji
            if user_name and detected_lang == 'fr':
                answer = f"Bonjour {user_name}! 😊 Enchanté de faire votre connaissance! Comment allez-vous? Qu'aimeriez-vous savoir sur ExpoBeton RDC?"
            elif user_name and detected_lang == 'en':
                answer = f"Hello {user_name}! 😊 Nice to meet you! How are you doing? What would you like to know about ExpoBeton RDC?"
            else:
                # Add emoji to generic greeting
                base_answer = get_multilingual_response('greeting', detected_lang)
                if detected_lang == 'fr':
                    answer = base_answer.replace("Bonjour!", "Bonjour! 😊")
                elif detected_lang == 'en':
                    answer = base_answer.replace("Hello!", "Hello! 😊")
                else:
                    answer = base_answer
            
            dispatcher.utter_message(text=answer)
            bot_response = answer
            
            # Language-specific suggestions (only if no name given)
            if not user_name:
                if detected_lang == 'fr':
                    suggestion = "\n💡 Vous pourriez me demander:\n• C'est quoi ExpoBeton?\n• Quelles sont les dates?\n• Comment devenir ambassadeur?"
                elif detected_lang == 'en':
                    suggestion = "\n💡 You could ask me:\n• What is ExpoBeton?\n• What are the dates?\n• How to become an ambassador?"
                elif detected_lang == 'zh':
                    suggestion = "\n💡 您可以问我：\n• 什么是ExpoBeton？\n• 日期是什么时候？\n• 如何成为大使？"
                elif detected_lang == 'ru':
                    suggestion = "\n💡 Вы можете спросить меня:\n• Что такое ExpoBeton?\n• Какие даты?\n• Как стать послом?"
                elif detected_lang == 'es':
                    suggestion = "\n💡 Podría preguntarme:\n• ¿Qué es ExpoBeton?\n• ¿Cuáles son las fechas?\n• ¿Cómo convertirse en embajador?"
                elif detected_lang == 'ar':
                    suggestion = "\n💡 يمكنك أن تسألني:\n• ما هو ExpoBeton؟\n• ما هي التواريخ؟\n• كيف تصبح سفيرا؟"
                else:
                    suggestion = "\n💡 Vous pourriez me demander:\n• C'est quoi ExpoBeton?\n• Quelles sont les dates?\n• Comment devenir ambassadeur?"
                dispatcher.utter_message(text=suggestion)
                bot_response += suggestion
            
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Thank you responses
        if any(word in user_question for word in ['merci', 'thanks', 'thank you', 'thank', 'danke', 'gracias', 'спасибо', 'شكرا']):
            answer = get_multilingual_response('thank_you', detected_lang)
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Goodbye responses
        if any(word in user_question for word in ['au revoir', 'bye', 'goodbye', 'à bientôt', 'adieu', 'ciao', 'adiós', 'пока', '再见', 'مع السلامة']):
            answer = get_multilingual_response('goodbye', detected_lang)
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            # Send conversation email
            if session_id in CONVERSATION_LOGS:
                conversation = CONVERSATION_LOGS[session_id]
                if len(conversation['messages']) > 0:
                    send_conversation_email(
                        session_id,
                        conversation['user_info'],
                        conversation['messages']
                    )
            return []
        
        # Ambassador questions - MULTILINGUAL SUPPORT
        if any(word in user_question for word in ['ambassadeur', 'ambassador', 'devenir', 'rejoindre', 'become']):
            # Check if we have multilingual content for ambassador
            if detected_lang == 'en':
                answer = "To become an ExpoBeton RDC Ambassador:\n\n✅ Membership is by selection\n✅ Apply online at https://expobetonrdc.com/\n\nProfiles sought:\n• Technical and scientific experts\n• Opinion leaders and influencers\n• Construction professionals\n• Innovative entrepreneurs\n• Academics and researchers\n\nAs an Ambassador, you participate in thematic Think Tanks, contribute to reconstruction policies, and benefit from a national and international network of influence."
                suggestion = "\n💡 You might also ask:\n• What is ExpoBeton?\n• What are the event dates?\n• Who are the founders?"
            else:  # French (default)
                answer = "Pour devenir Ambassadeur d'Expo Béton RDC :\n\n✅ L'adhésion se fait sur sélection\n✅ Postulez en ligne sur https://expobetonrdc.com/\n\nProfils recherchés :\n• Experts techniques et scientifiques\n• Leaders d'opinion et influenceurs\n• Professionnels du BTP\n• Entrepreneurs innovants\n• Universitaires et chercheurs\n\nEn tant qu'Ambassadeur, vous participez aux Think Tanks thématiques, contribuez aux politiques de reconstruction, et bénéficiez d'un réseau d'influence national et international."
                suggestion = "\n💡 Vous pourriez aussi me demander :\n• C'est quoi ExpoBeton ?\n• Quelles sont les dates de l'événement ?\n• Qui sont les fondateurs ?"
            
            dispatcher.utter_message(text=answer)
            bot_response = answer
            dispatcher.utter_message(text=suggestion)
            bot_response += suggestion
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Try to find relevant documents
        try:
            relevant_docs = find_relevant_docs(tracker.latest_message.get('text', ''), top_k=2)
        except:
            relevant_docs = []
        
        # Founder questions
        if any(word in user_question for word in ['fondateur', 'créateur', 'président', 'qui est', 'qui sont']):
            if 'jean' in user_question or 'bamanisa' in user_question or 'fondateur' in user_question or 'créateur' in user_question:
                answer = "Jean Bamanisa Saïdi est le président, promoteur, créateur et fondateur d'ExpoBeton RDC. C'est un homme d'affaires et personnalité politique congolaise, ancien gouverneur de la province de l'Ituri. Il porte la vision stratégique de l'événement et met en avant la reconstruction, l'urbanisation et le développement durable de la RDC."
                dispatcher.utter_message(text=answer)
                suggestion = "\n💡 Vous pourriez aussi demander :\n• Qui est le vice-président ?\n• Comment devenir ambassadeur ?\n• Quelles sont les dates de l'événement ?"
                dispatcher.utter_message(text=suggestion)
                return []
            if 'momo' in user_question or 'sungunza' in user_question or 'vice' in user_question:
                answer = "Momo Sungunza est le vice-président d'ExpoBeton RDC. Il assure la coordination opérationnelle et organisationnelle du forum, et travaille en tandem avec Jean Bamanisa pour mobiliser les partenaires publics et privés."
                dispatcher.utter_message(text=answer)
                suggestion = "\n💡 Vous pourriez aussi demander :\n• Qui est le fondateur ?\n• C'est quoi le thème de l'édition 2025 ?\n• Comment participer ?"
                dispatcher.utter_message(text=suggestion)
                return []
        
        # What is ExpoBeton (handle typos like 'expbeton', 'expo beton')
        if any(word in user_question for word in ['quoi', 'what', 'est-ce', 'c\'est', 'qué', '什么', 'что', 'ما']):
            # Check for 'expobeton' or common typos like 'expbeton'
            if 'expobeton' in user_question or 'expbeton' in user_question or 'expo beton' in user_question or 'expo béton' in user_question:
                answer = get_multilingual_response('what_is_expobeton', detected_lang)
                dispatcher.utter_message(text=answer)
                bot_response = answer
                log_conversation_message(session_id, 'bot', bot_response, metadata)
                return []
        
        # Dates
        if any(word in user_question for word in ['date', 'when', 'quand', 'cuándo', 'когда', '什么时候', 'متى']):
            answer = get_multilingual_response('dates', detected_lang)
            dispatcher.utter_message(text=answer)
            return []
        
        # Location
        if any(word in user_question for word in ['lieu', 'where', 'où', 'dónde', 'где', '哪里', 'أين']):
            answer = get_multilingual_response('location', detected_lang)
            dispatcher.utter_message(text=answer)
            return []
        
        # Theme
        if any(word in user_question for word in ['thème', 'theme', 'sujet']):
            answer = "Le thème de l'édition 2025 est : '100 milliards USD pour rebâtir la RDC post-conflit : catalyser une transformation audacieuse pour le 21ème siècle'."
            dispatcher.utter_message(text=answer)
            suggestion = "\n💡 Vous pourriez aussi demander :\n• Qui sont les fondateurs ?\n• Comment devenir ambassadeur ?\n• Où se déroule l'événement ?"
            dispatcher.utter_message(text=suggestion)
            return []
        
        # Registration / Participation
        if any(word in user_question for word in ['inscription', 'register', 'participer', 'participate', 'subscribe', 'join', 'enroll']):
            answer = get_multilingual_response('registration', detected_lang)
            dispatcher.utter_message(text=answer)
            bot_response = answer
            log_conversation_message(session_id, 'bot', bot_response, metadata)
            return []
        
        # Default: show help and log unanswered question
        user_message = tracker.latest_message.get('text', '')
        session_id = tracker.sender_id
        metadata = tracker.latest_message.get('metadata', {})
        
        # Send email notification for unanswered question
        send_unanswered_question_email(user_message)
        
        # Use multilingual fallback message
        fallback_message = get_multilingual_response('fallback', detected_lang)
        
        dispatcher.utter_message(text=fallback_message)
        
        # Log bot response
        log_conversation_message(session_id, 'bot', fallback_message, metadata)
        
        # Send conversation email after every 3 messages or fallback
        if session_id in CONVERSATION_LOGS:
            msg_count = len(CONVERSATION_LOGS[session_id]['messages'])
            if msg_count >= 4:  # Send after 4 messages (2 user + 2 bot minimum)
                send_conversation_email(
                    session_id,
                    CONVERSATION_LOGS[session_id]['user_info'],
                    CONVERSATION_LOGS[session_id]['messages']
                )
        
        return []

class ActionAnswerAndSuggest(Action):
    def name(self) -> Text:
        return "action_answer_and_suggest"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_question = tracker.latest_message.get('text')

        # Exemple simple : réponse + suggestion
        if "dates" in user_question.lower():
            answer = "Expo Béton RDC aura lieu du 8 au 11 octobre 2025 à Kinshasa."
            suggestion = "Souhaitez-vous connaître les exposants présents ?"
        else:
            answer = "Je suis là pour vous aider sur Expo Béton RDC."
            suggestion = "Souhaitez-vous découvrir les opportunités d'investissement ?"

        dispatcher.utter_message(text=answer)
        dispatcher.utter_message(text=suggestion)

        return []

class ActionEndConversation(Action):
    def name(self) -> Text:
        return "action_end_conversation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        session_id = tracker.sender_id
        metadata = tracker.latest_message.get('metadata', {})
        
        print(f"\n{'='*60}")
        print(f"[ACTION END CONVERSATION] Called for session: {session_id}")
        print(f"[ACTION END CONVERSATION] Metadata received: {metadata}")
        print(f"[ACTION END CONVERSATION] Has 'messages' in metadata: {'messages' in metadata}")
        print(f"[ACTION END CONVERSATION] Has 'user_info' in metadata: {'user_info' in metadata}")
        print(f"{'='*60}\n")
        
        # Get conversation data from metadata if provided by frontend
        if 'messages' in metadata and 'user_info' in metadata:
            print(f"[ACTION END CONVERSATION] Using metadata from frontend")
            # Frontend sent complete conversation data
            messages = metadata.get('messages', [])
            user_info = metadata.get('user_info', {})
            
            print(f"[ACTION END CONVERSATION] Messages count: {len(messages)}")
            print(f"[ACTION END CONVERSATION] User info: {user_info}")
            
            # Convert frontend message format to backend format
            formatted_messages = []
            for msg in messages:
                # Handle timestamp - JavaScript toISOString() adds 'Z' which needs to be replaced
                timestamp = msg.get('timestamp')
                if isinstance(timestamp, str):
                    try:
                        # Replace 'Z' with '+00:00' for Python compatibility
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except Exception as e:
                        print(f"[ERROR] Failed to parse timestamp '{timestamp}': {e}")
                        timestamp = datetime.now()
                elif not isinstance(timestamp, datetime):
                    timestamp = datetime.now()
                
                formatted_messages.append({
                    'sender': msg.get('sender'),
                    'text': msg.get('text'),
                    'timestamp': timestamp
                })
            
            # Send email with conversation
            print(f"[ACTION END CONVERSATION] Sending email...")
            send_conversation_email(session_id, user_info, formatted_messages)
            print(f"✅ [ACTION END CONVERSATION] Conversation ended and email sent for session: {session_id}")
            
        # Or check if we have messages in our local storage
        elif session_id in CONVERSATION_LOGS:
            print(f"[ACTION END CONVERSATION] Using conversation logs from memory")
            conversation = CONVERSATION_LOGS[session_id]
            if len(conversation['messages']) > 0:
                print(f"[ACTION END CONVERSATION] Messages in log: {len(conversation['messages'])}")
                send_conversation_email(
                    session_id,
                    conversation['user_info'],
                    conversation['messages']
                )
                # Clear conversation from memory
                del CONVERSATION_LOGS[session_id]
                print(f"✅ [ACTION END CONVERSATION] Conversation ended and email sent for session: {session_id}")
            else:
                print(f"⚠️ [ACTION END CONVERSATION] No messages found in conversation log")
        else:
            print(f"❌ [ACTION END CONVERSATION] No conversation data found!")
            print(f"   - Not in metadata")
            print(f"   - Not in CONVERSATION_LOGS")
            print(f"   - Available CONVERSATION_LOGS keys: {list(CONVERSATION_LOGS.keys())}")
        
        dispatcher.utter_message(
            text="👋 Merci pour votre visite! La conversation a été enregistrée."
        )
        
        return []

class ActionAskFeedbackRating(Action):
    """Custom action to ask for feedback in the user's language"""
    
    def name(self) -> Text:
        return "action_ask_feedback_rating"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Detect language from the LAST user message
        events = tracker.events
        user_messages = [e for e in events if e.get('event') == 'user']
        
        if user_messages:
            last_user_message = user_messages[-1].get('text', '')
            detected_lang = detect_language(last_user_message)
        else:
            detected_lang = 'fr'  # Default to French
        
        # Multilingual feedback prompts
        feedback_prompts = {
            'fr': {
                'text': "Nous aimerions connaître votre avis! Comment trouvez-vous notre service?",
                'thumbs_up': "👍 Excellent",
                'thumbs_down': "👎 Peut être amélioré"
            },
            'en': {
                'text': "We'd love to hear your feedback! How would you rate our service?",
                'thumbs_up': "👍 Excellent",
                'thumbs_down': "👎 Could be better"
            },
            'zh': {
                'text': "我们很想听到您的反馈！您如何评价我们的服务？",
                'thumbs_up': "👍 非常好",
                'thumbs_down': "👎 可以更好"
            },
            'ru': {
                'text': "Мы бы хотели услышать ваше мнение! Как вы оцениваете наш сервис?",
                'thumbs_up': "👍 Отлично",
                'thumbs_down': "👎 Можно лучше"
            },
            'es': {
                'text': "¡Nos encantaría conocer tu opinión! ¿Cómo calificarías nuestro servicio?",
                'thumbs_up': "👍 Excelente",
                'thumbs_down': "👎 Podría mejorar"
            },
            'ar': {
                'text': "نود أن نسمع رأيك! كيف تقيّم خدمتنا؟",
                'thumbs_up': "👍 ممتاز",
                'thumbs_down': "👎 يمكن أن يكون أفضل"
            }
        }
        
        prompt = feedback_prompts.get(detected_lang, feedback_prompts['fr'])
        
        buttons = [
            {"title": prompt['thumbs_up'], "payload": "/SetSlots(feedback_rating=thumbs_up)"},
            {"title": prompt['thumbs_down'], "payload": "/SetSlots(feedback_rating=thumbs_down)"}
        ]
        
        dispatcher.utter_message(text=prompt['text'], buttons=buttons)
        return []

class ActionThankYouPositive(Action):
    """Custom action for positive feedback thank you in user's language"""
    
    def name(self) -> Text:
        return "action_thankyou_positive"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Detect language from the LAST user message
        events = tracker.events
        user_messages = [e for e in events if e.get('event') == 'user']
        
        if user_messages:
            last_user_message = user_messages[-1].get('text', '')
            detected_lang = detect_language(last_user_message)
        else:
            detected_lang = 'fr'  # Default to French
        
        # Multilingual positive feedback responses
        positive_responses = {
            'fr': "C'est merveilleux à entendre! Merci d'avoir pris le temps de nous donner votre avis. 🌟",
            'en': "That's wonderful to hear! Thank you for taking the time to share your feedback. 🌟",
            'zh': "真好！感谢您花时间分享您的反馈。🌟",
            'ru': "Замечательно! Спасибо, что нашли время поделиться своим мнением. 🌟",
            'es': "¡Qué maravilloso escuchar eso! Gracias por tomarse el tiempo de compartir sus comentarios. 🌟",
            'ar': "هذا رائع! شكراً لك على أخذ الوقت لمشاركة رأيك. 🌟"
        }
        
        message = positive_responses.get(detected_lang, positive_responses['fr'])
        dispatcher.utter_message(text=message)
        return []

class ActionThankYouNegative(Action):
    """Custom action for negative feedback thank you in user's language"""
    
    def name(self) -> Text:
        return "action_thankyou_negative"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Detect language from the LAST user message
        events = tracker.events
        user_messages = [e for e in events if e.get('event') == 'user']
        
        if user_messages:
            last_user_message = user_messages[-1].get('text', '')
            detected_lang = detect_language(last_user_message)
        else:
            detected_lang = 'fr'  # Default to French
        
        # Multilingual negative feedback responses
        negative_responses = {
            'fr': "Nous apprécions que vous ayez pris le temps de nous donner votre avis. Nous travaillons toujours à améliorer notre service.",
            'en': "We appreciate you taking the time to share your feedback. We're always working to improve our service.",
            'zh': "感谢您花时间分享您的反馈。我们一直在努力改进我们的服务。",
            'ru': "Мы ценим, что вы нашли время поделиться своим мнением. Мы постоянно работаем над улучшением нашего сервиса.",
            'es': "Agradecemos que se haya tomado el tiempo de compartir sus comentarios. Siempre estamos trabajando para mejorar nuestro servicio.",
            'ar': "نحن نقدر أخذك الوقت لمشاركة رأيك. نحن نعمل دائماً على تحسين خدمتنا."
        }
        
        message = negative_responses.get(detected_lang, negative_responses['fr'])
        dispatcher.utter_message(text=message)
        return []
