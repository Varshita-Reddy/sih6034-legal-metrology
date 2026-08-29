# SIH-OCR

OCR module for the Smart India Hackathon project: *Software System to check
compliance of Packaged Commodities under Legal Metrology (Packaged
Commodities) Rules, 2011*.

This module owns one slice of the pipeline:

```
PRODUCT/LABEL IMAGE → PREPROCESSING → OCR → TEXT CLEANING → CONFIDENCE CHECK → OCR OUTPUT
```

The output (text + confidence + bounding boxes) is handed to the
feature-extraction / compliance module. This module does **not** decide
whether a product is compliant — only that it accurately reads the label.

## Project structure

```
SIH-OCR/
├── images/                    # put test product images here
├── preprocessing/
│   └── image_preprocess.py    # quality check, resize, denoise, contrast,
│                               # sharpen, rotation & perspective correction
├── ocr/
│   ├── ocr_engine.py          # PaddleOCR wrapper -> text + confidence + bbox
│   └── text_cleaner.py        # context-aware O/0, I/1, S/5, B/8 corrections
├── output/
│   └── sample_output.json     # example of the module's output contract
├── tests/
│   └── test_ocr.py            # pytest unit tests
├── run_pipeline.py            # end-to-end CLI entry point
├── requirements.txt
└── README.md
```

## Setup (Stage 1 — Environment)

From the `SIH-OCR/` folder, in a VS Code terminal:

```powershell
python --version
pip --version

python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS/Linux
```

You should see the prompt change to `(.venv) PS C:\...\SIH-OCR>`. Then in
VS Code: **Ctrl+Shift+P → Python: Select Interpreter →** choose the
`.venv` interpreter.

Install dependencies:

```powershell
pip install -r requirements.txt
```

> First-time PaddleOCR runs will download detection/recognition model
> weights automatically (a few hundred MB) — make sure you have internet
> access the first time you run it.

## Usage

Run the full pipeline on one image:

```powershell
python run_pipeline.py images/test1.jpg
```

Save the result to a JSON file:

```powershell
python run_pipeline.py images/test1.jpg --out output/result.json
```

Adjust the minimum OCR confidence to keep (default `0.5`):

```powershell
python run_pipeline.py images/test1.jpg --confidence 0.6
```

### Using the pieces individually

```python
import cv2
from preprocessing.image_preprocess import check_image_quality, adaptive_preprocess
from ocr.ocr_engine import OCREngine
from ocr.text_cleaner import clean_detections

image = cv2.imread("images/test1.jpg")
quality = check_image_quality(image)
preprocessed = adaptive_preprocess(image, quality=quality)

engine = OCREngine(confidence_threshold=0.5)
result = engine.run(preprocessed)

cleaned = clean_detections(result["detections"])
```

## Output contract

```json
{
  "image_path": "images/test1.jpg",
  "quality": { "is_low_quality": false, "messages": [], "blur_score": 245.7, "brightness": 142.3 },
  "raw_text": "BRAND XYZ\nNET QUANTITY 100 g\nMRP ₹50\n...",
  "detections": [
    { "text": "MRP ₹50", "confidence": 0.98, "bbox": [120, 240, 420, 280], "was_corrected": true }
  ]
}
```

See `output/sample_output.json` for a full example.

## Testing

```powershell
pytest tests/test_ocr.py -v
```

`text_cleaner` and `image_preprocess` tests run with just `opencv-python`
and `numpy` installed. Tests touching `ocr_engine.OCREngine` are
auto-skipped if `paddleocr` isn't installed yet, so you can develop and
test the rest of the pipeline before finishing the OCR install.

## Roadmap

- [x] Stage 1 — Environment setup
- [x] Stage 2-3 — Basic OCR + structured output (text, confidence, bbox)
- [x] Stage 4 — Image preprocessing (resize, denoise, contrast, sharpen,
      rotation, perspective correction)
- [x] Stage 5 — Context-aware text cleaning
- [x] Stage 6 — Quality control (blur/brightness/resolution checks)
- [ ] Stage 7 — Real-world testing on 30-50+ product images
- [ ] Stage 8 — Accuracy evaluation (CER / WER)
- [ ] Stage 9 — Optimization based on weak cases
- [ ] Stage 10 — Handoff to feature-extraction module
