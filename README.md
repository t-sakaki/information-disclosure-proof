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

### 5. ENS名表示（スポンサー技術: ENS、※従来のENS。ENSv2ではない）

リーダーボード上のアドレスは、ENS名が登録されていれば `peikun.eth` のように
人間が読める名前で表示される。これはEthereumメインネット上の**従来のENSの
逆引き解決**（`ens_resolve.py`、`w3.ens.name()`）であり、ENSv2の機能は使用していない。
ENSレコードはBase Sepoliaとは別の読み取り専用メインネットRPC接続で解決している
（秘密鍵は使用しない）。

ENS名の利用は個人の請求者には**強制しない**。プライバシー上の懸念がある個人
請求者は、ENS名を登録しなければリーダーボード上ではアドレス省略表記
（`0x1234...abcd`）のまま表示され、身元と請求内容が紐づくことはない。

### 6. 団体サブネーム登録（ENSv2互換・自己ホスト、団体向けオプション機能）

NPO・市民オンブズマン団体など、対外的に名乗りたい団体アカウントが任意で
使える機能。`static/index.html` の「団体サブネーム登録」フォームから、
自分のウォレットで直接署名して `sample-npo.npo.disclosureproof.eth` の
ような名前を登録できる（先着順、1アドレス1ラベル）。登録すると
リーダーボード上のアドレス表記がこの名前に置き換わる。

実装は [`contracts/OrgSubnameRegistryV2.sol`](contracts/OrgSubnameRegistryV2.sol)
（Base Sepolia上に自前でデプロイしたコントラクト）で、ENSv2が採用している
「固定の親名前の下で、ラベルとオーナーの対応をL2上のレジストリコントラクトが
直接管理する」という設計方式に倣っている。ただし、**ENS Labs公式のENSv2
Namechain上への登録ではなく**、本プロジェクトが独自にデプロイ・運用する
コントラクトである点は明確にしておく（デプロイ済みアドレスは
`.env.example` の `ENSV2_REGISTRY_ADDRESS` を参照）。個人の請求者はこの
機能を使う義務はなく、既存のENS/未登録アドレス表示にも影響しない。

読み取り側は [`ensv2_org.py`](ensv2_org.py) が担い、`leaderboard.py` は
各アドレスについて団体サブネーム（`org_subname`）→従来のENS名
（`ens_name`）→アドレス省略表記の順で表示名を解決する。

### 7. フロントエンド

`static/index.html` に、ウォレット接続・開示請求の刻印・投げ銭・
リーダーボード・急上昇ランキング閲覧をすべてブラウザから操作できるUIを実装。

## 今後の展望

- **JPYC対応**: JPYC（日本円ステーブルコイン）は現時点でEthereum・Polygon・
  Avalanche・Gnosis・Shiden・Astar上に展開されているが、Base上にはまだ
  デプロイされていない。BaseにJPYCが対応した際には、ETH・USDCに加えて
  投げ銭通貨として追加し、暗号資産に不慣れな日本の市民でも開示請求者を
  支援しやすくしたい。
- **ENSv2 Namechainへの正式移行**: 現在の団体サブネーム機能（上記「機能」の
  6番）は、ENSv2のL2レジストリ方式に倣った自前コントラクトであり、ENS Labs
  公式のENSv2 Namechain上への登録ではない。公式インフラ上での実装は、
  ENS Labs側の親ドメイン取得・公式L2レジストリとの連携が必要になるため、
  今回のハッカソン提出範囲には含めていない。将来的には公式ENSv2への移行を
  検討したい。
- **投げ銭受け取りウォレットとattestウォレットの分離**: 現在の実装では、
  開示請求者が刻印に使うウォレットと、投げ銭を受け取るウォレットが同一
  アドレスである。今回はこの構成のまま提出するが、請求者の秘匿性を高める
  観点では両者を分離できるようにする余地があり、将来の改訂課題として残す。

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
- `ENSV2_REGISTRY_ADDRESS` — 団体サブネームレジストリのコントラクトアドレス
  （下記「3. ENSv2団体サブネームレジストリのデプロイ」参照。既存のデプロイ済み
  アドレス `0x67e48e5e0DA4a160D0Cb5cE12ac311087ed68F1D` を使う場合は設定するだけでよい）

ブラウザからフロントエンド経由で使う場合は、MetaMask等のウォレットが
署名するためサーバー側の秘密鍵は使われない。

### 2. 依存関係のインストール

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. ENSv2団体サブネームレジストリのデプロイ（任意・初回のみ）

既存のデプロイ済みアドレス（Base Sepolia:
`0x67e48e5e0DA4a160D0Cb5cE12ac311087ed68F1D`）を使う場合はこの手順は不要。
自分で新しくデプロイし直す場合は:

```bash
.venv/bin/python deploy_ensv2_registry.py
```

表示されたコントラクトアドレスを `.env` の `ENSV2_REGISTRY_ADDRESS` と、
`static/index.html` 内の `ENSV2_REGISTRY_ADDRESS` 定数の両方に設定する。

### 4. APIサーバー起動

```bash
.venv/bin/uvicorn app:app --reload
```

ブラウザで `http://localhost:8000/` を開くとフロントエンドが表示される。

### 5. CLIでのテスト実行

```bash
.venv/bin/python attest.py
.venv/bin/python leaderboard.py
.venv/bin/python trending.py
.venv/bin/python ensv2_org.py <アドレス>
```

## 技術スタック

- **チェーン**: Base Sepolia (testnet)
- **オンチェーン証明**: EAS (Ethereum Attestation Service)
- **ウォレット連携**: ethers.js + MetaMask（ユーザー本人による直接署名）
- **通貨**: ETH, USDC（Circle公式Base Sepoliaテストネットコントラクト）
- **スポンサー技術**: ENS（応援者・紹介者のアドレス表示に利用）、
  ENSv2互換の団体サブネームレジストリ（自己ホスト、Base Sepolia）
- **AI技術**: なし（本プロジェクトはWeb3インフラに特化）
- **実行環境**: FastAPI + 静的HTML/JSフロントエンド

## デモ・提出資料

- [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) — 開発ステージの記録
- [docs/narration_script.md](docs/narration_script.md) — デモ動画用の読み上げ原稿
- [docs/demo_walkthrough.md](docs/demo_walkthrough.md) — 実演入りデモ動画の台本

実演・デモ動画中に映るウォレットアドレスはテストネット上の実演専用ウォレットで
あり、本番運用や個人の実ウォレットとは無関係。

## 提出に向けたTODO

- **デプロイ**: 現状は `uvicorn app:app --reload` によるローカル実行
  (`http://localhost:8000/`) のみで、ライブのデプロイ先URLは未用意。
  提出前にVercel/Railway/Renderなど何らかのホスティング先にデプロイし、
  `.env` の値（RPC URL・Schema UID等）を本番用に設定する必要がある。
- **デモ動画**: `docs/narration_script.md` / `docs/demo_walkthrough.md` の台本に
  沿って収録する（ETHGlobalルール: 2〜4分、720p以上、肉声のみ、音声加速編集不可）。
- **テストネット残高**: 実演用ウォレットにBase Sepolia ETHおよびテストUSDC
  （[faucet.circle.com](https://faucet.circle.com)）を用意しておく。

## 免責事項

本サービスはETHGlobal Tokyo 2026向けの試験実装であり、Base Sepoliaテストネット上で
動作します。実際の情報公開条例に基づく開示請求手続きとしての法的効力を持つものでは
ありません。

## ライセンス

MIT
