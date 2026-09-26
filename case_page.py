"""
Renders the public "Case" preview page: /case/{uid}.

This is the page meant to be shared on social media. It is the *only*
place tip/reaction UI lives -- the registration form on the homepage
(static/index.html) only notarizes a request and then links here. Keeping
the two apart means a link shared on X/Bluesky always opens on a page that
shows what was actually requested (server-rendered, so crawlers that don't
run JS still see real OGP tags), not a bare registration form.

The page itself is built as a plain HTML string rather than a template
engine (no new dependency for a single page) using html.escape() on every
on-chain string, since target_authority/summary/comment are attacker-
controlled (anyone can attest anything) and are interpolated into HTML
served to other users' browsers.
"""
from __future__ import annotations

from html import escape
from typing import Any

from ledger import format_amount
from translate import translate_to_english

EXPLORER_ATTESTATION_URL = "https://base-sepolia.easscan.org/attestation/view"
EXPLORER_ADDRESS_URL = "https://sepolia.basescan.org/address"


def _short(addr: str) -> str:
    return addr[:6] + "..." + addr[-4:]


def _avatar_hue(addr: str) -> int:
    return sum(ord(c) for c in addr) % 360


def _format_tip_rows(tips: list[dict[str, Any]]) -> str:
    if not tips:
        return (
            '<div class="empty-state">'
            '<div class="empty-state-icon">&#128075;</div>'
            '<p>No support yet &mdash; be the first.<span class="ja">まだ応援がありません。最初の応援者になりませんか。</span></p>'
            "</div>"
        )
    cards = []
    for t in tips:
        comment = escape(t["comment"]) if t["comment"] else ""
        hue = _avatar_hue(t["tipper"])
        cards.append(
            '<div class="supporter">'
            f'<div class="supporter-avatar" style="background:hsl({hue},65%,55%)"></div>'
            '<div class="supporter-body">'
            f'<div class="supporter-row"><span class="mono">{escape(_short(t["tipper"]))}</span>'
            f'<span class="amount-pill">{format_amount(t["amount"])} {escape(t["currency"])}</span></div>'
            + (f'<div class="supporter-comment">&ldquo;{comment}&rdquo;</div>' if comment else "")
            + "</div></div>"
        )
    return f'<div class="supporter-list">{"".join(cards)}</div>'


def render_case_html(uid: str, case: dict[str, Any], base_url: str) -> str:
    req = case["request"]
    page_url = f"{base_url}case/{uid}"
    og_image_url = f"{page_url}/og.png"
    totals_text = ", ".join(f'{format_amount(t["amount"])} {t["currency"]}' for t in case["totals"]) or "0"

    safe_authority = escape(req["target_authority"])
    safe_type = escape(req["request_type"])
    safe_summary = escape(req["summary"]) if req["summary"] else '<span class="empty-inline">(no summary provided / 要約なし)</span>'
    safe_requester = escape(req["requester"])
    safe_doc_hash = escape(req["document_hash"])
    tips_html = _format_tip_rows(case["tips"])

    # Translate once, up front, so both the <title>/OGP tags and the
    # Request-details card use the same English text -- a link shared on
    # SNS should preview in English (and the OGP tags are what crawlers
    # that don't run JS actually see), not just the on-page card.
    translated_authority = translate_to_english(req["target_authority"])
    translated_type = translate_to_english(req["request_type"])
    translated_summary = translate_to_english(req["summary"]) if req["summary"] else None

    title_en = f"{translated_authority or req['target_authority']} — {translated_type or req['request_type']}"
    description_en = translated_summary or req["summary"] or "On-chain Freedom-of-Information disclosure request notarized via EAS on Base Sepolia."

    safe_title = escape(title_en)
    safe_description = escape(description_en[:200])

    def _field_with_translation(safe_original: str, translated: str | None) -> str:
        """Renders on-chain Japanese text with a best-effort English
        machine translation above it, labeled as such -- the on-chain
        Japanese is always the source of truth, this is a convenience for
        English-speaking readers (e.g. ETHGlobal judges)."""
        if not translated:
            return safe_original
        return (
            f'<div class="translated">{escape(translated)}</div>'
            f'<div class="original">{safe_original}<span class="mt-tag">machine-translated from Japanese</span></div>'
        )

    authority_field = _field_with_translation(safe_authority, translated_authority)
    type_field = _field_with_translation(safe_type, translated_type)
    summary_field = (
        _field_with_translation(safe_summary, translated_summary) if req["summary"] else safe_summary
    )
    heading_authority = escape(translated_authority) if translated_authority else safe_authority
    heading_type = escape(translated_type) if translated_type else safe_type

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title} · Disclosure Proof</title>
<meta name="description" content="{safe_description}">

<meta property="og:type" content="article">
<meta property="og:title" content="{safe_title}">
<meta property="og:description" content="{safe_description}">
<meta property="og:url" content="{escape(page_url)}">
<meta property="og:site_name" content="Disclosure Proof">
<meta property="og:image" content="{escape(og_image_url)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{safe_title}">
<meta name="twitter:description" content="{safe_description}">
<meta name="twitter:image" content="{escape(og_image_url)}">

<style>
  :root {{
    color-scheme: light dark;
    --bg: #0b0d12; --surface: #14171f; --surface-2: #1b1f2a; --border: #262b38;
    --text: #eef0f4; --text-dim: #9aa1b1; --accent: #6d8bff; --accent-2: #7ef0c0;
    --danger: #ff6b6b; --radius: 14px;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg: #f4f5f9; --surface: #fff; --surface-2: #f0f1f6; --border: #e2e4ec; --text: #14161c; --text-dim: #666d80; --accent: #4361ee; --accent-2: #12b981; }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, "Hiragino Sans", "Noto Sans JP", "Segoe UI", sans-serif; -webkit-font-smoothing: antialiased; }}
  .shell {{ max-width: 1120px; margin: 0 auto; padding: 0.9rem 1.25rem 1rem; }}
  a {{ color: var(--accent); }}
  .back {{ display: inline-block; margin-bottom: 0.6rem; font-size: 0.8rem; color: var(--text-dim); text-decoration: none; }}
  .header-row {{ display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.6rem; }}
  .status-badge {{ display: inline-flex; align-items: center; gap: 0.4rem; background: var(--surface-2); border: 1px solid var(--border); color: var(--text-dim); font-size: 0.72rem; padding: 0.25rem 0.65rem; border-radius: 999px; white-space: nowrap; }}
  .status-badge .dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--accent-2); box-shadow: 0 0 6px var(--accent-2); }}
  h1 {{ font-size: 1.4rem; margin: 0 0 0.15rem; line-height: 1.3; }}
  h1 .ja {{ font-size: 0.6em; margin-top: 0.1rem; }}
  .meta {{ color: var(--text-dim); font-size: 0.78rem; margin-bottom: 0.9rem; }}
  .layout {{ display: grid; grid-template-columns: 1fr; gap: 0.7rem; align-items: start; }}
  @media (min-width: 880px) {{
    .layout {{ grid-template-columns: 1fr 1fr; }}
  }}
  .col {{ display: flex; flex-direction: column; gap: 0.7rem; min-width: 0; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 0.9rem 1.1rem; }}
  .card h2 {{ font-size: 0.9rem; margin: 0 0 0.7rem; }}
  dl {{ display: grid; grid-template-columns: auto 1fr; gap: 0.4rem 1rem; margin: 0; font-size: 0.85rem; }}
  dt {{ color: var(--text-dim); }}
  dd {{ margin: 0; word-break: break-all; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, monospace; font-size: 0.82rem; }}
  .empty, .empty-inline {{ color: var(--text-dim); }}
  .translated {{ color: var(--text); }}
  .original {{ color: var(--text-dim); font-size: 0.88em; margin-top: 0.25rem; }}
  .mt-tag {{ display: inline-block; margin-left: 0.5rem; font-size: 0.72em; text-transform: uppercase; letter-spacing: 0.03em; padding: 0.1rem 0.45rem; border-radius: 999px; background: var(--surface-2); border: 1px solid var(--border); color: var(--text-dim); vertical-align: 1px; }}
  .ja {{ display: block; font-size: 0.82em; font-weight: 400; opacity: 0.7; margin-top: 0.15rem; }}
  label .ja {{ text-transform: none; display: inline; margin-left: 0.4rem; }}
  button .ja {{ font-size: 0.8em; opacity: 0.85; }}

  /* --- stat tiles --- */
  .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin-bottom: 0.8rem; }}
  .stat-tile {{ background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 0.6rem 0.85rem; }}
  .stat-tile .stat-value {{ font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em; background: linear-gradient(90deg, var(--accent), var(--accent-2)); -webkit-background-clip: text; background-clip: text; color: transparent; }}
  .stat-tile .stat-label {{ font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.03em; margin-top: 0.15rem; }}

  /* --- wallet chip --- */
  .wallet-btn {{ display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.65rem 1rem; font-size: 0.88rem; font-weight: 600; cursor: pointer; border: 1px solid var(--border); border-radius: 10px; background: var(--surface-2); color: var(--text); width: 100%; justify-content: center; transition: border-color 0.15s, transform 0.1s; }}
  .wallet-btn:hover {{ border-color: var(--accent); }}
  .wallet-btn:active {{ transform: scale(0.98); }}
  .wallet-btn.connected {{ border-color: var(--accent-2); color: var(--accent-2); cursor: default; }}
  .wallet-btn:disabled {{ opacity: 0.7; cursor: default; }}

  /* --- tip form --- */
  form {{ display: flex; flex-direction: column; gap: 0.65rem; margin-top: 0.7rem; }}
  .field {{ display: flex; flex-direction: column; gap: 0.3rem; }}
  label {{ font-size: 0.75rem; font-weight: 600; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.03em; }}
  input {{ background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 0.7rem 0.85rem; font-size: 1rem; color: var(--text); font-family: inherit; transition: border-color 0.15s, box-shadow 0.15s; }}
  input:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent); }}

  .segmented {{ display: inline-flex; background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 3px; gap: 3px; }}
  .segmented-btn {{ padding: 0.5rem 1.1rem; font-size: 0.88rem; font-weight: 600; border: none; border-radius: 8px; background: transparent; color: var(--text-dim); cursor: pointer; transition: background 0.15s, color 0.15s; }}
  .segmented-btn.active {{ background: var(--surface); color: var(--text); box-shadow: 0 1px 3px rgba(0,0,0,0.15); }}

  .amount-input-wrap {{ position: relative; }}
  .amount-input-wrap input {{ padding-right: 4.2rem; font-weight: 700; font-size: 1.15rem; }}
  .amount-suffix {{ position: absolute; right: 0.85rem; top: 50%; transform: translateY(-50%); color: var(--text-dim); font-size: 0.85rem; font-weight: 600; pointer-events: none; }}
  .price-hint {{ font-size: 0.76rem; color: var(--text-dim); margin-top: 0.3rem; min-height: 1em; }}
  .price-hint .src {{ opacity: 0.7; }}

  .chip-row {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
  .chip {{ padding: 0.4rem 0.85rem; font-size: 0.82rem; font-weight: 600; border-radius: 999px; border: 1px solid var(--border); background: var(--surface-2); color: var(--text-dim); cursor: pointer; transition: all 0.15s; }}
  .chip:hover {{ border-color: var(--accent); color: var(--text); }}
  .chip.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

  .reaction-row {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.8rem; }}
  .reaction-btn {{ display: flex; align-items: center; gap: 0.35rem; padding: 0.35rem 0.6rem; border-radius: 999px; border: 1px solid var(--border); background: var(--surface-2); color: var(--text-dim); cursor: pointer; font-size: 0.78rem; font-weight: 600; transition: all 0.15s; }}
  .reaction-btn:hover {{ border-color: var(--accent); color: var(--text); }}
  .reaction-btn.mine {{ background: color-mix(in srgb, var(--accent) 16%, transparent); border-color: var(--accent); color: var(--accent); }}
  .reaction-btn:disabled {{ opacity: 0.5; cursor: wait; }}
  .reaction-emoji {{ font-size: 0.95rem; }}
  .reaction-count {{ font-weight: 800; min-width: 1ch; text-align: center; }}

  .btn-primary {{
    padding: 0.85rem 1.2rem; font-size: 0.98rem; font-weight: 700; cursor: pointer; border: none; border-radius: 12px;
    background: linear-gradient(135deg, var(--accent), #8a6dff); color: #fff;
    display: flex; align-items: center; justify-content: center; gap: 0.5rem;
    box-shadow: 0 4px 14px color-mix(in srgb, var(--accent) 35%, transparent);
    transition: transform 0.1s, box-shadow 0.15s;
  }}
  .btn-primary:hover:not(:disabled) {{ transform: translateY(-1px); box-shadow: 0 6px 18px color-mix(in srgb, var(--accent) 45%, transparent); }}
  .btn-primary:active:not(:disabled) {{ transform: translateY(0); }}
  .btn-primary:disabled {{ opacity: 0.55; cursor: wait; box-shadow: none; }}
  .spinner {{ width: 15px; height: 15px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: none; }}
  .btn-primary.loading .spinner {{ display: inline-block; }}
  .btn-primary.loading .btn-label {{ opacity: 0.85; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

  .step-track {{ display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; color: var(--text-dim); margin-top: 0.7rem; display: none; }}
  .step-track.show {{ display: flex; }}
  .step-track .step {{ display: flex; align-items: center; gap: 0.3rem; padding: 0.25rem 0.6rem; border-radius: 999px; background: var(--surface-2); border: 1px solid var(--border); }}
  .step-track .step.active {{ color: var(--accent); border-color: var(--accent); }}
  .step-track .step.done {{ color: var(--accent-2); border-color: var(--accent-2); }}
  .step-track .sep {{ opacity: 0.4; }}

  .result {{ margin-top: 0.9rem; padding: 0.9rem 1rem; border-radius: 12px; background: var(--surface-2); border: 1px solid var(--border); font-size: 0.85rem; line-height: 1.7; word-break: break-all; display: none; }}
  .result.show {{ display: block; animation: fade-in 0.25s ease; }}
  .result.success {{ border-color: var(--accent-2); }}
  .result.error {{ border-color: var(--danger); color: var(--danger); }}
  @keyframes fade-in {{ from {{ opacity: 0; transform: translateY(-4px); }} to {{ opacity: 1; transform: translateY(0); }} }}

  .share-btn {{ margin-top: 0.7rem; display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.65rem 1rem; border-radius: 10px; background: #000; color: #fff; text-decoration: none; font-size: 0.85rem; font-weight: 600; }}

  /* --- supporter list --- */
  .supporter-list {{ display: flex; flex-direction: column; gap: 0.4rem; max-height: 150px; overflow-y: auto; padding-right: 0.2rem; }}
  .supporter {{ display: flex; gap: 0.6rem; padding: 0.55rem 0.65rem; border-radius: 10px; background: var(--surface-2); border: 1px solid var(--border); }}
  .supporter-avatar {{ width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0; }}
  .supporter-body {{ min-width: 0; flex: 1; }}
  .supporter-row {{ display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; }}
  .amount-pill {{ font-size: 0.78rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 999px; background: color-mix(in srgb, var(--accent-2) 18%, transparent); color: var(--accent-2); white-space: nowrap; }}
  .supporter-comment {{ margin-top: 0.3rem; font-size: 0.85rem; color: var(--text-dim); font-style: italic; }}

  .empty-state {{ text-align: center; padding: 1rem; color: var(--text-dim); }}
  .empty-state-icon {{ font-size: 1.3rem; margin-bottom: 0.3rem; }}
</style>
</head>
<body>
<div class="shell">
  <div class="header-row">
    <div>
      <a class="back" href="/">&larr; Disclosure Proof</a>
      <h1>{heading_authority} &mdash; {heading_type}<span class="ja">{safe_authority} &mdash; {safe_type}</span></h1>
      <p class="meta">Notarized by {escape(_short(req['requester']))} on {escape(req['recorded_at']) if isinstance(req['recorded_at'], str) else req['recorded_at']}</p>
    </div>
    <div class="status-badge"><span class="dot"></span> Recorded on-chain · Base Sepolia · EAS<span class="ja">オンチェーン記録済み</span></div>
  </div>

  <div class="layout">
    <div class="col">
      <section class="card">
        <h2>Request details<span class="ja">請求内容</span></h2>
        <dl>
          <dt>Target authority<span class="ja">請求先</span></dt><dd>{authority_field}</dd>
          <dt>Request type<span class="ja">請求の種類</span></dt><dd>{type_field}</dd>
          <dt>Summary<span class="ja">要約</span></dt><dd>{summary_field}</dd>
          <dt>Document hash<span class="ja">文書ハッシュ</span></dt><dd class="mono">{safe_doc_hash}</dd>
          <dt>Requester<span class="ja">請求者</span></dt><dd class="mono"><a href="{EXPLORER_ADDRESS_URL}/{safe_requester}" target="_blank">{safe_requester}</a></dd>
          <dt>Attestation<span class="ja">証明レコード</span></dt><dd class="mono"><a href="{EXPLORER_ATTESTATION_URL}/{escape(uid)}" target="_blank">{escape(_short(uid))} &#8599;</a></dd>
        </dl>
      </section>

      <section class="card">
        <h2>Supporters<span class="ja">応援者一覧</span></h2>
        {tips_html}
      </section>
    </div>

    <div class="col">
      <section class="card">
        <h2>Support this request<span class="ja">この請求を応援する</span></h2>
        <div class="stats">
          <div class="stat-tile"><div class="stat-value">{escape(totals_text)}</div><div class="stat-label">Raised<span class="ja"> / 集まった応援</span></div></div>
          <div class="stat-tile"><div class="stat-value">{case['tip_count']}</div><div class="stat-label">Supporters<span class="ja"> / 応援者数</span></div></div>
        </div>

        <div class="reaction-row" id="reaction-row">
          <button type="button" class="reaction-btn" data-reaction="watch" data-title="Watching / 見守る" title="Connect your wallet first / 先にウォレットを接続してください" disabled><span class="reaction-emoji">&#128064;</span><span class="reaction-count">0</span></button>
          <button type="button" class="reaction-btn" data-reaction="want_to_know" data-title="I want to know too / 私も知りたい" title="Connect your wallet first / 先にウォレットを接続してください" disabled><span class="reaction-emoji">&#128587;</span><span class="reaction-count">0</span></button>
          <button type="button" class="reaction-btn" data-reaction="fork_local" data-title="In my area too / 自分の自治体でも" title="Connect your wallet first / 先にウォレットを接続してください" disabled><span class="reaction-emoji">&#128257;</span><span class="reaction-count">0</span></button>
        </div>
        <div class="result" id="reaction-result"></div>

        <button class="wallet-btn" id="connect-wallet">&#129443; Connect Wallet<span class="ja">ウォレットを接続</span></button>
        <div class="result" id="wallet-result"></div>

        <form id="tip-form">
          <div class="field">
            <label>Currency<span class="ja">通貨</span></label>
            <div class="segmented" id="currency-toggle">
              <button type="button" class="segmented-btn active" data-currency="ETH">ETH</button>
              <button type="button" class="segmented-btn" data-currency="USDC">USDC</button>
            </div>
          </div>
          <div class="field">
            <label>Tip amount<span class="ja">投げ銭額</span></label>
            <div class="amount-input-wrap">
              <input type="number" id="amount" step="0.000001" min="0" placeholder="0.0001" required>
              <span class="amount-suffix" id="amount-suffix">ETH</span>
            </div>
            <div class="chip-row" id="amount-chips"></div>
            <div class="price-hint" id="price-hint"></div>
          </div>
          <div class="field"><label>Message <span class="ja">応援メッセージ（任意）</span></label><input type="text" id="comment" placeholder="Keep going! / 応援しています！"></div>
          <button type="submit" class="btn-primary" id="tip-submit" disabled title="Connect your wallet first / 先にウォレットを接続してください">
            <span class="spinner"></span>
            <span class="btn-label">&#128184; Send Tip<span class="ja">投げ銭する</span></span>
          </button>
          <div class="step-track" id="step-track">
            <span class="step" id="step-1">1&nbsp;&middot;&nbsp;Transfer</span>
            <span class="sep">&rarr;</span>
            <span class="step" id="step-2">2&nbsp;&middot;&nbsp;Record on-chain</span>
          </div>
        </form>
        <div class="result" id="tip-result"></div>
        <div id="share-slot"></div>
      </section>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/ethers@6.13.4/dist/ethers.umd.min.js"></script>
<script>
const CASE_UID = {uid!r};
const RECIPIENT = {req['requester']!r};
const BASE_SEPOLIA_CHAIN_ID_HEX = "0x14a34";
const BASE_SEPOLIA_PARAMS = {{ chainId: BASE_SEPOLIA_CHAIN_ID_HEX, chainName: "Base Sepolia", nativeCurrency: {{ name: "Base Sepolia ETH", symbol: "ETH", decimals: 18 }}, rpcUrls: ["https://sepolia.base.org"], blockExplorerUrls: ["https://sepolia.basescan.org"] }};
const EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021";
const TIP_SCHEMA_UID = "0xb047ba9c9239b1578838500266a3199191c45b28b001d2b3ab3e1e2cb7815b58";
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const TOKENS = {{ ETH: {{ address: ZERO_ADDRESS, decimals: 18 }}, USDC: {{ address: "0x036CbD53842c5426634e7929541eC2318f3dCF7e", decimals: 6 }} }};
const EAS_ABI = ["function attest((bytes32 schema,(address recipient,uint64 expirationTime,bool revocable,bytes32 refUID,bytes data,uint256 value) data) request) payable returns (bytes32)", "event Attested(address indexed recipient, address indexed attester, bytes32 uid, bytes32 indexed schemaUID)"];

const AMOUNT_PRESETS = {{ ETH: ["0.001", "0.005", "0.01", "0.05"], USDC: ["1", "5", "10", "25"] }};
let provider, signer, eas;
let selectedCurrency = "ETH";

function short(addr) {{ return addr ? addr.slice(0, 6) + "..." + addr.slice(-4) : ""; }}
function txLink(hash) {{ return `<a href="https://sepolia.basescan.org/tx/${{hash}}" target="_blank">${{short(hash)}} &#8599;</a>`; }}
function setResult(el, html, isError = false) {{
  el.classList.add("show");
  el.classList.toggle("error", isError);
  el.classList.toggle("success", !isError);
  el.innerHTML = html;
}}

function renderAmountChips() {{
  const wrap = document.getElementById("amount-chips");
  const amountInput = document.getElementById("amount");
  wrap.innerHTML = AMOUNT_PRESETS[selectedCurrency]
    .map((v) => `<button type="button" class="chip" data-amount="${{v}}">${{v}} ${{selectedCurrency}}</button>`)
    .join("");
  wrap.querySelectorAll(".chip").forEach((chip) => {{
    chip.addEventListener("click", () => {{
      amountInput.value = chip.dataset.amount;
      wrap.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
    }});
  }});
}}
document.getElementById("amount").addEventListener("input", () => {{
  document.querySelectorAll("#amount-chips .chip").forEach((c) => c.classList.toggle("active", c.dataset.amount === document.getElementById("amount").value));
  updatePriceHint();
}});

document.getElementById("currency-toggle").addEventListener("click", (e) => {{
  const btn = e.target.closest(".segmented-btn");
  if (!btn) return;
  selectedCurrency = btn.dataset.currency;
  document.querySelectorAll("#currency-toggle .segmented-btn").forEach((b) => b.classList.toggle("active", b === btn));
  document.getElementById("amount-suffix").textContent = selectedCurrency;
  renderAmountChips();
  updatePriceHint();
}});
renderAmountChips();

// Read-only USD reference price (Uniswap V3 Quoter on Base mainnet, no
// wallet/gas involved -- see uniswap_price.py). Purely informational: it
// never affects what's actually sent, just gives ETH tippers a sense of
// scale in dollar terms.
let ethUsdPrice = null;
fetch("/api/price/eth-usd").then((r) => r.json()).then((d) => {{ ethUsdPrice = d.usd_per_eth; updatePriceHint(); }}).catch(() => {{}});

function updatePriceHint() {{
  const hint = document.getElementById("price-hint");
  const amount = parseFloat(document.getElementById("amount").value);
  if (selectedCurrency !== "ETH" || !ethUsdPrice || !amount) {{ hint.textContent = ""; return; }}
  const usd = (amount * ethUsdPrice).toLocaleString(undefined, {{ maximumFractionDigits: 2 }});
  hint.innerHTML = `&asymp; $${{usd}} <span class="src">(via Uniswap)</span>`;
}}

async function connectWallet() {{
  const out = document.getElementById("wallet-result");
  const walletBtn = document.getElementById("connect-wallet");
  if (!window.ethereum) {{ setResult(out, "No wallet extension found. / ウォレットが見つかりません。", true); return; }}
  try {{
    walletBtn.disabled = true;
    provider = new ethers.BrowserProvider(window.ethereum);
    await provider.send("eth_requestAccounts", []);
    const network = await provider.getNetwork();
    if ("0x" + network.chainId.toString(16) !== BASE_SEPOLIA_CHAIN_ID_HEX) {{
      try {{ await window.ethereum.request({{ method: "wallet_switchEthereumChain", params: [{{ chainId: BASE_SEPOLIA_CHAIN_ID_HEX }}] }}); }}
      catch (e) {{ if (e.code === 4902) {{ await window.ethereum.request({{ method: "wallet_addEthereumChain", params: [BASE_SEPOLIA_PARAMS] }}); }} else {{ throw e; }} }}
      provider = new ethers.BrowserProvider(window.ethereum);
    }}
    signer = await provider.getSigner();
    eas = new ethers.Contract(EAS_CONTRACT_ADDRESS, EAS_ABI, signer);
    const address = await signer.getAddress();
    setResult(out, `Connected: ${{address}} / 接続済み`);
    walletBtn.textContent = "\\uD83E\\uDD8A " + short(address) + " connected";
    walletBtn.classList.add("connected");
    document.getElementById("tip-submit").disabled = false;
    document.getElementById("tip-submit").removeAttribute("title");
    document.querySelectorAll(".reaction-btn").forEach((b) => {{
      b.disabled = false;
      b.title = b.dataset.title;
    }});
    loadReactions();
  }} catch (err) {{
    walletBtn.disabled = false;
    setResult(out, "Connection failed / 接続失敗: " + err.message, true);
  }}
}}
document.getElementById("connect-wallet").addEventListener("click", connectWallet);

async function loadReactions() {{
  try {{
    const address = signer ? await signer.getAddress() : null;
    const url = `/api/case/${{CASE_UID}}/reactions` + (address ? `?address=${{address}}` : "");
    const res = await fetch(url);
    const data = await res.json();
    document.querySelectorAll(".reaction-btn").forEach((btn) => {{
      const r = data[btn.dataset.reaction];
      if (!r) return;
      btn.querySelector(".reaction-count").textContent = r.count;
      btn.classList.toggle("mine", !!r.mine);
    }});
  }} catch (err) {{ /* reactions are a soft feature -- fail silently */ }}
}}
loadReactions();

document.querySelectorAll(".reaction-btn").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    const out = document.getElementById("reaction-result");
    if (!signer) {{ setResult(out, "Please connect your wallet first / 先にウォレットを接続してください", true); return; }}
    const reaction = btn.dataset.reaction;
    document.querySelectorAll(".reaction-btn").forEach((b) => (b.disabled = true));
    try {{
      const address = await signer.getAddress();
      const timestamp = Math.floor(Date.now() / 1000);
      const message = `Disclosure Proof reaction (no gas, not a transaction)\ncase: ${{CASE_UID.toLowerCase()}}\nreaction: ${{reaction}}\ntimestamp: ${{timestamp}}`;
      const signature = await signer.signMessage(message);
      const res = await fetch(`/api/case/${{CASE_UID}}/reactions`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ reaction, address, timestamp, signature }}),
      }});
      if (!res.ok) {{
        const errBody = await res.json().catch(() => ({{}}));
        throw new Error(errBody.detail || `HTTP ${{res.status}}`);
      }}
      const data = await res.json();
      document.querySelectorAll(".reaction-btn").forEach((b) => {{
        const r = data[b.dataset.reaction];
        if (!r) return;
        b.querySelector(".reaction-count").textContent = r.count;
        b.classList.toggle("mine", !!r.mine);
      }});
      out.classList.remove("show");
    }} catch (err) {{
      setResult(out, "Error / エラー: " + err.message, true);
    }} finally {{
      document.querySelectorAll(".reaction-btn").forEach((b) => (b.disabled = false));
    }}
  }});
}});

function setStep(n) {{
  const track = document.getElementById("step-track");
  track.classList.add("show");
  const step1 = document.getElementById("step-1");
  const step2 = document.getElementById("step-2");
  step1.classList.toggle("active", n === 1);
  step1.classList.toggle("done", n > 1);
  step2.classList.toggle("active", n === 2);
  step2.classList.toggle("done", n > 2);
}}

document.getElementById("tip-form").addEventListener("submit", async (e) => {{
  e.preventDefault();
  const btn = document.getElementById("tip-submit");
  const out = document.getElementById("tip-result");
  btn.disabled = true;
  btn.classList.add("loading");
  document.getElementById("step-track").classList.add("show");
  try {{
    if (!signer) throw new Error("Please connect your wallet first / 先にウォレットを接続してください");
    const currency = TOKENS[selectedCurrency];
    const amount = ethers.parseUnits(document.getElementById("amount").value || "0", currency.decimals);
    const comment = document.getElementById("comment").value;
    setStep(1);
    setResult(out, `Please sign the ${{selectedCurrency}} transfer in your wallet... (1/2)`);
    let transferReceipt;
    if (currency.address === ZERO_ADDRESS) {{
      const tx = await signer.sendTransaction({{ to: RECIPIENT, value: amount }});
      transferReceipt = await tx.wait();
    }} else {{
      const token = new ethers.Contract(currency.address, ["function transfer(address to, uint256 amount) returns (bool)"], signer);
      const tx = await token.transfer(RECIPIENT, amount);
      transferReceipt = await tx.wait();
    }}
    setStep(2);
    setResult(out, "Please sign the support record in your wallet... (2/2)");
    const coder = ethers.AbiCoder.defaultAbiCoder();
    const encodedData = coder.encode(["address", "address", "uint256", "string"], [currency.address, ZERO_ADDRESS, amount, comment]);
    const attestTx = await eas.attest({{ schema: TIP_SCHEMA_UID, data: {{ recipient: RECIPIENT, expirationTime: 0, revocable: true, refUID: CASE_UID, data: encodedData, value: 0 }} }});
    const attestReceipt = await attestTx.wait();
    setStep(3);
    setResult(out, `&#9989; Tip sent (signed by your own wallet) / 投げ銭完了<br>transfer: ${{txLink(transferReceipt.hash)}}<br>record: ${{txLink(attestReceipt.hash)}}`);
    const shareUrl = window.location.href.split("?")[0];
    const text = `I supported a Freedom-of-Information disclosure request. / 情報公開請求を応援しました。 #DisclosureProof`;
    const intent = `https://twitter.com/intent/tweet?text=${{encodeURIComponent(text)}}&url=${{encodeURIComponent(shareUrl)}}`;
    document.getElementById("share-slot").innerHTML = `<a class="share-btn" href="${{intent}}" target="_blank">&#128293; Share this on X / この応援をXでシェア</a>`;
  }} catch (err) {{
    setResult(out, "Error / エラー: " + err.message, true);
  }} finally {{
    btn.disabled = false;
    btn.classList.remove("loading");
  }}
}});
</script>
</body>
</html>"""
