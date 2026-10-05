<?php
/**
 * Heartbeat de présence opérateur (appelé toutes les 45 s par le dashboard).
 * Rafraîchit last_presence_at ; l'endpoint public api_live_status.php en
 * déduit le mode du widget public (live humain ou chatbot).
 */
header('Content-Type: application/json');
require_once __DIR__ . '/auth.php';

if (!isLoggedIn()) {
    http_response_code(401);
    echo json_encode(['ok' => false, 'error' => 'not logged in']);
    exit;
}

try {
    $stmt = getDB()->prepare("UPDATE admin_users SET last_presence_at = NOW() WHERE id = ?");
    $stmt->execute([(int)$_SESSION['admin_id']]);
    echo json_encode(['ok' => true]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'db']);
}
