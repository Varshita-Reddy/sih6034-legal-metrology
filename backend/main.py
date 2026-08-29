from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_GENERATOR_FOLDER = PROJECT_ROOT / "report_generator"

sys.path.insert(0, str(REPORT_GENERATOR_FOLDER))

from report_generator import generate_report


# -------------------------------------------------
# FastAPI application
# -------------------------------------------------

app = FastAPI(
    title="Legal Metrology Compliance API",
    version="1.0.0"
)


# -------------------------------------------------
# CORS
# -------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------
# Request model
# -------------------------------------------------

class ReportRequest(BaseModel):
    product: dict
    status: str
    violations: list
    checked_rules: list


# -------------------------------------------------
# Root endpoint
# -------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Legal Metrology Backend is running"
    }


# -------------------------------------------------
# Generate compliance report
# -------------------------------------------------

@app.post(
    "/api/report/generate",
    response_class=FileResponse
)
def generate_compliance_report(
    request: ReportRequest
):

    compliance_result = {
        "product": request.product,
        "status": request.status,
        "violations": request.violations,
        "checked_rules": request.checked_rules
    }

    pdf_file = generate_report(
        compliance_result
    )

    pdf_path = Path(
        pdf_file
    ).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(
            "PDF was not generated."
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="compliance_report.pdf"
    )