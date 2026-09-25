# information-disclosure-proof

行政文書開示請求（Freedom of Information disclosure request）を、
[EAS (Ethereum Attestation Service)](https://attest.org) を使って
Base Sepolia 上にオンチェーンで証明として刻印し、市民が投げ銭で
応援できるプロジェクトです。

> This project is unrelated to [LENS Protocol](https://lens.xyz).

## 課題

日本には公的なオンブズマン制度が存在せず、行政文書開示請求を行う市民・
市民オンブズマン団体の活動は孤独になりがちです。また、いつ・どの実施機関に・
何を請求したかという記録は請求者の手元にしか残らず、後から第三者が検証
できません。

本プロジェクトは以下によってこれを解決します:

1. **証明**: 請求内容のハッシュと請求先・請求種別を改ざん不可能な形で
   オンチェーンに刻印し、請求の存在と内容を誰でも検証できるようにする。
   刻印は**請求者本人のウォレットで署名**され、サーバーが代理署名することはない
2. **応援**: 開示請求をETHまたはUSDCの「投げ銭」で応援できるようにし、
   地道な市民活動を可視化・支援する。応援は紹介者付きで記録され、
   応援の輪が広がる仕組みを持つ

## 対象ユーザー

行政文書開示請求を行う市民・市民オンブズマン団体、およびそれを応援したい市民。

## 開発について

本リポジトリはETHGlobal Tokyo 2026向けに、ハッカソン開催中にゼロから
段階的に開発しました。開発の進め方・各ステージの動作確認記録は
[docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) を参照してください。

## 機能

### 0. ウォレット直接署名（サーバー代理署名なし）

フロントエンドはMetaMask等のウォレットに直接接続し、ethers.jsで**ユーザー本人が**
Base Sepolia上のEASコントラクトへattestationを送信する。バックエンドの秘密鍵は
CLIデモ・API単体テスト用の代替経路としてのみ使い、実運用のフロントエンドは
サーバーが代理署名することはない。

### 1. 開示請求の刻印

請求先・請求種別・請求書ハッシュ・要約をEASでオンチェーンに記録する。

```
string targetAuthority,  // 実施機関の正式名称。例: "〇〇市長", "〇〇県知事", "〇〇市教育委員会"
string requestType,      // 請求の種類。例: "行政文書開示請求"
bytes32 documentHash,    // 請求書本文のsha256ハッシュ（改ざん検知用）
string summary           // 請求内容の要約
```

Schema UID (Base Sepolia): `0x92cf840e48d7893e83e58e67e6209f0a9ad5b720bafdffc2fd740a38585d549a`

### 2. 投げ銭（ETH / USDC + 紹介リレー）

対象の開示請求（attestation UID）を指定し、請求者のウォレットへ実際にETHまたは
USDCを送金すると同時に、応援メッセージをオンチェーンに記録する（`refUID`で元の
attestationに紐づけ）。紹介者アドレスも記録でき、応援が応援を呼ぶ導線になる。

```
address token,      // トークンアドレス（ゼロアドレス = ETH、それ以外はERC-20コントラクト）
address referrer,   // 紹介者のアドレス（なければゼロアドレス）
uint256 amount,     // 投げ銭額（トークンの最小単位。ETHはwei、USDCは6桁単位）
string  comment     // 応援メッセージ
```

Schema UID (Base Sepolia): `0xb047ba9c9239b1578838500266a3199191c45b28b001d2b3ab3e1e2cb7815b58`

USDCはCircle公式のBase Sepoliaテストネットコントラクト
（`0x036CbD53842c5426634e7929541eC2318f3dCF7e`）を使用。

### 3. リーダーボード / 急上昇ランキング

投げ銭・紹介の集計を、別データベースを持たずEASのGraphQLインデクサから
直接計算して返す（`GET /leaderboard`）。ETH/USDCなど通貨ごとに内訳を分けて
集計する。`GET /trending` は直近24時間の応援数でランキングし、話題になった
請求をすぐに可視化する。

### 4. ワンタップ拡散

投げ銭完了後、その場でX（旧Twitter）投稿画面を開けるボタンを表示する。
投稿リンクには紹介者として自分のアドレスが埋め込まれ、リンク経由で
来た人が投げ銭すると紹介リレーに自動で記録される。

### 5. ENS名表示（スポンサー技術: ENS）

リーダーボード上のアドレスは、ENS名が登録されていれば `peikun.eth` のように
人間が読める名前で表示される。ENSレコードはEthereumメインネット上にあるため、
Base Sepoliaとは別の読み取り専用RPC接続で解決している（秘密鍵は使用しない）。

### 6. フロントエンド

`static/index.html` に、ウォレット接続・開示請求の刻印・投げ銭・
リーダーボード・急上昇ランキング閲覧をすべてブラウザから操作できるUIを実装。

## 動作方法

### 1. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集し、以下を設定:

- `CHAIN_RPC_URL` — Base Sepolia RPCエンドポイント
- `CHAIN_PRIVATE_KEY` — 署名用ウォレットの秘密鍵（テストネット専用ウォレット推奨。CLIデモ用）
- `EAS_CONTRACT_ADDRESS` — EASコントラクトアドレス（デフォルト値で動作）
- `EAS_SCHEMA_UID` — 開示請求用Schema UID（上記）
- `TIP_SCHEMA_UID` — 投げ銭用Schema UID（上記）
- `USDC_CONTRACT_ADDRESS` — USDCコントラクトアドレス（デフォルト値で動作）
- `EASSCAN_GRAPHQL_URL` — EAS GraphQLインデクサ（デフォルト値で動作）
- `ENS_RPC_URL` — ENS解決用メインネットRPC（デフォルト値で動作）

ブラウザからフロントエンド経由で使う場合は、MetaMask等のウォレットが
署名するためサーバー側の秘密鍵は使われない。

### 2. 依存関係のインストール

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. APIサーバー起動

```bash
.venv/bin/uvicorn app:app --reload
```

ブラウザで `http://localhost:8000/` を開くとフロントエンドが表示される。

### 4. CLIでのテスト実行

```bash
.venv/bin/python attest.py
.venv/bin/python leaderboard.py
.venv/bin/python trending.py
```

## 技術スタック

- **チェーン**: Base Sepolia (testnet)
- **オンチェーン証明**: EAS (Ethereum Attestation Service)
- **ウォレット連携**: ethers.js + MetaMask（ユーザー本人による直接署名）
- **通貨**: ETH, USDC（Circle公式Base Sepoliaテストネットコントラクト）
- **スポンサー技術**: ENS（応援者・紹介者のアドレス表示に利用）
- **AI技術**: なし（本プロジェクトはWeb3インフラに特化）
- **実行環境**: FastAPI + 静的HTML/JSフロントエンド

## デモ・提出資料

- [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) — 開発ステージの記録
- [docs/narration_script.md](docs/narration_script.md) — デモ動画用の読み上げ原稿
- [docs/demo_walkthrough.md](docs/demo_walkthrough.md) — 実演入りデモ動画の台本

## 免責事項

本サービスはETHGlobal Tokyo 2026向けの試験実装であり、Base Sepoliaテストネット上で
動作します。実際の情報公開条例に基づく開示請求手続きとしての法的効力を持つものでは
ありません。

## ライセンス

MIT
