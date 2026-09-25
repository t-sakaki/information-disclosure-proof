# 開発ステージ記録

ETHGlobal Tokyo 2026提出用。本当のハッカソン開始時刻（2026-09-25 夜〜）以降の
作業のみを、このリポジトリのコミット履歴として残す。

## ステージ一覧

- [x] **Stage 1: 最小構成** — EAS attestation単体（`attest.py`）が動く状態
- [x] **Stage 2: API化** — FastAPIで`/attest`エンドポイントを追加
- [x] **Stage 3: 投げ銭（ETH）** — `tip.py`、送金+応援attestation
- [x] **Stage 4: リーダーボード** — EAS GraphQLインデクサからの集計
- [x] **Stage 5: フロントエンド** — ブラウザUI（静的HTML/JS）
- [x] **Stage 6: ウォレット直接署名** — サーバー代理署名の撤廃（ethers.js + MetaMask）
- [x] **Stage 7: マルチ通貨対応** — USDC投げ銭
- [x] **Stage 8: 拡散機能** — 急上昇ランキング・ワンタップシェア
- [x] **Stage 9: ENS対応** — 応援者・紹介者のアドレスをENS名表示
- [x] **Stage 10: 仕上げ** — README整備、デモ動画準備
- [x] **Stage 11: ENSv2団体サブネーム登録** — 団体向けオプション機能として、
  ENSv2のL2レジストリ方式に倣った自前コントラクト（`OrgSubnameRegistryV2`）を
  Base Sepoliaにデプロイし、リーダーボード表示・フロントエンドの登録UIに統合

## 進め方のルール

- 1ステージ = 1つ以上の意味のあるコミット（大きな差分を1コミットにまとめない）
- 各ステージ完了時に、Base Sepoliaで実際に動作確認してからコミットする
- コード自体はAIが書くが、コミット操作（add/commit/push）は本人が行う
- 本人が仕組みを説明できる状態を保つ（ピッチでの質問対応のため）

## 進捗ログ

| ステージ | 状態 | 備考 |
|---|---|---|
| Stage 1 | 完了 | attest.py作成・Base Sepoliaで動作確認済み（tx: 0x7d42e68083536e3ae7c4bc0c15f53c7b5991a34f649713d737c07d57adfa89c0）。push済み |
| Stage 2 | 完了 | app.py（/attestエンドポイント）作成・動作確認済み（tx: 0x89d4f031b3cdd3abc08dd74cd2e3da6010ff7e68ade40cfa27f162b695b501fb）。push済み |
| Stage 3 | 完了 | tip.py・/tipエンドポイント作成、ETH投げ銭を動作確認済み（送金tx: 0xa319b6a77c24fbb07ccadc74720331ed1917b24dcd4fbc89bf50dd3d0d025103）。push済み |
| Stage 4 | 完了 | leaderboard.py・/leaderboardエンドポイント作成、集計動作確認済み。push済み |
| Stage 5 | 完了 | static/index.html（サーバー経由の初期版UI）作成、動作確認済み。push済み |
| Stage 6 | 完了 | ethers.js + MetaMaskでフロントがウォレット直接署名するよう変更。JS構文・API import確認済み。push済み |
| Stage 7 | 完了 | tip.py/leaderboard.py/フロントをUSDC対応に拡張。実USDC投げ銭・通貨別集計を動作確認済み（tx: 0x2d58889a020883449977350449ab71ca1f9154e3d36b727e81ff2cf41c557afe）。push済み |
| Stage 8 | 完了 | trending.py・/trendingエンドポイント・フロントの急上昇セクション+SNSシェアボタン追加。動作確認済み。push済み |
| Stage 9 | 完了 | ens_resolve.py作成、leaderboard.py・フロントをENS名表示に対応。動作確認済み。push済み |
| Stage 10 | 完了 | README全面刷新、デモ資料（narration_script.md, demo_walkthrough.md）配置。全エンドポイント最終動作確認済み。コミット待ち |
| Stage 11 | 完了 | `contracts/OrgSubnameRegistryV2.sol`作成・Base Sepoliaにデプロイ済み（tx: 0xb70fd3bdffb35db003bf77f5e9d8ce09bbc268b87ecd85c58b9889a4d0c5b4c6、contract: 0x67e48e5e0DA4a160D0Cb5cE12ac311087ed68F1D）。`registerSubname`実行・`ensv2_org.py`での逆引き・`/leaderboard`への`org_subname`反映まで実際に動作確認済み |
