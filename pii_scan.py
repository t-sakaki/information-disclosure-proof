"""
Personal-information scan for text that will be recorded on-chain in plain
text (the requestedDocuments field of the disclosure-request attestation).

Ported from civic-lens's web3_attestation.scan_personal_info() so that both
repositories apply the same check before publishing plaintext that anyone
can read forever -- an EAS attestation cannot be edited or deleted.
"""
import re
from typing import Dict, List

MAX_REQUESTED_DOCUMENTS_BYTES = 1000

_PERSONAL_INFO_PATTERNS = [
    ("メールアドレス", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("電話番号", re.compile(r"0\d{1,4}[-(（]?\d{1,4}[-)）]?\d{3,4}")),
    ("郵便番号", re.compile(r"〒?\s?\d{3}-\d{4}")),
    ("番地・住所", re.compile(r"\d+\s?(丁目|番地|番\d+号)|\d+-\d+-\d+")),
    # 「様式」「様態」「氏名」などの一般語は除外する
    ("個人の氏名（敬称つき）", re.compile(r"[一-龥々]{2,5}\s?(氏(?!名)|様(?![式態相子])|さん|君|殿)")),
    ("12桁の番号（個人番号の可能性）", re.compile(r"(?<!\d)\d{12}(?!\d)")),
    ("生年月日", re.compile(r"生年月日")),
]


class PersonalInfoWarning(Exception):
    """公開記録に個人情報らしき記述が含まれ、本人の確認が済んでいない場合に送出する"""

    def __init__(self, warnings: List[Dict[str, str]]):
        self.warnings = warnings
        super().__init__("請求内容に個人情報の可能性がある記述が含まれています")


def normalize_requested_documents(text: str) -> str:
    return " ".join((text or "").split())


def scan_personal_info(text: str) -> List[Dict[str, str]]:
    """オンチェーンに平文で載せる前に、個人情報らしき記述を検出する。"""
    found = []
    for label, pattern in _PERSONAL_INFO_PATTERNS:
        for m in pattern.finditer(text or ""):
            found.append({"type": label, "match": m.group(0)})
    return found
