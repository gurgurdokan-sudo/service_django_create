"""Sheetをまたいで使うExcel書き込みの共通処理"""
import textwrap
import tempfile
import subprocess
from pathlib import Path

from django.conf import settings
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

def auto_newline(text, ws, cell, line=10):
    """セル内で自動改行するためのヘルパー"""
    text = str(text)
    wrapped = "\n".join(textwrap.wrap(text, line))
    ws[cell] = wrapped
    ws[cell].alignment = Alignment(wrap_text=True, vertical="center")

def write_digits(ws, row, start_col, value, length):
    """番号を1マス1文字で書く桁数違いは帳票の欄ずれになるためエラーにする"""
    text = str(value or "").strip()
    if len(text) != length:
        raise ValueError(f"{length}桁の番号を設定してください: {text!r}")
    for i, char in enumerate(text):
        ws[f"{get_column_letter(start_col + i)}{row}"] = char

def sum_int(rows, key):
    """明細の指定キーを整数として合計する"""
    return sum(int(row.get(key) or 0) for row in rows)

def convert_xlsx_to_pdf(xlsx_input,stem: str = "document", filename="claim.xlsx"):
    """XLSXのバイト列をLibreOfficeでPDF化し、PDFのバイト列を返す。

    呼び出し側は返り値を application/pdf のHttpResponseに設定して返す。
    """
    if isinstance(xlsx_input, (str, Path)):
        xlsx_bytes = Path(xlsx_input).read_bytes()
        if stem == "document" and isinstance(xlsx_input, (str, Path)):
            stem = Path(xlsx_input).stem
    elif isinstance(xlsx_input, (bytes, bytearray, memoryview)):
        xlsx_bytes = bytes(xlsx_input)
    elif hasattr(xlsx_input, "getvalue"):  # io.BytesIO の場合
        xlsx_bytes = xlsx_input.getvalue()
    elif hasattr(xlsx_input, "read"):  # ファイル風オブジェクトの場合
        xlsx_bytes = xlsx_input.read()
    else:
        raise TypeError(
            f"bytes, Path, または str が必要です (受け取った型: {type(xlsx_input).__name__})"
        )
    # ファイル名からパス要素を除いて、一時ディレクトリ内にのみ保存する。
    stem = Path(filename).stem or "claim"

    with tempfile.TemporaryDirectory(prefix="claim_pdf_") as temp_dir:
        temp_path = Path(temp_dir)
        input_path = temp_path / f"{stem}.xlsx"
        output_dir = temp_path / "pdf"
        profile_dir = temp_path / "lo-profile"
        output_dir.mkdir()
        profile_dir.mkdir()
        input_path.write_bytes(xlsx_bytes)

        command = [
            getattr(settings, "LIBREOFFICE_BIN", "soffice"),
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless",
            "--convert-to",
            "pdf:calc_pdf_Export",
            "--outdir",
            str(output_dir),
            str(input_path),
        ]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=90,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(
                "LibreOfficeが見つからないか、PDF変換がタイムアウトしました。"
            ) from exc

        pdf_path = output_dir / f"{stem}.pdf"
        if result.returncode != 0 or not pdf_path.is_file():
            detail = (result.stderr or result.stdout).strip()
            raise RuntimeError(f"XLSXからPDFへ変換できませんでした: {detail}")

        return pdf_path.read_bytes()