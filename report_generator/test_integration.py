from report_generator import generate_report
import os


compliance_result = {
    "product": {
        "product_name": "",
        "brand_name": "",
        "common_generic_name": "Potato Chips",
        "product_category": "Food",
        "product_subcategory": "Snacks"
    },
    "status": "NON_COMPLIANT",
    "violations": [
        {
            "field": "expiry_date",
            "message": "Best before / use by / expiry date (FSSAI labeling regulations — not Legal Metrology) is missing"
        }
    ],
    "checked_rules": [
        "common_generic_name",
        "manufacturer_name",
        "manufacturer_address",
        "net_quantity",
        "manufacturing_date",
        "mrp",
        "consumer_care",
        "country_of_origin",
        "expiry_date"
    ]
}


print("Testing Mani's actual compliance result...")
print()

pdf_file = generate_report(compliance_result)

print()
print("Returned PDF:", pdf_file)

if os.path.exists(pdf_file):
    print("PDF file exists: YES")
else:
    print("PDF file exists: NO")

print()
print("Integration test completed.")