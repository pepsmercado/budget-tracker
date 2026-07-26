"""
Google Sheet cleanup script.
Reorganizes all tabs: correct headers, column order, bold headers,
auto-resize columns, freeze header row, trim empty rows/columns.

Run: cd backend && GOOGLE_SHEET_ID=xxx GOOGLE_SERVICE_ACCOUNT=data.json ./venv2/bin/python -m scripts.migrate_sheet
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
from services.sheets import SHEET_TABS


def get_client():
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(
        os.environ.get("GOOGLE_SERVICE_ACCOUNT", "data.json"),
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
    )
    return gspread.authorize(creds)


def migrate():
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not sheet_id:
        print("ERROR: GOOGLE_SHEET_ID not set")
        print("Usage: GOOGLE_SHEET_ID=xxx GOOGLE_SERVICE_ACCOUNT=data.json ./venv2/bin/python -m scripts.migrate_sheet")
        sys.exit(1)

    client = get_client()
    spreadsheet = client.open_by_key(sheet_id)
    print(f"Connected to: {spreadsheet.title}\n")

    for tab_name, expected_headers in SHEET_TABS.items():
        print(f"=== {tab_name} ===")
        try:
            ws = spreadsheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"  Creating new tab...")
            ws = spreadsheet.add_worksheet(title=tab_name, rows=50, cols=len(expected_headers) + 2)
            ws.update("A1", [expected_headers])
            _format_header(ws, len(expected_headers))
            ws.freeze(rows=1)
            print(f"  Created with {len(expected_headers)} columns")
            continue

        all_values = ws.get_all_values()
        if not all_values:
            print("  Empty tab, writing headers only")
            ws.update("A1", [expected_headers])
            _format_header(ws, len(expected_headers))
            ws.freeze(rows=1)
            continue

        current_headers = [h.strip() for h in all_values[0]]
        data_rows = all_values[1:]

        # Filter out completely empty rows
        data_rows = [row for row in data_rows if any(cell.strip() for cell in row)]
        # Also trim trailing empty cells from each row
        while data_rows and all(c == "" for c in data_rows[-1]):
            data_rows.pop()

        print(f"  Before: {len(current_headers)} columns, {len(data_rows)} rows")
        print(f"  Headers: {current_headers}")

        # Build new data with correct column order
        old_index = {h: i for i, h in enumerate(current_headers)}
        new_rows = []
        for row in data_rows:
            new_row = []
            for h in expected_headers:
                if h in old_index:
                    idx = old_index[h]
                    new_row.append(row[idx] if idx < len(row) else "")
                else:
                    new_row.append("")
            new_rows.append(new_row)

        # Resize to fit exactly
        total_rows = len(new_rows) + 1  # +1 header
        total_cols = len(expected_headers)

        # Resize first (larger) then clear
        ws.resize(rows=total_rows + 50, cols=total_cols + 2)
        ws.clear()

        # Write header + all data in one batch
        all_data = [expected_headers] + new_rows
        ws.update(range_name="A1", values=all_data, value_input_option="USER_ENTERED")

        # Trim to exact size + small buffer
        ws.resize(rows=max(total_rows + 5, 20), cols=total_cols)

        # Format
        _format_header(ws, total_cols)
        ws.freeze(rows=1)

        print(f"  After:  {total_cols} columns, {len(new_rows)} rows")
        print(f"  Headers: {expected_headers}")
        print()

    # Check for extra tabs
    code_tabs = set(SHEET_TABS.keys())
    sheet_tabs = {ws.title for ws in spreadsheet.worksheets()}
    extra_tabs = sheet_tabs - code_tabs
    if extra_tabs:
        print(f"=== Extra tabs (not in app code, keeping as-is) ===")
        for t in sorted(extra_tabs):
            print(f"  - {t}")

    print("\nDone! Open the sheet to verify.")


def _format_header(ws, num_cols):
    """Bold header row with light background."""
    end_col = gspread.utils.rowcol_to_a1(1, num_cols)
    fmt = {
        "textFormat": {"bold": True, "fontSize": 10},
        "backgroundColor": {"red": 0.93, "green": 0.95, "blue": 0.93},
    }
    ws.format(f"A1:{end_col}", fmt)


if __name__ == "__main__":
    migrate()
