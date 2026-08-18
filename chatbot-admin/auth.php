<?php
/**
 * Authentication helpers for the dashboard (with RBAC).
 *
 * Roles:
 *   - super_admin : full control, incl. managing admin accounts
 *   - admin       : can view all data + reply email + mark resolved
 *   - viewer      : read-only (no email reply, no mark resolved)
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

/**
 * Apply RBAC migrations once per process. Each ALTER is wrapped in a
 * try/catch so re-runs are safe no-ops if the column already exists.
 */
function ensureRbacMigrations() {
    static $done = false;
    if ($done) return;
    $done = true;

    $db = getDB();
    $alters = [
        "ALTER TABLE admin_users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'admin'",
        "ALTER TABLE admin_users ADD COLUMN full_name VARCHAR(128) NULL",
        "ALTER TABLE admin_users ADD COLUMN email VARCHAR(191) NULL",
        "ALTER TABLE admin_users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1",
        "ALTER TABLE admin_users ADD COLUMN last_login_at DATETIME NULL",
        "ALTER TABLE admin_users ADD COLUMN created_by INT NULL",
    ];
    foreach ($alters as $sql) {
        try { $db->exec($sql); } catch (Exception $e) { /* column already exists */ }
    }

    // Auto-promote the oldest admin to super_admin if nobody has that role yet.
    try {
        $hasSuper = (int)$db->query("SELECT COUNT(*) FROM admin_users WHERE role = 'super_admin'")->fetchColumn();
        if ($hasSuper === 0) {
            $db->exec("UPDATE admin_users SET role = 'super_admin' WHERE id = (SELECT * FROM (SELECT MIN(id) FROM admin_users) AS t)");
        }
    } catch (Exception $e) { /* ignore */ }
}

function isLoggedIn() {
    return isset($_SESSION['admin_id']) && isset($_SESSION['admin_user']);
}

function requireLogin() {
    ensureRbacMigrations();

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

    // Re-fetch role and active status from DB at each request so revocations
    // take effect immediately (defend against stale session data).
    try {
        $db = getDB();
        $stmt = $db->prepare("SELECT role, is_active FROM admin_users WHERE id = ?");
        $stmt->execute([(int)$_SESSION['admin_id']]);
        $row = $stmt->fetch();
        if (!$row || (int)$row['is_active'] !== 1) {
            session_destroy();
            header('Location: login.php?disabled=1');
            exit;
        }
        $_SESSION['admin_role'] = $row['role'];
    } catch (Exception $e) {
        // On DB error, fall back to whatever is in the session; do not lock out.
    }
}

function currentRole() {
    return isset($_SESSION['admin_role']) ? $_SESSION['admin_role'] : 'viewer';
}

function isSuperAdmin() { return currentRole() === 'super_admin'; }
function isAdmin()      { return currentRole() === 'admin'; }
function isViewer()     { return currentRole() === 'viewer'; }

function canManageAdmins() { return isSuperAdmin(); }
function canEditData()     { return isSuperAdmin() || isAdmin(); }
function canView()         { return isSuperAdmin() || isAdmin() || isViewer(); }

/**
 * Hard-gate a page to a set of roles. Redirects with ?denied=1 when refused.
 */
function requireRole(array $allowed) {
    if (!in_array(currentRole(), $allowed, true)) {
        header('Location: dashboard.php?denied=1');
        exit;
    }
}

function loginUser($username, $password) {
    ensureRbacMigrations();
    $db = getDB();
    $stmt = $db->prepare("SELECT id, username, password_hash, role, is_active FROM admin_users WHERE username = ?");
    $stmt->execute([$username]);
    $user = $stmt->fetch();

    if (!$user || !password_verify($password, $user['password_hash'])) {
        return false;
    }
    if ((int)$user['is_active'] !== 1) {
        return 'disabled';
    }

    $_SESSION['admin_id']   = $user['id'];
    $_SESSION['admin_user'] = $user['username'];
    $_SESSION['admin_role'] = $user['role'];
    $_SESSION['last_activity'] = time();

    try {
        $upd = $db->prepare("UPDATE admin_users SET last_login_at = NOW() WHERE id = ?");
        $upd->execute([(int)$user['id']]);
    } catch (Exception $e) { /* ignore */ }

    return true;
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
    return htmlspecialchars($str === null ? '' : $str, ENT_QUOTES, 'UTF-8');
}

/**
 * Render the shared role-aware top navigation bar. $active is the base filename
 * of the current page (e.g. 'dashboard', 'conversations', 'users', ...).
 */
function renderNavbar($active = '') {
    $activeCls = function($name) use ($active) {
        return $name === $active ? ' active' : '';
    };
    $superAdmin = isSuperAdmin();
    ?>
    <nav class="navbar navbar-expand-lg navbar-dark" style="background: #0A2A66;">
        <div class="container-fluid">
            <a class="navbar-brand fw-bold" href="dashboard.php">ExpoBeton Analytics</a>
            <div class="navbar-nav ms-auto d-flex flex-row gap-2 flex-wrap">
                <a class="nav-link<?= $activeCls('dashboard') ?>" href="dashboard.php"><i class="bi bi-speedometer2"></i> Dashboard</a>
                <a class="nav-link<?= $activeCls('conversations') ?>" href="conversations.php"><i class="bi bi-chat-dots"></i> Conversations</a>
                <a class="nav-link<?= $activeCls('analytics') ?>" href="analytics.php"><i class="bi bi-bar-chart"></i> Analytics</a>
                <a class="nav-link<?= $activeCls('users') ?>" href="users.php"><i class="bi bi-people"></i> Visitors</a>
                <a class="nav-link<?= $activeCls('registrations') ?>" href="registrations.php"><i class="bi bi-person-vcard"></i> Registrations</a>
                <?php if ($superAdmin): ?>
                <a class="nav-link<?= $activeCls('admin_accounts') ?>" href="admin_accounts.php"><i class="bi bi-shield-lock"></i> Admin Accounts</a>
                <?php endif; ?>
                <span class="nav-link text-white-50 small">
                    <i class="bi bi-person-circle"></i>
                    <?= escape($_SESSION['admin_user'] ?? '') ?>
                    <span class="badge role-badge role-<?= escape(currentRole()) ?> ms-1"><?= escape(currentRole()) ?></span>
                </span>
                <a class="nav-link text-warning<?= $activeCls('logout') ?>" href="logout.php"><i class="bi bi-box-arrow-right"></i> Logout</a>
            </div>
        </div>
    </nav>
    <?php
}
