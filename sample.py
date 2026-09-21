import datetime
import os

os.makedirs('data', exist_ok=True)
base_time = datetime.datetime(2026, 8, 21, 9, 15, tzinfo=datetime.UTC)
price = 2950.0

with open('data/sample.csv', 'w', encoding='utf-8') as f:
    f.write('timestamp,open,high,low,close,volume\n')
    for i in range(375):
        t = (base_time + datetime.timedelta(minutes=i)).isoformat()
        o = round(price + (i * 0.15) + (i % 3 - 1), 2)
        h = round(o + 2.50, 2)
        l = round(o - 1.80, 2)
        c = round(o + 0.75, 2)
        v = 15000 + (i * 50)
        f.write(f'{t},{o},{h},{l},{c},{v}\n')

print('Successfully generated data/sample.csv (375 candles)')