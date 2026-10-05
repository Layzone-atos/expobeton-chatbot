<?php
/**
 * ExpoBeton RDC — Proxy local vers le webhook Rasa (Railway).
 *
 * Déployé sur /public_html/chat/rasa_proxy.php du site principal, il permet au
 * widget (servi en same-origin via l'iframe /chat/chatbot-embed-left.html)
 * d'interroger le bot sans exposer l'URL Railway et sans CORS.
 *
 * - POST uniquement, body JSON ≤ 64 Ko ;
 * - renvoie tel quel le JSON du webhook Rasa ;
 * - aucune authentification : le webhook Rasa est déjà public et cet endpoint
 *   ne fait que relayer un message visiteur.
 *
 * Compatibilité : PHP 7.0+.
 */

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

define('RASA_UPSTREAM', 'https://web-production-9f398e.up.railway.app/webhooks/rest/webhook');
define('RASA_MAX_BODY', 65536); // 64 Ko

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    header('Allow: POST');
    echo json_encode(['error' => 'Méthode non autorisée (POST requis).']);
    exit;
}

$raw = file_get_contents('php://input');
if ($raw === false || strlen($raw) > RASA_MAX_BODY) {
    http_response_code(413);
    echo json_encode(['error' => 'Corps de requête absent ou trop volumineux.']);
    exit;
}

$payload = json_decode($raw, true);
if (!is_array($payload)) {
    http_response_code(400);
    echo json_encode(['error' => 'JSON invalide.']);
    exit;
}

$ch = curl_init(RASA_UPSTREAM);
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => $raw,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
    CURLOPT_TIMEOUT        => 30,
    CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_SSL_VERIFYHOST => 2,
]);
$response = curl_exec($ch);
$httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlErr  = curl_error($ch);
curl_close($ch);

if ($response === false || $httpCode < 200 || $httpCode >= 300) {
    error_log('[rasa_proxy] upstream failure http=' . $httpCode . ' err=' . $curlErr);
    http_response_code(502);
    echo json_encode(['error' => 'Service du chatbot momentanément indisponible.']);
    exit;
}

echo $response;
