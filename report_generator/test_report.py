from report_generator import generate_report


test_data = {
    "product": {
        "product_name": "Lay's Classic Salted",
        "brand_name": "Lay's",
        "common_generic_name": "Potato Chips",
        "product_category": "Food",
        "product_subcategory": "Snacks"
    },
    "status": "COMPLIANT",
    "violations": [],
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


generate_report(test_data)