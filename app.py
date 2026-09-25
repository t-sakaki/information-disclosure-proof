"""
Minimal API to attest Freedom-of-Information disclosure requests on-chain.

POST /attest
    multipart/form-data:
        file=<document>
        target_authority=<実施機関名, e.g. "〇〇市長">
        request_type=<請求の種類, e.g. "行政文書開示請求">
        summary=<short text>
    -> { "tx_hash": "0x...", "attestation_uid": "0x..." }

POST /tip
    投げ銭: 開示請求への応援としてETHを請求者に送金し、応援メッセージを
    元のattestationに紐づけて記録する。
    json body:
        recipient_address=<請求者のウォレットアドレス>
        ref_attestation_uid=<応援対象のattestation UID>
        amount=<送金額（トークンの最小単位。ETHならwei, USDCなら6桁単位）>
        comment=<応援メッセージ>
        referrer_address=<紹介者のウォレットアドレス（任意、投げ銭リレー用）>
        token_address=<トークンコントラクトアドレス（任意、省略でETH）>
    -> { "transfer_tx_hash": "0x...", "attestation_tx_hash": "0x...", "tip_attestation_uid": "0x..." }

GET /leaderboard
    投げ銭額の多い応援者・紹介者ランキングをオンチェーンデータから集計して返す。
    -> { "top_tippers": [...], "top_referrers": [...] }
"""
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from attest import ZERO_ADDRESS, submit_attestation
from leaderboard import build_leaderboard
from tip import send_tip

app = FastAPI(title="information-disclosure-proof")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


class TipRequest(BaseModel):
    recipient_address: str
    ref_attestation_uid: str
    amount: int
    comment: str = ""
    referrer_address: str = ZERO_ADDRESS
    token_address: str = ZERO_ADDRESS


@app.post("/attest")
async def attest(
    file: UploadFile = File(...),
    target_authority: str = Form(...),
    request_type: str = Form(...),
    summary: str = Form(...),
):
    document_bytes = await file.read()
    return submit_attestation(document_bytes, target_authority, request_type, summary)


@app.post("/tip")
async def tip(body: TipRequest):
    return send_tip(
        body.recipient_address,
        body.ref_attestation_uid,
        body.amount,
        body.comment,
        body.referrer_address,
        body.token_address,
    )


@app.get("/leaderboard")
async def leaderboard():
    return build_leaderboard()


@app.get("/health")
async def health():
    return {"status": "ok"}
