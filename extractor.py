import re


def extract_product_fields(ocr_text):
    """
    Extract product information from OCR text.

    Input:
        ocr_text (str): Raw OCR text.

    Output:
        dict: 15-field product dictionary for the Compliance Checker.
    """

    product_data = {
        "product_name": "",
        "brand_name": "",
        "common_generic_name": "",
        "product_category": "",
        "product_subcategory": "",

        "net_quantity": "",
        "mrp": "",
        "manufacturing_date": "",
        "packing_date": "",
        "best_before": "",
        "expiry_date": "",

        "manufacturer_name": "",
        "manufacturer_address": "",
        "consumer_care": "",
        "country_of_origin": ""
    }

    # ==================================================
    # CLEAN OCR
    # ==================================================

    lines = [
        line.strip()
        for line in ocr_text.splitlines()
        if line.strip()
    ]

    # ==================================================
    # PRODUCT NAME
    # ==================================================

    product_name_labels = [
        "product name",
        "product"
    ]

    # First try explicit Product / Product Name labels
    for i, line in enumerate(lines):

        lower = line.lower()

        for label in product_name_labels:

            if lower.startswith(label):

                after_label = line[len(label):].strip()
                after_label = after_label.lstrip(":- ").strip()

                if after_label:
                    product_data["product_name"] = after_label
                    break

                if i + 1 < len(lines):
                    product_data["product_name"] = lines[i + 1]
                    break

        if product_data["product_name"]:
            break

    # --------------------------------------------------
    # FALLBACK PRODUCT NAME
    # --------------------------------------------------
    # If there is no Product/Product Name label,
    # use the first meaningful OCR line that is not
    # another known field.

    if not product_data["product_name"]:

        known_field_prefixes = [
            "common generic name",
            "common generic",
            "generic name",

            "net weight",
            "net content",
            "net quantity",
            "net. wt.",
            "net wt.",
            "net qty",

            "mrp",
            "m.r.p",
            "maximum retail price",

            "mfd",
            "mfd.",
            "mfg",
            "mfg.",
            "manufactured on",
            "date of manufacture",
            "manufacturing date",

            "pkd",
            "pkd.",
            "pkd. on",
            "pkd date",
            "packed on",
            "date of packing",
            "packing date",

            "best before",

            "expiry",
            "expiry date",
            "exp date",
            "use by",
            "use before",

            "manufactured by",
            "manufactured & marketed by",
            "manufactured and marketed by",
            "marketed by",

            "customer care",
            "consumer care",
            "consumer helpline",
            "customer service",
            "consumer service",

            "country of origin",
            "made in country",
            "made in",
            "product of",
            "origin"
        ]

        for line in lines:

            cleaned_line = line.strip()
            lower_line = cleaned_line.lower()

            if not cleaned_line:
                continue

            # Skip known field lines
            is_known_field = False

            for prefix in known_field_prefixes:

                if lower_line.startswith(prefix):
                    is_known_field = True
                    break

            if is_known_field:
                continue

            # Skip lines containing only numbers/dates/symbols
            if re.fullmatch(
                r"[\d\s./:%₹€$,\-]+",
                cleaned_line
            ):
                continue

            # Skip phone-number-only lines
            if re.fullmatch(
                r"[\d\s()+\-]+",
                cleaned_line
            ):
                continue

            # First meaningful line
            product_data["product_name"] = cleaned_line
            break

    # ==================================================
    # BRAND NAME
    # ==================================================

    brand_name_labels = [
        "brand name",
        "brand"
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in brand_name_labels:

            if lower.startswith(label):

                after_label = line[len(label):].strip()
                after_label = after_label.lstrip(":- ").strip()

                if after_label:
                    product_data["brand_name"] = after_label
                    break

                if i + 1 < len(lines):
                    product_data["brand_name"] = lines[i + 1]
                    break

        if product_data["brand_name"]:
            break

    # ==================================================
    # NET QUANTITY
    # ==================================================

    net_quantity_labels = [
        "net weight",
        "net content",
        "net quantity",
        "net. wt.",
        "net wt.",
        "net qty"
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in net_quantity_labels:

            if label in lower:

                after_label = lower.split(label, 1)[-1].strip()

                match = re.search(
                    r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b",
                    after_label,
                    re.IGNORECASE
                )

                if match:
                    product_data["net_quantity"] = match.group(0)
                    break

                if i + 1 < len(lines):

                    match = re.search(
                        r"^\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\s*$",
                        lines[i + 1],
                        re.IGNORECASE
                    )

                    if match:
                        product_data["net_quantity"] = match.group(0)
                        break

        if product_data["net_quantity"]:
            break

    # ==================================================
    # COMMON GENERIC NAME
    # ==================================================

    generic_labels = [
        "common generic name",
        "common generic",
        "generic name"
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in generic_labels:

            if label in lower:

                after_label = line[
                    lower.find(label) + len(label):
                ].strip()

                after_label = after_label.lstrip(":- ").strip()

                if after_label:
                    product_data["common_generic_name"] = after_label
                    break

                if i + 1 < len(lines):
                    product_data["common_generic_name"] = lines[i + 1]
                    break

        if product_data["common_generic_name"]:
            break

    # ==================================================
    # MRP
    # ==================================================

    mrp_label_pattern = re.compile(
        r"(?:maximum retail price|m\.?\s*r\.?\s*p\.?)"
        r"(?=\s|:|-|₹|rs\.?|inr|$)",
        re.IGNORECASE
    )

    currency_pattern = re.compile(
        r"(₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):

        label_match = mrp_label_pattern.search(line)

        if not label_match:
            continue

        after_label = line[label_match.end():].strip()
        after_label = after_label.lstrip(":- ").strip()

        match = currency_pattern.search(after_label)

        if match:
            product_data["mrp"] = match.group(0)
            break

        if i + 1 < len(lines):

            next_line = lines[i + 1].strip()

            match = currency_pattern.search(next_line)

            if match:
                product_data["mrp"] = next_line
                break

    # ==================================================
    # MANUFACTURING DATE
    # ==================================================

    manufacturing_labels = [
        "mfd.",
        "mfd",
        "mfg.",
        "mfg",
        "manufactured on",
        "date of manufacture",
        "manufacturing date"
    ]

    date_pattern = (
        r"\b(?:0?[1-9]|1[0-2])"
        r"[/\-.]"
        r"(?:20\d{2})\b"
    )

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in manufacturing_labels:

            if label in lower:

                after_label = lower.split(label, 1)[-1].strip()

                match = re.search(
                    date_pattern,
                    after_label
                )

                if match:
                    product_data["manufacturing_date"] = match.group(0)
                    break

                if i + 1 < len(lines):

                    match = re.search(
                        date_pattern,
                        lines[i + 1]
                    )

                    if match:
                        product_data["manufacturing_date"] = match.group(0)
                        break

        if product_data["manufacturing_date"]:
            break

    # ==================================================
    # PACKING DATE
    # ==================================================

    packing_labels = [
        "pkd. on",
        "pkd date",
        "pkd.",
        "pkd",
        "packed on",
        "date of packing",
        "packing date"
    ]

    month_year_pattern = re.compile(
        r"\b(?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)"
        r"\s+20\d{2}\b",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in packing_labels:

            if label in lower:

                after_label = line[
                    lower.find(label) + len(label):
                ].strip()

                match = re.search(
                    date_pattern,
                    after_label
                )

                if match:
                    product_data["packing_date"] = match.group(0)
                    break

                match = month_year_pattern.search(
                    after_label
                )

                if match:
                    product_data["packing_date"] = match.group(0)
                    break

                if i + 1 < len(lines):

                    next_line = lines[i + 1]

                    match = re.search(
                        date_pattern,
                        next_line
                    )

                    if match:
                        product_data["packing_date"] = match.group(0)
                        break

                    match = month_year_pattern.search(
                        next_line
                    )

                    if match:
                        product_data["packing_date"] = match.group(0)
                        break

        if product_data["packing_date"]:
            break

    # ==================================================
    # BEST BEFORE
    # ==================================================

    best_before_labels = [
        "best before end",
        "best before date",
        "best before",
        "bb"
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in best_before_labels:

            if label in lower:

                after_label = lower.split(label, 1)[-1].strip()

                match = re.search(
                    r"\b\d+(?:\.\d+)?\s*"
                    r"(?:days?|months?|years?)\b",
                    after_label,
                    re.IGNORECASE
                )

                if match:
                    product_data["best_before"] = match.group(0)
                    break

                if i + 1 < len(lines):

                    match = re.search(
                        r"\b\d+(?:\.\d+)?\s*"
                        r"(?:days?|months?|years?)\b",
                        lines[i + 1],
                        re.IGNORECASE
                    )

                    if match:
                        product_data["best_before"] = match.group(0)
                        break

        if product_data["best_before"]:
            break

    # ==================================================
    # EXPIRY / USE BY
    # ==================================================

    expiry_labels = [
        "use by",
        "use before",
        "expiry date",
        "expiry",
        "exp date",
        "expire"
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in expiry_labels:

            if label in lower:

                after_label = lower.split(label, 1)[-1].strip()

                match = re.search(
                    date_pattern,
                    after_label
                )

                if match:
                    product_data["expiry_date"] = match.group(0)
                    break

                if i + 1 < len(lines):

                    match = re.search(
                        date_pattern,
                        lines[i + 1]
                    )

                    if match:
                        product_data["expiry_date"] = match.group(0)
                        break

        if product_data["expiry_date"]:
            break

    # ==================================================
    # CUSTOMER / CONSUMER CARE
    # ==================================================

    customer_labels = [
        "customer care",
        "consumer care",
        "consumer helpline",
        "customer service",
        "consumer service"
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in customer_labels:

            if label in lower:

                after_label = line[
                    lower.find(label) + len(label):
                ].strip()

                after_label = after_label.lstrip(":- ").strip()

                if after_label:
                    product_data["consumer_care"] = after_label
                    break

                if i + 1 < len(lines):
                    product_data["consumer_care"] = lines[i + 1]
                    break

        if product_data["consumer_care"]:
            break

    # ==================================================
    # COUNTRY OF ORIGIN
    # ==================================================

    origin_labels = [
        "made in country",
        "country of origin",
        "made in",
        "product of",
        "origin"
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in origin_labels:

            if label in lower:

                after_label = line[
                    lower.find(label) + len(label):
                ].strip()

                after_label = after_label.lstrip(":- ").strip()

                if after_label:
                    product_data["country_of_origin"] = after_label
                    break

                if i + 1 < len(lines):
                    product_data["country_of_origin"] = lines[i + 1]
                    break

        if product_data["country_of_origin"]:
            break

    # ==================================================
    # MANUFACTURER
    # ==================================================

    manufacturer_labels = [
        "manufactured by",
        "manufactured & marketed by",
        "manufactured and marketed by",
        "marketed by"
    ]

    for i, line in enumerate(lines):

        lower = line.lower()

        for label in manufacturer_labels:

            if label in lower:

                after_label = line[
                    lower.find(label) + len(label):
                ].strip()

                after_label = after_label.lstrip(":- ").strip()

                if after_label:

                    product_data["manufacturer_name"] = after_label

                    if i + 1 < len(lines):
                        product_data["manufacturer_address"] = (
                            lines[i + 1]
                        )

                    break

                if i + 1 < len(lines):

                    product_data["manufacturer_name"] = lines[i + 1]

                    if i + 2 < len(lines):
                        product_data["manufacturer_address"] = (
                            lines[i + 2]
                        )

                    break

        if product_data["manufacturer_name"]:
            break

    return product_data
