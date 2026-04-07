#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extraction du PDF 2026"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from extract_pdfs import extract_pdf_to_txt
from pathlib import Path

# Extraction du PDF 2026
pdf_path = Path('pdf_source_2026/Brochure_ExpoBeton_RDC_2026.pdf')
output_dir = Path('docs')

print("🚀 Extraction de la brochure ExpoBeton 2026...")
if extract_pdf_to_txt(pdf_path, output_dir):
    print("✅ Extraction réussie!")
else:
    print("❌ Erreur d'extraction")
