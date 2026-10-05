<?php
/**
 * ExpoBeton RDC — Transcript e-mail des conversations BOT (mode chatbot).
 *
 * Déployé sur /public_html/chat/conversation_email.php. Appelé par le widget
 * (same-origin) en fin de conversation bot. Deux rôles :
 *
 * 1. Envoyer le transcript par mail() (MTA cPanel, mécanisme éprouvé) au
 *    format standard CORRECTION_EMAILS.md, sujet « [Bot] Conversation - … » ;
 *    le SMTP de Railway est injoignable (Errno 101), d'où ce relais local.
 * 2. Transférer côté serveur un « session_end » vers l'API analytics admincb
 *    (api_key dans le body) pour que la session apparaisse clôturée dans
 *    conversations.php sans dépendre de Railway.
 *
 * POST JSON attendu : { session_id, user_info: {name, phone, email, …},
 *                       messages: [{text, sender, timestamp}, …] }
 *
 * Compatibilité : PHP 7.0+.
 */

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

// Constantes alignées sur chatbot-admin/config.php (docroot distincte : on ne
// peut pas inclure le fichier, les valeurs sont recopiées volontairement).
define('CONV_NOTIFY_EMAIL', 'bot@expobetonrdc.com');
define('CONV_FROM_ADDRESS', 'info@expobetonrdc.com');
define('CONV_FROM_NAME', 'ExpoBeton RDC');
define('CONV_REPLY_TO', 'info@expobetonrdc.com');
define('CONV_ANALYTICS_URL', 'https://admincb.expobetonrdc.com/api_chatbot_analytics.php');
define('CONV_API_KEY', 'ebx-rasa-2026-kAlEmIe-be96bac9f905b106ed2b941dfe536b07');
define('CONV_MAX_BODY', 262144); // 256 Ko

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    header('Allow: POST');
    echo json_encode(['error' => 'Méthode non autorisée (POST requis).']);
    exit;
}

$raw = file_get_contents('php://input');
if ($raw === false || strlen($raw) > CONV_MAX_BODY) {
    http_response_code(413);
    echo json_encode(['error' => 'Corps de requête absent ou trop volumineux.']);
    exit;
}

$input = json_decode($raw, true);
if (!is_array($input)) {
    http_response_code(400);
    echo json_encode(['error' => 'JSON invalide.']);
    exit;
}

$sessionId = isset($input['session_id']) && is_string($input['session_id'])
    ? substr(trim($input['session_id']), 0, 128) : '';
$userInfo  = isset($input['user_info']) && is_array($input['user_info']) ? $input['user_info'] : [];
$messages  = isset($input['messages']) && is_array($input['messages']) ? $input['messages'] : [];

if ($sessionId === '' || count($messages) === 0) {
    http_response_code(400);
    echo json_encode(['error' => 'session_id et messages requis.']);
    exit;
}

function conv_str($value)
{
    if (is_array($value) || is_object($value)) {
        return '';
    }
    return trim((string)$value);
}

function conv_sender_label($sender)
{
    switch ($sender) {
        case 'user':     return 'Utilisateur';
        case 'bot':      return 'Chatbot';
        case 'operator': return 'Conseiller';
        case 'system':   return 'Système';
        default:         return 'Inconnu';
    }
}

// ------------------------------------------------------------
// 1. E-mail transcript (format CORRECTION_EMAILS.md)
// ------------------------------------------------------------

$nom       = conv_str(isset($userInfo['name']) ? $userInfo['name'] : '');
$telephone = conv_str(isset($userInfo['phone']) ? $userInfo['phone'] : '');
$email     = conv_str(isset($userInfo['email']) ? $userInfo['email'] : '');

$sujet = '[Bot] Conversation - ' . ($nom !== '' ? $nom : 'Visiteur') . ' - ' . date('Y-m-d H:i');

$lignes   = [];
$lignes[] = 'Bonjour,';
$lignes[] = '';
$lignes[] = 'Voici le transcript d\'une conversation du chatbot ExpoBeton RDC.';
$lignes[] = '';
$lignes[] = '=== INFORMATIONS UTILISATEUR ===';
$lignes[] = 'Nom: ' . ($nom !== '' ? $nom : '-');
$lignes[] = 'Téléphone: ' . ($telephone !== '' ? $telephone : '-');
$lignes[] = 'Email: ' . ($email !== '' ? $email : '-');
$lignes[] = 'Session ID: ' . $sessionId;
$lignes[] = '';
$lignes[] = '=== CONVERSATION ===';
foreach ($messages as $m) {
    if (!is_array($m)) {
        continue;
    }
    $texte = conv_str(isset($m['text']) ? $m['text'] : '');
    if ($texte === '') {
        continue;
    }
    $ts = isset($m['timestamp']) ? strtotime(conv_str($m['timestamp'])) : false;
    $h  = $ts ? date('H:i:s', $ts) : date('H:i:s');
    $lignes[] = '[' . $h . '] ' . conv_sender_label(isset($m['sender']) ? $m['sender'] : '') . ': ' . $texte;
    $lignes[] = '';
}
$lignes[] = '=== FIN DE CONVERSATION ===';
$lignes[] = '';
$lignes[] = 'Date: ' . date('Y-m-d H:i:s');
$lignes[] = 'Nombre de messages: ' . count($messages);
$lignes[] = '';
$lignes[] = 'Cordialement,';
$lignes[] = 'ExpoBeton RDC — Chatbot';

$enTetes  = 'From: ' . CONV_FROM_NAME . ' <' . CONV_FROM_ADDRESS . ">\r\n";
$enTetes .= 'Reply-To: ' . CONV_REPLY_TO . "\r\n";
$enTetes .= "MIME-Version: 1.0\r\n";
$enTetes .= "Content-Type: text/plain; charset=UTF-8\r\n";
$enTetes .= "Content-Transfer-Encoding: 8bit\r\n";

$sujetEncode = mb_encode_mimeheader($sujet, 'UTF-8');
$mailOk = @mail(
    CONV_NOTIFY_EMAIL,
    $sujetEncode,
    implode("\r\n", $lignes) . "\r\n",
    $enTetes,
    '-f' . CONV_FROM_ADDRESS
);

// ------------------------------------------------------------
// 2. session_end vers l'API analytics admincb (server-to-server)
// ------------------------------------------------------------

$analyticsOk = false;
$payload = json_encode([
    'api_key'    => CONV_API_KEY,
    'session_id' => $sessionId,
]);
$ch = curl_init(CONV_ANALYTICS_URL . '?action=session_end');
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => $payload,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
    CURLOPT_TIMEOUT        => 15,
    CURLOPT_CONNECTTIMEOUT => 5,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_SSL_VERIFYHOST => 2,
]);
$resp     = curl_exec($ch);
$httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
if ($resp !== false && $httpCode >= 200 && $httpCode < 300) {
    $decoded = json_decode($resp, true);
    $analyticsOk = is_array($decoded) && !empty($decoded['success']);
}
if (!$analyticsOk) {
    error_log('[conversation_email] session_end analytics échoué http=' . $httpCode . ' session=' . $sessionId);
}

echo json_encode([
    'ok'        => true,
    'mail'      => (bool)$mailOk,
    'analytics' => $analyticsOk,
]);
