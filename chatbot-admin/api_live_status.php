<?php
/**
 * Endpoint PUBLIC de présence : dit au widget de chat du site si un opérateur
 * humain est actuellement connecté au dashboard.
 *
 * Aucune donnée sensible (un mode et un compteur), d'où le CORS ouvert.
 * Réponse : {"mode":"live"|"bot","operators":N}
 *
 * La fenêtre de présence (120 s) est volontairement plus large que la période
 * du heartbeat (45 s) : un onglet admin qui rafale reste « présent » malgré
 * une micro-coupure réseau, et disparaît vite après fermeture du navigateur.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

/* auth.php apporte config, getDB() et les migrations (last_presence_at). */
require_once __DIR__ . '/auth.php';
ensureRbacMigrations();

$operators = 0;
try {
    $operators = (int)getDB()->query(
        "SELECT COUNT(*) FROM admin_users
          WHERE is_active = 1
            AND last_presence_at > NOW() - INTERVAL 120 SECOND"
    )->fetchColumn();
} catch (Exception $e) {
    /* Présence indétectable (colonne absente, DB hors ligne…) : mode bot,
       le repli sûr — le widget continuera de servir via le chatbot. */
    $operators = 0;
}

echo json_encode([
    'mode'      => $operators > 0 ? 'live' : 'bot',
    'operators' => $operators,
]);
