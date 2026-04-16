<?php
/**
 * Authentication helpers for the dashboard
 */

require_once __DIR__ . '/config.php';

session_start();

function getDB() {
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO(
            'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
            DB_USER,
            DB_PASS,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
        );
    }
    return $pdo;
}

function isLoggedIn() {
    return isset($_SESSION['admin_id']) && isset($_SESSION['admin_user']);
}

function requireLogin() {
    if (!isLoggedIn()) {
        header('Location: login.php');
        exit;
    }
    // Check session timeout
    if (isset($_SESSION['last_activity']) && (time() - $_SESSION['last_activity']) > SESSION_TIMEOUT) {
        session_destroy();
        header('Location: login.php?timeout=1');
        exit;
    }
    $_SESSION['last_activity'] = time();
}

function loginUser($username, $password) {
    $db = getDB();
    $stmt = $db->prepare("SELECT id, username, password_hash FROM admin_users WHERE username = ?");
    $stmt->execute([$username]);
    $user = $stmt->fetch();
    
    if ($user && password_verify($password, $user['password_hash'])) {
        $_SESSION['admin_id'] = $user['id'];
        $_SESSION['admin_user'] = $user['username'];
        $_SESSION['last_activity'] = time();
        return true;
    }
    return false;
}

function hasAdminUsers() {
    $db = getDB();
    $count = $db->query("SELECT COUNT(*) FROM admin_users")->fetchColumn();
    return $count > 0;
}

function formatDuration($seconds) {
    if ($seconds === null) return '-';
    if ($seconds < 60) return $seconds . 's';
    if ($seconds < 3600) return floor($seconds / 60) . 'm ' . ($seconds % 60) . 's';
    return floor($seconds / 3600) . 'h ' . floor(($seconds % 3600) / 60) . 'm';
}

function escape($str) {
    return htmlspecialchars($str ?? '', ENT_QUOTES, 'UTF-8');
}
