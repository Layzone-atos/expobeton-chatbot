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
define('DB_NAME', 'expobetonrdc_admincb');
define('DB_USER', 'expobetonrdc_admincb');
define('DB_PASS', '5NOLnwx&WPbS');

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

// ============================================================
// COUNTRY FLAG HELPER
// ============================================================
// Maps country names (French) to flag emoji + ISO code
function getCountryFlag($countryName) {
    static $map = [
        'Afrique du Sud' => '🇿🇦', 'Afghanistan' => '🇦🇫', 'Albanie' => '🇦🇱', 'Algérie' => '🇩🇿',
        'Allemagne' => '🇩🇪', 'Andorre' => '🇦🇩', 'Angola' => '🇦🇴', 'Arabie Saoudite' => '🇸🇦',
        'Argentine' => '🇦🇷', 'Arménie' => '🇦🇲', 'Australie' => '🇦🇺', 'Autriche' => '🇦🇹',
        'Azerbaïdjan' => '🇦🇿', 'Bahamas' => '🇧🇸', 'Bahreïn' => '🇧🇭', 'Bangladesh' => '🇧🇩',
        'Belgique' => '🇧🇪', 'Bénin' => '🇧🇯', 'Biélorussie' => '🇧🇾', 'Bolivie' => '🇧🇴',
        'Bosnie-Herzégovine' => '🇧🇦', 'Botswana' => '🇧🇼', 'Brésil' => '🇧🇷', 'Burkina Faso' => '🇧🇫',
        'Burundi' => '🇧🇮', 'Cambodge' => '🇰🇭', 'Cameroun' => '🇨🇲', 'Canada' => '🇨🇦',
        'Chili' => '🇨🇱', 'Chine' => '🇨🇳', 'Chypre' => '🇨🇾', 'Colombie' => '🇨🇴',
        'Comores' => '🇰🇲', 'Congo' => '🇨🇬', 'Corée du Nord' => '🇰🇵', 'Corée du Sud' => '🇰🇷',
        'Costa Rica' => '🇨🇷', "Côte d'Ivoire" => '🇨🇮', 'Croatie' => '🇭🇷', 'Cuba' => '🇨🇺',
        'Danemark' => '🇩🇰', 'Djibouti' => '🇩🇯', 'Égypte' => '🇪🇬', 'Émirats arabes unis' => '🇦🇪',
        'Équateur' => '🇪🇨', 'Érythrée' => '🇪🇷', 'Espagne' => '🇪🇸', 'Estonie' => '🇪🇪',
        'États-Unis' => '🇺🇸', 'Éthiopie' => '🇪🇹', 'Fidji' => '🇫🇯', 'Finlande' => '🇫🇮',
        'France' => '🇫🇷', 'Gabon' => '🇬🇦', 'Gambie' => '🇬🇲', 'Géorgie' => '🇬🇪',
        'Ghana' => '🇬🇭', 'Grèce' => '🇬🇷', 'Guatemala' => '🇬🇹', 'Guinée' => '🇬🇳',
        'Guinée équatoriale' => '🇬🇶', 'Guinée-Bissau' => '🇬🇼', 'Haïti' => '🇭🇹',
        'Honduras' => '🇭🇳', 'Hongrie' => '🇭🇺', 'Inde' => '🇮🇳', 'Indonésie' => '🇮🇩',
        'Irak' => '🇮🇶', 'Iran' => '🇮🇷', 'Irlande' => '🇮🇪', 'Islande' => '🇮🇸',
        'Israël' => '🇮🇱', 'Italie' => '🇮🇹', 'Jamaïque' => '🇯🇲', 'Japon' => '🇯🇵',
        'Jordanie' => '🇯🇴', 'Kazakhstan' => '🇰🇿', 'Kenya' => '🇰🇪', 'Kirghizistan' => '🇰🇬',
        'Koweït' => '🇰🇼', 'Laos' => '🇱🇦', 'Lesotho' => '🇱🇸', 'Lettonie' => '🇱🇻',
        'Liban' => '🇱🇧', 'Liberia' => '🇱🇷', 'Liechtenstein' => '🇱🇮', 'Libye' => '🇱🇾',
        'Lituanie' => '🇱🇹', 'Luxembourg' => '🇱🇺', 'Madagascar' => '🇲🇬', 'Malaisie' => '🇲🇾',
        'Malawi' => '🇲🇼', 'Maldives' => '🇲🇻', 'Mali' => '🇲🇱', 'Malte' => '🇲🇹',
        'Maroc' => '🇲🇦', 'Maurice' => '🇲🇺', 'Mauritanie' => '🇲🇷', 'Mexique' => '🇲🇽',
        'Moldavie' => '🇲🇩', 'Monaco' => '🇲🇨', 'Mongolie' => '🇲🇳', 'Monténégro' => '🇲🇪',
        'Mozambique' => '🇲🇿', 'Myanmar' => '🇲🇲', 'Namibie' => '🇳🇦', 'Népal' => '🇳🇵',
        'Nicaragua' => '🇳🇮', 'Niger' => '🇳🇪', 'Nigeria' => '🇳🇬', 'Norvège' => '🇳🇴',
        'Nouvelle-Zélande' => '🇳🇿', 'Oman' => '🇴🇲', 'Ouganda' => '🇺🇬', 'Ouzbékistan' => '🇺🇿',
        'Pakistan' => '🇵🇰', 'Panama' => '🇵🇦', 'Papouasie-Nouvelle-Guinée' => '🇵🇬',
        'Paraguay' => '🇵🇾', 'Pays-Bas' => '🇳🇱', 'Pérou' => '🇵🇪', 'Philippines' => '🇵🇭',
        'Pologne' => '🇵🇱', 'Portugal' => '🇵🇹', 'Qatar' => '🇶🇦',
        'République Centrafricaine' => '🇨🇫', 'République Démocratique du Congo' => '🇨🇩',
        'République Dominicaine' => '🇩🇴', 'République Tchèque' => '🇨🇿',
        'Roumanie' => '🇷🇴', 'Royaume-Uni' => '🇬🇧', 'Russie' => '🇷🇺', 'Rwanda' => '🇷🇼',
        'Salvador' => '🇸🇻', 'São Tomé-et-Príncipe' => '🇸🇹', 'Sénégal' => '🇸🇳',
        'Serbie' => '🇷🇸', 'Seychelles' => '🇸🇨', 'Sierra Leone' => '🇸🇱', 'Singapour' => '🇸🇬',
        'Slovaquie' => '🇸🇰', 'Slovénie' => '🇸🇮', 'Somalie' => '🇸🇴', 'Soudan' => '🇸🇩',
        'Soudan du Sud' => '🇸🇸', 'Sri Lanka' => '🇱🇰', 'Suède' => '🇸🇪', 'Suisse' => '🇨🇭',
        'Suriname' => '🇸🇷', 'Syrie' => '🇸🇾', 'Tadjikistan' => '🇹🇯', 'Taïwan' => '🇹🇼',
        'Tanzanie' => '🇹🇿', 'Tchad' => '🇹🇩', 'Thaïlande' => '🇹🇭', 'Togo' => '🇹🇬',
        'Trinité-et-Tobago' => '🇹🇹', 'Tunisie' => '🇹🇳', 'Turkménistan' => '🇹🇲',
        'Turquie' => '🇹🇷', 'Ukraine' => '🇺🇦', 'Uruguay' => '🇺🇾', 'Venezuela' => '🇻🇪',
        'Vietnam' => '🇻🇳', 'Yémen' => '🇾🇪', 'Zambie' => '🇿🇲', 'Zimbabwe' => '🇿🇼',
        // English country names from geolocation API
        'South Africa' => '🇿🇦', 'Algeria' => '🇩🇿', 'Germany' => '🇩🇪', 'Saudi Arabia' => '🇸🇦',
        'Australia' => '🇦🇺', 'Austria' => '🇦🇹', 'Belgium' => '🇧🇪', 'Brazil' => '🇧🇷',
        'Cameroon' => '🇨🇲', 'China' => '🇨🇳', 'Colombia' => '🇨🇴', 'South Korea' => '🇰🇷',
        'Denmark' => '🇩🇰', 'Egypt' => '🇪🇬', 'United Arab Emirates' => '🇦🇪', 'Spain' => '🇪🇸',
        'United States' => '🇺🇸', 'Ethiopia' => '🇪🇹', 'Finland' => '🇫🇮', 'France' => '🇫🇷',
        'Ghana' => '🇬🇭', 'Greece' => '🇬🇷', 'Guinea' => '🇬🇳', 'India' => '🇮🇳',
        'Indonesia' => '🇮🇩', 'Ireland' => '🇮🇪', 'Italy' => '🇮🇹', 'Japan' => '🇯🇵',
        'Kenya' => '🇰🇪', 'Morocco' => '🇲🇦', 'Mexico' => '🇲🇽', 'Nigeria' => '🇳🇬',
        'Norway' => '🇳🇴', 'Netherlands' => '🇳🇱', 'Pakistan' => '🇵🇰', 'Philippines' => '🇵🇭',
        'Poland' => '🇵🇱', 'Portugal' => '🇵🇹', 'Democratic Republic of the Congo' => '🇨🇩',
        'Congo (DRC)' => '🇨🇩', 'Republic of the Congo' => '🇨🇬',
        'Romania' => '🇷🇴', 'United Kingdom' => '🇬🇧', 'Russia' => '🇷🇺', 'Rwanda' => '🇷🇼',
        'Senegal' => '🇸🇳', 'Singapore' => '🇸🇬', 'Sweden' => '🇸🇪', 'Switzerland' => '🇨🇭',
        'Tunisia' => '🇹🇳', 'Turkey' => '🇹🇷', 'Ukraine' => '🇺🇦',
    ];
    return $map[$countryName] ?? '🌍';
}

// Format country with flag for display
function formatCountryWithFlag($countryName) {
    if (!$countryName || $countryName === '-' || $countryName === 'Unknown' || $countryName === 'Local') {
        return '<span class="text-muted">-</span>';
    }
    $flag = getCountryFlag($countryName);
    return $flag . ' ' . htmlspecialchars($countryName);
}
