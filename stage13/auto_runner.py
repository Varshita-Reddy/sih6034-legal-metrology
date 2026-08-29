"""
stage13/auto_runner.py
----------------------

Stage 13 - Automatic OCR Watcher + Frontend Router

The program continuously watches:

    stage13/incoming/

Whenever a new image appears:

    incoming/
        ↓
    run_pipeline.py
        ↓
    field extraction
        ↓
    validation
        ↓
    compliance
        ↓
    frontend action
        ↓
    ┌──────────────┬─────────────────┐
    │              │                 │
  ACCEPT/REVIEW  RETAKE        NON_COMPLIANT
    │              │                 │
    ↓              ↓                 ↓
processed/       retake/          processed/

The complete JSON result is also saved in:

    stage13/results/

This file is designed to run continuously.

Start manually:

    python stage13/auto_runner.py

After it starts, simply place images into:

    stage13/incoming/

No additional command is required for every image.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from datetime import datetime


# =====================================================================
# PROJECT ROOT
# =====================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STAGE13_DIR = PROJECT_ROOT / "stage13"

INCOMING_DIR = STAGE13_DIR / "incoming"
PROCESSED_DIR = STAGE13_DIR / "processed"
RETAKE_DIR = STAGE13_DIR / "retake"
RESULTS_DIR = STAGE13_DIR / "results"


# =====================================================================
# SUPPORTED IMAGE TYPES
# =====================================================================

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


# =====================================================================
# PYTHON PATH
# =====================================================================

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =====================================================================
# IMPORT OCR PIPELINE
# =====================================================================

try:

    from run_pipeline import run

except Exception as e:

    print()
    print("=" * 70)
    print("❌ COULD NOT IMPORT run_pipeline.py")
    print("=" * 70)
    print(f"Error: {e}")
    print()
    print("Make sure run_pipeline.py exists in:")
    print(PROJECT_ROOT)
    print()

    sys.exit(1)


# =====================================================================
# CREATE DIRECTORIES
# =====================================================================

for directory in (
    INCOMING_DIR,
    PROCESSED_DIR,
    RETAKE_DIR,
    RESULTS_DIR,
):

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def print_header():
    """Print watcher startup information."""

    print()
    print("=" * 70)
    print("🚀 STAGE 13 AUTO RUNNER")
    print("=" * 70)
    print()
    print(f"📂 Watching : {INCOMING_DIR}")
    print(f"✅ Processed: {PROCESSED_DIR}")
    print(f"📸 Retake   : {RETAKE_DIR}")
    print(f"📄 Results  : {RESULTS_DIR}")
    print()
    print("📥 Drop an image into the incoming folder.")
    print("🤖 It will be processed automatically.")
    print("🛑 Press Ctrl+C to stop.")
    print()
    print("=" * 70)
    print()


def is_image(path: Path) -> bool:
    """Return True if the file is a supported image."""

    return (
        path.is_file()
        and path.suffix.lower() in ALLOWED_EXTENSIONS
    )


def unique_destination(
    destination: Path,
) -> Path:
    """
    Prevent overwriting an existing file.

    Example:

        photo.jpg
        photo_1.jpg
        photo_2.jpg
    """

    if not destination.exists():
        return destination

    counter = 1

    while True:

        candidate = (
            destination.parent
            / f"{destination.stem}_{counter}{destination.suffix}"
        )

        if not candidate.exists():
            return candidate

        counter += 1


def wait_until_file_ready(
    path: Path,
    timeout: int = 30,
) -> bool:
    """
    Wait until the file has finished copying.

    This is important because a frontend may place a large
    image into incoming/ while Windows is still writing it.
    """

    start_time = time.time()

    previous_size = -1
    stable_count = 0

    while time.time() - start_time < timeout:

        if not path.exists():
            return False

        try:

            current_size = path.stat().st_size

        except OSError:

            time.sleep(0.5)
            continue

        if current_size > 0 and current_size == previous_size:

            stable_count += 1

        else:

            stable_count = 0

        previous_size = current_size

        # File size unchanged for two consecutive checks.
        if stable_count >= 2:

            return True

        time.sleep(0.5)

    return False


# =====================================================================
# IMAGE ROUTING
# =====================================================================

def route_image(
    image_path: Path,
    action: str,
) -> tuple[Path | None, str]:

    """
    Route image according to frontend action.

    ACCEPT
        -> processed/

    REVIEW
        -> processed/

    NON_COMPLIANT
        -> processed/

    RETAKE
        -> retake/
    """

    action = str(action).upper().strip()

    if not image_path.exists():

        return (
            None,
            "Image does not exist.",
        )

    if action == "RETAKE":

        destination_dir = RETAKE_DIR

    else:

        destination_dir = PROCESSED_DIR

    destination = (
        destination_dir
        / image_path.name
    )

    destination = unique_destination(
        destination
    )

    try:

        shutil.move(
            str(image_path),
            str(destination),
        )

        return (
            destination,
            "Image routed successfully.",
        )

    except Exception as e:

        return (
            None,
            f"Could not move image: {e}",
        )


# =====================================================================
# ERROR RESPONSE
# =====================================================================

def error_response(
    image_path: Path,
    reason: str,
) -> dict:

    return {

        "success": False,

        "action": "RETAKE",

        "label": "📸 Retake Photo",

        "next_step": "REQUEST_RETAKE",

        "send_to_feature_engineering": False,

        "reason": reason,

        "user_message": (
            "Something went wrong while processing "
            "the image. Please try again."
        ),

        "frontend_instruction": (
            "Ask the user to capture another photo."
        ),

        "image": {
            "original_path": str(image_path),
            "routed_path": None,
            "routing_message": "",
        },
    }


# =====================================================================
# FRONTEND RESPONSE
# =====================================================================

def build_frontend_response(
    result: dict,
    original_image: Path,
) -> dict:

    """
    Convert run_pipeline.py output into the Stage 13
    frontend response.
    """

    frontend_action = result.get(
        "frontend_action",
        {},
    )

    action = str(
        frontend_action.get(
            "action",
            "RETAKE",
        )
    ).upper().strip()

    if action not in {
        "ACCEPT",
        "RETAKE",
        "REVIEW",
        "NON_COMPLIANT",
    }:

        action = "RETAKE"

    label = frontend_action.get(
        "label",
        "📸 Retake Photo",
    )

    reason = frontend_action.get(
        "reason",
        "OCR result could not be classified.",
    )

    user_message = frontend_action.get(
        "user_message",
        "Please retake the photo.",
    )

    send_to_feature_engineering = bool(
        frontend_action.get(
            "send_to_feature_engineering",
            False,
        )
    )

    # ---------------------------------------------------------------
    # FRONTEND NEXT STEP
    # ---------------------------------------------------------------

    if action == "ACCEPT":

        next_step = "SEND_TO_FEATURE_ENGINEERING"

        frontend_instruction = (
            "Image accepted. Send the extracted "
            "product information to the Feature "
            "Engineering module."
        )

    elif action == "RETAKE":

        next_step = "REQUEST_RETAKE"

        frontend_instruction = (
            "Ask the user to capture another photo."
        )

    elif action == "REVIEW":

        next_step = "REQUEST_MANUAL_REVIEW"

        frontend_instruction = (
            "Ask for manual verification of the "
            "extracted information."
        )

    elif action == "NON_COMPLIANT":

        next_step = "SHOW_NON_COMPLIANT"

        frontend_instruction = (
            "Display the non-compliance result "
            "and extracted information."
        )

    else:

        next_step = "REQUEST_RETAKE"

        frontend_instruction = (
            "Ask the user to capture another photo."
        )

    # ---------------------------------------------------------------
    # ROUTE IMAGE
    # ---------------------------------------------------------------

    routed_path, routing_message = route_image(
        original_image,
        action,
    )

    # ---------------------------------------------------------------
    # FEATURE ENGINEERING DATA
    # ---------------------------------------------------------------

    should_send_to_fe = (
        action == "ACCEPT"
        and send_to_feature_engineering
    )

    fields = result.get(
        "fields",
        {},
    )

    # Product name is kept inside fields.
    #
    # Therefore Feature Engineering can receive:
    #
    # fields.product_name
    #
    # as well as:
    #
    # mrp
    # net_quantity
    # manufacturing_date
    # best_before
    # manufacturer

    feature_engineering = {

        "send": should_send_to_fe,

        "image_path": (
            str(routed_path)
            if should_send_to_fe
            and routed_path is not None
            else None
        ),

        "fields": (
            fields
            if should_send_to_fe
            else None
        ),

        "product_name": (
            fields.get(
                "product_name",
                {},
            )
            if should_send_to_fe
            else None
        ),

        "reason": reason,
    }

    # ---------------------------------------------------------------
    # FINAL RESPONSE
    # ---------------------------------------------------------------

    return {

        "success": True,

        "action": action,

        "label": label,

        "reason": reason,

        "user_message": user_message,

        "send_to_feature_engineering": (
            should_send_to_fe
        ),

        "feature_engineering": (
            feature_engineering
        ),

        "next_step": next_step,

        "frontend_instruction": (
            frontend_instruction
        ),

        "image": {

            "original_path": (
                str(original_image)
            ),

            "routed_path": (
                str(routed_path)
                if routed_path
                else None
            ),

            "routing_message": (
                routing_message
            ),
        },

        "ocr_quality": result.get(
            "ocr_quality",
            {},
        ),

        "quality": result.get(
            "quality",
            {},
        ),

        "readability": result.get(
            "readability",
            {},
        ),

        "fields": result.get(
            "fields",
            {},
        ),

        "validation": result.get(
            "validation",
            {},
        ),

        "compliance": result.get(
            "compliance",
            {},
        ),

        "preprocessing_attempt_used": (
            result.get(
                "preprocessing_attempt_used"
            )
        ),

        "processed_at": (
            datetime.now().isoformat()
        ),
    }


# =====================================================================
# SAVE JSON RESULT
# =====================================================================

def save_result(
    response: dict,
    original_name: str,
) -> Path:

    """
    Save Stage 13 JSON result.

    Example:

        stage13/results/photo1.json
    """

    filename = (
        Path(original_name).stem
        + ".json"
    )

    result_path = (
        RESULTS_DIR
        / filename
    )

    result_path = unique_destination(
        result_path
    )

    with open(
        result_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            response,
            f,
            indent=2,
            ensure_ascii=False,
        )

    return result_path


# =====================================================================
# PROCESS ONE IMAGE
# =====================================================================

def process_image(
    image_path: Path,
) -> dict:

    """
    Run complete OCR + Stage 13 processing.
    """

    print()
    print("=" * 70)
    print("🆕 NEW IMAGE DETECTED")
    print("=" * 70)
    print(f"📷 Image: {image_path.name}")
    print()

    # ---------------------------------------------------------------
    # Wait until copying is finished
    # ---------------------------------------------------------------

    print("⏳ Waiting for image file to finish copying...")

    if not wait_until_file_ready(image_path):

        response = error_response(
            image_path,
            "Image file was not ready before timeout.",
        )

        return response

    print("✅ Image file is ready.")

    # ---------------------------------------------------------------
    # Run OCR pipeline
    # ---------------------------------------------------------------

    print()
    print("🔎 Running OCR pipeline...")
    print()

    try:

        result = run(
            str(image_path)
        )

    except FileNotFoundError as e:

        return error_response(
            image_path,
            f"Image could not be read: {e}",
        )

    except Exception as e:

        return error_response(
            image_path,
            f"OCR pipeline error: {e}",
        )

    # ---------------------------------------------------------------
    # Build Stage 13 response
    # ---------------------------------------------------------------

    response = build_frontend_response(
        result,
        image_path,
    )

    # ---------------------------------------------------------------
    # Save result
    # ---------------------------------------------------------------

    try:

        result_path = save_result(
            response,
            image_path.name,
        )

        response["result_file"] = str(
            result_path
        )

    except Exception as e:

        print(
            f"⚠️ Could not save result JSON: {e}"
        )

    # ---------------------------------------------------------------
    # Display summary
    # ---------------------------------------------------------------

    print()
    print("📱 STAGE 13 DECISION")
    print("-" * 70)

    print(
        f"➡️ Action: {response['action']}"
    )

    print(
        f"🏷️ Label: {response['label']}"
    )

    print(
        f"📝 Reason: {response['reason']}"
    )

    print(
        "📤 Send to Feature Engineering: "
        f"{response['send_to_feature_engineering']}"
    )

    routed_path = response["image"].get(
        "routed_path"
    )

    if routed_path:

        print(
            f"📂 Routed to: {routed_path}"
        )

    if response.get("result_file"):

        print(
            f"📄 Result saved: "
            f"{response['result_file']}"
        )

    print()
    print("=" * 70)
    print()

    return response


# =====================================================================
# WATCHER
# =====================================================================

def watch_incoming():

    """
    Continuously watch the incoming directory.

    The watcher does NOT require a command for every image.

    Once this program is running, simply copy/drop images into:

        stage13/incoming/
    """

    print_header()

    # ---------------------------------------------------------------
    # Files already present when watcher starts
    # ---------------------------------------------------------------

    already_present = set()

    for path in INCOMING_DIR.iterdir():

        if is_image(path):

            already_present.add(
                str(path.resolve())
            )

    if already_present:

        print(
            f"📦 Found {len(already_present)} "
            "existing image(s) in incoming."
        )

        print(
            "🤖 Processing them automatically..."
        )

        print()

        for path_string in sorted(
            already_present
        ):

            path = Path(path_string)

            if path.exists():

                process_image(path)

    # ---------------------------------------------------------------
    # Main watcher loop
    # ---------------------------------------------------------------

    processed_seen = set()

    while True:

        try:

            current_files = {
                str(path.resolve()): path
                for path in INCOMING_DIR.iterdir()
                if is_image(path)
            }

            for path_string, path in current_files.items():

                # Process each file only once.
                if path_string in processed_seen:
                    continue

                processed_seen.add(
                    path_string
                )

                process_image(path)

            # Remove files from tracking if they
            # disappeared from incoming.
            existing_paths = set(
                current_files.keys()
            )

            processed_seen.intersection_update(
                existing_paths
            )

            time.sleep(1)

        except KeyboardInterrupt:

            print()
            print("🛑 Stage 13 Auto Runner stopped.")
            print()

            break

        except Exception as e:

            print()
            print(
                f"⚠️ Watcher error: {e}"
            )

            print(
                "🔄 Continuing to watch..."
            )

            time.sleep(2)


# =====================================================================
# MAIN
# =====================================================================

def main():

    watch_incoming()


# =====================================================================
# ENTRY POINT
# =====================================================================

if __name__ == "__main__":

    main()