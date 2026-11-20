# MMD → Auto-Rig Pro Quick Rig プリセット

mmd_tools で読み込んだ MMD モデル（PMX / PMD）を、Auto-Rig Pro: Quick Rig で ARP リグ化するためのプリセット集です。

- 検証環境：Blender 5.3 / mmd_tools（拡張機能版）/ Auto-Rig Pro 3.79.22 / Quick Rig 1.28.39
- 配布されている MMD モデル 241 体（PMX / PMD）のボーン構造を解析し、構造パターンごとに代表 36 体で Make Rig を実行して検証済み（Convert 版・Preserve 版とも）

プリセットは 2 系統あります。

| 系統 | ファイル | Make Rig のモード | 特徴 |
|---|---|---|---|
| Convert 版 | `MMD_*.py`（20 個） | Convert | 骨格を ARP に置き換えてウェイトを載せ替える。ゲームエンジン書き出しなど ARP の機能をフルに使える。構造ごとにプリセットが細かく分かれる |
| Preserve 版 | `MMD_P_*.py`（10 個） | Preserve + 後処理スクリプト | 元の MMD 骨格・付与・補助ボーンを残し、操作用ボーンだけを ARP で動かす（VMD と同じ考え方）。パターンが少なく、補助ボーンの多いモデルにも対応しやすい |

## 導入

1. `presets/*.py` を Quick Rig の Custom Presets Path にコピーします（両系統とも同じフォルダで構いません）
   （既定は `~/Documents/AutoRigPro/Quick Rig Presets/`。Quick Rig のアドオン設定で変更できます）
2. Blender を再起動するか、アドオンを再読み込みします
3. Quick Rig の「Import Preset」メニューに `Mmd_Std_D` などが表示されます（表示名は先頭大文字に変換されます）

プリセットは ASCII（`\uXXXX` エスケープ）で書き出しているので、日本語版 Windows でも文字化けしません。

## 使い方

1. mmd_tools で PMX / PMD をインポートします
   - **「ボーン名の変換（Rename Bones - L / R Suffix）」は ON のまま**にしてください（既定値）。プリセットは `左腕` → `腕.L` 形式の名前を前提にしています
   - 「Use Underscore」や辞書による英訳は使わないでください
2. 下の一覧、または `mmd_to_arp/detect.py` で使うプリセットを決めます
3. アーマチュア（`<モデル名>_arm`）を選択して、ARP タブ → Quick Rig → Import Preset → プリセットを選択
4. Make Rig! を実行します
   - Convert 版（`MMD_*`）：**Convert** モードで実行します。Convert 版を Preserve モードで使う場合は、ダイアログの **「Constrain Overrides」を ON** にしてください（腕の捩じり割り当てに必要です）
   - Preserve 版（`MMD_P_*`）：**Preserve** モードで実行し、続けて下記の後処理スクリプトを実行します

### Convert 版の後処理（推奨）

Convert モードでは、割り当てていないボーンのコンストレイントはコピーされません。そのため、MMD の IK で腕などを追いかける補助ボーン（例：袖。肩襟から垂れ下がり、腕捩・手首の子の IK ターゲットを追う）が動かなくなります。

Make Rig! の後、ARP リグを選択して `mmd_to_arp/fix_convert.py` をテキストエディタで「Run Script」してください。IK の持ち主とターゲットが両方ともリグにオーファンボーンとして残っていて、チェーンに ARP のボーンを含まない MMD IK だけを再作成します。対象の無いモデルでは何もしません。何度実行しても重複しません。

### Preserve 版の後処理（必須）

Preserve モードの Quick Rig は、割り当てていないボーンも含めて**元の骨格の全ボーンを ARP 側に拘束**します。そのままでは足D・腕捩1〜3・補助ボーンなどの付与（回転コピー）が上書きされ、D ボーンのモデルでは足首が 15cm ほどずれます。

Make Rig! の後、`mmd_to_arp/fix_preserve.py` を Blender のテキストエディタで開いて「Run Script」を実行してください（ARP リグか MMD アーマチュアを選択した状態。何度実行しても問題ありません）。このスクリプトは次の処理をします。

- プリセットで割り当てたボーンを含む MMD の IK（足ＩＫ・つま先ＩＫ、頭まで届く髪 IK など）をミュートする（ARP が動かすボーンを MMD の IK が引き戻さないように）
- 付与・IK で動くボーン（D ボーン、腕捩1〜3、手捩1〜3、補助ボーン、mmd_tools 内部の `_shadow_` / `_dummy_`）とその子孫から Quick Rig の拘束を外し、モデル本来の仕組みで動かす
- 髪・スカートなど、割り当てボーンの下に素直にぶら下がるボーンは拘束を残す（ARP のオーファンコントローラーで動かせる）

### プリセットの自動判定

インポート直後（Make Rig の前）に、MMD モデルのルートかアーマチュアを選択した状態で、Blender のテキストエディタから `mmd_to_arp/detect.py` を開いて「Run Script」を実行すると、Convert 版・Preserve 版それぞれの推奨プリセットがポップアップとコンソールに表示されます。

## プリセット一覧

### Preserve 版

名前は `MMD_P_<背骨>[_nothumb0]` です（背骨・親指の条件は下の Convert 版と同じ）。特殊プリセットは `MMD_P_spine1m`（背骨が 上半身1- / 上半身2-）と `MMD_P_std_hand`（手首が「手」）の 2 つだけです。D ボーンの有無や捩じりボーンの本数は MMD 側の付与で吸収されるので区別しません。

| ARP | MMD |
|---|---|
| Spine | 下半身 / 上半身 / 上半身2 / (上半身1・上半身3) |
| Head | 首 / 頭 |
| Arm | 肩 / 腕 / ひじ / 手捩（→ forearm_twist）/ 手首 |
| Fingers | 親指０(or 親指１) / 人指１ / 中指１ / 薬指１ / 小指１ |
| Leg | 足 / ひざ / 足首 / 足先EX |

- 前腕は 手捩 を ARP の forearm_twist（手首の捩じりを 100% 受けるボーン）に割り当てており、手捩1〜3 は MMD の付与で分配されます（手首 90° 捩じりで、肘 1.5° → 手首 82.5° と滑らかに分布することを確認）
- 上腕の 腕捩 は割り当てていません。上腕の捩じりは 腕 ごと回転するので、MMD で 腕 を捩じったときと同じ挙動です

### Convert 版

名前は `MMD_<背骨>[_nothumb0][_D]` の組み合わせです。

| 要素 | 値 | 条件 |
|---|---|---|
| 背骨 | `std` | 下半身 > 上半身 > 上半身2（大半のモデル） |
| | `spine3` | 上半身3 まである |
| | `spine1` | 上半身 > 上半身1 > 上半身2 |
| | `nospine2` | 上半身のみ（古い PMD） |
| `_nothumb0` | | 親指０が無い（親指１・親指２の 2 本構成） |
| `_D` | | 準標準 D ボーン（足D / ひざD / 足首D）に脚のウェイトがある |

モデル固有の特殊プリセット：

| プリセット | 対象 |
|---|---|
| `MMD_spine1m` | 背骨が 上半身1- / 上半身2-、前腕が 手捩1〜5 |
| `MMD_std_hand` | 手首ボーンの名前が「手」 |
| `MMD_std_D_ankle` | 足D・ひざD はあるが足首D が無い |
| `MMD_std_Dempty` | D ボーンにウェイトが無く、つま先「足首EX」が足首D の子 |

## マッピングの設計（Convert 版）

| ARP | MMD | 補足 |
|---|---|---|
| Spine: root / spine_01.. | 下半身 / 上半身 / 上半身2 / (上半身3) | 下半身は下向きなので `pelvis_up` ON |
| Head: neck / head | 首 / 頭 | |
| Arm: shoulder / arm / forearm / hand | 肩 / 腕 / ひじ / 手首 | |
| Arm twist | 腕捩, 腕捩1〜3 / 手捩, 手捩1〜3 | 下記参照 |
| Fingers | 親指０(or 親指１) / 人指１ / 中指１ / 薬指１ / 小指１ | 3 本指（Metacarpal 無し） |
| Leg: thigh / calf / foot / toes | 足 / ひざ / 足首 / 足先EX（`_D` では 足D / ひざD / 足首D） | 足先EX が無いモデルは足首の向きからつま先を推定 |

### 腕の捩じり

ARP と MMD では捩じりの分担が逆になっているため、そのまま割り当てると肘付近で捩じりが途切れます。

- 上腕：ARP は「肩側 0%（c_arm_twist_offset）→ arm_twist_2/3/4（25/50/75%）→ arm_stretch（100%）」、MMD は「腕 0% → 腕捩1/2/3 → 腕捩 100%」
  → Weights Override で **腕のウェイトを捩じり 0% のボーンへ、腕捩のウェイトを arm_stretch へ入れ替え**ています
- 前腕：ARP の forearm_twist_2/3/4 は 75/50/25% と逆順なので、**手捩3/2/1 の順**に割り当てています

手首を 90° 捩じったとき、前腕の頂点の回転量が肘 0° → 手首 90° へ単調に増えることを計測で確認しています（素直に割り当てた場合は途中で回転が戻ります）。

### D ボーン

`_D` プリセットでは D ボーンを「メインボーン」として割り当てています。Weights Override でウェイトだけ D ボーンから取る方式では、D ボーンの子（足指や脚に付いた装備など）が腰に置き去りになるためです。D ボーンは tail が真上を向いていますが、ローカル Z 軸が正面を向いているので `foot_dir_axis = Z` で足の向きを決めています。

## 制限事項

- **付与（他ボーンの回転コピー）で動く補助ボーン**は、Convert モードでは連動が失われ、親ボーンに固定で追従するだけになります。IK で動く補助ボーンは `mmd_to_arp/fix_convert.py` で復元できます。気になる場合は Preserve モードを使ってください。Make Rig の「Copy Constraints」は mmd_tools の内部ボーンを壊すので ON にしないでください
- **腕が補助ボーン鎖で変形するモデル**は Convert では腕が正しく変形しません。Preserve 版を使ってください（両モデルとも Preserve 版 + 後処理で動作を確認済み）
- Preserve 版では、割り当てボーンを含む MMD IK をミュートします。そのため髪 IK などは無効になり、髪は ARP のオーファンコントローラーで動かすことになります
- 一部のモデルは、mmd_tools 単体で MMD ボーンを動かしても補助ボーン機構が再現されないため対象外です
- 腕捩が無い古いモデルは、上腕のウェイトが捩じり 0% 側に割り当てられるため、上腕を捩じっても上腕部は捩じれません（曲げは問題ありません）
- 髪・スカート・IK ボーンなど割り当てていないボーンは Quick Rig のオーファンボーン（黄色い球のコントローラー）になります。物理演算（剛体）は再現されません

## リポジトリ構成

| パス | 内容 |
|---|---|
| `presets/` | 生成済みの Quick Rig プリセット（Convert 版 `MMD_*`、Preserve 版 `MMD_P_*`） |
| `mmd_to_arp/` | Blender アドオン（拡張機能）。各モジュールは単体スクリプトとしても使用可 |
| `mmd_to_arp/mapping.py` | プリセットのマッピング定義 |
| `mmd_to_arp/detect.py` | 推奨プリセットの判定（Blender のテキストエディタ / `python3 mmd_to_arp/detect.py bones.json [--preserve]`） |
| `mmd_to_arp/fix_convert.py` | Convert 版の後処理：補助ボーンの MMD IK を ARP リグに再作成 |
| `mmd_to_arp/fix_preserve.py` | Preserve 版の後処理：付与・IK で動くボーンを MMD 側に戻す |
| `tools/make_presets.py` | `mapping.py` からプリセットファイルを生成（`python3 tools/make_presets.py`） |
| `tools/pmx_bones.py` | PMX / PMD のボーン名・親子・ウェイト合計を JSON に書き出す（構造調査用） |
| `tests/blender/` | Blender 上での検証ハーネス（インポート → プリセット適用 → Make Rig → ウェイト移行・追従・捩じり分布のチェック） |
| `_local/` | コミットしないローカルデータ（MMD モデル、解析結果など）。`.gitignore` 済み |
