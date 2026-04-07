#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract Kalemie 2026 PDF"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from extract_pdfs import extract_pdf_to_txt
from pathlib import Path

# Extract Kalemie 2026 PDF
pdf_path = Path('pdf_source_2026/FR_V1_Brochure_ExpoBetonRDC_Kalemie 2026.pdf')
output_dir = Path('pdf_source_2026')

print("🚀 Extracting Kalemie 2026 brochure...")
if extract_pdf_to_txt(pdf_path, output_dir):
    print("✅ Extraction successful!")
else:
    print("❌ Extraction error")
