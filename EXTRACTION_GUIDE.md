# 📚 Guide d'extraction PDF → TXT pour ExpoBeton RDC

## 🎯 Objectif
Convertir les PDFs de documentation ExpoBeton en fichiers texte (.txt) pour améliorer les réponses du chatbot via Cohere.

---

## 📋 Étapes rapides

### 1️⃣ Créer la structure de dossiers
```
pdf_source/
├── 2025/     ← Mettez vos PDFs 2025 ici
├── 2024/     ← Mettez vos PDFs 2024 ici
└── 2023/     ← Mettez vos PDFs 2023 ici
```

### 2️⃣ Installer PyPDF2
Double-cliquez sur: **install_pypdf2.bat**

### 3️⃣ Lancer l'extraction
Double-cliquez sur: **run_extract.bat**

Le script vous demandera quelle année extraire:
- **1** = 2025 (recommandé pour commencer)
- **2** = 2024
- **3** = 2023
- **4** = Autre année
- **5** = Tout extraire (attention: long!)

### 4️⃣ Résultat
Les fichiers .txt seront créés dans le dossier **docs/**

Le bot les utilisera automatiquement! ✅

---

## 🐳 Alternative: Utiliser Docker

Si Python n'est pas installé sur votre machine:

```bash
docker run --rm -v "F:/Louison/Layhosting/Clients/Expo beton/prod-rasa-d3f2c138:/app" -w /app python:3.10 bash -c "pip install PyPDF2 && python extract_pdfs.py"
```

---

## ⚡ Conseils

### Extraction par palier (recommandé)
1. **Commencez avec 2025** (les plus récents et pertinents)
2. **Testez le bot** avec quelques questions
3. **Ajoutez 2024, 2023** si nécessaire
4. **Archives** seulement si demandé

### Pourquoi par palier?
- ✅ Plus rapide à traiter
- ✅ Permet de tester rapidement
- ✅ Évite de surcharger le bot
- ✅ Cohere indexera plus vite

---

## 🔧 Dépannage

### "Python n'a pas été trouvé"
→ Installez Python 3.10 depuis https://python.org
→ OU utilisez Docker (voir ci-dessus)

### "Peu de texte extrait"
→ Le PDF contient probablement beaucoup d'images
→ Utilisez un outil OCR si nécessaire

### "Aucun fichier PDF trouvé"
→ Vérifiez que les PDFs sont dans pdf_source/ANNÉE/

---

## 📊 Après l'extraction

1. Les fichiers .txt sont dans **docs/**
2. **Redéployez sur Railway** pour que le bot les utilise
3. Le bot cherchera automatiquement dans ces nouveaux fichiers avec Cohere! 🎉

---

## 💡 Questions?

Le script affiche:
- ✅ Nombre de caractères extraits
- ⚠️ Avertissements si peu de texte
- ❌ Erreurs rencontrées
- 📊 Statistiques finales

Bon courage! 💪
