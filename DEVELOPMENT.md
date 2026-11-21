# 開発者向け情報

利用者向けの説明は [README.ja.md](README.ja.md)（[English](README.md)）を参照してください。

## リポジトリの構成

| パス | 内容 |
|---|---|
| `mmd_to_arp/` | アドオン本体（Blender 拡張機能）。`detect.py` / `fix_*.py` は単体スクリプトとしても動作します |
| `presets/` | 生成済みの Quick Rig プリセット |
| `docs/presets.md` | プリセットの一覧とマッピングの設計 |
| `tools/make_presets.py` | `mmd_to_arp/mapping.py` からプリセットファイルを生成します |
| `tools/build_extension.sh` | 拡張機能の zip を `dist/` にビルドします |
| `tools/pmx_bones.py` | PMX / PMD のボーン名・親子・ウェイト合計を JSON に書き出します（構造調査用） |
| `tests/blender/` | Blender 上での検証ハーネス（インポート → 変換 → ウェイト移行・追従・捩じり分布のチェック） |
| `CHANGELOG.md` / `CHANGELOG.ja.md` | 利用者向けの変更履歴（英語・日本語） |
| `CONTRIBUTING.md` | 不具合の報告・PR の案内（GitHub が Issue や PR の画面にリンクを表示します） |
| `CLAUDE.md` | AI コーディングアシスタント向けのプロジェクトのルール。個人用の `CLAUDE.local.md` はコミットしません |
| `.github/ISSUE_TEMPLATE/` | Issue のフォーム（不具合の報告、機能の要望） |
| `_local/` | コミットしないローカルデータ（MMD モデル、モーション、解析結果など）。`.gitignore` で除外しています |

## 開発環境

- `mmd_to_arp/` を Blender の拡張機能フォルダ（例：`~/.config/blender/<version>/extensions/user_default/mmd_to_arp`）にシンボリックリンクすると、作業ツリーがそのまま読み込まれます。変更後は Blender を再起動するか、アドオンを有効にし直してください。
- Blender のバージョンごとに、mmd_tools・Auto-Rig Pro・Quick Rig も有効にしておく必要があります。

## ビルド

```sh
BLENDER=/path/to/blender tools/build_extension.sh
```

- アドオンを一時フォルダに複製し、リポジトリの `LICENSE` を加えてから、検証（`extension validate`）とビルド（`extension build`）を行います。
- `__pycache__` は含めません。
- 出力先は `dist/mmd_to_arp-<version>.zip` です。

## プリセットの生成

マッピングの定義（`mmd_to_arp/mapping.py`）を変えたら、プリセットファイルを生成し直してコミットします。

```sh
python3 tools/make_presets.py presets
```

プリセットは ASCII（`\uXXXX` エスケープ）で書き出します。Quick Rig は OS 既定のエンコーディングでプリセットを読むため、日本語版 Windows でもボーン名が文字化けしないようにしています。

## テスト

検証は、作業中のシーンを壊さないように、バックグラウンドの Blender（`blender -b --python <script>`）で行います。

- `tests/blender/qr_test_helper.py` と `qr_pose_test.py` は、スクリプトから `exec()` で読み込んで使います（`REPO` にリポジトリのパスを渡します）。モデルの読み込み（`import_mmd`）、リグの生成（`generate_rig`）、検証（`validate_model`）などの関数があります。
- `tests/blender/qr_batch.py` は、複数のモデルを続きから検証するバッチです。必要なグローバル変数はファイルの先頭に書いてあります。
- MMD モデルは `_local/mmd/` に置きます（`qr_batch.py` では `MODELS_DIR` で変更できます）。モデルはコミットしないでください。
- 公開するファイル（コード、ドキュメント、コミットメッセージ）には、検証に使ったモデルの名前を書かないでください。プリセットやコメントでは、ボーン構造で説明します。

## バージョンとブランチ

- バージョンは `mmd_to_arp/blender_manifest.toml` で管理します。形式は `<major>.<minor>.<fix>` です。
- 作業の単位ごとに、最新の main からブランチを作ります。
  - 機能の追加は minor、修正は fix を上げ、`-dev.1` を付けます。
  - アドオンの動作が変わるコミットごとに、dev の番号を 1 つ上げます。ドキュメントやテストだけのコミットでは上げません。
- リリース時は `-dev` を外してコミットし、main にマージして `v<version>` のタグを付けます。

## リリースの手順

1. リリースするブランチで、`mmd_to_arp/blender_manifest.toml` の `-dev.<n>` を外してコミットします（コミットメッセージは `Release <version>`）。
2. `CHANGELOG.md` と `CHANGELOG.ja.md` に、利用者向けの変更点を追記します。
3. main にマージし（`--no-ff`）、`v<version>` のタグを付けます。
4. `tools/build_extension.sh` で zip を作ります。中身（manifest、LICENSE、`.py`）を確認します。
5. 配布先を更新します。
   - GitHub Releases：タグからリリースを作り、zip を添付し、CHANGELOG の該当部分を貼ります。
   - BOOTH：zip を差し替え、商品ページの更新履歴を更新します。
   - 独自サイト：バージョン、zip のリンク、拡張機能リポジトリ（`index.json`）を更新します。
6. 公開する文章（CHANGELOG、リリースノート、商品ページ）に、モデル名が入っていないことを確認します。

## 対応バージョンの更新

Auto-Rig Pro と Quick Rig の内部（Quick Rig のオペレーターの内部状態、Auto-Rig Pro のスナップ・焼き込み関数）を直接使っています。新しいバージョンで動作を確認したら、`mmd_to_arp/quickrig.py` の `TESTED_VERSIONS` と、README の動作確認バージョンを更新してください。範囲外のバージョンでは、パネルに小さく注意を表示します。
