## Instructions du Bot ExpoBeton RDC — Flux d'Inscription & Comportement

Ce document décrit le comportement attendu du chatbot ExpoBeton RDC pour l'inscription,
l'accueil personnalisé, et la gestion des interactions utilisateur.

---

## 🧠 Mémoire utilisateur et reconnaissance

- Le bot collecte les informations suivantes via le formulaire d'inscription :
  prénom (via le slot `person`), e-mail (`reg_email`), téléphone (`reg_phone`),
  entreprise (`reg_company`), pays (`reg_country`), ville (`reg_city`),
  catégorie (`reg_category`), méthode de paiement (`reg_payment`),
  besoin de visa (`reg_visa`), historique de participation (`reg_history`).

- À chaque nouvelle conversation, le bot détecte le prénom de l'utilisateur
  à partir du message initial (ex : « Bonjour, je m'appelle Louison »).
  - **Si le prénom est détecté** :
    → Le bot le salue chaleureusement par son prénom et demande proactivement
    ce qu'il souhaite savoir sur ExpoBeton RDC.
    Exemple : *« Bonjour Louison ! 😊 Je suis ravi de vous aider.
    Comment puis-je vous renseigner sur ExpoBeton RDC aujourd'hui ? »*
  - **Si aucun prénom n'est détecté** :
    → Le bot utilise une salutation générique et propose son aide.

- Le bot **adapte la langue de ses réponses** à la langue du dernier message
  de l'utilisateur (français par défaut, anglais si l'utilisateur écrit en anglais).

---

## 📝 Réponse à « Comment participer ? »

Lorsque l'utilisateur demande comment participer (ou toute variante :
« je veux participer », « comment rejoindre », « inscription »,
« how to participate », « register ») :

1. Le bot explique les trois catégories de participation :
   - **Sponsor** (4 niveaux : Platinum 40 000$, Gold 20 000$, Silver 15 000$, Bronze 12 000$)
   - **Exposant** (3 types de stands : 3×3m à 5 000$, 2×4m à 3 000$, 2×3m à 2 000$)
   - **Participant Simple** (gratuit)

2. Il enchaîne avec :
   *« Voulez-vous que je vous guide dans l'inscription ? »*

3. **Si oui** → Lancer le processus d'enregistrement (voir ci-dessous).
   **Si non** → Ne pas insister. Proposer d'autres sujets :
   - *« Souhaitez-vous en savoir plus sur le thème de l'édition 2026 ? »*
   - *« Voulez-vous connaître les intervenants principaux ? »*
   - *« Puis-je vous aider avec autre chose ? »*

---

## ✍️ Processus d'enregistrement (inscription)

### Déclenchement
L'inscription est déclenchée par l'intent `register` via des phrases comme :
- « Je veux m'inscrire », « inscription », « register me »,
  « comment s'inscrire », « je souhaite participer »

### Accueil personnalisé
Quand l'inscription démarre, le bot salue l'utilisateur par son prénom :
*« D'accord [PRÉNOM], je vais vous aider à vous inscrire étape par étape ! 📝 »*

### Étapes du formulaire (`registration_form`)
Le bot collecte les informations suivantes, une par une :

| # | Champ | Slot | Validation |
|---|-------|------|-----------|
| 1 | Nom de l'entreprise/organisation | `reg_company` | Min. 2 caractères |
| 2 | Nom complet du contact | `reg_contact_name` | Min. 2 caractères |
| 3 | Adresse e-mail | `reg_email` | Format email valide |
| 4 | Numéro de téléphone | `reg_phone` | Min. 6 chiffres, + autorisé |
| 5 | Pays | `reg_country` | Normalise les variantes (RDC, Congo, etc.) |
| 6 | Ville | `reg_city` | Min. 2 caractères |
| 7 | Catégorie de participation | `reg_category` | Voir menu de sélection ci-dessous |
| 8 | Méthode de paiement | `reg_payment` | Chèque ou Veuillez Facturer (auto N/A pour gratuit) |
| 9 | Besoin d'assistance visa | `reg_visa` | oui / non |
| 10 | Participation antérieure à ExpoBeton | `reg_history` | oui / non |

### Sélection de catégorie (menu à 2 niveaux)
Le bot utilise un système de sous-menus numérotés :

**Menu principal :**
```
Choisissez votre catégorie :
1️⃣ Sponsor
2️⃣ Exposant
3️⃣ Participant Simple (gratuit)
```

**Si Sponsor sélectionné → sous-menu :**
```
Choisissez votre niveau de sponsoring :
1️⃣ Platinum — 40 000 $
2️⃣ Gold — 20 000 $
3️⃣ Silver — 15 000 $
4️⃣ Bronze — 12 000 $
```

**Si Exposant sélectionné → sous-menu :**
```
Choisissez votre type de stand :
1️⃣ Stand 3×3m — 5 000 $
2️⃣ Stand 2×4m — 3 000 $
3️⃣ Stand 2×3m — 2 000 $
```

L'utilisateur peut répondre par numéro (1, 2, 3…) ou par nom (Platinum, Gold, 3x3m…).
Plus de 80 variantes de saisie sont reconnues et normalisées.

### Méthode de paiement
- **Sponsors et Exposants** : Choix entre « Chèque » et « Veuillez Facturer »
- **Participant Simple** : Paiement automatiquement défini à « N/A » (gratuit)

---

## 📎 Upload de documents

Après la collecte du formulaire, le bot détermine les documents nécessaires :

| Catégorie | Logo entreprise | Document visa (passeport) |
|-----------|:-:|:-:|
| Sponsor / Exposant | ✅ Requis | Si visa = oui |
| Participant Simple | ❌ | Si visa = oui |

### Formats acceptés
- **Logo** : JPG, PNG, SVG, GIF — max 10 Mo
- **Passeport** : PDF uniquement — max 10 Mo

### Flux d'upload
1. Le bot envoie des cartes d'upload au widget (type `upload_sequence`)
2. L'utilisateur sélectionne ses fichiers via l'interface du widget
3. Le widget stocke les fichiers localement et envoie `/registration_review`
4. Le bot affiche le récapitulatif avec le statut des fichiers
5. Après confirmation, le bot soumet l'inscription à l'API
6. Le bot envoie le message `do_uploads` avec le numéro de référence
7. Le widget envoie les fichiers à `upload_documents.php?ref=REFERENCE&type=logo|passport`

---

## 🔍 Révision et confirmation (`registration_review_form`)

Après l'upload (ou s'il n'y a pas d'upload nécessaire), le bot affiche
un récapitulatif numéroté :

```
📋 Récapitulatif de votre inscription :
1. Entreprise : ACME Corp
2. Nom du contact : Louison Atundu
3. Email : louison@example.com
4. Téléphone : +243 999 000 000
5. Pays : RDC
6. Ville : Lubumbashi
7. Catégorie : Gold
8. Paiement : Veuillez Facturer
9. Visa : Non
10. Déjà participé : Oui
11. Logo : ✅ Sélectionné
12. Passeport : Non fourni

Tapez le numéro (1-12) pour modifier, ou "ok" pour confirmer.
```

### Mots-clés de confirmation acceptés :
`ok`, `oui`, `confirmer`, `c'est bon`, `valider`, `confirm`, `yes`, `c'est correct`

### Modification d'un champ :
- L'utilisateur tape un numéro (1-10) → le bot repose la question correspondante
- L'utilisateur tape 11 ou 12 → le bot renvoie la carte d'upload
- Après modification, le récapitulatif est réaffiché

---

## ✅ Soumission à l'API

Après confirmation :
1. Le bot envoie les données à `POST https://expobetonrdc.com/api_chatbot_register.php?action=register`
2. Authentification par Bearer token (`EXPOBETON_API_KEY`)
3. **En cas de succès** :
   - Le bot affiche le numéro de référence : `EXPOBETON-2026-XXXXX`
   - *« 🎉 Félicitations [PRÉNOM] ! Votre inscription est enregistrée.
     Référence : EXPOBETON-2026-XXXXX. Un email de confirmation vous sera envoyé. »*
   - Les fichiers sont envoyés via le widget
4. **En cas de doublon** (email déjà inscrit) :
   - Le bot affiche la référence existante et le statut
5. **En cas d'erreur** :
   - Le bot affiche un message d'erreur et propose de réessayer

Tous les slots sont réinitialisés après la soumission.

---

## 🌍 Candidature Ambassadeur

En plus de l'inscription classique, le bot gère les candidatures ambassadeur
(`apply_ambassador` intent) :

**Champs collectés :**
- Identité complète, genre, téléphone, email
- Entreprise, pays, ville
- Choix du think tank (parmi 8 options)
- Déclaration de contribution
- Expérience professionnelle

**Soumission** : `POST ?action=ambassador` → Référence ambassadeur renvoyée.

---

## 🧩 Gestion des scénarios

### 1. Annulation en cours d'inscription
L'utilisateur peut annuler à tout moment avec :
- `annuler`, `stop`, `cancel`, `quitter`, `arrêter`, `/stop`

Le bot répond :
*« D'accord, inscription annulée. Pas de souci ! 😊 Puis-je vous aider
avec autre chose ? »*

### 2. Erreurs de saisie pendant le formulaire
- Si la validation échoue, le bot explique l'erreur et repose la question :
  *« ❌ L'adresse email ne semble pas valide. Pouvez-vous la vérifier ? »*
- Le bot ne bloque jamais — il reformule et offre toujours une sortie

### 3. Réponses hors-sujet pendant l'inscription
- Le bot recentre gentiment sur la question en cours
- Il rappelle la possibilité d'annuler

### 4. Personnalité du bot
- Amical, professionnel, enthousiaste sans excès
- Utilise des émoticônes avec parcimonie (😊, 📝, 🎉, ✅)
- Vouvoiement par défaut
- S'adapte à la langue de l'utilisateur (français ↔ anglais)

### 5. Sortie de conversation
- Si l'utilisateur dit « au revoir », « merci », « à plus tard » :
  → Le bot demande un feedback (1-5 étoiles) dans la langue de l'utilisateur
  → Il propose de revenir à tout moment
  → Message adapté à la langue du dernier message

---

## 🔁 Résumé du flux (arbre de décision)

```
1. Arrivée utilisateur
   → Prénom détecté ? oui → Salutation personnalisée + question proactive
   → non → Salutation générique + proposition d'aide

2. Demande "comment participer"
   → Afficher les 3 catégories avec tarifs
   → Proposer l'inscription

3. Intent "register" détecté
   → ActionStartRegistration : salutation personnalisée
   → registration_form : collecte des 10 champs
     → Chaque champ validé individuellement
     → Sélection de catégorie en 2 niveaux (menu + sous-menu)
     → Paiement auto N/A pour Participant Simple

4. Formulaire complété
   → ActionSubmitRegistration : déterminer les uploads nécessaires
   → Si uploads requis → envoyer cartes d'upload au widget
   → Widget signale /registration_review quand terminé

5. Révision (registration_review_form)
   → Afficher récapitulatif numéroté (1-12)
   → Permettre modification par numéro
   → Confirmation par "ok"

6. Soumission (ActionConfirmRegistration)
   → Appel API register → Référence EXPOBETON-2026-XXXXX
   → Upload des fichiers via widget
   → Reset de tous les slots

7. Annulation à tout moment
   → Message neutre + proposition d'alternatives
```

---

## 📊 Tracking Analytics

Chaque conversation est automatiquement envoyée au tableau de bord analytics
(`https://admincb.expobetonrdc.com`) :
- **Session start** : IP, appareil, navigateur, OS, langue, referrer
- **Messages** : texte, intent détecté, score de confiance
- **Session end** : durée calculée
- **Données utilisateur** : nom et email (quand fournis) liés à la session

Le dashboard est accessible à `https://admincb.expobetonrdc.com`
avec authentification admin.
