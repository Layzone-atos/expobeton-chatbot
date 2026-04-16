<?php
require_once __DIR__ . '/auth.php';
requireLogin();
$db = getDB();

// KPI data
$totalSessions = $db->query("SELECT COUNT(*) FROM sessions")->fetchColumn();
$todaySessions = $db->query("SELECT COUNT(*) FROM sessions WHERE DATE(started_at) = CURDATE()")->fetchColumn();
$totalMessages = $db->query("SELECT COUNT(*) FROM messages")->fetchColumn();
$uniqueUsers = $db->query("SELECT COUNT(*) FROM users")->fetchColumn();
$avgDuration = $db->query("SELECT COALESCE(AVG(duration_seconds), 0) FROM sessions WHERE duration_seconds IS NOT NULL")->fetchColumn();

// Sessions per day (last 30 days)
$dailyData = $db->query("SELECT DATE(started_at) as day, COUNT(*) as cnt FROM sessions WHERE started_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) GROUP BY day ORDER BY day")->fetchAll();
$chartLabels = array_map(fn($r) => $r['day'], $dailyData);
$chartValues = array_map(fn($r) => (int)$r['cnt'], $dailyData);

// Device breakdown
$devices = $db->query("SELECT device_type, COUNT(*) as cnt FROM sessions GROUP BY device_type ORDER BY cnt DESC")->fetchAll();
$deviceLabels = array_map(fn($r) => ucfirst($r['device_type'] ?? 'unknown'), $devices);
$deviceValues = array_map(fn($r) => (int)$r['cnt'], $devices);

// Top countries
$countries = $db->query("SELECT country, COUNT(*) as cnt FROM sessions WHERE country IS NOT NULL AND country != '' GROUP BY country ORDER BY cnt DESC LIMIT 10")->fetchAll();
$countryLabels = array_map(fn($r) => $r['country'], $countries);
$countryValues = array_map(fn($r) => (int)$r['cnt'], $countries);

// Recent conversations
$recent = $db->query("SELECT session_id, user_name, user_email, country, device_type, duration_seconds, message_count, started_at FROM sessions ORDER BY started_at DESC LIMIT 20")->fetchAll();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
</head>
<body>
    <!-- Navbar -->
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
        <!-- KPI Cards -->
        <div class="row g-3 mb-4">
            <div class="col-md col-6">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-body text-center">
                        <div class="text-muted small">Total Sessions</div>
                        <div class="fs-2 fw-bold" style="color:#0A2A66;"><?= number_format($totalSessions) ?></div>
                    </div>
                </div>
            </div>
            <div class="col-md col-6">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-body text-center">
                        <div class="text-muted small">Today</div>
                        <div class="fs-2 fw-bold text-success"><?= number_format($todaySessions) ?></div>
                    </div>
                </div>
            </div>
            <div class="col-md col-6">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-body text-center">
                        <div class="text-muted small">Total Messages</div>
                        <div class="fs-2 fw-bold text-info"><?= number_format($totalMessages) ?></div>
                    </div>
                </div>
            </div>
            <div class="col-md col-6">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-body text-center">
                        <div class="text-muted small">Unique Users</div>
                        <div class="fs-2 fw-bold text-warning"><?= number_format($uniqueUsers) ?></div>
                    </div>
                </div>
            </div>
            <div class="col-md col-6">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-body text-center">
                        <div class="text-muted small">Avg Duration</div>
                        <div class="fs-2 fw-bold text-danger"><?= formatDuration(round($avgDuration)) ?></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Charts Row -->
        <div class="row g-3 mb-4">
            <div class="col-lg-8">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold">Sessions (Last 30 Days)</div>
                    <div class="card-body">
                        <canvas id="sessionsChart" height="80"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold">Device Types</div>
                    <div class="card-body">
                        <canvas id="devicesChart" height="160"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row g-3 mb-4">
            <div class="col-lg-5">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold">Top Countries</div>
                    <div class="card-body">
                        <canvas id="countriesChart" height="160"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-lg-7">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold">Recent Conversations</div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th>User</th>
                                        <th>Country</th>
                                        <th>Device</th>
                                        <th>Messages</th>
                                        <th>Duration</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php foreach ($recent as $s): ?>
                                    <tr style="cursor:pointer;" onclick="location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'">
                                        <td><?= escape($s['user_name'] ?: ($s['user_email'] ?: substr($s['session_id'], 0, 15) . '...')) ?></td>
                                        <td><?= escape($s['country'] ?? '-') ?></td>
                                        <td><span class="badge bg-<?= $s['device_type']==='mobile'?'success':($s['device_type']==='tablet'?'warning':'primary') ?>"><?= escape($s['device_type'] ?? 'unknown') ?></span></td>
                                        <td><?= $s['message_count'] ?></td>
                                        <td><?= formatDuration($s['duration_seconds']) ?></td>
                                        <td><?= date('M j, H:i', strtotime($s['started_at'])) ?></td>
                                    </tr>
                                    <?php endforeach; ?>
                                    <?php if (empty($recent)): ?>
                                    <tr><td colspan="6" class="text-center text-muted py-4">No conversations yet</td></tr>
                                    <?php endif; ?>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
        // Sessions line chart
        new Chart(document.getElementById('sessionsChart'), {
            type: 'line',
            data: {
                labels: <?= json_encode($chartLabels) ?>,
                datasets: [{
                    label: 'Sessions',
                    data: <?= json_encode($chartValues) ?>,
                    borderColor: '#0A2A66',
                    backgroundColor: 'rgba(10,42,102,0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        });
        
        // Devices pie chart
        new Chart(document.getElementById('devicesChart'), {
            type: 'doughnut',
            data: {
                labels: <?= json_encode($deviceLabels) ?>,
                datasets: [{
                    data: <?= json_encode($deviceValues) ?>,
                    backgroundColor: ['#0A2A66', '#28a745', '#ffc107', '#dc3545', '#17a2b8']
                }]
            },
            options: { responsive: true }
        });
        
        // Countries bar chart
        new Chart(document.getElementById('countriesChart'), {
            type: 'bar',
            data: {
                labels: <?= json_encode($countryLabels) ?>,
                datasets: [{
                    label: 'Sessions',
                    data: <?= json_encode($countryValues) ?>,
                    backgroundColor: '#0A2A66'
                }]
            },
            options: { responsive: true, indexAxis: 'y', plugins: { legend: { display: false } } }
        });
    </script>
</body>
</html>
