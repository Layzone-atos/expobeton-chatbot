<?php
require_once __DIR__ . '/auth.php';
requireLogin();
$db = getDB();

// Filters
$page = max(1, intval($_GET['page'] ?? 1));
$search = trim($_GET['search'] ?? '');
$country = trim($_GET['country'] ?? '');
$device = trim($_GET['device'] ?? '');
$dateFrom = trim($_GET['date_from'] ?? '');
$dateTo = trim($_GET['date_to'] ?? '');

$where = [];
$params = [];

if ($search) {
    $where[] = "(s.user_name LIKE ? OR s.user_email LIKE ? OR s.session_id LIKE ?)";
    $params[] = "%$search%";
    $params[] = "%$search%";
    $params[] = "%$search%";
}
if ($country) {
    $where[] = "s.country = ?";
    $params[] = $country;
}
if ($device) {
    $where[] = "s.device_type = ?";
    $params[] = $device;
}
if ($dateFrom) {
    $where[] = "DATE(s.started_at) >= ?";
    $params[] = $dateFrom;
}
if ($dateTo) {
    $where[] = "DATE(s.started_at) <= ?";
    $params[] = $dateTo;
}

$whereSQL = $where ? 'WHERE ' . implode(' AND ', $where) : '';

// Count
$countStmt = $db->prepare("SELECT COUNT(*) FROM sessions s $whereSQL");
$countStmt->execute($params);
$total = $countStmt->fetchColumn();
$totalPages = max(1, ceil($total / ITEMS_PER_PAGE));
$offset = ($page - 1) * ITEMS_PER_PAGE;

// Fetch
$stmt = $db->prepare("SELECT s.*, (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.session_id) AS real_message_count FROM sessions s $whereSQL ORDER BY s.started_at DESC LIMIT " . ITEMS_PER_PAGE . " OFFSET $offset");
$stmt->execute($params);
$sessions = $stmt->fetchAll();

// Get distinct countries and devices for filter dropdowns
$countryList = $db->query("SELECT DISTINCT country FROM sessions WHERE country IS NOT NULL AND country != '' ORDER BY country")->fetchAll(PDO::FETCH_COLUMN);
$deviceList = $db->query("SELECT DISTINCT device_type FROM sessions WHERE device_type IS NOT NULL ORDER BY device_type")->fetchAll(PDO::FETCH_COLUMN);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conversations - <?= APP_NAME ?></title>
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
                <a class="nav-link active" href="conversations.php"><i class="bi bi-chat-dots"></i> Conversations</a>
                <a class="nav-link" href="analytics.php"><i class="bi bi-bar-chart"></i> Analytics</a>
                <a class="nav-link" href="users.php"><i class="bi bi-people"></i> Users</a>
                <a class="nav-link text-warning" href="logout.php"><i class="bi bi-box-arrow-right"></i> Logout</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <h4 class="mb-3">Conversations <span class="text-muted fs-6">(<?= number_format($total) ?> total)</span></h4>
        
        <!-- Filters -->
        <form class="card border-0 shadow-sm mb-4" method="GET">
            <div class="card-body">
                <div class="row g-2 align-items-end">
                    <div class="col-md-3">
                        <label class="form-label small">Search</label>
                        <input type="text" class="form-control form-control-sm" name="search" value="<?= escape($search) ?>" placeholder="Name, email, session ID...">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small">Country</label>
                        <select class="form-select form-select-sm" name="country">
                            <option value="">All</option>
                            <?php foreach ($countryList as $c): ?>
                                <option value="<?= escape($c) ?>" <?= $country === $c ? 'selected' : '' ?>><?= escape($c) ?></option>
                            <?php endforeach; ?>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small">Device</label>
                        <select class="form-select form-select-sm" name="device">
                            <option value="">All</option>
                            <?php foreach ($deviceList as $d): ?>
                                <option value="<?= escape($d) ?>" <?= $device === $d ? 'selected' : '' ?>><?= ucfirst(escape($d)) ?></option>
                            <?php endforeach; ?>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small">From</label>
                        <input type="date" class="form-control form-control-sm" name="date_from" value="<?= escape($dateFrom) ?>">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small">To</label>
                        <input type="date" class="form-control form-control-sm" name="date_to" value="<?= escape($dateTo) ?>">
                    </div>
                    <div class="col-md-1">
                        <button type="submit" class="btn btn-sm btn-primary w-100" style="background:#0A2A66; border-color:#0A2A66;">Filter</button>
                    </div>
                </div>
            </div>
        </form>

        <!-- Table -->
        <div class="card border-0 shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Session</th>
                            <th>User</th>
                            <th>Country</th>
                            <th>Device</th>
                            <th>Browser</th>
                            <th>Messages</th>
                            <th>Duration</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($sessions as $s): ?>
                        <tr style="cursor:pointer;" onclick="location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'">
                            <td class="text-truncate" style="max-width:120px;" title="<?= escape($s['session_id']) ?>"><?= escape(substr($s['session_id'], 0, 20)) ?>...</td>
                            <td><?= escape($s['user_name'] ?: ($s['user_email'] ?: '-')) ?></td>
                            <td><?= escape($s['country'] ?? '-') ?></td>
                            <td><span class="badge bg-<?= $s['device_type']==='mobile'?'success':($s['device_type']==='tablet'?'warning':'primary') ?>"><?= escape($s['device_type'] ?? '-') ?></span></td>
                            <td><?= escape($s['browser'] ?? '-') ?></td>
                            <td><?= $s['real_message_count'] ?: $s['message_count'] ?></td>
                            <td><?= formatDuration($s['duration_seconds']) ?></td>
                            <td><?= date('M j, H:i', strtotime($s['started_at'])) ?></td>
                        </tr>
                        <?php endforeach; ?>
                        <?php if (empty($sessions)): ?>
                        <tr><td colspan="8" class="text-center text-muted py-4">No conversations found</td></tr>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Pagination -->
        <?php if ($totalPages > 1): ?>
        <nav class="mt-3">
            <ul class="pagination justify-content-center">
                <?php for ($i = max(1, $page-2); $i <= min($totalPages, $page+2); $i++): ?>
                    <li class="page-item <?= $i === $page ? 'active' : '' ?>">
                        <a class="page-link" href="?<?= http_build_query(array_merge($_GET, ['page' => $i])) ?>"><?= $i ?></a>
                    </li>
                <?php endfor; ?>
            </ul>
        </nav>
        <?php endif; ?>
    </div>
</body>
</html>
