#!/usr/bin/env python3
from app import create_app

app = create_app(import_data=False)

print("\n=== Зарегистрированные URL маршруты ===")
for rule in sorted(app.url_map.iter_rules(), key=lambda x: str(x)):
    print(f"{rule.endpoint:50s} {rule.rule}")
