"""
One-time migration script to reorganize the Google Sheet.
Ensures all tabs have correct headers matching SHEET_TABS,
reorders columns, and removes legacy/extra columns.

Run: cd backend && python -m scripts.migrate_sheet
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
        sys.exit(1)

    client = get_client()
    spreadsheet = client.open_by_key(sheet_id)

    for tab_name, expected_headers in SHEET_TABS.items():
        print(f"\n--- {tab_name} ---")
        try:
            ws = spreadsheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"  Creating tab '{tab_name}' with headers: {expected_headers}")
            ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(expected_headers) + 5)
            ws.update("A1", [expected_headers])
            continue

        all_values = ws.get_all_values()
        if not all_values:
            print("  Empty tab, writing headers only")
            ws.update("A1", [expected_headers])
            continue

        current_headers = [h.strip() for h in all_values[0]]
        data_rows = all_values[1:]

        # Filter out completely empty rows
        data_rows = [row for row in data_rows if any(cell.strip() for cell in row)]

        print(f"  Current columns ({len(current_headers)}): {current_headers}")
        print(f"  Expected columns ({len(expected_headers)}): {expected_headers}")
        print(f"  Data rows: {len(data_rows)}")

        extra = [h for h in current_headers if h not in expected_headers]
        missing = [h for h in expected_headers if h not in current_headers]
        if extra:
            print(f"  EXTRA columns (will be dropped): {extra}")
        if missing:
            print(f"  MISSING columns (will be added empty): {missing}")

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

        # Resize worksheet if needed
        needed_cols = len(expected_headers) + 5
        current_cols = ws.col_count
        if needed_cols > current_cols:
            ws.resize(cols=needed_cols)

        # Clear everything and rewrite
        # First resize rows to fit
        needed_rows = len(new_rows) + 1  # +1 for header
        if needed_rows > ws.row_count:
            ws.resize(rows=needed_rows + 100)

        # Clear existing data
        if all_values:
            ws.clear()

        # Write header + data
        if new_rows:
            ws.update("A1", [expected_headers] + new_rows, value_input_option="USER_ENTERED")
        else:
            ws.update("A1", [expected_headers])

        # Trim excess rows
        ws.resize(rows=max(needed_rows + 10, 20))

        print(f"  DONE: {len(expected_headers)} columns, {len(new_rows)} rows")

    # Handle legacy 'budgets' tab - keep it but note it
    print(f"\n--- legacy_check ---")
    for tab_name in [ws.title for ws in spreadsheet.worksheets()]:
        if tab_name not in SHEET_TABS:
            print(f"  WARNING: Tab '{tab_name}' exists in sheet but not in SHEET_TABS (keeping as-is)")

    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
