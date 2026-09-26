# Civic Disclosure Tip (information-disclosure-proof)

行政文書開示請求（Freedom of Information disclosure request）を、
[EAS (Ethereum Attestation Service)](https://attest.org) を使って
Base Sepolia 上にオンチェーンで証明として刻印し、Caseごとに公開される
プレビューページで市民が投げ銭・シェアで応援できるプロジェクトです。

> This project is unrelated to [LENS Protocol](https://lens.xyz).

## 位置づけ: このプロジェクトが証明・可視化する層を担う

「怒りを開示請求に変換するAIエージェント」（[Civic Lens](https://civic-lens-jp.vercel.app)、
Google Cloud ADK製、Zenn Agentic AIミニハッカソン優勝作品）と本プロジェクトは、
役割を分けています。

| | 作成（入口） | 証明・可視化（本プロジェクト） |
|---|---|---|
| 何をするか | 怒り→条例マッチング→開示請求書の文面生成 | 提出という事実をオンチェーンに刻印し、検証・応援・拡散できる形にする |
| 責務の境界 | 請求書の**下書き**を作るところまで | 記録された内容を**改ざん不可能な形で**保持・表示するところから |
| 実装 | FastAPI + Gemini/Vertex AI (Python) | FastAPI + EAS + ethers.js (Python/TS) |

Civic Lensで生成した請求書をもとに、実際に市役所へ提出したという行為を
本人のウォレットで刻印する、という繋がりを想定しています。ただし本プロジェクトは
Civic Lens経由でなくても単体で使えます。

## 課題

日本には公的なオンブズマン制度が存在せず、行政文書開示請求を行う市民・
市民オンブズマン団体の活動は孤独になりがちです。また、いつ・どの実施機関に・
何を請求したかという記録は請求者の手元にしか残らず、後から第三者が検証
できません。さらに、応援したい閲覧者の目に触れる場所（SNS等）と、
実際に何を請求したかの内容が分かる場所が一致しておらず、内容を確認
しないまま応援・拡散が起きてしまうという問題もあります。

本プロジェクトは以下によってこれを解決します:

1. **証明**: 請求内容のハッシュと請求先・請求種別を改ざん不可能な形で
   オンチェーンに刻印し、請求の存在と内容を誰でも検証できるようにする。
   刻印は**請求者本人のウォレットで署名**され、サーバーが代理署名することはない
2. **可視化**: 刻印された請求1件ごとに、独立した公開URL（Caseプレビュー
   ページ）が発行される。閲覧者はこのページで請求内容を確認してから
   応援できる
3. **応援**: 開示請求をETHまたはUSDCの「投げ銭」で応援できるようにし、
   地道な市民活動を可視化・支援する

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

### 1. 開示請求の刻印（トップページ）

トップページ（`static/index.html`）では、請求先・請求種別・請求内容（原本からの
逐語引用）・請求書ハッシュ・根拠法令をEASでオンチェーンに記録する**ことだけ**を
行う。投げ銭・応援UIはここにはなく、刻印が完了すると次項のCaseプレビューページ
へのリンクが表示される。

このスキーマは civic-lens リポジトリと共通仕様にしている（フィールド名・順序を
揃えてある）。要約（要約者の解釈・省略が入る自由記述）ではなく、原本からの
逐語引用（`requestedDocuments`）のみを平文で記録する設計にしているのは、
「正確な記録」であるべき開示請求の証跡に、記録者の言い換えが構造的に入り込む
余地を残さないため。公開前には `pii_scan.py`（civic-lens の `scan_personal_info`
と同じロジック）で氏名・住所等らしき記述を検出し、本人の確認なしには記録しない。

```
string recordId,            // 呼び出し側が割り振るID（例: "req-ab12cd34"）
string authority,            // 実施機関の正式名称。例: "〇〇市長", "〇〇県知事", "〇〇市教育委員会"
string requestType,          // 請求の種類。例: "行政文書開示請求"
string requestedDocuments,   // 請求する公文書の特定内容（原本からの逐語引用。要約・言い換えは不可）
bytes32 documentHash,        // 請求書本文のsha256ハッシュ（改ざん検知用）
uint256 timestamp,           // 請求日時（unix time）
string legalBasis            // 根拠法令・条例。例: "情報公開法"
```

Schema UID (Base Sepolia): 旧スキーマ（`summary`を含む4フィールド版）は
`0x92cf840e48d7893e83e58e67e6209f0a9ad5b720bafdffc2fd740a38585d549a` として
登録済みだったが、上記の新スキーマは別のUIDとして再登録が必要（EASスキーマは
不変のため）。新しいUIDを`register_schema.py`で発行し、`.env`の
`EAS_SCHEMA_UID`を更新すること。

### 2. Caseプレビューページ（`/case/{attestation_uid}`）— 投げ銭・応援・シェアはここで行う

刻印された開示請求1件ごとに発行される独立した公開ページ。**登録フォームとは
意図的に別の画面**にしてあり、このページだけが以下を担う:

- 請求内容（請求先・種別・請求する公文書の特定内容・根拠法令・文書ハッシュ・
  請求者アドレス）をオンチェーンデータから直接表示
- 投げ銭フォーム（ETH/USDC、応援メッセージ付き）
- これまでの応援者一覧と応援総額
- このページ自体へのX共有ボタン

サーバーサイドでHTMLを描画しており、`og:title`/`og:description`/`og:url`
などのOGPタグを埋め込んでいる。そのため、SNSにリンクを貼った際、JavaScriptを
実行しないクローラーでも「何の開示請求か」が正しくプレビューされる。

投げ銭は登録フォームには置かず、必ずこのCaseページ上で、請求内容を見た
うえで行われる導線にしてある。これは「情報開示請求」という公的な申請行為の
記録と、「投げ銭」という私的な支援行為を同じ画面に混在させないための設計判断。

### 3. 台帳の一般化（`ledger.py`）

以前は`leaderboard.py`と`trending.py`にそれぞれEASのattestationデコード
処理が重複していたが、`ledger.py`に一本化した。以下を提供する:

- `get_request(uid)` / `fetch_requests()` — 開示請求attestationの読み取り
- `fetch_tips_for(uid)` — ある請求（`refUID`で参照）への投げ銭一覧
- `get_case(uid)` — 上記2つをまとめ、Caseプレビューページ・APIが必要とする
  形（請求内容＋応援一覧＋通貨別合計）にして返す

台帳は本プロジェクト自身のデータベースを持たず、EASの公開GraphQL
インデクサから毎回直接読み出す。表示内容そのものが検証済みの事実になり、
運営者側が中身を改変・捏造する余地がない。

この構成にしたのは、将来的に開示請求以外の段階（実施機関の処分、審査請求、
審査会の答申、裁決）を追加する場合に備えるため。各段階が新しいEASスキーマ
として登録されても、`get_case()`が返す辞書に新しいキー（例:
`case["decision"]`）を足すだけで済み、読み取り側のロジックを個別に
書き直す必要がない設計にしてある（本ハッカソン提出範囲では未実装。
「今後の展望」参照）。

### 4. 投げ銭（ETH / USDC + 紹介リレー）

Caseページから、対象の開示請求（attestation UID）に紐づけて、請求者の
ウォレットへ実際にETHまたはUSDCを送金すると同時に、応援メッセージを
オンチェーンに記録する（`refUID`で元のattestationに紐づけ）。

```
address token,      // トークンアドレス（ゼロアドレス = ETH、それ以外はERC-20コントラクト）
address referrer,   // 紹介者のアドレス（なければゼロアドレス）
uint256 amount,     // 投げ銭額（トークンの最小単位。ETHはwei、USDCは6桁単位）
string  comment     // 応援メッセージ
```

Schema UID (Base Sepolia): `0xb047ba9c9239b1578838500266a3199191c45b28b001d2b3ab3e1e2cb7815b58`

USDCはCircle公式のBase Sepoliaテストネットコントラクト
（`0x036CbD53842c5426634e7929541eC2318f3dCF7e`）を使用。

### 5. リーダーボード / 急上昇ランキング（トップページ）

投げ銭・紹介の集計を、別データベースを持たず`ledger.py`経由でEASの
GraphQLインデクサから直接計算して返す（`GET /leaderboard`）。ETH/USDCなど
通貨ごとに内訳を分けて集計する。`GET /trending`は直近24時間の応援数で
ランキングし、話題になった請求をすぐに可視化する。各エントリは対応する
Caseページへのリンクになっている。

### 6. ENS名表示（スポンサー技術: ENS、※従来のENS。ENSv2ではない）

リーダーボード上のアドレスは、ENS名が登録されていれば `peikun.eth` のように
人間が読める名前で表示される。これはEthereumメインネット上の**従来のENSの
逆引き解決**（`ens_resolve.py`、`w3.ens.name()`）であり、ENSv2の機能は使用していない。
ENSレコードはBase Sepoliaとは別の読み取り専用メインネットRPC接続で解決している
（秘密鍵は使用しない）。

ENS名の利用は個人の請求者には**強制しない**。プライバシー上の懸念がある個人
請求者は、ENS名を登録しなければリーダーボード上ではアドレス省略表記
（`0x1234...abcd`）のまま表示され、身元と請求内容が紐づくことはない。

### 7. 団体サブネーム登録（ENSv2互換・自己ホスト、団体向けオプション機能）

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

### 8. 英語自動翻訳（Caseページ）

Caseページの請求先・請求種別・請求する公文書の特定内容は、オンチェーンには日本語で記録されている
（日本の行政に対する実際の開示請求のため）。英語話者（ETHGlobal審査員等）
のために、[`translate.py`](translate.py)が`GEMINI_API_KEY`が設定されていれば
Gemini APIで、未設定ならAPIキー不要のMyMemoryにフォールバックして機械翻訳を
生成し、原文の日本語と並べて「machine-translated from Japanese」と明示した
上で表示する。翻訳はあくまで補助であり、日本語原文が常に正（オンチェーンの
真実）である。

### 9. リアクション（👀🙋🔁、Upstash Redis）

投げ銭とは別に、より気軽な「反応」を3種類に限定して用意している（自由記述の
コメント欄はなし、荒らし対策）:

- 👀 見守る（watch）
- 🙋 私も知りたい（want_to_know）
- 🔁 自分の自治体でも（fork_local）

投げ銭と違い、絵文字1つの反応にガス代・オンチェーンtxを要求するのはUXとして
過剰なので、[`reactions.py`](reactions.py)ではウォレットの**署名のみ**
（`personal_sign`、ガス代なし・トランザクションではない）で本人確認し、
Upstash Redis（Setのトグル）に記録する。1ウォレット1種類につき1回まで、
誰が反応したかは公開せず件数のみ表示する。`UPSTASH_REDIS_REST_URL` /
`UPSTASH_REDIS_REST_TOKEN`が未設定でもアプリ自体は起動し、反応機能だけが
0件表示のまま無効化される。

### 10. Uniswap価格参照（読み取り専用、スポンサー技術: Uniswap）

Caseページで投げ銭額（ETH）を入力すると、「&asymp; $26.88 (via Uniswap)」の
ようにドル換算の目安が表示される。[`uniswap_price.py`](uniswap_price.py)が
Baseメインネット上のUniswap V3 Quoter（`quoteExactInputSingle`を`eth_call`
で呼ぶ読み取り専用シミュレーション）に、実際にUniswapの公式フロントエンドが
見積もりを取るのと同じ方法で問い合わせる。ウォレット署名・ガス代・実際の
スワップは一切発生しない。投げ銭自体はこれまで通りBase Sepolia上でETH/USDC
を直接送金する（Base SepoliaにUniswapの公式デプロイ・流動性がある保証がない
ため、投げ銭のスワップ機能そのものはスコープ外とした。「今後の展望」参照）。

### 11. フロントエンド

- `static/index.html` — ウォレット接続・開示請求の刻印・団体サブネーム登録・
  リーダーボード・急上昇ランキング閲覧
- Caseページ（`/case/{uid}`、`case_page.py`が生成）— 請求内容の確認・
  英語自動翻訳・投げ銭・リアクション・応援者一覧・SNSシェア

## 今後の展望

- **開示請求ライフサイクルの拡張（処分・審査請求・答申・裁決）**: 現在
  オンチェーンに刻印できるのは「①開示請求」のみ。行政法上、これに続く
  「②処分（開示・部分開示・不開示）」「③審査請求」「④審査会の答申」
  「⑤裁決」はそれぞれ法的性格が異なる（②は行政処分、④は諮問機関の
  事実上の意見、⑤は終局判断）。将来的にはこれらをそれぞれ別のEAS
  スキーマとして追加し、共通の`caseId`で束ねることで、1つの開示請求が
  最終的にどう決着したかまで検証可能な形で辿れるようにしたい。
  `ledger.py`の`get_case()`はこの拡張を見込んだ設計にしてある。
- **JPYC対応**: JPYC（日本円ステーブルコイン）は現時点でEthereum・Polygon・
  Avalanche・Gnosis・Shiden・Astar上に展開されているが、Base上にはまだ
  デプロイされていない。BaseにJPYCが対応した際には、ETH・USDCに加えて
  投げ銭通貨として追加し、暗号資産に不慣れな日本の市民でも開示請求者を
  支援しやすくしたい。
- **ENSv2 Namechainへの正式移行**: 現在の団体サブネーム機能（上記「機能」の
  7番）は、ENSv2のL2レジストリ方式に倣った自前コントラクトであり、ENS Labs
  公式のENSv2 Namechain上への登録ではない。公式インフラ上での実装は、
  ENS Labs側の親ドメイン取得・公式L2レジストリとの連携が必要になるため、
  今回のハッカソン提出範囲には含めていない。将来的には公式ENSv2への移行を
  検討したい。
- **投げ銭受け取りウォレットとattestウォレットの分離**: 現在の実装では、
  開示請求者が刻印に使うウォレットと、投げ銭を受け取るウォレットが同一
  アドレスである。今回はこの構成のまま提出するが、請求者の秘匿性を高める
  観点では両者を分離できるようにする余地があり、将来の改訂課題として残す。
- **Civic Lensとの連携API**: Civic Lensで生成した開示請求書を、そのまま
  本プロジェクトのCase刻印に渡せるAPI連携。
- **投げ銭のUniswapスワップ対応**: 現状「10. Uniswap価格参照」は読み取り
  専用のドル換算表示のみで、実際のスワップは行っていない。Uniswapは
  Base Sepolia向けの公式デプロイ・流動性が確認できなかったため（Uniswapの
  公式SDKが対応チェーンとして列挙しているのはBase本番網とEthereum Sepolia
  等で、Base Sepoliaは含まれていない）、投げ銭で使う通貨をその場でETH/USDC
  にスワップする機能は今回のハッカソン提出範囲には含めなかった。将来的には
  投げ銭自体をUniswapが公式対応するチェーンに載せるか、Base本番網への移行と
  合わせて対応したい。

## 動作方法

### 1. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集し、以下を設定:

- `CHAIN_RPC_URL` — Base Sepolia RPCエンドポイント
- `CHAIN_PRIVATE_KEY` — 署名用ウォレットの秘密鍵（**任意**。テストネット専用ウォレット推奨。
  `POST /attest`・`POST /tip`というCLIデモ用フォールバックAPIでのみ使用し、
  ブラウザからの通常利用（ウォレット直接署名）では不要。未設定でもアプリは
  起動する）
- `EAS_CONTRACT_ADDRESS` — EASコントラクトアドレス（デフォルト値で動作）
- `EAS_SCHEMA_UID` — 開示請求用Schema UID（上記）
- `TIP_SCHEMA_UID` — 投げ銭用Schema UID（上記）
- `USDC_CONTRACT_ADDRESS` — USDCコントラクトアドレス（デフォルト値で動作）
- `EASSCAN_GRAPHQL_URL` — EAS GraphQLインデクサ（デフォルト値で動作）
- `ENS_RPC_URL` — ENS解決用メインネットRPC（デフォルト値で動作）
- `ENSV2_REGISTRY_ADDRESS` — 団体サブネームレジストリのコントラクトアドレス
  （下記「3. ENSv2団体サブネームレジストリのデプロイ」参照。既存のデプロイ済み
  アドレス `0x67e48e5e0DA4a160D0Cb5cE12ac311087ed68F1D` を使う場合は設定するだけでよい）
- `GEMINI_API_KEY` — Caseページの英語自動翻訳用（**任意**。未設定なら
  APIキー不要のMyMemoryにフォールバックする。無料枠は
  [aistudio.google.com/apikey](https://aistudio.google.com/apikey)で発行）
- `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` — リアクション機能用
  （**任意**。未設定でもアプリは起動し、反応機能だけ0件表示で無効化される。
  [upstash.com](https://upstash.com)の無料枠でRedisデータベースを作成し、
  REST APIのURL・トークンを設定する）

ブラウザからフロントエンド経由で使う場合は、MetaMask等のウォレットが
署名するためサーバー側の秘密鍵は使われない。Uniswap価格参照
（`uniswap_price.py`）は公開のBaseメインネットRPCを直接使うため、
環境変数の設定は不要。

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
開示請求を刻印すると、`http://localhost:8000/case/<attestation_uid>` に
そのCaseプレビューページが表示される。

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
- **スポンサー技術**:
  - **ENS**（$10,000枠）— 応援者・紹介者のアドレス表示（従来のENS逆引き）、
    およびENSv2互換の団体サブネームレジストリ（自己ホスト、Base Sepolia）
  - **Uniswap**（$10,000枠）— Baseメインネット上のUniswap V3 Quoterから
    読み取り専用でETH/USDC価格を取得し、Caseページの投げ銭額にドル換算
    表示を添える（実スワップなし）
- **AI技術**: Gemini API（Caseページの英語自動翻訳、任意・未設定ならMyMemoryに
  フォールバック）。本プロジェクトの中心はWeb3インフラで、開示請求書の生成
  そのもののAI活用は「作成」層を担う姉妹プロジェクトCivic Lens側の役割
- **実行環境**: FastAPI + 静的HTML/JSフロントエンド + サーバーサイド
  レンダリングのCaseプレビューページ

## デモ・提出資料

- [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md) — 開発ステージの記録
- [docs/narration_script.md](docs/narration_script.md) — デモ動画用の読み上げ原稿
- [docs/demo_walkthrough.md](docs/demo_walkthrough.md) — 実演入りデモ動画の台本

実演・デモ動画中に映るウォレットアドレスはテストネット上の実演専用ウォレットで
あり、本番運用や個人の実ウォレットとは無関係。

## 提出に向けたTODO

- ~~**デプロイ**~~ ✅ 完了。Vercelにデプロイ済み: **https://civic-disclosure-tip.vercel.app**
  （旧URL `https://information-disclosure-proof.vercel.app` は308リダイレクトで新URLへ転送）
  （`vercel.json`の`rewrites`で`/api/index`（`api/index.py`、`app.py`のFastAPI
  appを再エクスポートするだけのエントリポイント）に流す構成。本番の環境変数は
  `CHAIN_RPC_URL`・`EAS_CONTRACT_ADDRESS`・`EAS_SCHEMA_UID`・`TIP_SCHEMA_UID`・
  `USDC_CONTRACT_ADDRESS`・`EASSCAN_GRAPHQL_URL`・`ENS_RPC_URL`・
  `ENSV2_REGISTRY_ADDRESS`・`SCHEMA_REGISTRY_ADDRESS`のみを設定しており、
  いずれも秘密情報ではない（RPC URLは2つとも公開エンドポイント、それ以外は
  公開されているコントラクトアドレス・Schema UID）。**`CHAIN_PRIVATE_KEY`は
  本番環境変数として登録していない**——刻印・投げ銭はどちらもブラウザの
  ウォレットが直接署名する設計であり、この鍵は`POST /attest`・`POST /tip`
  というCLIデモ用のサーバー代理署名フォールバックでしか使われないため
  （`attest.py`・`tip.py`は鍵が無い場合、起動は成功しこのフォールバックAPIを
  呼んだ時だけ明示的なエラーを返す）。
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
