import json
from rules import COMMON_RULES, CATEGORY_RULES, FSSAI_RULES


def check_compliance(product_data):
    """
    Check a product against the applicable packaged-commodity rules.
    """

    violations = []
    checked_rules = []

    category = product_data.get("product_category")
    subcategory = product_data.get("product_subcategory")

    selected_fields = CATEGORY_RULES.get(category, {}).get(subcategory)

    if selected_fields is None:
        selected_fields = list(COMMON_RULES.keys())

    All_RULESS = {**COMMON_RULES, **FSSAI_RULES}

    selected_rules = {
        field: All_RULESS[field]
        for field in selected_fields
        if field in All_RULESS
    }

    for field, rule in selected_rules.items():

        checked_rules.append(field)
        value = product_data.get(field)

        # 1. Check whether required field is missing
        if rule.get("required") and (value is None or value == ""):
            violations.append({
                "field": field,
                "message": f"{rule['description']} is missing"
            })
            continue

        # 2. Field-specific validations
        if value is not None and value != "":

            if field == "net_quantity":
                quantity = str(value).lower()
                valid_units = ["g", "kg", "ml", "l"]

                if not any(unit in quantity for unit in valid_units):
                    violations.append({
                        "field": field,
                        "message": (
                            "Net quantity must include a valid unit "
                            "such as g, kg, ml or l"
                        )
                    })

            elif field == "mrp":
                mrp = str(value).strip()

                if not any(char.isdigit() for char in mrp):
                    violations.append({
                        "field": field,
                        "message": "MRP must contain a numeric value"
                    })

            elif field == "manufacturing_date":
                date_value = str(value).strip()

                if not any(char.isdigit() for char in date_value):
                    violations.append({
                        "field": field,
                        "message": (
                            "Manufacturing date must contain a valid date value"
                        )
                    })

            elif field == "manufacturer_name":
                manufacturer = str(value).strip()

                if len(manufacturer) < 2:
                    violations.append({
                        "field": field,
                        "message": "Manufacturer name is invalid"
                    })

            elif field == "manufacturer_address":
                address = str(value).strip()

                if len(address) < 5:
                    violations.append({
                        "field": field,
                        "message": "Manufacturer address is invalid"
                    })

            elif field == "consumer_care":
                consumer_care = str(value).strip()

                if len(consumer_care) < 5:
                    violations.append({
                        "field": field,
                        "message": "Consumer care details are invalid"
                    })

            elif field == "expiry_date":
                expiry = str(value).strip()

                if not any(char.isdigit() for char in expiry):
                    violations.append({
                        "field": field,
                        "message": (
                            "Expiry/best-before date must contain "
                            "a valid date value"
                        )
                    })

    # Decide final status
    if violations:
        status = "NON_COMPLIANT"
    else:
        status = "COMPLIANT"

    return {
        "product": {
            "product_name": product_data.get("product_name"),
            "brand_name": product_data.get("brand_name"),
            "common_generic_name": product_data.get("common_generic_name"),
            "product_category": product_data.get("product_category"),
            "product_subcategory": product_data.get("product_subcategory")
        },
        "status": status,
        "violations": violations,
        "checked_rules": checked_rules
    }


# Run the temporary test ONLY when this file is executed directly.
# It will NOT run when another file imports check_compliance().
if __name__ == "__main__":

    # Temporary test product
    test_product = {
        "product_name": "Good Day Cashew Cookies",
        "brand_name": "Britannia",
        "common_generic_name": "Biscuits",
        "product_category": "Food",
        "product_subcategory": "Snacks",

        "net_quantity": "100 g",
        "mrp": "₹30",
        "manufacturing_date": "06/2026",
        "manufacturer_name": "Britannia Industries Ltd.",
        "manufacturer_address": "Example Address, Mumbai",
        "consumer_care": "1800-XXXXXXX",
        "country_of_origin": "India",
        "expiry_date": "12/2026"
    }

    result = check_compliance(test_product)

    print("\nComplete Result:")
    print(result)

    print("\nCompliance Result")
    print("-----------------")
    print("Status:", result["status"])

    print("\nJSON Result:")
    print(json.dumps(result, indent=4))