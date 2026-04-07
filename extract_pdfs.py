#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'extraction PDF → TXT pour ExpoBeton RDC
Extrait le texte des PDFs et crée des fichiers .txt pour le chatbot Cohere
"""

import os
import sys
from pathlib import Path
import re

try:
    import PyPDF2
except ImportError:
    print("❌ PyPDF2 n'est pas installé!")
    print("📦 Installation: pip install PyPDF2")
    sys.exit(1)

def clean_text(text):
    """Nettoie le texte extrait des PDFs"""
    # Supprime les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    # Supprime les sauts de ligne excessifs
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    # Trim
    text = text.strip()
    return text

def extract_pdf_to_txt(pdf_path, output_dir):
    """
    Extrait le texte d'un PDF et le sauvegarde en .txt
    
    Args:
        pdf_path: Chemin du fichier PDF
        output_dir: Dossier de sortie pour les .txt
    
    Returns:
        bool: True si succès, False si erreur
    """
    try:
        # Nom du fichier de sortie
        pdf_name = Path(pdf_path).stem
        txt_path = Path(output_dir) / f"{pdf_name}.txt"
        
        # Lecture du PDF
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extraction du texte de toutes les pages
            full_text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # Nettoyage du texte
            full_text = clean_text(full_text)
            
            # Vérification qu'on a bien extrait du texte
            if not full_text or len(full_text) < 50:
                print(f"  ⚠️  Peu de texte extrait ({len(full_text)} caractères)")
                return False
            
            # Sauvegarde en .txt
            with open(txt_path, 'w', encoding='utf-8') as txt_file:
                txt_file.write(full_text)
            
            print(f"  ✅ {pdf_name}.pdf → {len(full_text)} caractères")
            return True
            
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def extract_folder(source_folder, output_folder, year=None):
    """
    Extrait tous les PDFs d'un dossier
    
    Args:
        source_folder: Dossier contenant les PDFs
        output_folder: Dossier de destination pour les .txt
        year: Année optionnelle (pour préfixer les fichiers)
    """
    source_path = Path(source_folder)
    output_path = Path(output_folder)
    
    # Création du dossier de sortie
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Liste des PDFs
    pdf_files = list(source_path.glob('*.pdf'))
    
    if not pdf_files:
        print(f"❌ Aucun fichier PDF trouvé dans {source_folder}")
        return
    
    print(f"\n📚 {len(pdf_files)} fichiers PDF trouvés")
    print(f"📁 Source: {source_folder}")
    print(f"📁 Destination: {output_folder}")
    print(f"\n{'='*60}")
    
    success_count = 0
    error_count = 0
    
    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{idx}/{len(pdf_files)}] {pdf_file.name}")
        
        if extract_pdf_to_txt(pdf_file, output_path):
            success_count += 1
        else:
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Succès: {success_count}")
    print(f"❌ Erreurs: {error_count}")
    print(f"📊 Total: {len(pdf_files)}")
    print(f"\n🎉 Extraction terminée!")

def main():
    """Fonction principale"""
    print("="*60)
    print("🚀 Extraction PDF → TXT pour ExpoBeton RDC")
    print("="*60)
    
    # Chemins par défaut
    workspace = Path(__file__).parent
    
    # Menu interactif
    print("\n📋 Quelle édition voulez-vous extraire?")
    print("  1️⃣  2025 (recommandé pour commencer)")
    print("  2️⃣  2024")
    print("  3️⃣  2023")
    print("  4️⃣  Autre année")
    print("  5️⃣  Tous les dossiers pdf_source_* (attention: peut être long!)")
    
    choice = input("\n👉 Votre choix (1-5): ").strip()
    
    if choice == "1":
        year = "2025"
    elif choice == "2":
        year = "2024"
    elif choice == "3":
        year = "2023"
    elif choice == "4":
        year = input("👉 Année: ").strip()
    elif choice == "5":
        # Extraction de tous les dossiers pdf_source_*
        docs_output = workspace / "docs"
        
        # Chercher tous les dossiers pdf_source_*
        pdf_folders = list(workspace.glob("pdf_source_*"))
        
        if not pdf_folders:
            print(f"❌ Aucun dossier pdf_source_* trouvé!")
            print(f"📁 Créez des dossiers comme: pdf_source_2025, pdf_source_2024, etc.")
            return
        
        # Parcourir tous les dossiers trouvés
        for pdf_folder in sorted(pdf_folders):
            if pdf_folder.is_dir():
                year_name = pdf_folder.name.replace("pdf_source_", "")
                print(f"\n\n{'#'*60}")
                print(f"📅 Traitement de: {pdf_folder.name} (année {year_name})")
                print(f"{'#'*60}")
                extract_folder(pdf_folder, docs_output, year_name)
        return
    else:
        print("❌ Choix invalide")
        return
    
    # Chemins spécifiques - nouveau format pdf_source_ANNÉE
    source_folder = workspace / f"pdf_source_{year}"
    output_folder = workspace / "docs"
    
    # Vérification que le dossier source existe
    if not source_folder.exists():
        print(f"\n❌ Dossier introuvable: {source_folder}")
        print(f"\n📁 Créez le dossier et ajoutez vos PDFs:")
        print(f"   mkdir \"{source_folder}\"")
        return
    
    # Extraction
    extract_folder(source_folder, output_folder, year)

if __name__ == "__main__":
    main()
