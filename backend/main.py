import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# Existing working pipeline
from run_pipeline import run

# Mohan's PDF Report Generator
try:
    from report_generator.report_generator import generate_report
except ImportError:
    try:
        from report_generator import generate_report
    except ImportError:
        generate_report = None

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Legal Metrology Compliance API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "Legal Metrology Compliance Engine"}

@app.post("/scan")
async def scan_label(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    file_ext = Path(file.filename).suffix.lower() or ".jpg"
    unique_id = str(uuid.uuid4())[:8]
    temp_filename = f"scan_{unique_id}{file_ext}"
    saved_file_path = UPLOAD_DIR / temp_filename

    try:
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. Run core pipeline
        pipeline_result: Dict[str, Any] = run(image_path=str(saved_file_path))

        # 2. Parse compliance status accurately
        compliance_summary = pipeline_result.get("compliance", {})
        decision = compliance_summary.get("decision", "").lower()
        is_compliant = (decision == "compliant") or (pipeline_result.get("action") == "ACCEPT")

        extracted_fields = pipeline_result.get("fields", {})

        # 3. Generate PDF Inspection Report
        pdf_filename = f"compliance_report_{unique_id}.pdf"
        pdf_path = REPORT_DIR / pdf_filename
        report_url = None

        report_payload = {
            "image_name": file.filename,
            "compliant": is_compliant,
            "decision": compliance_summary.get("decision", "non_compliant"),
            "compliance": compliance_summary,
            "extracted_fields": extracted_fields,
            "fields": extracted_fields,
            "validation": pipeline_result.get("validation", {}),
            "quality": pipeline_result.get("quality", {}),
            "ocr_quality": pipeline_result.get("ocr_quality", {}),
            "raw_text": pipeline_result.get("raw_text", ""),
            "frontend_action": pipeline_result.get("frontend_action", {})
        }

        if generate_report is not None:
            try:
                generate_report(report_payload, output_path=str(pdf_path))
                report_url = f"/reports/{pdf_filename}"
            except Exception:
                try:
                    generate_report(report_payload)
                    default_pdf = Path("compliance_report.pdf")
                    if default_pdf.exists():
                        shutil.move(str(default_pdf), str(pdf_path))
                        report_url = f"/reports/{pdf_filename}"
                except Exception:
                    report_url = None

        # 4. Return consolidated JSON matching frontend specs
        response_data = {
            "status": "success",
            "filename": file.filename,
            "compliant": is_compliant,
            "overall_status": "COMPLIANT" if is_compliant else "NON-COMPLIANT",
            "extracted_fields": extracted_fields,
            "compliance_details": compliance_summary,
            "frontend_action": pipeline_result.get("frontend_action", {}),
            "validation": pipeline_result.get("validation", {}),
            "quality": pipeline_result.get("quality", {}),
            "ocr_quality": pipeline_result.get("ocr_quality", {}),
            "report_url": report_url,
            "raw_pipeline_output": pipeline_result
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")

@app.get("/reports/{filename}")
async def get_report(filename: str) -> FileResponse:
    file_path = REPORT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report PDF not found.")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename
    )