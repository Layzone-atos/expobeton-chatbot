<?php
require_once __DIR__ . '/auth.php';
requireLogin();
$db = getDB();

$sessionId = $_GET['id'] ?? '';
if (!$sessionId) { header('Location: conversations.php'); exit; }

// Get session info
$stmt = $db->prepare("SELECT * FROM sessions WHERE session_id = ?");
$stmt->execute([$sessionId]);
$session = $stmt->fetch();

if (!$session) { header('Location: conversations.php'); exit; }

// Get messages
$stmt = $db->prepare("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC");
$stmt->execute([$sessionId]);
$messages = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conversation Detail - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark" style="background: #0A2A66;">
        <div class="container-fluid">
            <a class="navbar-brand fw-bold" href="dashboard.php">ExpoBeton Analytics</a>
            <div class="navbar-nav ms-auto d-flex flex-row gap-2">
                <a class="nav-link" href="dashboard.php"><i class="bi bi-speedometer2"></i> Dashboard</a>
                <a class="nav-link" href="conversations.php"><i class="bi bi-chat-dots"></i> Conversations</a>
                <a class="nav-link" href="analytics.php"><i class="bi bi-bar-chart"></i> Analytics</a>
                <a class="nav-link" href="users.php"><i class="bi bi-people"></i> Users</a>
                <a class="nav-link text-warning" href="logout.php"><i class="bi bi-box-arrow-right"></i> Logout</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <a href="conversations.php" class="btn btn-outline-secondary btn-sm mb-3"><i class="bi bi-arrow-left"></i> Back</a>
        
        <div class="row g-4">
            <!-- Sidebar: Session Info -->
            <div class="col-lg-4">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold">Session Info</div>
                    <div class="card-body">
                        <table class="table table-sm table-borderless mb-0">
                            <tr><td class="text-muted">Session ID</td><td class="text-break" style="font-size:0.8rem;"><?= escape($session['session_id']) ?></td></tr>
                            <tr><td class="text-muted">User</td><td><?= escape($session['user_name'] ?: '-') ?></td></tr>
                            <tr><td class="text-muted">Email</td><td><?= escape($session['user_email'] ?: '-') ?></td></tr>
                            <tr><td class="text-muted">Country</td><td><?= formatCountryWithFlag($session['country'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">City</td><td><?= escape($session['city'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">IP</td><td><?= escape($session['ip_address'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">Device</td><td><span class="badge bg-primary"><?= escape($session['device_type'] ?? '-') ?></span></td></tr>
                            <tr><td class="text-muted">Browser</td><td><?= escape($session['browser'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">OS</td><td><?= escape($session['os'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">Screen</td><td><?= ($session['screen_width'] && $session['screen_height']) ? escape($session['screen_width'] . 'x' . $session['screen_height']) : '-' ?></td></tr>
                            <tr><td class="text-muted">Language</td><td><?= escape($session['language'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">Started</td><td><?= date('M j, Y H:i:s', strtotime($session['started_at'])) ?></td></tr>
                            <tr><td class="text-muted">Ended</td><td><?= $session['ended_at'] ? date('M j, Y H:i:s', strtotime($session['ended_at'])) : '<span class="text-warning">Active</span>' ?></td></tr>
                            <tr><td class="text-muted">Duration</td><td><?= formatDuration($session['duration_seconds']) ?></td></tr>
                            <tr><td class="text-muted">Messages</td><td><?= count($messages) ?: $session['message_count'] ?></td></tr>
                            <?php if ($session['referrer_url']): ?>
                            <tr><td class="text-muted">Referrer</td><td class="text-break" style="font-size:0.8rem;"><?= escape($session['referrer_url']) ?></td></tr>
                            <?php endif; ?>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- Chat Messages -->
            <div class="col-lg-8">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold">Conversation (<?= count($messages) ?> messages)</div>
                    <div class="card-body chat-history" style="max-height: 70vh; overflow-y: auto; background: #f8f9fa;">
                        <?php if (empty($messages)): ?>
                            <p class="text-center text-muted py-5">No messages recorded</p>
                        <?php else: ?>
                            <?php foreach ($messages as $msg): ?>
                                <div class="d-flex mb-3 <?= $msg['sender'] === 'user' ? 'justify-content-end' : 'justify-content-start' ?>">
                                    <div class="chat-bubble <?= $msg['sender'] === 'user' ? 'chat-user' : 'chat-bot' ?>">
                                        <div class="small fw-bold mb-1"><?= $msg['sender'] === 'user' ? 'User' : 'Bot' ?></div>
                                        <div><?= nl2br(escape($msg['message_text'])) ?></div>
                                        <div class="text-end mt-1" style="font-size: 0.7rem; opacity: 0.7;">
                                            <?= date('H:i:s', strtotime($msg['timestamp'])) ?>
                                            <?php if ($msg['intent']): ?>
                                                <span class="ms-1 badge bg-secondary" style="font-size:0.6rem;"><?= escape($msg['intent']) ?> (<?= round(($msg['confidence'] ?? 0) * 100) ?>%)</span>
                                            <?php endif; ?>
                                        </div>
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
