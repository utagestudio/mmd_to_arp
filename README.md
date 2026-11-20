# MMD to Auto-Rig Pro

mmd_tools で読み込んだ MMD モデル（PMX / PMD）を、[Auto-Rig Pro](https://lucky3d.fr/auto-rig-pro/) のリグに変換する Blender アドオンです。変換そのものは Auto-Rig Pro: Quick Rig が行い、このアドオンはモデルの骨格に合ったマッピングの選択と、MMD 特有の仕組み（付与・IK で動く補助ボーン）の後処理を自動化します。

Blender add-on that turns MMD models imported with mmd_tools into Auto-Rig Pro rigs, by driving Auto-Rig Pro: Quick Rig with skeleton-specific limb mappings and fixing up MMD helper bones afterwards.

- 配布されている MMD モデル 241 体（PMX / PMD）のボーン構造を解析し、構造パターンごとに代表 36 体で変換を検証しています
- アドオンを使わずに、Quick Rig のプリセットファイルとして使うこともできます（[後述](#アドオンを使わない場合)）

## 必要なもの

| | 動作確認バージョン |
|---|---|
| Blender 4.2 以降 | 5.3 |
| [mmd_tools](https://extensions.blender.org/add-ons/mmd-tools/) | 拡張機能版 |
| Auto-Rig Pro（有償） | 3.79.22 |
| Auto-Rig Pro: Quick Rig（有償） | 1.28.39 |

このアドオンは上記 3 つがインストール・有効化されている前提で動作します。

## インストール

1. 拡張機能の zip（`mmd_to_arp-<version>.zip`）を用意します。リポジトリから作る場合は `tools/build_extension.sh` を実行すると `dist/` に作成されます
2. Blender の「編集 > プリファレンス > 拡張機能」右上のメニューから「ディスクからインストール」で zip を選びます（zip を Blender にドラッグ＆ドロップしても構いません）

## 使い方

1. mmd_tools で PMX / PMD をインポートします
   - **「ボーン名の変換（Rename Bones - L / R Suffix）」は ON のまま**にしてください（既定値）。`左腕` → `腕.L` 形式の名前を前提にしています
   - 「Use Underscore」や辞書による英訳は使わないでください
2. モデル（ルート・アーマチュア・メッシュのどれでも可）を選択し、3D ビューのサイドバー「**MMD ARP**」タブを開きます
3. **Mode** を選びます（下表）。迷ったら Convert で構いません
4. 「**Detect Preset**」で判定結果と注意事項を確認します（省略可）
5. 「**Convert to Auto-Rig Pro**」を押します。マッピングの設定、Quick Rig の Make Rig!、後処理までをまとめて実行します

| Mode | 内容 | 向いている用途 |
|---|---|---|
| Convert | MMD の骨格を ARP に置き換え、ウェイトを ARP のボーンに載せ替える | ARP の機能をフルに使う（ゲームエンジンへの書き出し、リターゲットなど） |
| Preserve | MMD の骨格・付与・補助ボーンを残し、MMD の操作用ボーンだけを ARP で動かす（VMD と同じ考え方） | 補助ボーンの多いモデルを、元の変形のまま ARP で動かす |

**Preset** を「Auto」以外にすると、判定を使わずに指定したマッピングで変換します。

### 手順を分けて実行する

サイドバーの「Step by Step」から、各手順を個別に実行できます。

1. **Load Mapping to Quick Rig**：マッピングを Quick Rig のリム一覧に読み込むだけ。Quick Rig の画面で内容を確認・修正できます
2. Quick Rig の「Make Rig!」を実行
3. 生成されたリグを選択して **Run Post-Fix**：Convert / Preserve は自動判別します

### 後処理の内容

- **Convert**：Quick Rig はオーファンボーンのコンストレイントをコピーしないため、MMD の IK で腕などを追いかける補助ボーン（袖など）が動かなくなります。IK の持ち主とターゲットがリグに残っていて、チェーンに ARP のボーンを含まない MMD IK を ARP リグ側に再作成します
- **Preserve**：Quick Rig は元の骨格の全ボーンを ARP に拘束するため、D ボーンや捩じりボーンの付与が上書きされます。割り当てたボーンを含む MMD IK（足ＩＫ・つま先ＩＫ、頭まで届く髪 IK など）をミュートし、付与・IK で動くボーンとその子孫から Quick Rig の拘束を外して、モデル本来の仕組みで動かします。髪・スカートなど素直にぶら下がるボーンは ARP のコントローラーで動かせるまま残します

プリセットの一覧とマッピングの設計は [docs/presets.md](docs/presets.md) を参照してください。

## 制限事項

- **付与（他ボーンの回転コピー）で動く補助ボーン**は、Convert では連動が失われ、親ボーンに固定で追従するだけになります。気になる場合は Preserve を使ってください。Make Rig の「Copy Constraints」は mmd_tools の内部ボーンを壊すので ON にしないでください
- 補助ボーンを独自の仕組みで動かすモデルのうち、mmd_tools 単体でも補助ボーンの仕組みが再現されないモデルは、どちらのモードでも正しく変形しません（判定時に警告を表示します）
- Preserve では割り当てボーンを含む MMD IK をミュートするため、髪 IK などは無効になります。髪は ARP のオーファンコントローラーで動かします
- 腕捩が無い古いモデルは、Convert で上腕を捩じっても上腕部は捩じれません（曲げは問題ありません）
- 髪・スカート・IK ボーンなど割り当てていないボーンは、Quick Rig のオーファンボーン（黄色い球のコントローラー）になります。物理演算（剛体）は再現されません

## アドオンを使わない場合

`presets/` のファイルは、Quick Rig のプリセットとしてそのまま使えます。

1. `presets/*.py` を Quick Rig の Custom Presets Path（既定は `~/Documents/AutoRigPro/Quick Rig Presets/`）にコピーし、Blender を再起動します。「Import Preset」メニューに `Mmd_Std_D` などが表示されます
2. 使うプリセットは、インポート直後に `mmd_to_arp/detect.py` をテキストエディタで開いて「Run Script」すると表示されます
3. Convert 版（`MMD_*`）は Convert モード、Preserve 版（`MMD_P_*`）は Preserve モードで Make Rig! を実行します。Convert 版を Preserve モードで使う場合は「Constrain Overrides」を ON にしてください
4. 生成されたリグを選択して、Convert なら `mmd_to_arp/fix_convert.py`、Preserve なら `mmd_to_arp/fix_preserve.py` をテキストエディタで「Run Script」します（Preserve では必須）

プリセットは ASCII（`\uXXXX` エスケープ）で書き出しているので、日本語版 Windows でも文字化けしません。

## 開発

| パス | 内容 |
|---|---|
| `mmd_to_arp/` | アドオン本体（Blender 拡張機能）。`detect.py` / `fix_*.py` は単体スクリプトとしても動作 |
| `presets/` | 生成済みの Quick Rig プリセット |
| `docs/` | ドキュメント |
| `tools/make_presets.py` | `mmd_to_arp/mapping.py` からプリセットファイルを生成 |
| `tools/build_extension.sh` | 拡張機能 zip を `dist/` にビルド（`BLENDER=/path/to/blender` で Blender を指定） |
| `tools/pmx_bones.py` | PMX / PMD のボーン名・親子・ウェイト合計を JSON に書き出す（構造調査用） |
| `tests/blender/` | Blender 上での検証ハーネス（インポート → 変換 → ウェイト移行・追従・捩じり分布のチェック） |
| `_local/` | コミットしないローカルデータ（MMD モデル、解析結果など） |

バージョンは `mmd_to_arp/blender_manifest.toml` で管理し、`<major>.<minor>.<fix>` の形式です。開発中は `-dev.<n>` を付けます。

## ライセンス

GPL-3.0-or-later
