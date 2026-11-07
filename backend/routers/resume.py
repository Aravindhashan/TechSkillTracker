"""Resume upload endpoint."""

from __future__ import annotations

import os

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.dependencies import get_dataframe

router = APIRouter(prefix="/api/resume", tags=["resume"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/analyze")
async def analyze_resume_endpoint(
    file: UploadFile = File(...),
    df=Depends(get_dataframe),
) -> dict:
    from modules import resume_analyzer

    filename = file.filename or ""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type. Use PDF or DOCX.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Empty file.")

    try:
        text = resume_analyzer.extract_text(content, filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")

    if not (text or "").strip():
        raise HTTPException(status_code=422, detail="No readable text found in the file.")

    frame = df if df is not None else pd.DataFrame()
    try:
        analysis = resume_analyzer.analyze_resume(text, frame)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Analysis failed: {exc}")

    resume_id = None
    try:
        resume_id = resume_analyzer.save_report(filename, analysis)
    except Exception:
        resume_id = None

    payload = dict(analysis or {})
    payload["filename"] = filename
    payload["resume_id"] = resume_id
    return payload
