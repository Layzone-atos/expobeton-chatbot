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
function geolocateIP($ip) {
    if (!$ip || $ip === '127.0.0.1' || $ip === '::1') {
        return ['country' => 'Local', 'city' => 'Local'];
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
    echo json_encode([
        'success' => true,
        'service' => 'chatbot-analytics',
        'db_connected' => true,
        'timestamp' => date('Y-m-d H:i:s')
    ]);
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
    if ($stmt->fetch()) {
        echo json_encode(['success' => true, 'message' => 'Session already exists']);
        return;
    }
    
    // Geolocate IP
    $ip = $data['ip_address'] ?? null;
    $geo = geolocateIP($ip);
    
    $stmt = $db->prepare("INSERT INTO sessions 
        (session_id, started_at, ip_address, country, city, device_type, browser, os, 
         screen_width, screen_height, language, referrer_url, user_agent, user_name, user_email)
        VALUES (?, NOW(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    
    $stmt->execute([
        $sessionId,
        $ip,
        $geo['country'],
        $geo['city'],
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
    
    echo json_encode(['success' => true, 'message' => 'Session created', 'country' => $geo['country'], 'city' => $geo['city']]);
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
        $db->prepare("INSERT INTO sessions (session_id, started_at) VALUES (?, NOW())")->execute([$sessionId]);
    }
    
    $stmt = $db->prepare("INSERT INTO messages 
        (session_id, sender, message_text, intent, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?, NOW())");
    
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
    default:
        http_response_code(400);
        echo json_encode(['error' => 'Unknown action', 'valid_actions' => ['health', 'session_start', 'log_message', 'session_end', 'update_session', 'registration']]);
}
