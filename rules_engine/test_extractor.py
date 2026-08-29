from extractor import extract_product_fields


ocr_text = """
Product XYZ

Brand ABC

Common Generic Name: Potato Chips

Net Weight
32g

MRP
₹20

Mfd.
08/2026

Pkd.
09/2026

Best Before
6 Months

Expiry Date
08/2027

Consumer Care
1800-123-4567

Made in India

Manufactured By
ABC Foods Pvt Ltd
123 Industrial Area
"""


result = extract_product_fields(ocr_text)

print("\nEXTRACTION RESULT")
print("-----------------")

for key, value in result.items():
    print(f"{key}: {value}")