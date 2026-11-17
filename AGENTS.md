<!-- agent-ninja-START -->
## Agent Skills

> **IMPORTANT**: Prefer skill-led reasoning over pre-training-led reasoning.
> See [Agent Skills](.github/skills/README.md) before working on tasks covered by these skills.

<!-- agent-ninja-END -->

## マニュアル編集・日英同期・スクリーンショット撮影原則

1. **簡潔でプレイヤー視点の記述**:
   - タイトル画面やドロワーメニューのボタン説明は、ビューワの細かい機能列挙を避け、用途が直感的に伝わる簡潔な表現に留める。
   - 「セーブデータと言語コアは別々に扱われます」のような内部実装寄りの曖昧な表現は書かず、プレイヤーが取るべき具体的な操作のみを記載する。
2. **日英完全同期と章・図番号整合**:
   - `manual.md` / `manual_en.md` / `annotations/ja.json` / `annotations/en.json` は常に日英セットで更新する。
   - 新章を挿入した際は、後続の章番号・図番号（`図 X-Y` / `Figure X-Y`）・本文中の章相互参照（`第N章` / `Chapter N`）を漏れなく更新する。
3. **スクリーンショット品質・撮影用 VM 原則**:
   - スクリーンショットは必ず `DEBUG` バナーの入らない **Release APK** で撮影する。
   - 撮影用 Android 仮想マシン（AVD）は、通常画面（縦）には **`Pixel_9a`**（`1080x2424`）、タブレット横画面比較（`20_tablet_layout_compare.png` 等）には **`Small_Tablet`**（`1920x1200`）を使用し、既存の注釈座標と解像度を揃える。
   - 設定画面など縦に長いセクションは、全項目が切れずに収まるよう複数枚（上段・中段・下段）に分割して撮影・図解する。
   - `annotate_screenshots.py` 実行後は、生成された `images/manual/{ja,en}/*.png` を目視確認し、枠線やバッジのズレを修正してから完了とする。
4. **コミット対象の管理**:
   - `git commit` 時は `graphify-out/` などの未追跡作業ディレクトリを含めない。
