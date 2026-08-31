from extractor import extract_product_fields
from compliance_checker import check_compliance


ocr_text = """
LAYS CLASSIC SALTED

Common Generic Name: Potato Chips
Net Weight: 50g
M.R.P. ₹20
Mfd. 08/2026
Best Before 6 Months
Consumer Care: 1800-123-4567
Made in India
Manufactured By: ABC Foods Pvt Ltd
123 Industrial Area
"""


# 1. Surya extracts fields from OCR
surya_output = extract_product_fields(ocr_text)

# 2. Category information comes from frontend/backend
surya_output["product_category"] = "Food"
surya_output["product_subcategory"] = "Snacks"

print("\n--- SURYA OUTPUT ---")
for key, value in surya_output.items():
    print(f"{key}: {value}")


# 3. YOUR COMPLIANCE CHECKER receives Surya's output
compliance_result = check_compliance(surya_output)

print("\n--- COMPLIANCE RESULT ---")
print("Status:", compliance_result["status"])

print("\nViolations:")
for violation in compliance_result["violations"]:
    print(violation)