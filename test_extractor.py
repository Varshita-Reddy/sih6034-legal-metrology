from extractor import extract_product_fields


# ==================================================
# TEST OCR
# ==================================================

ocr_text = """
LAYS CLASSIC SALTED

Common Generic Name: Potato Chips
Net Weight: 50g
M.R.P. ₹20
MFD: 08/2026
PKD: 09/2026
Best Before 6 Months
Expiry: 08/2027
Manufactured by: ABC Foods Pvt Ltd
123 Industrial Area
Consumer Care: 1800-123-4567
Country of Origin: India
"""


# ==================================================
# RUN EXTRACTION
# ==================================================

result = extract_product_fields(ocr_text)


# ==================================================
# DISPLAY RESULT
# ==================================================

print()
print("EXTRACTION RESULT")
print("-----------------")

for field, value in result.items():
    print(f"{field}: {value}")
