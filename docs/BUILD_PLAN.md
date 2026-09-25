# 開発ステージ記録

ETHGlobal Tokyo 2026提出用。本当のハッカソン開始時刻（2026-09-25 夜〜）以降の
作業のみを、このリポジトリのコミット履歴として残す。

## ステージ一覧

- [x] **Stage 1: 最小構成** — EAS attestation単体（`attest.py`）が動く状態
- [x] **Stage 2: API化** — FastAPIで`/attest`エンドポイントを追加
- [x] **Stage 3: 投げ銭（ETH）** — `tip.py`、送金+応援attestation
- [x] **Stage 4: リーダーボード** — EAS GraphQLインデクサからの集計
- [x] **Stage 5: フロントエンド** — ブラウザUI（静的HTML/JS）
- [ ] **Stage 6: ウォレット直接署名** — サーバー代理署名の撤廃（ethers.js + MetaMask）
- [ ] **Stage 7: マルチ通貨対応** — USDC投げ銭
- [ ] **Stage 8: 拡散機能** — 急上昇ランキング・ワンタップシェア
- [ ] **Stage 9: ENS対応** — 応援者・紹介者のアドレスをENS名表示
- [ ] **Stage 10: 仕上げ** — README整備、デモ動画準備

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
| Stage 5 | 完了 | static/index.html（サーバー経由の初期版UI）作成、動作確認済み。コミット待ち |
