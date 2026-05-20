#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.utils.helpers import csv_to_dynamic_contacts

# Read the test CSV file
with open('test_sample.csv', 'r') as f:
    csv_content = f.read()

print("=== CSV Content ===")
print(repr(csv_content))
print("\n=== Processing CSV ===")

try:
    headers, contacts = csv_to_dynamic_contacts(csv_content)
    print(f"\n=== Results ===")
    print(f"Headers: {headers}")
    print(f"Number of contacts: {len(contacts)}")
    for i, contact in enumerate(contacts):
        print(f"Contact {i+1}: {contact}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()