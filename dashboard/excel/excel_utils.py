"""Sheetをまたいで使うExcel書き込みの共通処理"""
import textwrap

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