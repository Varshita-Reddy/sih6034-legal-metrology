from report_generator import generate_report


# ---------------------------------
# TEST 1 - FOOD PRODUCT
# ---------------------------------

food_product = {
    "product": {
        "product_name": "Rice Packet",
        "brand_name": "Test Rice",
        "common_generic_name": "Rice",
        "product_category": "Food",
        "product_subcategory": "Grains"
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


print("\n========== TEST 1: FOOD PRODUCT ==========\n")
generate_report(food_product)

personal_care_product = {
    "product": {
        "product_name": "Shampoo",
        "brand_name": "Test Shampoo",
        "common_generic_name": "Hair Shampoo",
        "product_category": "Personal Care",
        "product_subcategory": "Hair Care"
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


print("\n========== TEST 2: PERSONAL CARE PRODUCT ==========\n")
generate_report(personal_care_product)


# ---------------------------------
# TEST 3 - ONE VIOLATION
# ---------------------------------

one_violation_product = {
    "product": {
        "product_name": "Biscuits",
        "brand_name": "Test Biscuits",
        "common_generic_name": "Wheat Biscuits",
        "product_category": "Food",
        "product_subcategory": "Biscuits"
    },
    "status": "NON_COMPLIANT",
    "violations": [
        {
            "field": "mrp",
            "message": "Retail sale price / MRP is missing"
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


print("\n========== TEST 3: ONE VIOLATION ==========\n")
generate_report(one_violation_product)

multiple_violation_product = {
    "product": {
        "product_name": "Cooking Oil",
        "brand_name": "Test Oil",
        "common_generic_name": "Edible Vegetable Oil",
        "product_category": "Food",
        "product_subcategory": "Cooking Oil"
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
        },
        {
            "field": "manufacturer_address",
            "message": "Manufacturer address is missing"
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


print("\n========== TEST 4: MULTIPLE VIOLATIONS ==========\n")
generate_report(multiple_violation_product)


print("\n==============================================")
print("ALL RANDOM PRODUCT TESTS COMPLETED")
print("==============================================")