import json
dicti = {'nu_template': {'cbook_amount': '1130.1', 'invoice_amount': '1130.00'},
         'shams_bakery': {'cbook_amount': '39.0', 'invoice_amount': '59'}}
with open("sample.json", "w") as outfile:
    json.dump(dicti, outfile, indent=4)