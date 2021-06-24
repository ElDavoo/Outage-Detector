import gspread


class GSheet:
    def __init__(self, file, doc):
        client = gspread.service_account(file)
        self.sheet = client.open_by_key(doc).sheet1

    def append(self, row):
        self.sheet.append_row(row)
