<?php
require_once __DIR__ . '/auth.php';
requireLogin();
$db = getDB();

// Date range
$dateFrom = trim(isset($_GET['date_from']) ? $_GET['date_from'] : date('Y-m-d', strtotime('-30 days')));
$dateTo = trim(isset($_GET['date_to']) ? $_GET['date_to'] : date('Y-m-d'));

// Daily sessions trend
$daily = $db->prepare("SELECT DATE(started_at) as day, COUNT(*) as cnt FROM sessions WHERE DATE(started_at) BETWEEN ? AND ? GROUP BY day ORDER BY day");
$daily->execute([$dateFrom, $dateTo]);
$dailyData = $daily->fetchAll();
$dailyLabels = array_map(function($r) { return $r['day']; }, $dailyData);
$dailyValues = array_map(function($r) { return (int)$r['cnt']; }, $dailyData);

// Hourly distribution
$hourly = $db->prepare("SELECT HOUR(started_at) as hr, COUNT(*) as cnt FROM sessions WHERE DATE(started_at) BETWEEN ? AND ? GROUP BY hr ORDER BY hr");
$hourly->execute([$dateFrom, $dateTo]);
$hourlyData = $hourly->fetchAll();
$hourlyLabels = array_map(function($r) { return str_pad($r['hr'], 2, '0', STR_PAD_LEFT) . ':00'; }, $hourlyData);
$hourlyValues = array_map(function($r) { return (int)$r['cnt']; }, $hourlyData);

// Device types
$devStmt = $db->prepare("SELECT device_type, COUNT(*) as cnt FROM sessions WHERE DATE(started_at) BETWEEN ? AND ? GROUP BY device_type ORDER BY cnt DESC");
$devStmt->execute([$dateFrom, $dateTo]);
$devData = $devStmt->fetchAll();
$devLabels = array_map(function($r) { return ucfirst(isset($r['device_type']) ? $r['device_type'] : 'unknown'); }, $devData);
$devValues = array_map(function($r) { return (int)$r['cnt']; }, $devData);

// Browsers
$brStmt = $db->prepare("SELECT browser, COUNT(*) as cnt FROM sessions WHERE DATE(started_at) BETWEEN ? AND ? AND browser IS NOT NULL GROUP BY browser ORDER BY cnt DESC LIMIT 10");
$brStmt->execute([$dateFrom, $dateTo]);
$brData = $brStmt->fetchAll();
$brLabels = array_map(function($r) { return $r['browser']; }, $brData);
$brValues = array_map(function($r) { return (int)$r['cnt']; }, $brData);

// OS versions
$osStmt = $db->prepare("SELECT os, COUNT(*) as cnt FROM sessions WHERE DATE(started_at) BETWEEN ? AND ? AND os IS NOT NULL GROUP BY os ORDER BY cnt DESC LIMIT 10");
$osStmt->execute([$dateFrom, $dateTo]);
$osData = $osStmt->fetchAll();
$osLabels = array_map(function($r) { return $r['os']; }, $osData);
$osValues = array_map(function($r) { return (int)$r['cnt']; }, $osData);

// Top countries
$cStmt = $db->prepare("SELECT country, COUNT(*) as cnt FROM sessions WHERE DATE(started_at) BETWEEN ? AND ? AND country IS NOT NULL AND country != '' GROUP BY country ORDER BY cnt DESC LIMIT 15");
$cStmt->execute([$dateFrom, $dateTo]);
$cData = $cStmt->fetchAll();
$cLabels = array_map(function($r) { return $r['country']; }, $cData);
$cValues = array_map(function($r) { return (int)$r['cnt']; }, $cData);

// Avg duration trend
$durStmt = $db->prepare("SELECT DATE(started_at) as day, AVG(duration_seconds) as avg_dur FROM sessions WHERE DATE(started_at) BETWEEN ? AND ? AND duration_seconds IS NOT NULL GROUP BY day ORDER BY day");
$durStmt->execute([$dateFrom, $dateTo]);
$durData = $durStmt->fetchAll();
$durLabels = array_map(function($r) { return $r['day']; }, $durData);
$durValues = array_map(function($r) { return round($r['avg_dur']); }, $durData);

// Export CSV
if (isset($_GET['export']) && $_GET['export'] === 'csv') {
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="analytics_' . $dateFrom . '_' . $dateTo . '.csv"');
    $out = fopen('php://output', 'w');
    fputcsv($out, ['Session ID', 'User Name', 'Email', 'Country', 'City', 'Device', 'Browser', 'OS', 'Duration (s)', 'Messages', 'Started At']);
    $expStmt = $db->prepare("SELECT * FROM sessions WHERE DATE(started_at) BETWEEN ? AND ? ORDER BY started_at DESC");
    $expStmt->execute([$dateFrom, $dateTo]);
    while ($row = $expStmt->fetch()) {
        fputcsv($out, [$row['session_id'], $row['user_name'], $row['user_email'], $row['country'], $row['city'], $row['device_type'], $row['browser'], $row['os'], $row['duration_seconds'], $row['message_count'], $row['started_at']]);
    }
    fclose($out);
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
</head>
<body>
    <?php renderNavbar('analytics'); ?>

    <div class="container-fluid mt-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4>Analytics</h4>
            <a href="?<?= http_build_query(array_merge($_GET, ['export' => 'csv'])) ?>" class="btn btn-sm btn-outline-success"><i class="bi bi-download"></i> Export CSV</a>
        </div>
        
        <!-- Date Range -->
        <form class="card border-0 shadow-sm mb-4" method="GET">
            <div class="card-body">
                <div class="row g-2 align-items-end">
                    <div class="col-md-3">
                        <label class="form-label small">From</label>
                        <input type="date" class="form-control form-control-sm" name="date_from" value="<?= escape($dateFrom) ?>">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small">To</label>
                        <input type="date" class="form-control form-control-sm" name="date_to" value="<?= escape($dateTo) ?>">
                    </div>
                    <div class="col-md-2">
                        <button type="submit" class="btn btn-sm btn-primary" style="background:#0A2A66; border-color:#0A2A66;">Apply</button>
                    </div>
                </div>
            </div>
        </form>

        <!-- Charts -->
        <div class="row g-3 mb-4">
            <div class="col-lg-8">
                <div class="card border-0 shadow-sm"><div class="card-header bg-white fw-bold">Daily Sessions</div><div class="card-body"><canvas id="dailyChart" height="80"></canvas></div></div>
            </div>
            <div class="col-lg-4">
                <div class="card border-0 shadow-sm"><div class="card-header bg-white fw-bold">Hourly Distribution</div><div class="card-body"><canvas id="hourlyChart" height="160"></canvas></div></div>
            </div>
        </div>
        
        <div class="row g-3 mb-4">
            <div class="col-lg-4">
                <div class="card border-0 shadow-sm"><div class="card-header bg-white fw-bold">Devices</div><div class="card-body"><canvas id="devChart" height="160"></canvas></div></div>
            </div>
            <div class="col-lg-4">
                <div class="card border-0 shadow-sm"><div class="card-header bg-white fw-bold">Browsers</div><div class="card-body"><canvas id="brChart" height="160"></canvas></div></div>
            </div>
            <div class="col-lg-4">
                <div class="card border-0 shadow-sm"><div class="card-header bg-white fw-bold">Operating Systems</div><div class="card-body"><canvas id="osChart" height="160"></canvas></div></div>
            </div>
        </div>
        
        <div class="row g-3 mb-4">
            <div class="col-lg-6">
                <div class="card border-0 shadow-sm"><div class="card-header bg-white fw-bold">Top Countries</div><div class="card-body"><canvas id="countryChart" height="200"></canvas></div></div>
            </div>
            <div class="col-lg-6">
                <div class="card border-0 shadow-sm"><div class="card-header bg-white fw-bold">Avg Session Duration (seconds)</div><div class="card-body"><canvas id="durChart" height="200"></canvas></div></div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
        const colors = ['#0A2A66','#28a745','#ffc107','#dc3545','#17a2b8','#6f42c1','#fd7e14','#20c997','#e83e8c','#6610f2'];
        
        new Chart(document.getElementById('dailyChart'), { type:'line', data:{ labels:<?= json_encode($dailyLabels) ?>, datasets:[{label:'Sessions', data:<?= json_encode($dailyValues) ?>, borderColor:'#0A2A66', backgroundColor:'rgba(10,42,102,0.1)', fill:true, tension:0.3}] }, options:{responsive:true, plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true, ticks:{stepSize:1}}}} });
        
        new Chart(document.getElementById('hourlyChart'), { type:'bar', data:{ labels:<?= json_encode($hourlyLabels) ?>, datasets:[{data:<?= json_encode($hourlyValues) ?>, backgroundColor:'#17a2b8'}] }, options:{responsive:true, plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true, ticks:{stepSize:1}}}} });
        
        new Chart(document.getElementById('devChart'), { type:'doughnut', data:{ labels:<?= json_encode($devLabels) ?>, datasets:[{data:<?= json_encode($devValues) ?>, backgroundColor:colors}] }, options:{responsive:true} });
        
        new Chart(document.getElementById('brChart'), { type:'doughnut', data:{ labels:<?= json_encode($brLabels) ?>, datasets:[{data:<?= json_encode($brValues) ?>, backgroundColor:colors}] }, options:{responsive:true} });
        
        new Chart(document.getElementById('osChart'), { type:'doughnut', data:{ labels:<?= json_encode($osLabels) ?>, datasets:[{data:<?= json_encode($osValues) ?>, backgroundColor:colors}] }, options:{responsive:true} });
        
        new Chart(document.getElementById('countryChart'), { type:'bar', data:{ labels:<?= json_encode($cLabels) ?>, datasets:[{data:<?= json_encode($cValues) ?>, backgroundColor:'#0A2A66'}] }, options:{responsive:true, indexAxis:'y', plugins:{legend:{display:false}}} });
        
        new Chart(document.getElementById('durChart'), { type:'line', data:{ labels:<?= json_encode($durLabels) ?>, datasets:[{label:'Avg Duration (s)', data:<?= json_encode($durValues) ?>, borderColor:'#dc3545', backgroundColor:'rgba(220,53,69,0.1)', fill:true, tension:0.3}] }, options:{responsive:true, plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true}}} });
    </script>
</body>
</html>
