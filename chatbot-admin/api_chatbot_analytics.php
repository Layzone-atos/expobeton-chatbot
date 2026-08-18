<?php
/**
 * ExpoBeton RDC - Chatbot Analytics API
 * 
 * Receives tracking data from the Rasa chatbot on Railway.
 * Auto-creates database tables on first run.
 * 
 * Endpoints:
 *   GET  ?action=health         - Health check
 *   POST ?action=session_start  - Create new session
 *   POST ?action=log_message    - Log a message
 *   POST ?action=session_end    - End a session
 *   POST ?action=registration   - Track a registration
 *   POST ?action=update_session - Update session info (email, name)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Load config
require_once __DIR__ . '/config.php';

// ============================================================
// DATABASE CONNECTION
// ============================================================
function getDB() {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $pdo = new PDO(
                'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
                DB_USER,
                DB_PASS,
                [
                    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
                ]
            );
        } catch (PDOException $e) {
            http_response_code(500);
            echo json_encode(['error' => 'Database connection failed', 'detail' => $e->getMessage()]);
            exit;
        }
    }
    return $pdo;
}

// ============================================================
// AUTO-MIGRATION: Create tables if they don't exist
// ============================================================
function ensureTables() {
    $db = getDB();
    
    $db->exec("CREATE TABLE IF NOT EXISTS sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(255) UNIQUE NOT NULL,
        started_at DATETIME NOT NULL,
        ended_at DATETIME NULL,
        duration_seconds INT NULL,
        user_email VARCHAR(255) NULL,
        user_name VARCHAR(255) NULL,
        ip_address VARCHAR(45) NULL,
        country VARCHAR(100) NULL,
        city VARCHAR(100) NULL,
        device_type VARCHAR(50) NULL,
        browser VARCHAR(100) NULL,
        os VARCHAR(100) NULL,
        screen_width INT NULL,
        screen_height INT NULL,
        language VARCHAR(10) NULL,
        referrer_url TEXT NULL,
        user_agent TEXT NULL,
        message_count INT DEFAULT 0,
        INDEX idx_started (started_at),
        INDEX idx_email (user_email)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    
    $db->exec("CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(255) NOT NULL,
        sender ENUM('user','bot') NOT NULL,
        message_text TEXT,
        intent VARCHAR(100) NULL,
        confidence FLOAT NULL,
        timestamp DATETIME NOT NULL,
        INDEX idx_session (session_id),
        INDEX idx_timestamp (timestamp)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    
    $db->exec("CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255) NULL,
        first_seen DATETIME NOT NULL,
        last_seen DATETIME NOT NULL,
        session_count INT DEFAULT 1,
        country VARCHAR(100) NULL,
        city VARCHAR(100) NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    
    $db->exec("CREATE TABLE IF NOT EXISTS admin_users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    
    $db->exec("CREATE TABLE IF NOT EXISTS registrations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(255) NULL,
        reference_number VARCHAR(50) NULL,
        category VARCHAR(100) NULL,
        company VARCHAR(255) NULL,
        contact_name VARCHAR(255) NULL,
        email VARCHAR(255) NULL,
        phone VARCHAR(50) NULL,
        country VARCHAR(100) NULL,
        registered_at DATETIME NOT NULL,
        INDEX idx_session (session_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    
    $db->exec("CREATE TABLE IF NOT EXISTS daily_stats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date DATE UNIQUE NOT NULL,
        total_sessions INT DEFAULT 0,
        unique_users INT DEFAULT 0,
        total_messages INT DEFAULT 0,
        avg_duration_seconds INT DEFAULT 0,
        mobile_count INT DEFAULT 0,
        desktop_count INT DEFAULT 0,
        tablet_count INT DEFAULT 0,
        INDEX idx_date (date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    // Admin replies to offline users (for unresolved conversations)
    $db->exec("CREATE TABLE IF NOT EXISTS admin_replies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(255) NOT NULL,
        admin_username VARCHAR(50) NULL,
        recipient_email VARCHAR(255) NOT NULL,
        recipient_name VARCHAR(255) NULL,
        subject VARCHAR(255) NOT NULL,
        message_text MEDIUMTEXT NOT NULL,
        sent_at DATETIME NOT NULL,
        email_status VARCHAR(32) DEFAULT 'sent',
        error_message TEXT NULL,
        INDEX idx_session (session_id),
        INDEX idx_sent (sent_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    // Additive columns for resolution tracking (ignore errors if column exists)
    try { $db->exec("ALTER TABLE sessions ADD COLUMN is_unresolved TINYINT(1) NOT NULL DEFAULT 0"); } catch (Exception $e) {}
    try { $db->exec("ALTER TABLE sessions ADD COLUMN resolved_at DATETIME NULL"); } catch (Exception $e) {}
    try { $db->exec("ALTER TABLE sessions ADD COLUMN resolved_by VARCHAR(64) NULL"); } catch (Exception $e) {}
    try { $db->exec("ALTER TABLE sessions ADD INDEX idx_unresolved (is_unresolved)"); } catch (Exception $e) {}
}

// ============================================================
// AUTHENTICATION
// ============================================================
function authenticate() {
    $token = null;
    
    // Check Authorization header (multiple methods for cPanel/Apache compatibility)
    // Method 1: getallheaders()
    if (function_exists('getallheaders')) {
        $headers = getallheaders();
        foreach ($headers as $key => $value) {
            if (strtolower($key) === 'authorization') {
                if (preg_match('/Bearer\s+(.+)/i', $value, $matches)) {
                    $token = $matches[1];
                }
            }
        }
    }
    
    // Method 2: Apache CGI/FastCGI workarounds
    if (!$token && isset($_SERVER['REDIRECT_HTTP_AUTHORIZATION'])) {
        if (preg_match('/Bearer\s+(.+)/i', $_SERVER['REDIRECT_HTTP_AUTHORIZATION'], $matches)) {
            $token = $matches[1];
        }
    }
    if (!$token && isset($_SERVER['HTTP_AUTHORIZATION'])) {
        if (preg_match('/Bearer\s+(.+)/i', $_SERVER['HTTP_AUTHORIZATION'], $matches)) {
            $token = $matches[1];
        }
    }
    
    // Method 3: Fallback - query parameter
    if (!$token && isset($_GET['api_key'])) {
        $token = $_GET['api_key'];
    }
    
    // Method 4: Fallback - POST body
    if (!$token) {
        $input = json_decode(file_get_contents('php://input'), true);
        if (isset($input['api_key'])) {
            $token = $input['api_key'];
        }
    }
    
    if (!$token || $token !== API_KEY) {
        http_response_code(401);
        echo json_encode(['error' => 'Unauthorized', 'message' => 'Invalid or missing API key']);
        exit;
    }
}

// ============================================================
// IP GEOLOCATION (free ip-api.com, 45 req/min)
// ============================================================

// Get real client IP from request headers (handles proxies/load balancers)
function getRealClientIP() {
    $headers = ['HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'HTTP_X_CLIENT_IP', 'REMOTE_ADDR'];
    foreach ($headers as $header) {
        if (!empty($_SERVER[$header])) {
            // X-Forwarded-For may contain multiple IPs, take the first
            $ip = trim(explode(',', $_SERVER[$header])[0]);
            if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
                return $ip;
            }
        }
    }
    return $_SERVER['REMOTE_ADDR'] ?? null;
}

function geolocateIP($ip) {
    // If no IP provided, try to detect from request headers
    if (!$ip) {
        $ip = getRealClientIP();
    }
    if (!$ip || $ip === '127.0.0.1' || $ip === '::1') {
        return ['country' => 'Unknown', 'city' => 'Unknown'];
    }
    
    try {
        $ctx = stream_context_create(['http' => ['timeout' => 3]]);
        $response = @file_get_contents("http://ip-api.com/json/{$ip}?fields=status,country,city", false, $ctx);
        if ($response) {
            $data = json_decode($response, true);
            if ($data && $data['status'] === 'success') {
                return [
                    'country' => $data['country'] ?? 'Unknown',
                    'city' => $data['city'] ?? 'Unknown'
                ];
            }
        }
    } catch (Exception $e) {
        // Ignore geolocation errors
    }
    return ['country' => 'Unknown', 'city' => 'Unknown'];
}

// ============================================================
// HANDLERS
// ============================================================

function handleHealth() {
    $db = getDB();
    // Auto-close stale sessions on health check (poor man's cron)
    autoCloseStaleSessions($db);
    echo json_encode([
        'success' => true,
        'service' => 'chatbot-analytics',
        'db_connected' => true,
        'timestamp' => date('Y-m-d H:i:s')
    ]);
}

/**
 * Auto-close sessions that have been inactive for >30 min without explicit end.
 * Handles cases where the user closes the tab without triggering pagehide/beforeunload.
 */
function autoCloseStaleSessions($db) {
    try {
        $db->exec("
            UPDATE sessions s
            SET 
                s.ended_at = COALESCE(
                    (SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.session_id),
                    s.started_at
                ),
                s.duration_seconds = TIMESTAMPDIFF(SECOND, s.started_at, COALESCE(
                    (SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.session_id),
                    s.started_at
                ))
            WHERE s.ended_at IS NULL 
              AND s.started_at < DATE_SUB(NOW(), INTERVAL 30 MINUTE)
        ");
        // Flag stale sessions that were just auto-closed as potentially unresolved
        $stale = $db->query("SELECT session_id FROM sessions 
                             WHERE is_unresolved = 0 AND resolved_at IS NULL 
                               AND ended_at IS NOT NULL
                               AND ended_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)")->fetchAll(PDO::FETCH_COLUMN);
        foreach ($stale as $sid) {
            flagUnresolvedIfNeeded($db, $sid);
        }
    } catch (Exception $e) {
        // Silently ignore - best-effort cleanup
    }
}

/**
 * Flag a session as unresolved when:
 *  - any of the last 3 bot messages contains a known "can't answer" pattern, OR
 *  - the user's last message got no bot reply before the session ended.
 */
function flagUnresolvedIfNeeded($db, $sessionId) {
    try {
        // Skip if already resolved or already flagged
        $cur = $db->prepare("SELECT is_unresolved, resolved_at FROM sessions WHERE session_id = ?");
        $cur->execute([$sessionId]);
        $row = $cur->fetch();
        if (!$row || $row['resolved_at']) return;
        if ((int)$row['is_unresolved'] === 1) return;

        $unresolved = false;

        // Check last 3 bot messages for fallback patterns
        $stmt = $db->prepare("SELECT message_text FROM messages 
                              WHERE session_id = ? AND sender = 'bot' 
                              ORDER BY timestamp DESC LIMIT 3");
        $stmt->execute([$sessionId]);
        $botMsgs = $stmt->fetchAll(PDO::FETCH_COLUMN);
        $patterns = $GLOBALS['UNRESOLVED_BOT_PATTERNS'] ?? [];
        foreach ($botMsgs as $text) {
            foreach ($patterns as $p) {
                if ($p && stripos($text, $p) !== false) { $unresolved = true; break 2; }
            }
        }

        // Check if user's last message got no bot reply
        if (!$unresolved) {
            $last = $db->prepare("SELECT sender FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1");
            $last->execute([$sessionId]);
            if ($last->fetchColumn() === 'user') $unresolved = true;
        }

        if ($unresolved) {
            $db->prepare("UPDATE sessions SET is_unresolved = 1 WHERE session_id = ?")->execute([$sessionId]);
        }
    } catch (Exception $e) { /* ignore */ }
}

function handleSessionStart($data) {
    $db = getDB();
    
    $sessionId = $data['session_id'] ?? null;
    if (!$sessionId) {
        http_response_code(400);
        echo json_encode(['error' => 'session_id required']);
        return;
    }
    
    // Check if session already exists
    $stmt = $db->prepare("SELECT id FROM sessions WHERE session_id = ?");
    $stmt->execute([$sessionId]);
    $existsRow = $stmt->fetch();
    if ($existsRow) {
        // Session row was likely auto-created by an early log_message arriving
        // before session_start (race condition). Fill in any NULL/empty metadata
        // columns now — COALESCE never overwrites already-rich values.
        $ip = $data['ip_address'] ?? null;
        if (!$ip) { $ip = getRealClientIP(); }
        $geo = geolocateIP($ip);
        $country = !empty($data['country']) ? $data['country'] : $geo['country'];
        $city    = $geo['city'];

        $upd = $db->prepare("UPDATE sessions SET
            ip_address    = COALESCE(NULLIF(ip_address,''),    ?),
            country       = COALESCE(NULLIF(country,''),       ?),
            city          = COALESCE(NULLIF(city,''),          ?),
            device_type   = COALESCE(NULLIF(device_type,''),   ?),
            browser       = COALESCE(NULLIF(browser,''),       ?),
            os            = COALESCE(NULLIF(os,''),            ?),
            screen_width  = COALESCE(screen_width,  ?),
            screen_height = COALESCE(screen_height, ?),
            language      = COALESCE(NULLIF(language,''),      ?),
            referrer_url  = COALESCE(NULLIF(referrer_url,''),  ?),
            user_agent    = COALESCE(NULLIF(user_agent,''),    ?),
            user_name     = COALESCE(NULLIF(user_name,''),     ?),
            user_email    = COALESCE(NULLIF(user_email,''),    ?)
            WHERE session_id = ?");
        $upd->execute([
            $ip, $country, $city,
            $data['device_type']    ?? 'unknown',
            $data['browser']        ?? 'unknown',
            $data['os']             ?? 'unknown',
            $data['screen_width']   ?? null,
            $data['screen_height']  ?? null,
            $data['language']       ?? null,
            $data['referrer']       ?? null,
            $data['user_agent']     ?? null,
            $data['user_name']      ?? null,
            $data['user_email']     ?? null,
            $sessionId,
        ]);
        echo json_encode(['success' => true, 'message' => 'Session enriched', 'country' => $country, 'city' => $city]);
        return;
    }
    
    // Geolocate IP (auto-detect from request headers if not provided)
    $ip = $data['ip_address'] ?? null;
    if (!$ip) {
        $ip = getRealClientIP();
    }
    $geo = geolocateIP($ip);
    
    // Prefer user-provided country (from form selection) over geolocation
    $country = !empty($data['country']) ? $data['country'] : $geo['country'];
    $city = $geo['city'];
    
    $stmt = $db->prepare("INSERT INTO sessions 
        (session_id, started_at, ip_address, country, city, device_type, browser, os, 
         screen_width, screen_height, language, referrer_url, user_agent, user_name, user_email)
        VALUES (?, NOW(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    
    $stmt->execute([
        $sessionId,
        $ip,
        $country,
        $city,
        $data['device_type'] ?? 'unknown',
        $data['browser'] ?? 'unknown',
        $data['os'] ?? 'unknown',
        $data['screen_width'] ?? null,
        $data['screen_height'] ?? null,
        $data['language'] ?? null,
        $data['referrer'] ?? null,
        $data['user_agent'] ?? null,
        $data['user_name'] ?? null,
        $data['user_email'] ?? null
    ]);
    
    // Update daily stats
    updateDailyStats('session', $data['device_type'] ?? 'desktop');
    
    echo json_encode(['success' => true, 'message' => 'Session created', 'country' => $country, 'city' => $city]);
}

function handleLogMessage($data) {
    $db = getDB();
    
    $sessionId = $data['session_id'] ?? null;
    $sender = $data['sender'] ?? null;
    $text = $data['message_text'] ?? $data['text'] ?? '';
    
    if (!$sessionId || !$sender) {
        http_response_code(400);
        echo json_encode(['error' => 'session_id and sender required']);
        return;
    }
    
    // Auto-create session if it doesn't exist (handles race condition)
    $check = $db->prepare("SELECT id FROM sessions WHERE session_id = ?");
    $check->execute([$sessionId]);
    if (!$check->fetch()) {
        // Capture whatever we can from the HTTP request itself so the row is
        // not completely empty if session_start never arrives.
        $ip  = getRealClientIP();
        $geo = geolocateIP($ip);
        $ua  = $_SERVER['HTTP_USER_AGENT'] ?? null;
        $ref = $_SERVER['HTTP_REFERER']    ?? null;
        $ins = $db->prepare("INSERT INTO sessions
            (session_id, started_at, ip_address, country, city, user_agent, referrer_url)
            VALUES (?, NOW(), ?, ?, ?, ?, ?)");
        $ins->execute([$sessionId, $ip, $geo['country'], $geo['city'], $ua, $ref]);
    }
    
    $stmt = $db->prepare("INSERT INTO messages 
        (session_id, sender, message_text, intent, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?, NOW())");

    // ── Deduplication ─────────────────────────────────────────────────
    // The chat widget and the Rasa server can both log the same message
    // (user messages arrive twice; the server copy carries the NLU intent).
    // When an identical message already arrived for this session within the
    // last 5 minutes, merge instead of inserting a duplicate row.
    try {
        $dup = $db->prepare("SELECT id, intent FROM messages
                             WHERE session_id = ? AND sender = ? AND message_text = ?
                               AND timestamp >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                             ORDER BY id DESC LIMIT 1");
        $dup->execute([$sessionId, $sender, $text]);
        $existing = $dup->fetch();
        if ($existing) {
            $newIntent = $data['intent'] ?? null;
            if ($newIntent && empty($existing['intent'])) {
                $db->prepare("UPDATE messages SET intent = ?, confidence = ? WHERE id = ?")
                   ->execute([$newIntent, $data['confidence'] ?? null, $existing['id']]);
            }
            echo json_encode(['success' => true, 'deduplicated' => true]);
            return;
        }
    } catch (Exception $e) {
        // Fall through to normal insert on any dedup error
    }
    
    $stmt->execute([
        $sessionId,
        $sender,
        $text,
        $data['intent'] ?? null,
        $data['confidence'] ?? null
    ]);
    
    // Update message count on session
    $db->prepare("UPDATE sessions SET message_count = message_count + 1 WHERE session_id = ?")->execute([$sessionId]);
    
    // Update daily message stats
    updateDailyStats('message');
    
    echo json_encode(['success' => true]);
}

function handleSessionEnd($data) {
    $db = getDB();
    
    $sessionId = $data['session_id'] ?? null;
    if (!$sessionId) {
        http_response_code(400);
        echo json_encode(['error' => 'session_id required']);
        return;
    }
    
    $stmt = $db->prepare("UPDATE sessions SET 
        ended_at = NOW(),
        duration_seconds = TIMESTAMPDIFF(SECOND, started_at, NOW())
        WHERE session_id = ?");
    $stmt->execute([$sessionId]);
    
    // Flag as unresolved if bot failed to answer or user's last message got no reply
    flagUnresolvedIfNeeded($db, $sessionId);
    
    // Update avg duration in daily stats
    $row = $db->query("SELECT AVG(duration_seconds) as avg_dur FROM sessions WHERE DATE(started_at) = CURDATE() AND duration_seconds IS NOT NULL")->fetch();
    if ($row && $row['avg_dur']) {
        $db->prepare("UPDATE daily_stats SET avg_duration_seconds = ? WHERE date = CURDATE()")->execute([intval($row['avg_dur'])]);
    }
    
    echo json_encode(['success' => true, 'message' => 'Session ended']);
}

function handleUpdateSession($data) {
    $db = getDB();
    
    $sessionId = $data['session_id'] ?? null;
    if (!$sessionId) {
        http_response_code(400);
        echo json_encode(['error' => 'session_id required']);
        return;
    }
    
    $updates = [];
    $params = [];
    
    if (!empty($data['user_email'])) {
        $updates[] = "user_email = ?";
        $params[] = $data['user_email'];
        
        // Upsert into users table
        upsertUser($data['user_email'], $data['user_name'] ?? null, $sessionId);
    }
    if (!empty($data['user_name'])) {
        $updates[] = "user_name = ?";
        $params[] = $data['user_name'];
    }
    
    if (!empty($updates)) {
        $params[] = $sessionId;
        $sql = "UPDATE sessions SET " . implode(', ', $updates) . " WHERE session_id = ?";
        $db->prepare($sql)->execute($params);
    }
    
    echo json_encode(['success' => true]);
}

function handleRegistration($data) {
    $db = getDB();
    
    $stmt = $db->prepare("INSERT INTO registrations 
        (session_id, reference_number, category, company, contact_name, email, phone, country, registered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW())");
    
    $stmt->execute([
        $data['session_id'] ?? null,
        $data['reference_number'] ?? null,
        $data['category'] ?? null,
        $data['company'] ?? null,
        $data['contact_name'] ?? null,
        $data['email'] ?? null,
        $data['phone'] ?? null,
        $data['country'] ?? null
    ]);
    
    echo json_encode(['success' => true]);
}

// ============================================================
// HELPER FUNCTIONS
// ============================================================

function upsertUser($email, $name, $sessionId) {
    $db = getDB();
    
    // Get country from session
    $sess = $db->prepare("SELECT country, city FROM sessions WHERE session_id = ?");
    $sess->execute([$sessionId]);
    $sessData = $sess->fetch();
    
    $stmt = $db->prepare("SELECT id FROM users WHERE email = ?");
    $stmt->execute([$email]);
    
    if ($stmt->fetch()) {
        $db->prepare("UPDATE users SET last_seen = NOW(), session_count = session_count + 1, name = COALESCE(?, name) WHERE email = ?")
           ->execute([$name, $email]);
    } else {
        $db->prepare("INSERT INTO users (email, name, first_seen, last_seen, session_count, country, city) VALUES (?, ?, NOW(), NOW(), 1, ?, ?)")
           ->execute([$email, $name, $sessData['country'] ?? null, $sessData['city'] ?? null]);
    }
}

function updateDailyStats($type, $deviceType = null) {
    $db = getDB();
    $today = date('Y-m-d');
    
    // Ensure today's row exists
    $db->prepare("INSERT IGNORE INTO daily_stats (date) VALUES (?)")->execute([$today]);
    
    if ($type === 'session') {
        $device_col = 'desktop_count';
        if ($deviceType === 'mobile') $device_col = 'mobile_count';
        elseif ($deviceType === 'tablet') $device_col = 'tablet_count';
        
        $db->prepare("UPDATE daily_stats SET total_sessions = total_sessions + 1, {$device_col} = {$device_col} + 1 WHERE date = ?")->execute([$today]);
    } elseif ($type === 'message') {
        $db->prepare("UPDATE daily_stats SET total_messages = total_messages + 1 WHERE date = ?")->execute([$today]);
    }
}

// ============================================================
// ROUTER
// ============================================================

ensureTables();

$action = $_GET['action'] ?? '';

if ($action === 'health') {
    handleHealth();
    exit;
}

// All other actions require authentication
authenticate();

$input = json_decode(file_get_contents('php://input'), true) ?? [];

switch ($action) {
    case 'session_start':
        handleSessionStart($input);
        break;
    case 'log_message':
        handleLogMessage($input);
        break;
    case 'session_end':
        handleSessionEnd($input);
        break;
    case 'update_session':
        handleUpdateSession($input);
        break;
    case 'registration':
        handleRegistration($input);
        break;
    // === MONITOR (read-only) actions, used by tools/convo_monitor.py ===
    case 'list_sessions':
        handleListSessions();
        break;
    case 'get_session':
        handleGetSession();
        break;
    case 'get_messages':
        handleGetMessages();
        break;
    case 'list_errors':
        handleListErrors();
        break;
    case 'monitor_stats':
        handleMonitorStats();
        break;
    case 'flag_session':
        handleFlagSession($input);
        break;
    default:
        http_response_code(400);
        echo json_encode(['error' => 'Unknown action', 'valid_actions' => [
            'health', 'session_start', 'log_message', 'session_end', 'update_session', 'registration',
            'list_sessions', 'get_session', 'get_messages', 'list_errors', 'monitor_stats', 'flag_session'
        ]]);
}

// ============================================================
// MONITOR HANDLERS (read-only, used by tools/convo_monitor.py)
// ============================================================

function handleListSessions() {
    $db = getDB();
    autoCloseStaleSessions($db);

    $limit  = max(1, min(500, (int)($_GET['limit']  ?? 50)));
    $offset = max(0,          (int)($_GET['offset'] ?? 0));
    $since  = $_GET['since']  ?? null;   // e.g. "2026-02-25 00:00:00" or "24h"
    $status = $_GET['status'] ?? 'all';  // all | active | ended | unresolved | resolved
    $search = trim((string)($_GET['search'] ?? ''));

    $where  = [];
    $params = [];

    if ($since) {
        if (preg_match('/^(\d+)\s*([hdm])$/i', $since, $m)) {
            $n = (int)$m[1];
            $unit = strtolower($m[2]);
            $interval = $unit === 'h' ? "INTERVAL $n HOUR" : ($unit === 'd' ? "INTERVAL $n DAY" : "INTERVAL $n MINUTE");
            $where[] = "s.started_at >= DATE_SUB(NOW(), $interval)";
        } else {
            $where[] = "s.started_at >= ?";
            $params[] = $since;
        }
    }
    if ($status === 'active')     $where[] = "s.ended_at IS NULL";
    if ($status === 'ended')      $where[] = "s.ended_at IS NOT NULL";
    if ($status === 'unresolved') $where[] = "s.is_unresolved = 1 AND s.resolved_at IS NULL";
    if ($status === 'resolved')   $where[] = "s.resolved_at IS NOT NULL";

    if ($search !== '') {
        $where[] = "(s.session_id LIKE ? OR s.user_email LIKE ? OR s.user_name LIKE ?)";
        $params[] = "%$search%"; $params[] = "%$search%"; $params[] = "%$search%";
    }

    $whereSql = $where ? ('WHERE ' . implode(' AND ', $where)) : '';
    $sql = "SELECT s.session_id, s.started_at, s.ended_at, s.duration_seconds,
                   s.user_name, s.user_email, s.country, s.city, s.device_type,
                   s.message_count, s.is_unresolved, s.resolved_at, s.resolved_by
            FROM sessions s
            $whereSql
            ORDER BY s.started_at DESC
            LIMIT $limit OFFSET $offset";
    $stmt = $db->prepare($sql);
    $stmt->execute($params);
    $rows = $stmt->fetchAll();

    $countSql = "SELECT COUNT(*) FROM sessions s $whereSql";
    $cstmt = $db->prepare($countSql);
    $cstmt->execute($params);
    $total = (int)$cstmt->fetchColumn();

    echo json_encode(['success' => true, 'total' => $total, 'limit' => $limit, 'offset' => $offset, 'sessions' => $rows]);
}

function handleGetSession() {
    $db = getDB();
    $sid = $_GET['session_id'] ?? '';
    if (!$sid) { http_response_code(400); echo json_encode(['error' => 'session_id required']); return; }

    $stmt = $db->prepare("SELECT * FROM sessions WHERE session_id = ?");
    $stmt->execute([$sid]);
    $session = $stmt->fetch();
    if (!$session) { http_response_code(404); echo json_encode(['error' => 'Session not found']); return; }

    $stmt = $db->prepare("SELECT id, sender, message_text, intent, confidence, timestamp
                          FROM messages WHERE session_id = ? ORDER BY timestamp ASC, id ASC");
    $stmt->execute([$sid]);
    $messages = $stmt->fetchAll();

    $stmt = $db->prepare("SELECT reference_number, category, company, contact_name, email, phone, country, registered_at
                          FROM registrations WHERE session_id = ? ORDER BY registered_at DESC");
    $stmt->execute([$sid]);
    $registrations = $stmt->fetchAll();

    $stmt = $db->prepare("SELECT admin_username, recipient_email, subject, sent_at, email_status
                          FROM admin_replies WHERE session_id = ? ORDER BY sent_at DESC");
    $stmt->execute([$sid]);
    $replies = $stmt->fetchAll();

    echo json_encode([
        'success' => true,
        'session' => $session,
        'messages' => $messages,
        'registrations' => $registrations,
        'admin_replies' => $replies,
    ]);
}

function handleGetMessages() {
    $db = getDB();
    $since = $_GET['since'] ?? null; // ISO timestamp
    $limit = max(1, min(1000, (int)($_GET['limit'] ?? 200)));

    if ($since) {
        $stmt = $db->prepare("SELECT m.id, m.session_id, m.sender, m.message_text, m.intent, m.confidence, m.timestamp,
                                     s.user_name, s.user_email
                              FROM messages m
                              LEFT JOIN sessions s ON s.session_id = m.session_id
                              WHERE m.timestamp > ?
                              ORDER BY m.timestamp ASC, m.id ASC LIMIT $limit");
        $stmt->execute([$since]);
    } else {
        $stmt = $db->prepare("SELECT m.id, m.session_id, m.sender, m.message_text, m.intent, m.confidence, m.timestamp,
                                     s.user_name, s.user_email
                              FROM messages m
                              LEFT JOIN sessions s ON s.session_id = m.session_id
                              ORDER BY m.timestamp DESC, m.id DESC LIMIT $limit");
        $stmt->execute();
    }
    $rows = $stmt->fetchAll();
    echo json_encode(['success' => true, 'count' => count($rows), 'messages' => $rows, 'server_time' => date('Y-m-d H:i:s')]);
}

function handleListErrors() {
    // Returns sessions that LIKELY contain issues, with heuristics applied server-side.
    $db = getDB();
    autoCloseStaleSessions($db);

    $since = $_GET['since'] ?? '7d';
    if (preg_match('/^(\d+)\s*([hdm])$/i', $since, $m)) {
        $n = (int)$m[1]; $u = strtolower($m[2]);
        $interval = $u === 'h' ? "INTERVAL $n HOUR" : ($u === 'd' ? "INTERVAL $n DAY" : "INTERVAL $n MINUTE");
        $sinceSql = "s.started_at >= DATE_SUB(NOW(), $interval)";
    } else {
        $sinceSql = "s.started_at >= '" . addslashes($since) . "'";
    }

    $sql = "SELECT s.session_id, s.started_at, s.ended_at, s.duration_seconds,
                   s.user_name, s.user_email, s.country, s.message_count,
                   s.is_unresolved, s.resolved_at
            FROM sessions s
            WHERE $sinceSql
            ORDER BY s.started_at DESC
            LIMIT 500";
    $sessions = $db->query($sql)->fetchAll();

    $results = [];
    foreach ($sessions as $s) {
        $sid = $s['session_id'];
        $mstmt = $db->prepare("SELECT sender, message_text, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp ASC, id ASC");
        $mstmt->execute([$sid]);
        $msgs = $mstmt->fetchAll();
        $flags = detectErrorFlags($msgs, $s);
        if ($flags) {
            $results[] = [
                'session_id'       => $sid,
                'started_at'       => $s['started_at'],
                'ended_at'         => $s['ended_at'],
                'duration_seconds' => $s['duration_seconds'],
                'user_name'        => $s['user_name'],
                'user_email'       => $s['user_email'],
                'country'          => $s['country'],
                'message_count'    => (int)$s['message_count'],
                'is_unresolved'    => (int)$s['is_unresolved'],
                'resolved_at'      => $s['resolved_at'],
                'error_flags'      => $flags,
            ];
        }
    }
    echo json_encode(['success' => true, 'count' => count($results), 'errors' => $results]);
}

/**
 * Heuristic error detector. Returns a list of tag strings for a session.
 * Tags:
 *   nlu_fallback, form_blocked, abandoned_registration,
 *   repeated_user_message, no_bot_reply, bot_fallback_text,
 *   dont_understand, very_short, long_inactivity, validation_loop
 */
function detectErrorFlags($msgs, $session) {
    if (!$msgs) return [];
    $flags = [];
    $userMsgs = []; $botMsgs = [];
    foreach ($msgs as $m) {
        if ($m['sender'] === 'user') $userMsgs[] = $m;
        elseif ($m['sender'] === 'bot') $botMsgs[] = $m;
    }
    $userTexts = array_map(function($m) { return strtolower(trim(isset($m['message_text']) ? $m['message_text'] : '')); }, $userMsgs);
    $botTexts  = array_map(function($m) { return strtolower(trim(isset($m['message_text']) ? $m['message_text'] : '')); }, $botMsgs);

    // 1. Explicit "don't understand" phrases from user
    $dontPatterns = ['je comprends pas', 'je ne comprends pas', "j'ai pas compris", 'pas compris', 'c est quoi', "c'est quoi", 'help', 'aidez', 'aide', "aidez-moi", 'je sais pas'];
    foreach ($userTexts as $t) {
        foreach ($dontPatterns as $p) {
            if ($p && strpos($t, $p) !== false) { $flags[] = 'dont_understand'; break 2; }
        }
    }

    // 2. Bot fallback text (configured patterns)
    $botFbPatterns = $GLOBALS['UNRESOLVED_BOT_PATTERNS'] ?? [];
    foreach ($botMsgs as $bm) {
        foreach ($botFbPatterns as $p) {
            if ($p && stripos($bm['message_text'] ?? '', $p) !== false) { $flags[] = 'bot_fallback_text'; break 2; }
        }
    }

    // 3. nlu_fallback heuristic: user message followed by bot message that suggests registration/guide + "pourriez aussi demander"
    foreach ($botTexts as $bt) {
        if (strpos($bt, 'pourriez aussi demander') !== false || strpos($bt, 'nlu_fallback') !== false) {
            $flags[] = 'nlu_fallback'; break;
        }
    }

    // 4. Repeated user messages (same text 2+ times within 5 minutes)
    $seen = [];
    foreach ($userMsgs as $um) {
        $key = strtolower(trim($um['message_text'] ?? ''));
        if (!$key) continue;
        if (isset($seen[$key])) { $flags[] = 'repeated_user_message'; break; }
        $seen[$key] = true;
    }

    // 5. Bot repeats same prompt 3+ times (form_blocked / validation_loop)
    $botCounts = [];
    foreach ($botTexts as $bt) {
        $k = substr($bt, 0, 80);
        if (!$k) continue;
        $botCounts[$k] = ($botCounts[$k] ?? 0) + 1;
    }
    foreach ($botCounts as $c) {
        if ($c >= 3) { $flags[] = 'form_blocked'; break; }
    }

    // 6. Validation loop: user typing category prompts multiple times (e.g. bot says "tapez le numéro" 3+ times)
    $cnt = 0;
    foreach ($botTexts as $bt) {
        if (strpos($bt, 'tapez le numéro') !== false || strpos($bt, 'pour quelle catégorie') !== false) $cnt++;
    }
    if ($cnt >= 3) $flags[] = 'validation_loop';

    // 7. Abandoned registration: bot asked for company/email/phone but no registration row + session ended
    $askedReg = false;
    foreach ($botTexts as $bt) {
        if (strpos($bt, "nom de votre entreprise") !== false || strpos($bt, "quelle est votre adresse email") !== false || strpos($bt, "numéro de téléphone") !== false) {
            $askedReg = true; break;
        }
    }
    if ($askedReg) {
        $db = getDB();
        $has = $db->prepare("SELECT COUNT(*) FROM registrations WHERE session_id = ?");
        $has->execute([$session['session_id']]);
        $regCount = (int)$has->fetchColumn();
        $ended = !empty($session['ended_at']);
        if ($regCount === 0 && $ended) $flags[] = 'abandoned_registration';
    }

    // 8. User's last message got no bot reply
    if ($msgs) {
        $last = end($msgs);
        if ($last['sender'] === 'user' && !empty($session['ended_at'])) $flags[] = 'no_bot_reply';
    }

    // 9. Very short session (< 3 total messages, ended)
    if (count($msgs) <= 2 && !empty($session['ended_at'])) $flags[] = 'very_short';

    // 10. Long inactivity gap inside conversation (>= 3 minutes between consecutive messages)
    for ($i = 1; $i < count($msgs); $i++) {
        $d = strtotime($msgs[$i]['timestamp']) - strtotime($msgs[$i-1]['timestamp']);
        if ($d >= 180) { $flags[] = 'long_inactivity'; break; }
    }

    return array_values(array_unique($flags));
}

function handleMonitorStats() {
    $db = getDB();
    autoCloseStaleSessions($db);
    $range = $_GET['range'] ?? '7d';
    if (preg_match('/^(\d+)\s*([hdm])$/i', $range, $m)) {
        $n = (int)$m[1]; $u = strtolower($m[2]);
        $interval = $u === 'h' ? "INTERVAL $n HOUR" : ($u === 'd' ? "INTERVAL $n DAY" : "INTERVAL $n MINUTE");
        $sinceSql = "DATE_SUB(NOW(), $interval)";
    } else {
        $sinceSql = "DATE_SUB(NOW(), INTERVAL 7 DAY)";
    }

    $totalSess = (int)$db->query("SELECT COUNT(*) FROM sessions WHERE started_at >= $sinceSql")->fetchColumn();
    $totalMsgs = (int)$db->query("SELECT COUNT(*) FROM messages m JOIN sessions s ON s.session_id = m.session_id WHERE s.started_at >= $sinceSql")->fetchColumn();
    $active    = (int)$db->query("SELECT COUNT(*) FROM sessions WHERE ended_at IS NULL AND started_at >= DATE_SUB(NOW(), INTERVAL 30 MINUTE)")->fetchColumn();
    $unresolved= (int)$db->query("SELECT COUNT(*) FROM sessions WHERE is_unresolved = 1 AND resolved_at IS NULL AND started_at >= $sinceSql")->fetchColumn();
    $registrations = (int)$db->query("SELECT COUNT(*) FROM registrations WHERE registered_at >= $sinceSql")->fetchColumn();
    $avgMsgs   = (float)$db->query("SELECT AVG(message_count) FROM sessions WHERE started_at >= $sinceSql")->fetchColumn();
    $avgDur    = (float)$db->query("SELECT AVG(duration_seconds) FROM sessions WHERE started_at >= $sinceSql AND duration_seconds IS NOT NULL")->fetchColumn();

    echo json_encode([
        'success' => true,
        'range' => $range,
        'total_sessions' => $totalSess,
        'total_messages' => $totalMsgs,
        'active_now' => $active,
        'unresolved' => $unresolved,
        'registrations' => $registrations,
        'avg_messages_per_session' => round($avgMsgs, 1),
        'avg_duration_seconds' => (int)$avgDur,
    ]);
}

function handleFlagSession($data) {
    $db = getDB();
    $sid   = $data['session_id'] ?? '';
    $flag  = $data['flag']       ?? 'resolved'; // resolved | unresolved
    $by    = $data['by']         ?? 'monitor-cli';
    if (!$sid) { http_response_code(400); echo json_encode(['error' => 'session_id required']); return; }

    if ($flag === 'resolved') {
        $db->prepare("UPDATE sessions SET resolved_at = NOW(), resolved_by = ?, is_unresolved = 0 WHERE session_id = ?")
           ->execute([$by, $sid]);
    } elseif ($flag === 'unresolved') {
        $db->prepare("UPDATE sessions SET is_unresolved = 1, resolved_at = NULL, resolved_by = NULL WHERE session_id = ?")
           ->execute([$sid]);
    } else {
        http_response_code(400); echo json_encode(['error' => 'flag must be resolved|unresolved']); return;
    }
    echo json_encode(['success' => true]);
}
