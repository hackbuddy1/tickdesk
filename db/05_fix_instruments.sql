BEGIN;

UPDATE instruments SET name = v.name, sector = v.sector, exchange = 'NSE', currency = 'INR'
FROM (VALUES
    ('RELIANCE',   'Reliance Industries',        'Energy'),
    ('TCS',        'Tata Consultancy Services',  'Technology'),
    ('INFY',       'Infosys',                    'Technology'),
    ('WIPRO',      'Wipro',                      'Technology'),
    ('HDFCBANK',   'HDFC Bank',                  'Financials'),
    ('ICICIBANK',  'ICICI Bank',                 'Financials'),
    ('SBIN',       'State Bank of India',        'Financials'),
    ('AXISBANK',   'Axis Bank',                  'Financials'),
    ('KOTAKBANK',  'Kotak Mahindra Bank',        'Financials'),
    ('BAJFINANCE', 'Bajaj Finance',              'Financials'),
    ('BHARTIARTL', 'Bharti Airtel',              'Telecom'),
    ('HINDUNILVR', 'Hindustan Unilever',         'Consumer'),
    ('ITC',        'ITC',                        'Consumer'),
    ('NESTLEIND',  'Nestle India',               'Consumer'),
    ('TITAN',      'Titan Company',              'Consumer'),
    ('MARUTI',     'Maruti Suzuki India',        'Automobile'),
    ('TATAMOTORS', 'Tata Motors',                'Automobile'),
    ('SUNPHARMA',  'Sun Pharmaceutical',         'Healthcare'),
    ('LT',         'Larsen & Toubro',            'Industrials'),
    ('ULTRACEMCO', 'UltraTech Cement',           'Materials')
) AS v(symbol, name, sector)
WHERE instruments.symbol = v.symbol;

COMMIT;