<?php
require_once __DIR__ . '/auth.php';

// Redirect if already logged in
if (isLoggedIn()) {
    header('Location: dashboard.php');
    exit;
}

// Redirect to setup if no admin exists
if (!hasAdminUsers()) {
    header('Location: setup.php');
    exit;
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';
    
    if (loginUser($username, $password)) {
        header('Location: dashboard.php');
        exit;
    } else {
        $error = 'Invalid username or password.';
    }
}

$timeout = isset($_GET['timeout']);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
</head>
<body class="bg-dark d-flex align-items-center justify-content-center" style="min-height: 100vh;">
    <div class="card shadow-lg" style="width: 100%; max-width: 420px;">
        <div class="card-body p-5">
            <div class="text-center mb-4">
                <h3 class="fw-bold" style="color: #0A2A66;">ExpoBeton RDC</h3>
                <p class="text-muted">Chatbot Analytics Dashboard</p>
            </div>
            
            <?php if ($error): ?>
                <div class="alert alert-danger"><?= escape($error) ?></div>
            <?php endif; ?>
            
            <?php if ($timeout): ?>
                <div class="alert alert-warning">Session expired. Please log in again.</div>
            <?php endif; ?>
            
            <form method="POST">
                <div class="mb-3">
                    <label for="username" class="form-label">Username</label>
                    <input type="text" class="form-control" id="username" name="username" required autofocus>
                </div>
                <div class="mb-3">
                    <label for="password" class="form-label">Password</label>
                    <input type="password" class="form-control" id="password" name="password" required>
                </div>
                <button type="submit" class="btn btn-primary w-100" style="background: #0A2A66; border-color: #0A2A66;">
                    Log In
                </button>
            </form>
        </div>
    </div>
</body>
</html>
