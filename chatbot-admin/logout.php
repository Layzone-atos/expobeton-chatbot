<?php
require_once __DIR__ . '/auth.php';

/* Efface la présence immédiatement : sans cela, la déconnexion ne prendrait
   effet qu'après la fenêtre de 120 s et le widget resterait en mode « live »
   devant un dashboard vide. */
if (isLoggedIn()) {
    try {
        $upd = getDB()->prepare("UPDATE admin_users SET last_presence_at = NULL WHERE id = ?");
        $upd->execute([(int)$_SESSION['admin_id']]);
    } catch (Exception $e) { /* ne bloque jamais la déconnexion */ }
}

session_destroy();
header('Location: login.php');
exit;
