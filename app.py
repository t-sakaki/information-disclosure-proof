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

GET /trending
    直近(デフォルト24時間)で最も応援が集まっている開示請求を「急上昇」として返す。

GET /case/{uid}
    開示請求1件のプレビューページ（SNSシェア用のOGPタグ付きHTML）。
    投げ銭・応援UIはこのページにのみ存在し、登録フォーム（"/")には無い。

GET /api/case/{uid}
    上記ページと同じデータをJSONで返す（プレビューページのUIが叩く用途）。

GET /case/{uid}/og.png
    上記プレビューページのog:image。開示請求の内容（請求先・種別・要約・
    応援状況）を焼き込んだ画像をPNGで返す（毎回オンチェーンデータから
    動的に生成、キャッシュDBは持たない）。

GET /api/case/{uid}/reactions?address=0x...
    Caseへのリアクション（👀🙋🔁）の件数と、addressを渡した場合は
    自分がすでに反応済みかを返す。オンチェーンではなくUpstash Redis
    に保存（投げ銭と違い、絵文字クリック1つにガス代・署名トランザクション
    を要求するのはUX上望ましくないため）。

POST /api/case/{uid}/reactions
    json body: { reaction, address, timestamp, signature }
    signatureはブラウザがreactions.build_message()と同じ文言に対して
    personal_signで署名したもの（ガス代なし、トランザクションではない）。
    トグル動作（すでに反応済みなら取り消す）。

GET /api/price/eth-usd
    UniswapのオンチェーンQuoter（Baseメインネット、読み取り専用・
    ガス代なし）から1ETHあたりのUSDC建て参考価格を取得する。
    スワップは一切実行しない、投げ銭額のドル換算表示用。
"""
import os

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from attest import ZERO_ADDRESS, submit_attestation
from case_page import render_case_html
from ledger import get_case
from leaderboard import build_leaderboard
from og_image import render_case_og_image
from reactions import ReactionsNotConfigured, get_reactions, toggle_reaction
from tip import send_tip
from trending import trending_requests
from uniswap_price import get_eth_usd_price

# Absolute path so this resolves the same way whether run via `uvicorn
# app:app` from the repo root, or bundled and invoked from an arbitrary
# working directory by Vercel's Python runtime (see api/index.py).
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = FastAPI(title="information-disclosure-proof")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/case/{uid}", response_class=HTMLResponse)
async def case_page(uid: str, request: Request):
    case = get_case(uid)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found / 該当する開示請求が見つかりません")
    return render_case_html(uid, case, str(request.base_url))


@app.get("/api/case/{uid}")
async def case_api(uid: str):
    case = get_case(uid)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found / 該当する開示請求が見つかりません")
    return case


@app.get("/case/{uid}/og.png")
async def case_og_image(uid: str):
    case = get_case(uid)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found / 該当する開示請求が見つかりません")
    png_bytes = render_case_og_image(uid, case)
    return Response(content=png_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=60"})


@app.get("/api/case/{uid}/reactions")
async def case_reactions(uid: str, address: str | None = None):
    return get_reactions(uid, address)


class ReactionRequest(BaseModel):
    reaction: str
    address: str
    timestamp: int
    signature: str


@app.post("/api/case/{uid}/reactions")
async def case_react(uid: str, body: ReactionRequest):
    try:
        return toggle_reaction(uid, body.reaction, body.address, body.timestamp, body.signature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ReactionsNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))


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


@app.get("/trending")
async def trending(window_hours: int = 24, limit: int = 10):
    return trending_requests(window_hours, limit)


@app.get("/api/price/eth-usd")
async def price_eth_usd():
    return {"usd_per_eth": get_eth_usd_price()}


@app.get("/health")
async def health():
    return {"status": "ok"}
