# Simple script to fix the "Unknown property alternate-row-colors" error
with open('trading_ui_connected.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Replace the problematic property
fixed_content = content.replace('alternate-row-colors: true;', '')

with open('trading_ui_connected.py', 'w', encoding='utf-8') as file:
    file.write(fixed_content)

print("Fixed alternate-row-colors property in trading_ui_connected.py") 