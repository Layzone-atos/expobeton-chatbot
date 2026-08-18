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
$unresolvedOnly = !empty($_GET['unresolved']);

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
if ($unresolvedOnly) {
    $where[] = "s.is_unresolved = 1 AND s.resolved_at IS NULL";
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

// Count unresolved (for header badge)
$unresolvedCount = (int)$db->query("SELECT COUNT(*) FROM sessions WHERE is_unresolved = 1 AND resolved_at IS NULL")->fetchColumn();
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
    <?php renderNavbar('conversations'); ?>

    <div class="container-fluid mt-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="mb-0">Conversations <span class="text-muted fs-6">(<?= number_format($total) ?> total)</span></h4>
            <?php if ($unresolvedCount > 0): ?>
                <a href="?unresolved=1" class="btn btn-sm <?= $unresolvedOnly ? 'btn-warning' : 'btn-outline-warning' ?>">
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <?= $unresolvedCount ?> unresolved
                </a>
            <?php endif; ?>
        </div>
        
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
                                <?php $cc = getCountryCode($c); ?>
                                <option value="<?= escape($c) ?>" <?= $country === $c ? 'selected' : '' ?>><?= $cc ? strtoupper($cc) : '' ?> <?= escape($c) ?></option>
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
                <div class="row mt-2">
                    <div class="col-12">
                        <div class="form-check form-check-inline">
                            <input class="form-check-input" type="checkbox" name="unresolved" id="flt_unresolved" value="1" <?= $unresolvedOnly ? 'checked' : '' ?>>
                            <label class="form-check-label small" for="flt_unresolved">
                                <i class="bi bi-exclamation-triangle-fill text-warning"></i>
                                Show only <strong>unresolved</strong> conversations (user left without a satisfactory answer)
                            </label>
                        </div>
                    </div>
                </div>
            </div>
        </form>

        <!-- Bulk export bar -->
        <form id="bulkExportForm" method="POST" action="export_conversations.php" target="_blank" class="card border-0 shadow-sm mb-3">
            <div class="card-body py-2 d-flex flex-wrap align-items-center gap-2">
                <span class="small text-muted me-2">
                    <i class="bi bi-download"></i>
                    <span id="selectedCountLabel">0</span> selected
                </span>
                <div class="vr d-none d-md-block"></div>
                <label class="small text-muted mb-0 me-1">Format:</label>
                <select name="format" class="form-select form-select-sm" style="width:auto;" id="exportFormat">
                    <option value="csv">CSV (Excel)</option>
                    <option value="json">JSON</option>
                    <option value="pdf">PDF (print)</option>
                </select>
                <button type="submit" id="exportSelectedBtn" class="btn btn-sm btn-primary" style="background:#0A2A66;border-color:#0A2A66;" disabled>
                    <i class="bi bi-download"></i> Export selected
                </button>
                <button type="button" id="exportAllPageBtn" class="btn btn-sm btn-outline-primary" title="Select every conversation visible on this page and export them">
                    <i class="bi bi-collection"></i> Select all on page &amp; export
                </button>
                <span class="ms-auto text-muted small">
                    <i class="bi bi-info-circle"></i>
                    PDF opens a print-friendly page — choose <em>Save as PDF</em> in the browser dialog.
                </span>
            </div>
            <!-- Hidden ids[] are injected by JS on submit -->
            <div id="exportIdsContainer"></div>
        </form>

        <!-- Table -->
        <div class="card border-0 shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover mb-0">
                    <thead class="table-light">
                        <tr>
                            <th style="width:36px;">
                                <input class="form-check-input" type="checkbox" id="selectAllRows" title="Select all on this page">
                            </th>
                            <th>Status</th>
                            <th>Session</th>
                            <th>User</th>
                            <th>Country</th>
                            <th>Device</th>
                            <th>Browser</th>
                            <th>Messages</th>
                            <th>Duration</th>
                            <th>Date</th>
                            <th style="width:64px;"></th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($sessions as $s): ?>
                        <?php
                            $isUnresolved = !empty($s['is_unresolved']) && empty($s['resolved_at']);
                            $isResolved = !empty($s['resolved_at']);
                            $rowStyle = $isUnresolved ? 'background-color:#fff7e6;' : '';
                        ?>
                        <tr class="conv-row" data-session-id="<?= escape($s['session_id']) ?>" style="<?= $rowStyle ?>">
                            <td onclick="event.stopPropagation();">
                                <input class="form-check-input row-check" type="checkbox" value="<?= escape($s['session_id']) ?>" aria-label="Select conversation">
                            </td>
                            <td>
                                <?php if ($isUnresolved): ?>
                                    <span class="badge bg-warning text-dark" title="User left without satisfactory answer"><i class="bi bi-exclamation-triangle-fill"></i> Unresolved</span>
                                <?php elseif ($isResolved): ?>
                                    <span class="badge bg-success" title="Admin replied by email"><i class="bi bi-envelope-check"></i> Replied</span>
                                <?php else: ?>
                                    <span class="badge bg-light text-muted">OK</span>
                                <?php endif; ?>
                            </td>
                            <td class="text-truncate" style="max-width:120px;cursor:pointer;" title="<?= escape($s['session_id']) ?>" onclick="window.location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'"><?= escape(substr($s['session_id'], 0, 20)) ?>...</td>
                            <td style="cursor:pointer;" onclick="window.location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'"><?= escape($s['user_name'] ?: ($s['user_email'] ?: '-')) ?></td>
                            <td style="cursor:pointer;" onclick="window.location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'"><?= formatCountryWithFlag($s['country'] ?? '-') ?></td>
                            <td style="cursor:pointer;" onclick="window.location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'"><span class="badge bg-<?= $s['device_type']==='mobile'?'success':($s['device_type']==='tablet'?'warning':'primary') ?>"><?= escape($s['device_type'] ?? '-') ?></span></td>
                            <td style="cursor:pointer;" onclick="window.location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'"><?= escape($s['browser'] ?? '-') ?></td>
                            <td style="cursor:pointer;" onclick="window.location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'"><?= $s['real_message_count'] ?: $s['message_count'] ?></td>
                            <td style="cursor:pointer;" onclick="window.location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'"><?= formatDuration($s['duration_seconds']) ?></td>
                            <td style="cursor:pointer;" onclick="window.location.href='conversation_detail.php?id=<?= urlencode($s['session_id']) ?>'"><?= date('M j, H:i', strtotime($s['started_at'])) ?></td>
                            <td class="text-end" onclick="event.stopPropagation();">
                                <div class="dropdown">
                                    <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="dropdown" title="Export this conversation">
                                        <i class="bi bi-download"></i>
                                    </button>
                                    <ul class="dropdown-menu dropdown-menu-end">
                                        <li><a class="dropdown-item small" target="_blank" href="export_conversations.php?format=csv&amp;id=<?= urlencode($s['session_id']) ?>"><i class="bi bi-filetype-csv"></i> CSV</a></li>
                                        <li><a class="dropdown-item small" target="_blank" href="export_conversations.php?format=json&amp;id=<?= urlencode($s['session_id']) ?>"><i class="bi bi-filetype-json"></i> JSON</a></li>
                                        <li><a class="dropdown-item small" target="_blank" href="export_conversations.php?format=pdf&amp;id=<?= urlencode($s['session_id']) ?>"><i class="bi bi-filetype-pdf"></i> PDF</a></li>
                                    </ul>
                                </div>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                        <?php if (empty($sessions)): ?>
                        <tr><td colspan="11" class="text-center text-muted py-4">No conversations found</td></tr>
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
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    // ----- Bulk export wiring -----
    (function () {
        const form           = document.getElementById('bulkExportForm');
        const idsContainer   = document.getElementById('exportIdsContainer');
        const exportBtn      = document.getElementById('exportSelectedBtn');
        const exportAllBtn   = document.getElementById('exportAllPageBtn');
        const formatSel      = document.getElementById('exportFormat');
        const selectAll      = document.getElementById('selectAllRows');
        const selectedLabel  = document.getElementById('selectedCountLabel');
        const checks         = () => Array.from(document.querySelectorAll('.row-check'));

        function selectedIds() {
            return checks().filter(c => c.checked).map(c => c.value);
        }

        function refreshState() {
            const sel = selectedIds();
            selectedLabel.textContent = sel.length;
            exportBtn.disabled = sel.length === 0;

            const all = checks();
            if (all.length === 0) {
                selectAll.indeterminate = false;
                selectAll.checked = false;
            } else if (sel.length === all.length) {
                selectAll.indeterminate = false;
                selectAll.checked = true;
            } else if (sel.length === 0) {
                selectAll.indeterminate = false;
                selectAll.checked = false;
            } else {
                selectAll.indeterminate = true;
            }
        }

        function injectIds(ids) {
            idsContainer.innerHTML = '';
            ids.forEach(id => {
                const i = document.createElement('input');
                i.type = 'hidden';
                i.name = 'ids[]';
                i.value = id;
                idsContainer.appendChild(i);
            });
        }

        // Per-row checkbox change
        checks().forEach(c => c.addEventListener('change', refreshState));

        // Select-all header checkbox
        selectAll.addEventListener('change', function () {
            const v = this.checked;
            checks().forEach(c => { c.checked = v; });
            refreshState();
        });

        // Submit bulk export
        form.addEventListener('submit', function (e) {
            const ids = selectedIds();
            if (ids.length === 0) {
                e.preventDefault();
                alert('Please select at least one conversation to export.');
                return;
            }
            injectIds(ids);
        });

        // "Select all on page & export" shortcut
        exportAllBtn.addEventListener('click', function () {
            const all = checks();
            if (all.length === 0) {
                alert('There are no conversations on this page to export.');
                return;
            }
            all.forEach(c => { c.checked = true; });
            refreshState();
            // Trigger the form submission programmatically so hidden fields get injected
            form.requestSubmit ? form.requestSubmit() : form.submit();
        });

        refreshState();
    })();
</script>
</body>
</html>
