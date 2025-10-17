COLUMNS_OPEN = ['Position', 'Open time', 'Symbol', 'Type', 'Volume', 'Open price', 'Market price', 'Purchase value', 'Swap', 'Gross P/L']
COLUMNS_CLOSED = ['Position', 'Open time', 'Symbol', 'Type', 'Volume', 'Open price', 'Close price', 'Purchase value', 'Swap', 'Gross P/L']  # can add close time/price
COLUMNS_CASH = ['ID', 'Time', 'Symbol', 'Type', 'Amount']

TOTALS_COLS_OPEN = ['Swap', 'Gross P/L']
TOTALS_COLS_CLOSED = ['Swap', 'Gross P/L']
TOTALS_COLS_CASH = ['Amount']

OPEN_SHEET_TEMPLATE = 'OPEN POSITION {}'
CLOSED_SHEET_NAME = f'CLOSED POSITION HISTORY'
CASH_SHEET_NAME = f'CASH OPERATION HISTORY'