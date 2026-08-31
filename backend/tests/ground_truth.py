"""
ground_truth.py
----------------
Known-correct text and field values for the 18 synthetic test images
(tests/generate_test_set.py). Since we generated these ourselves, we know
exactly what they say — this is what makes real CER/WER measurement
possible, per the project notes: "we'll calculate it after testing, don't
invent a percentage."

Images 01-12 and 15-18 all render the same base biscuit label at
different degradation levels (blur, tilt, shadow, etc.) — same text, same
ground truth. Images 13 (spice packet) and 14 (oil bottle) use different
label content entirely.
"""

_BASE_LABEL_TEXT = (
    "BRAND XYZ FOODS\n"
    "Crunchy Wheat Biscuits\n"
    "Net Quantity: 100 g\n"
    "MRP (incl. of all taxes): Rs 50\n"
    "Mfg. Date: 06/2026\n"
    "Best Before: 12 Months from Mfg.\n"
    "Packed by: XYZ Foods Pvt. Ltd.\n"
    "Customer Care: 1800-000-0000"
)

_BASE_LABEL_FIELDS = {
    "mrp": {"amount": 50.0, "currency": "INR"},
    "net_quantity": {"amount": 100.0, "unit": "g"},
    "manufacturing_date": {"month": 6, "year": 2026},
    "best_before": {"amount": 12, "unit": "months", "reference": "manufacturing"},
    "manufacturer": "XYZ Foods Pvt. Ltd.",
}

_SPICE_LABEL_TEXT = (
    "MASALA SPICE MIX\n"
    "INGREDIENTS: Coriander, Cumin, Turmeric, Red Chilli,\n"
    "Black Pepper, Cardamom, Cinnamon, Cloves, Bay Leaf,\n"
    "Fennel, Mustard, Fenugreek, Asafoetida, Salt, Edible Oil.\n"
    "Nutritional Info (per 100g): Energy 320kcal, Protein 12g,\n"
    "Carbohydrate 45g, Fat 8g, Sodium 1200mg, Fibre 20g.\n"
    "Net Weight: 50 g   MRP: Rs 35 (Incl. of all taxes)\n"
    "Mfg Date: 03/2026   Best Before: 9 months from Mfg.\n"
    "Batch No: MS20260304   FSSAI Lic No: 10018043002145\n"
    "Manufactured & Packed by: Spice World Industries,\n"
    "Plot 14, Industrial Area, Kochi, Kerala - 682001.\n"
    "Customer Care: care@spiceworld.in / 1800-111-2222\n"
    "Store in a cool, dry place away from direct sunlight."
)

_SPICE_LABEL_FIELDS = {
    "mrp": {"amount": 35.0, "currency": "INR"},
    "net_quantity": {"amount": 50.0, "unit": "g"},
    "manufacturing_date": {"month": 3, "year": 2026},
    "best_before": {"amount": 9, "unit": "months", "reference": "manufacturing"},
    "manufacturer": "Spice World Industries,",
}

_OIL_LABEL_TEXT = (
    "PURE SUNFLOWER OIL\n"
    "1 Litre\n"
    "MRP: Rs 150"
)

_OIL_LABEL_FIELDS = {
    "mrp": {"amount": 150.0, "currency": "INR"},
    # No "Net Qty"/"Net Weight" keyword on this label by design (see
    # generate_test_set.py's large_sparse_label) — net_quantity is
    # expected to land as "uncertain", not "present", so it's
    # intentionally left out of the expected exact-match fields here.
    "manufacturing_date": None,
    "best_before": None,
    "manufacturer": None,
}

# Maps each test image filename to (expected_raw_text, expected_fields).
GROUND_TRUTH = {
    "01_clean_normal.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "02_dark.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "03_bright_overexposed.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "04_low_contrast.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "05_blurry.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "06_very_blurry.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "07_low_resolution.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "08_tilted_15deg.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "09_tilted_30deg.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "10_shadow.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "11_reflection_glare.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "12_noisy.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "13_small_text_dense.jpg": (_SPICE_LABEL_TEXT, _SPICE_LABEL_FIELDS),
    "14_large_text.jpg": (_OIL_LABEL_TEXT, _OIL_LABEL_FIELDS),
    "15_dark_packaging.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    "16_curved_packaging.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
    # 17_partial_occlusion.jpg is deliberately excluded: occlusion means
    # part of the physical label is genuinely covered, so comparing
    # against the FULL unobstructed text would count the occluded portion
    # as an "error" when really the image just never showed it. CER/WER
    # against full ground truth isn't a meaningful measure for this case.
    "18_mixed_dark_blur_tilt.jpg": (_BASE_LABEL_TEXT, _BASE_LABEL_FIELDS),
}
