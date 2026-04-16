<?php
/**
 * ExpoBeton RDC - Chatbot Analytics Dashboard Configuration
 * 
 * IMPORTANT: Update the database credentials below after creating
 * the MySQL database on your cPanel.
 */

// ============================================================
// DATABASE CONFIGURATION
// ============================================================
// Update these values after creating the database in cPanel:
//   1. Go to cPanel > MySQL Databases
//   2. Create database: chatbot_analytics
//   3. Create user: chatbot_api (with strong password)
//   4. Add user to database with ALL PRIVILEGES
define('DB_HOST', 'localhost');
define('DB_NAME', 'chatbot_analytics');
define('DB_USER', 'chatbot_api');
define('DB_PASS', 'CHANGE_ME');  // <-- Set your MySQL password here

// ============================================================
// API AUTHENTICATION
// ============================================================
// Must match EXPOBETON_API_KEY in your Railway .env file
define('API_KEY', 'ebx-rasa-2026-kAlEmIe-be96bac9f905b106ed2b941dfe536b07');

// ============================================================
// APPLICATION SETTINGS
// ============================================================
define('APP_NAME', 'ExpoBeton Chatbot Dashboard');
define('APP_VERSION', '1.0.0');
define('ITEMS_PER_PAGE', 25);
define('SESSION_TIMEOUT', 3600); // 1 hour in seconds

// Timezone
date_default_timezone_set('Africa/Lubumbashi');
