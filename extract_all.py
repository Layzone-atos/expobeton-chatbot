#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'extraction automatique de TOUS les PDFs
"""

import sys
import os

# Ajouter le chemin pour importer extract_pdfs
sys.path.insert(0, os.path.dirname(__file__))

from extract_pdfs import extract_folder
from pathlib import Path

def main():
    print("="*60)
    print("🚀 Extraction AUTOMATIQUE de TOUS les PDFs")
    print("="*60)
    
    workspace = Path(__file__).parent
    docs_output = workspace / "docs"
    
    # Chercher tous les dossiers pdf_source_*
    pdf_folders = sorted(workspace.glob("pdf_source_*"))
    
    if not pdf_folders:
        print(f"❌ Aucun dossier pdf_source_* trouvé!")
        return
    
    print(f"\n📚 {len(pdf_folders)} dossiers trouvés:")
    for folder in pdf_folders:
        year_name = folder.name.replace("pdf_source_", "")
        pdf_count = len(list(folder.glob("*.pdf")))
        print(f"   • {folder.name}: {pdf_count} PDFs")
    
    print(f"\n{'='*60}")
    print("🚀 DÉBUT DE L'EXTRACTION")
    print(f"{'='*60}\n")
    
    # Parcourir tous les dossiers trouvés
    for pdf_folder in pdf_folders:
        year_name = pdf_folder.name.replace("pdf_source_", "")
        print(f"\n\n{'#'*60}")
        print(f"📅 Traitement de: {pdf_folder.name} (année {year_name})")
        print(f"{'#'*60}")
        extract_folder(pdf_folder, docs_output, year_name)
    
    print(f"\n\n{'='*60}")
    print("✅ EXTRACTION COMPLÈTE TERMINÉE!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
