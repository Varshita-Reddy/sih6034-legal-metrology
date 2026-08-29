import re


def extract_product_fields(ocr_text):
    """
    Extract product information from Prem's OCR text.

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

    # Clean OCR into individual lines
    lines = [
        line.strip()
        for line in ocr_text.splitlines()
        if line.strip()
    ]

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

                # Example:
                # Net Weight 32g
                after_label = lower.split(label, 1)[-1].strip()

                match = re.search(
                    r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b",
                    after_label,
                    re.IGNORECASE
                )

                if match:
                    product_data["net_quantity"] = match.group(0)
                    break

                # Example:
                # Net Weight
                # 32g
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

                # Example:
                # Common Generic Name: Potato Chips
                after_label = line[
                    lower.find(label) + len(label):
                ].strip()

                # Remove : or -
                after_label = after_label.lstrip(":- ").strip()

                if after_label:
                    product_data["common_generic_name"] = after_label
                    break

                # Example:
                # Common Generic Name
                # Potato Chips
                if i + 1 < len(lines):
                    product_data["common_generic_name"] = lines[i + 1]
                    break

        if product_data["common_generic_name"]:
            break

    # ==================================================
    # MRP
    # ==================================================

    # Matches "MRP", "M.R.P.", "M.R.P", "M R P", "Maximum Retail Price",
    # with or without a trailing colon/dash, in any case.
    mrp_label_pattern = re.compile(
        r"\b(maximum retail price|m\.?\s*r\.?\s*p\.?)\b",
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

        # Example (same line):
        # MRP ₹20
        # M.R.P. ₹20
        # M.R.P.: ₹20
        # Maximum Retail Price ₹20
        after_label = line[label_match.end():].strip()
        after_label = after_label.lstrip(":- ").strip()

        match = currency_pattern.search(after_label)

        if match:
            product_data["mrp"] = match.group(0)
            break

        # Example (value on next line):
        # MRP
        # ₹20
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

                # Numeric date
                match = re.search(
                    date_pattern,
                    after_label
                )

                if match:
                    product_data["packing_date"] = match.group(0)
                    break

                # Month + year
                match = month_year_pattern.search(
                    after_label
                )

                if match:
                    product_data["packing_date"] = match.group(0)
                    break

                # Value on next line
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