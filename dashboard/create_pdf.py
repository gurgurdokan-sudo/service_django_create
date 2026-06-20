import subprocess
import os

def convert_excel_to_pdf(excel_path, pdf_path):
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", os.path.dirname(pdf_path),
        excel_path
    ]
    subprocess.run(cmd, check=True)
