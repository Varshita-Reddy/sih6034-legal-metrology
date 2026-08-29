from report_generator import generate_report
import os


# This represents the result that Mani's Rules Engine
# will eventually send to the Report Generator.

mani_result = {
    "product": {
        "product_name": "Test Product",
        "brand_name": "Test Brand",
        "common_generic_name": "Test Item",
        "product_category": "Food",
        "product_subcategory": "Snacks"
    },
    "status": "NON_COMPLIANT",
    "violations": [
        {
            "field": "mrp",
            "message": "Retail sale price / MRP is missing"
        },
        {
            "field": "net_quantity",
            "message": "Net quantity is missing"
        }
    ],
    "checked_rules": [
        "common_generic_name",
        "manufacturer_name",
        "manufacturer_address",
        "net_quantity",
        "manufacturing_date",
        "mrp",
        "consumer_care"
    ]
}


print("Starting integration test...")
print()

# Call the Report Generator exactly like
# another module will call it.
pdf_file = generate_report(mani_result)

print()
print("Returned PDF:", pdf_file)

# Check whether the PDF was actually created.
if os.path.exists(pdf_file):
    print("PDF file exists: YES")
else:
    print("PDF file exists: NO")

print()
print("Integration test completed.")