<?php
/**
 * ExpoBeton RDC — Relais Live Chat (PHP local, zéro requête Railway)
 *
 * Quand un opérateur est connecté au dashboard (heartbeat api_live_presence.php),
 * le widget public du site passe en mode « live » et dialogue avec ce point
 * d'entrée ; les échanges sont stockés dans livechat_sessions /
 * livechat_messages puis transcrits par email à la clôture, au même format
 * que les transcripts du chatbot (CORRECTION_EMAILS.md).
 *
 * Actions publiques (jeton visiteur)  : start, send, poll, close
 * Actions opérateur (session admincb) : operator_send, operator_poll, operator_close
 *
 * Ce fichier expose aussi ses fonctions à livechat.php (page opérateur) :
 * le dispatch ci-dessous ne tourne que lorsqu'il est appelé directement.
 */
/* En-têtes API posés seulement en appel direct : inclus par livechat.php,
   ce fichier ne doit pas imposer son Content-Type JSON à la page HTML. */
if (basename($_SERVER['SCRIPT_FILENAME']) === 'api_livechat.php') {
    header('Content-Type: application/json; charset=UTF-8');
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');

    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        http_response_code(200);
        exit;
    }
}

require_once __DIR__ . '/auth.php';

/* Boîte de traçabilité commune au bot et au live (cf. CORRECTION_EMAILS.md). */
if (!defined('LIVECHAT_NOTIFY_EMAIL')) {
    define('LIVECHAT_NOTIFY_EMAIL', 'bot@expobetonrdc.com');
}

/* ------------------------------------------------------------------ */
/* Schéma                                                              */
/* ------------------------------------------------------------------ */

function livechat_ensure_tables()
{
    static $done = false;
    if ($done) return;
    $done = true;
    $db = getDB();
    $db->exec("CREATE TABLE IF NOT EXISTS livechat_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        token CHAR(64) UNIQUE NOT NULL,
        nom VARCHAR(128) NOT NULL,
        telephone VARCHAR(32) NOT NULL,
        email VARCHAR(191) NULL,
        statut ENUM('open','closed') NOT NULL DEFAULT 'open',
        bot_transcript LONGTEXT NULL,
        operator_id INT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        closed_at DATETIME NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    $db->exec("CREATE TABLE IF NOT EXISTS livechat_messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id INT NOT NULL,
        sender ENUM('visitor','operator','system') NOT NULL,
        body TEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_livechat_session (session_id, id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
}

/* ------------------------------------------------------------------ */
/* Aides                                                               */
/* ------------------------------------------------------------------ */

function livechat_out($payload, $code = 200)
{
    http_response_code($code);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

function livechat_input()
{
    $raw = file_get_contents('php://input');
    if ($raw !== false && $raw !== '') {
        $j = json_decode($raw, true);
        if (is_array($j)) return $j;
    }
    return $_POST;
}

function livechat_str($v, $max)
{
    return mb_substr(trim((string)$v), 0, $max);
}

function livechat_session_by_token($token)
{
    $stmt = getDB()->prepare("SELECT * FROM livechat_sessions WHERE token = ?");
    $stmt->execute([$token]);
    $row = $stmt->fetch();
    return $row ?: null;
}

function livechat_session_by_id($id)
{
    $stmt = getDB()->prepare("SELECT * FROM livechat_sessions WHERE id = ?");
    $stmt->execute([(int)$id]);
    $row = $stmt->fetch();
    return $row ?: null;
}

function livechat_add_message($sessionId, $sender, $body)
{
    $db = getDB();
    $stmt = $db->prepare("INSERT INTO livechat_messages (session_id, sender, body) VALUES (?, ?, ?)");
    $stmt->execute([(int)$sessionId, $sender, $body]);
    return (int)$db->lastInsertId();
}

/**
 * Messages d'une session depuis un id exclu. $senders est une liste fermée
 * de constantes SQL — jamais une entrée utilisateur.
 */
function livechat_messages_since($sessionId, $afterId, array $senders)
{
    $in = implode(', ', array_map(function ($s) { return "'" . $s . "'"; }, $senders));
    $stmt = getDB()->prepare(
        "SELECT id, sender, body, created_at FROM livechat_messages
          WHERE session_id = ? AND id > ? AND sender IN ($in)
          ORDER BY id ASC"
    );
    $stmt->execute([(int)$sessionId, (int)$afterId]);
    return $stmt->fetchAll();
}

function livechat_all_messages($sessionId)
{
    $stmt = getDB()->prepare(
        "SELECT id, sender, body, created_at FROM livechat_messages
          WHERE session_id = ? ORDER BY id ASC"
    );
    $stmt->execute([(int)$sessionId]);
    return $stmt->fetchAll();
}

/* ------------------------------------------------------------------ */
/* Emails (MTA cPanel, même mécanique que sendAdminReplyEmail)         */
/* ------------------------------------------------------------------ */

function livechat_mail($subject, $plainBody)
{
    $fromAddr = EMAIL_FROM_ADDRESS;
    $fromName = EMAIL_FROM_NAME;
    $replyTo  = EMAIL_REPLY_TO;
    $headers  = "From: " . mb_encode_mimeheader($fromName, 'UTF-8', 'B') . " <{$fromAddr}>\r\n";
    $headers .= "Reply-To: {$replyTo}\r\n";
    $headers .= "MIME-Version: 1.0\r\n";
    $headers .= "Content-Type: text/plain; charset=UTF-8\r\n";
    $headers .= "X-Mailer: ExpoBetonLiveChat\r\n";
    return @mail(LIVECHAT_NOTIFY_EMAIL, mb_encode_mimeheader($subject, 'UTF-8', 'B'), $plainBody, $headers, "-f{$fromAddr}");
}

function livechat_sender_label($sender)
{
    if ($sender === 'visitor') return 'Visiteur';
    if ($sender === 'operator') return 'Opérateur';
    return 'Système';
}

/** Alerte immédiate à l'ouverture d'une session live. */
function livechat_mail_alerte($session, $premierMessage, $botTranscript)
{
    $sujet = '[Live] Nouvelle conversation - ' . $session['nom'] . ' - ' . date('Y-m-d H:i');
    $lignes = [];
    $lignes[] = 'Bonjour,';
    $lignes[] = '';
    $lignes[] = 'Un visiteur a ouvert une conversation live sur le site ExpoBeton RDC.';
    $lignes[] = 'Répondez depuis https://admincb.expobetonrdc.com/livechat.php?session=' . $session['id'];
    $lignes[] = '';
    $lignes[] = '=== INFORMATIONS UTILISATEUR ===';
    $lignes[] = 'Nom: ' . $session['nom'];
    $lignes[] = 'Téléphone: ' . $session['telephone'];
    $lignes[] = 'Email: ' . ($session['email'] !== null && $session['email'] !== '' ? $session['email'] : '-');
    $lignes[] = 'Session ID: live_' . $session['id'];
    if ($botTranscript !== null && $botTranscript !== '') {
        $lignes[] = '';
        $lignes[] = '=== CONVERSATION BOT PRÉCÉDENTE (bascule) ===';
        $lignes[] = $botTranscript;
    }
    if ($premierMessage !== '') {
        $lignes[] = '';
        $lignes[] = '=== PREMIER MESSAGE ===';
        $lignes[] = $premierMessage;
    }
    $lignes[] = '';
    $lignes[] = 'Cordialement,';
    $lignes[] = 'ExpoBeton RDC — Live Chat';
    livechat_mail($sujet, implode("\r\n", $lignes) . "\r\n");
}

/** Transcript de clôture, au format des emails du chatbot. */
function livechat_mail_transcript($session)
{
    $messages = livechat_all_messages($session['id']);
    $sujet = '[Live] Conversation - ' . $session['nom'] . ' - ' . date('Y-m-d H:i');
    $lignes = [];
    $lignes[] = 'Bonjour,';
    $lignes[] = '';
    $lignes[] = 'Voici le transcript d\'une conversation live avec un opérateur ExpoBeton RDC.';
    $lignes[] = '';
    $lignes[] = '=== INFORMATIONS UTILISATEUR ===';
    $lignes[] = 'Nom: ' . $session['nom'];
    $lignes[] = 'Téléphone: ' . $session['telephone'];
    $lignes[] = 'Email: ' . ($session['email'] !== null && $session['email'] !== '' ? $session['email'] : '-');
    $lignes[] = 'Session ID: live_' . $session['id'];
    $lignes[] = '';
    $lignes[] = '=== CONVERSATION ===';
    foreach ($messages as $m) {
        $h = date('H:i:s', strtotime($m['created_at']));
        $lignes[] = '[' . $h . '] ' . livechat_sender_label($m['sender']) . ': ' . $m['body'];
        $lignes[] = '';
    }
    $lignes[] = '=== FIN DE CONVERSATION ===';
    $lignes[] = '';
    $lignes[] = 'Date: ' . date('Y-m-d H:i:s');
    $lignes[] = 'Nombre de messages: ' . count($messages);
    $lignes[] = '';
    $lignes[] = 'Cordialement,';
    $lignes[] = 'ExpoBeton RDC — Live Chat';
    livechat_mail($sujet, implode("\r\n", $lignes) . "\r\n");
}

/** Clôture + transcript ; sans effet si déjà close. */
function livechat_close_session($sessionId)
{
    $db = getDB();
    $stmt = $db->prepare("UPDATE livechat_sessions SET statut = 'closed', closed_at = NOW() WHERE id = ? AND statut = 'open'");
    $stmt->execute([(int)$sessionId]);
    if ($stmt->rowCount() < 1) {
        return false;
    }
    $session = livechat_session_by_id($sessionId);
    if ($session) {
        livechat_mail_transcript($session);
    }
    return true;
}

/* ------------------------------------------------------------------ */
/* Dispatch (uniquement en appel direct)                               */
/* ------------------------------------------------------------------ */

if (basename($_SERVER['SCRIPT_FILENAME']) !== 'api_livechat.php') {
    return; /* inclus par livechat.php : fonctions seulement */
}

livechat_ensure_tables();
$input = livechat_input();
$action = isset($_GET['action']) ? $_GET['action'] : (isset($input['action']) ? $input['action'] : '');

switch ($action) {

    case 'start':
        $nom = livechat_str(isset($input['nom']) ? $input['nom'] : '', 128);
        $tel = livechat_str(isset($input['telephone']) ? $input['telephone'] : '', 32);
        if ($nom === '' || $tel === '') {
            livechat_out(['ok' => false, 'error' => 'nom et telephone requis'], 400);
        }
        $email = livechat_str(isset($input['email']) ? $input['email'] : '', 191);
        $message = livechat_str(isset($input['message']) ? $input['message'] : '', 2000);
        $botTranscript = null;
        if (isset($input['bot_transcript']) && is_array($input['bot_transcript'])) {
            $lignes = [];
            foreach ($input['bot_transcript'] as $m) {
                if (!is_array($m) || !isset($m['text'])) continue;
                $qui = (isset($m['sender']) && $m['sender'] === 'bot') ? 'Bot' : 'Utilisateur';
                $lignes[] = $qui . ': ' . mb_substr((string)$m['text'], 0, 500);
            }
            if ($lignes) $botTranscript = implode("\n", $lignes);
        }
        $token = bin2hex(random_bytes(32));
        $db = getDB();
        $stmt = $db->prepare(
            "INSERT INTO livechat_sessions (token, nom, telephone, email, bot_transcript)
             VALUES (?, ?, ?, ?, ?)"
        );
        $stmt->execute([$token, $nom, $tel, $email !== '' ? $email : null, $botTranscript]);
        $sessionId = (int)$db->lastInsertId();
        if ($message !== '') {
            livechat_add_message($sessionId, 'visitor', $message);
        }
        livechat_add_message($sessionId, 'system', 'Conversation live ouverte');
        $session = livechat_session_by_id($sessionId);
        livechat_mail_alerte($session, $message, $botTranscript);
        $msgs = livechat_all_messages($sessionId);
        $lastId = count($msgs) ? (int)$msgs[count($msgs) - 1]['id'] : 0;
        livechat_out(['ok' => true, 'token' => $token, 'session_id' => $sessionId, 'last_id' => $lastId]);
        break;

    case 'send':
        $token = livechat_str(isset($input['token']) ? $input['token'] : '', 64);
        $message = livechat_str(isset($input['message']) ? $input['message'] : '', 2000);
        $session = livechat_session_by_token($token);
        if (!$session || $session['statut'] !== 'open' || $message === '') {
            livechat_out(['ok' => false, 'error' => 'session introuvable ou close'], 404);
        }
        $id = livechat_add_message($session['id'], 'visitor', $message);
        livechat_out(['ok' => true, 'id' => $id]);
        break;

    case 'poll':
        $token = livechat_str(isset($_GET['token']) ? $_GET['token'] : (isset($input['token']) ? $input['token'] : ''), 64);
        $after = (int)(isset($_GET['after']) ? $_GET['after'] : (isset($input['after']) ? $input['after'] : 0));
        $session = livechat_session_by_token($token);
        if (!$session) {
            livechat_out(['ok' => false, 'error' => 'session introuvable'], 404);
        }
        livechat_out([
            'ok' => true,
            'statut' => $session['statut'],
            'messages' => livechat_messages_since($session['id'], $after, ['operator', 'system']),
        ]);
        break;

    case 'close':
        $token = livechat_str(isset($input['token']) ? $input['token'] : '', 64);
        $session = livechat_session_by_token($token);
        if (!$session) {
            livechat_out(['ok' => false, 'error' => 'session introuvable'], 404);
        }
        livechat_close_session($session['id']);
        livechat_out(['ok' => true]);
        break;

    case 'operator_send':
        if (!isLoggedIn()) livechat_out(['ok' => false, 'error' => 'non connecté'], 401);
        if (!canEditData()) livechat_out(['ok' => false, 'error' => 'droits insuffisants'], 403);
        $sessionId = (int)(isset($input['session_id']) ? $input['session_id'] : 0);
        $message = livechat_str(isset($input['message']) ? $input['message'] : '', 2000);
        $session = livechat_session_by_id($sessionId);
        if (!$session || $session['statut'] !== 'open' || $message === '') {
            livechat_out(['ok' => false, 'error' => 'session introuvable ou close'], 404);
        }
        $id = livechat_add_message($sessionId, 'operator', $message);
        $db = getDB();
        $db->prepare("UPDATE livechat_sessions SET operator_id = COALESCE(operator_id, ?) WHERE id = ?")
           ->execute([(int)$_SESSION['admin_id'], $sessionId]);
        livechat_out(['ok' => true, 'id' => $id]);
        break;

    case 'operator_poll':
        if (!isLoggedIn()) livechat_out(['ok' => false, 'error' => 'non connecté'], 401);
        $sessionId = (int)(isset($_GET['session_id']) ? $_GET['session_id'] : 0);
        $after = (int)(isset($_GET['after']) ? $_GET['after'] : 0);
        $session = livechat_session_by_id($sessionId);
        if (!$session) {
            livechat_out(['ok' => false, 'error' => 'session introuvable'], 404);
        }
        livechat_out([
            'ok' => true,
            'statut' => $session['statut'],
            'messages' => livechat_messages_since($sessionId, $after, ['visitor', 'operator', 'system']),
        ]);
        break;

    case 'operator_close':
        if (!isLoggedIn()) livechat_out(['ok' => false, 'error' => 'non connecté'], 401);
        if (!canEditData()) livechat_out(['ok' => false, 'error' => 'droits insuffisants'], 403);
        $sessionId = (int)(isset($input['session_id']) ? $input['session_id'] : 0);
        if (!livechat_close_session($sessionId)) {
            livechat_out(['ok' => false, 'error' => 'session déjà close ou introuvable'], 404);
        }
        livechat_out(['ok' => true]);
        break;

    default:
        livechat_out(['ok' => false, 'error' => 'action inconnue'], 400);
}
