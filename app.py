"""
Minimal API to attest Freedom-of-Information disclosure requests on-chain.

POST /attest
    multipart/form-data:
        file=<document>
        target_authority=<実施機関名, e.g. "〇〇市長">
        request_type=<請求の種類, e.g. "行政文書開示請求">
        summary=<short text>
    -> { "tx_hash": "0x...", "attestation_uid": "0x..." }
"""
from fastapi import FastAPI, File, Form, UploadFile

from attest import submit_attestation

app = FastAPI(title="information-disclosure-proof")


@app.post("/attest")
async def attest(
    file: UploadFile = File(...),
    target_authority: str = Form(...),
    request_type: str = Form(...),
    summary: str = Form(...),
):
    document_bytes = await file.read()
    return submit_attestation(document_bytes, target_authority, request_type, summary)


@app.get("/health")
async def health():
    return {"status": "ok"}
