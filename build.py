#!/usr/bin/env freecadcmd
# -*- coding: utf-8 -*-
# =============================================================================
# 単3電池の筒で傾ける左右分割キーボード（35キー＋Ø25トラックボール）
# ケース・プレート・ボールカップとアセンブリを組み、干渉を調べて書き出す
# -----------------------------------------------------------------------------
# 実行: /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd build.py
#   -> out/step/*.step   部品ごと（アセンブリ座標）と、左右を組んだアセンブリ
#      out/stl/*.stl     印刷向きの部品
#      out/stl/asm/*.stl アセンブリ座標の全部品（preview.scad が読む）
#
# 座標: 決定案の上面図の左上を原点に x 右・y 下向きで組み、最後に y を反転して
#       上から見た向きに直す。画像の 100px = キーピッチ 19.05mm で換算した。
#       ★寸法の定義はこのファイルだけに置く。
# =============================================================================
import math
import os
import sys

import FreeCAD
import Import
import MeshPart
import Part
from FreeCAD import Vector as V

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_STEP = os.path.join(HERE, "out", "step")
OUT_STL = os.path.join(HERE, "out", "stl")
OUT_ASM = os.path.join(OUT_STL, "asm")

# 実部品の参考モデル（torabo-tsuki-om-case/ref と同じもの。出典とライセンスは ref/*.LICENSE.txt）
REF_SWITCH = os.path.join(HERE, "ref", "choc-v2-red.step")                   # CC BY-NC-SA 4.0
REF_XIAO = os.path.join(HERE, "ref", "xiao-nrf52840.step")                     # Seeed。ライセンス表記なし（再配布しない）

# ---- 平面寸法 ---------------------------------------------------------------
W = 124.4            # キー配置の基準の幅（画像の外形）。外形はここから GROW だけ外へ広げる
# ★北と南の余白を詰めた（2026-09-30）。北の辺を N_TRIM だけ南へ、南の辺を S_TRIM だけ北へ寄せた。
# ★その後、ネジを外周に置くため、全周を GROW だけ広げた（2026-09-30）。キー・電池・ボールは動かない
# ★外周のネジをやめたので、外周のベゼルを詰めた（2026-10-04）。外側の辺（左は西、右は東）を OUTER_TRIM、南の辺を
#   S_TRIM（1.0 → 3.5）だけ寄せた。北の辺と内側の辺は、XIAO・カバー・リポバッテリの位置が決まっているので動かさない
# ★北の辺も詰めた（2026-10-06）。N_TRIM を 0.4 → 3.2 にし、キーキャップの縁〜外面を 6.9 → 4.1（外側の辺と同じ）にした。
#   XIAO（USB-C の先端は北の外面にそろう）とカバーも 2.8 南へ寄るので、リポバッテリを 502045 → 502040 に縮めた
N_TRIM = 3.2
S_TRIM = 3.5
GROW = 1.5
OUTER_TRIM = 3.0
X_W = -GROW                  # 外形の西の辺
X_E = W + GROW               # 外形の東の辺
Y_N = N_TRIM - GROW          # 外形の北の辺
W_OUT = X_E - X_W            # 外形の幅 127.4（外側の辺を詰める前）
X_OUT = {"L": X_W + OUTER_TRIM, "R": X_E - OUTER_TRIM}   # 外側の辺
H_THUMB = 88.8 - S_TRIM + GROW     # 親指段側の南の辺
# ★左手は親指段だけ H_THUMB まで深く、ほかは H_MAIN_L（画像の外形 ＋ GROW）。南西の角にあった
#   XIAO の出っ張りは、XIAO を電池の列へ移したのでやめた（2026-10-03）
H_MAIN_L = 81.52 - S_TRIM + GROW   # 左: 親指段でない側の南の辺（82.02）
THUMB_X0_L = 59.6    # 左: 親指段が手前へ張り出し始める x
H_MAIN_R = H_MAIN_L                # 右: 親指段とボールのふくらみ以外の南の辺。★タグの下の余白を左と
                                   #   そろえるため、H_THUMB から左と同じ 82.02 に上げた（2026-10-03）
THUMB_X1_R = 48.0    # 右: 親指段側の張り出しが終わる x（ふくらみの円の中に入れる。46.5 だと円と角が 0.01 で接して offset が失敗する）
BULGE_C = (62.2, 80.3)    # 右: ボール中心（ふくらみの中心）。★ZEN のリング（外径 34）が押し込んだ 3 段目の
                          #   キーキャップに当たらないよう、画像の 76.39 から南へ寄せた（2026-10-03。ベアリングを 35° にして
                          #   リングが外径 φ36.8 になったので、さらに 80.3 へ）
BULGE_R = 21.0           # ★台を円（半径 15.5）にし、ベゼルを詰めたので 23 から縮めた（2026-10-04）。カバーの穴（半径 17.6）の外に
                         #   面取り 2.5 と平らな上面 0.9 が残る
R_CONVEX = 4.5       # 外形の角 R
R_CONCAVE = 6.0      # 外形の入り隅 R
BOTTOM_FILLET = 1.5  # ★底面の縁の R（2026-10-03）。ケースの底の外周（電池の脚が続く内側の帯を除く）と、電池の脚の両端

PITCH = 19.05
KEYS = {
    "L": [(14.38 + PITCH * i, 14.57 + PITCH * j) for j in range(3) for i in range(5)],
    "R": [(33.62 + PITCH * i, 14.57 + PITCH * j) for j in range(3) for i in range(5)],
}
THUMBS = {
    "L": [(71.53, 74.2), (90.58, 74.2), (109.63, 74.2)],
    "R": [(14.57, 74.2), (33.62, 74.2)],
}
# ★電源はリポバッテリ（2026-10-04。単3 電池の筒とテントはやめた）。XIAO の南の内側の列（キーの無い帯）に、
#   床の上に寝かせて入れる。XIAO nRF52840 が充電する
#   ★内側の北寄りのネジをやめて北へ延ばし、PCB のバッテリの上を開けて厚くした（2026-10-04）。北は電源スイッチ
#     の本体（y 20.45 まで）と XIAO の南の端（y 24.18。2026-10-06 に北の辺を詰める前は 21.38）、南は親指段の内側のキーの北のピン（キーの中心から
#     北へ 5.5）で決まる
#   ★底から出し入れする（2026-10-04）。ケースの床にバッテリが通る穴を開け、底から掘り込んだ座にスライドする
#     ふた（別部品、電池ぶたの作り）をはめる。バッテリはふたの上に載る
#     - ふたの東西の縁の爪を、座の切り欠きから入れて北へ DOOR_SLIDE すべらせると、爪が座の溝の下の縁に掛かる
#     - ふたの南の端のたわむ舌の突起が、閉めた位置で床の穴にはまり、勝手に開かない。開けるときは、ふたの裏の
#       滑り止めに指を掛けて南へ引く（舌が下へたわんで突起が外れる）
LIPO = (20.0, 40.0, 5.0)            # 502040（幅 x・長さ y・厚さ）。2026-10-06 に 502045 から縮めた
LIPO_Y0 = 24.8                      # 北の端（XIAO の南の端 24.18 ＋ PCB の切り欠きのすき間）
LIPO_CLR = 0.3                      # 床の穴・PCB の切り欠きのすき間
LIPO_PLATE_CLR = 0.5                # リポバッテリの上面〜プレートの下面の最小
DOOR_T = 1.4                        # ふたの厚さ（= 座の深さ）。座の上の床は 0.6
DOOR_SIDE = 1.0                     # 床の穴から東西へのふたの張り出し
DOOR_END = (3.0, 5.0)               # 床の穴から北・南へのふたの張り出し（南は抜け止めの舌を置く）
DOOR_CLR = 0.2                      # 座とふたのすき間
DOOR_R = 1.0                        # ふたの角 R
DOOR_SLIDE = 4.0                    # 開け閉めのすべり量（閉めると座の南に 4.0 のすき間が残り、指掛かりになる）
DOOR_TAB = (5.0, 1.0, 0.7)          # 爪（長さ y・張り出し x・下面の z = 座の溝の下の縁の厚さ）
DOOR_TAB_AT = (0.18, 0.5, 0.82)     # 爪の位置（ふたの長さに対する割合）
DOOR_TONGUE = (9.0, 2.0, 0.6)       # 抜け止めの舌（長さ x・幅 y・まわりの切れ目の幅）
DOOR_BUMP = (0.7, 0.5)              # 舌の先の突起（半径・高さ）
DOOR_BUMP_HOLE_R = 0.9              # 床の、突起がはまる穴
DOOR_GRIP = (3, 0.8, 0.4, 1.6)      # ふたの裏の滑り止めの溝（本数・幅・深さ・ピッチ）
# ボールの台をケースに留めるタッピングネジ（ケースの底から）の下穴
FOOT_PILOT_R = 0.8
# ---- 締結: 床とトッププレートを M2 メス‒メススペーサーでつなぐ。上（プレート側）も下（床側）も皿ネジ。
#      PCB は固定しない（スペーサーは PCB の穴を素通りし、PCB はスイッチを介してプレートからぶら下がる）
# ★トッププレートをキーキャップの外周まで縮め、ケースの上面で囲んだので（2026-10-04）、外周のネジはやめ、
#   キーの間（4 つのキーの角の間、または親指段のキーの間）にスペーサーを置く。上の皿ネジの頭はプレートに沈め、
#   押し込んだキーキャップに当たらない
SCREW_IN = 4.65
_MID_ROW = 14.57 + PITCH * 1.5                     # 2-3 段の間
_XW, _XE, _YN = X_W + SCREW_IN, X_E - SCREW_IN, Y_N + SCREW_IN
_HP = PITCH / 2
_ROW_GAP = (14.57 + PITCH * 2 + 74.2) / 2          # 3 段目と親指段の間
# スペーサー（= プレートの皿ネジ・床の皿ネジ）。キーの角の間 4 点と、親指段のまわり 1 点。リポバッテリのふたを避ける
SCREWS = {
    "L": [(14.38 + _HP, 14.57 + _HP), (71.53 + _HP, 14.57 + _HP),
          (14.38 + _HP, 33.62 + _HP), (71.53 + _HP, 33.62 + _HP),
          (71.53 + _HP, 74.2)],                                     # 親指段の 1・2 番目のキーの間
    "R": [(33.62 + _HP, 14.57 + _HP), (90.77 + _HP, 14.57 + _HP),
          (33.62 + _HP, 33.62 + _HP), (90.77 + _HP, 33.62 + _HP),
          (33.62, _ROW_GAP)],                                       # 3 段目の 1 列目と親指段の 2 番目のキーの間
}
TAG_SCREW_LEN = 5.0  # タグのネジ M2 × 5（タグ 1.5 ＋ ケースの上面へ 3.5）
TAG_TAP_R = 0.8      # ★ケースはアルミなので、タッピングネジをやめて M2 のめねじを立てる（2026-10-06）。下穴 φ1.6
# LED（PCB の上）の穴。北の段の、内側の 2 列のキーキャップの間（プレートの中）に置く
LED = {"L": (71.53 + _HP, 6.5), "R": (33.62 + _HP, 6.5)}
# ---- 電源スイッチ（2026-09-30）: torabo-tsuki と同じ Switronic ISH-1260-HA-G を PCB の裏に付け、
#      つまみを内側の側面（左は東、右は西）へ向ける。つまみは壁の中で別部品のスライダー（`slider()`）が
#      挟み、スライダーの先が壁の窓から外へ出る。窓は外周の面取りより下に収まる。
#      寸法はメーカー図面（torabo-tsuki-om-case の README）: 本体 9.1 × 3.5 × 3.5、つまみ 1.5 角 × 出 2.0、
#      ストローク 2.0（中心から ±1.0）
PSW_Y = 15.9                          # スイッチの中心の y
PSW_X = {"L": 115.4, "R": 8.9}        # 本体の、壁から遠い側の面の x。★PCB ごとケースの上面の穴から入れるので、本体と
                                      #   つまみの先がマイコンカバーの範囲に入るよう、内側へ寄せた（2026-10-04。以前は 118.83・5.38）
PSW_BODY = (3.5, 9.1, 3.5)            # 本体（壁に直交・スライド方向・高さ）
PSW_KNOB, PSW_KNOB_L, PSW_STROKE = 1.5, 2.0, 2.0
SLD_NOSE = (3.7, 2.4)                 # スライダーの首（y 幅・高さ）。窓を通る
SLD_SLOT = 1.7                        # つまみを挟む溝の幅（z 方向に貫通）
SLD_CLR = 0.2

# ---- 高さ（torabo-tsuki-om-case と同じ Choc V2 の積み方）------------
FLOOR_T = 2.0
GAP_PCB = 4.2        # 床上面〜PCB 下面。★ZEN の台（高さ 6）が入るよう 2.2 から広げた（2026-10-04）
PCB_T = 1.6
# ---- Choc V2（PG1353）: Kailh 外形図 CPG135301D03。z は PCB 上面が 0 ----------
SW_LOW_W = 13.95     # 下胴（プレートを通る）
SW_LOW_H = 2.20      # = 座面。プレート上面はここ
SW_BODY_W = 15.00    # ハウジング
SW_BODY_H = 3.10
SW_BODY_TOP = SW_LOW_H + SW_BODY_H   # 5.30 ハウジング上面 = キーキャップ下面
SW_STEM_W = 6.50     # ステム部の包絡
SW_STEM_TOP = 8.60   # ステム上端

SEAT = SW_LOW_H      # PCB 上面〜プレート上面
PLATE_T = 2.0        # 1.5 → 2.0（2026-09-30）。上面は Choc の座面で決まるので、下面が 0.5 下がる
PCB_BOT = FLOOR_T + GAP_PCB
PCB_TOP = PCB_BOT + PCB_T
PLATE_TOP = PCB_TOP + SEAT           # = 壁の上端
PLATE_BOT = PLATE_TOP - PLATE_T
# ★トッププレートの外周をキーキャップの外周（＋ TOP_CLR）に合わせて縮め、ケースの壁と上面をキーキャップの下面の
#   CAP_RIM_GAP 下まで立ち上げて、ケースの外枠でスイッチを隠す（2026-10-04）。ケースの上面にはトッププレートの
#   外形 ＋ PLATE_CLEAR の穴を開け、プレート・PCB（スイッチ・XIAO・電源スイッチごと）・ボールの台をその穴から入れる
CAP_RIM_GAP = 0.5    # キーキャップの下面〜ケースの上面
CASE_TOP = PCB_TOP + SW_BODY_TOP - CAP_RIM_GAP   # ケースの壁の上端 = 上面
TOP_CLR = 0.75       # キーキャップの外〜トッププレートの縁（ケースの穴の縁まではさらに PLATE_CLEAR）
TOP_R = 1.0          # キーキャップのまわりの四角の角 R
TOP_CLOSE = 3.0      # 外形のくぼみを埋める半径（キーの島どうしと、マイコンカバー・ボールのまわりをつなぐ）
PCB_IN = 0.3         # ケースの穴の縁〜PCB の縁
WALL_T = 2.5
PLATE_CLEAR = 0.25
LEDGE_W = 1.5        # プレートを受ける内周の段
# 外周の面取り。内側の縁はプレートの落とし込みの縁（= トッププレートとの接点）から始め、
# 壁の上面に平らな部分を残さない。幅 = 壁厚
# ★下の縁はプレートの上面にそろえる（2026-10-06）。以前は高さも壁厚（2.5、45°）で、下の縁が z 10.1 だった。
#   マイコンのカバーの座（底 = プレートの上面 10.0）の両端で、面取りの下に 0.1 の段が出ていた。
#   いまは高さ 2.6（約 46°）
CHAMFER_W = WALL_T
CHAMFER_H = CASE_TOP - PLATE_TOP
# ---- ケースはアルミの CNC で削る（2026-10-06）。上（z+）から 1 回、底（z−）から 1 回の 2 工程を基本にし、
#      電源スイッチの窓だけ横から、リポバッテリのふたの爪の溝だけ T スロットカッターで削る
#      - 枠（ケースの上面）の下に空洞を作らない。中の空洞は上面の穴の範囲にとどめ、枠の下に要る空洞
#        （リポバッテリ・スライダー）は底から掘る
#      - 刃物の通る空洞の、平面で見た内側の角はすべて R を付ける（CNC_R。細い溝は CNC_R_SMALL）
CNC_R = 1.0          # 空洞の内側の角 R（φ2 の刃物）
CNC_R_SMALL = 0.5    # 幅 1.2 前後の細い溝の角 R（φ1 の刃物）
CNC_DZ = 0.2         # アンダーカットを調べる断面の間隔
CNC_Z0 = 0.137       # 断面の高さの始め（形の段の高さと重ならない端数）
CNC_MIN_AREA = 0.05  # これより小さいアンダーカットの断面は数えない（mm²）
SOCKET_H = 1.85      # Choc ホットスワップソケットの高さ（PCB の裏から）
SW_HOLE = 14.0       # Choc V2 の穴（下胴 13.95 が通る）。Choc V1 なら 13.8
# Choc V2 の爪（公開モデルの実測）: 穴の左右の辺の中央、幅 4.0（y ±2.0）、穴から 0.4 張り出し
# （x ±7.40）、PCB 上面から 0.15〜0.55。プレート 2.0 の下面は PCB 上面 + 0.20 なので、モデル上は
# 爪がプレートに埋まる。★実物は 2.0 のプレートにはまることを確かめてある（2026-09-30）ので、
# プレートの裏は加工しない。干渉チェックは爪の範囲（CLIP_BOX）だけを除いて見る
CLIP_HALF_W = 2.25   # 爪の幅の半分 2.0 ＋ 0.25
CLIP_OUT = 0.65      # 穴の辺から外へ（張り出し 0.4 ＋ 0.25）
CLIP_TOP = 0.60      # 爪の上端 0.55 ＋ 0.05（PCB 上面から）

# ---- 締結部品 --------------------------------------------------------------
SPACER_H = 6.0       # M2 メス‒メス 六角スペーサー。= 床上面〜プレート下面（ZEN の台に合わせて 6.0。2026-10-04）
# 床上面〜プレート下面がスペーサーより低いときだけ、床のスペーサーの位置を SPACER_SEAT 掘り下げる
# （いまは 0 で掘り下げない）
SPACER_SEAT = None   # 下で PLATE_BOT から決める
SPACER_R = 1.85      # 対辺 3.2 の角 3.7 を円で包む
SPACER_CLEAR = 0.25  # ケースの段・PCB の穴とスペーサーのすき間
M2_HOLE_R = 1.1
LOWHEAD_R = 1.9      # M2 低頭ネジの頭（φ3.8 × 1.0 で見積もる。★買うネジの寸法で直す）
LOWHEAD_H = 1.0
CSK_R = 1.9          # M2 皿ネジの頭（φ3.8、90°）
CSK_H = CSK_R - M2_HOLE_R   # 皿もみの深さ 0.8
BOT_CB_R = 2.2       # 脚の下の座ぐり
BOT_ENGAGE = 2.0     # 下の皿ネジがスペーサーへ入る長さ

# ---- テント ----------------------------------------------------------------
# ★テントはやめた（2026-10-04）。ケースの底は平らで、机にそのまま置く（tent_halfspace は z < 0）
TENT_RISE = 0.0
TENT_DEG = 0.0

SPACER_SEAT = SPACER_H - (PLATE_BOT - FLOOR_T)     # 床の掘り下げ（いまは 0）
assert DOOR_T + LIPO[2] + LIPO_PLATE_CLR <= PLATE_BOT + 1e-6, "リポバッテリがプレートの下面に近い"
SPACER_BOT = FLOOR_T - SPACER_SEAT                  # スペーサーの下面 z = 2.0
assert 0 <= SPACER_SEAT < FLOOR_T - CSK_H - 0.5, "床の掘り下げが深すぎる（皿もみの上に床が 0.5 残らない）"

# ---- マイコン XIAO nRF52840（2026-09-30）----------------------------------------
# メイン PCB の上に直接載せる（FPC は使わない）。★電池があった内側の列の北の端に置き（2026-10-03）、
# USB-C を北へ向けて、先端を北の外周の面と面一にする（はみ出さない）。XIAO には取り外せるカバー（`cover()`）をかぶせ、磁石で留める。
# XIAO はプレートより 2.3 高く出るので、プレートは XIAO のまわりを切り欠き、ケースの壁はカバーの
# 端が収まるよう上から切り欠く。★壁の切り欠きはプレートの上面までにとどめ、その下は外側に縁を残して
# USB-C の口だけを開ける（2026-10-06。カバーを外しても、壁がプレートと面一で続いて見える）。
# 寸法は Seeed の公開モデル（ref/xiao-nrf52840.step）の実測。
XIAO_LEN = 20.95     # 基板の長さ（USB-C の出っ張りを除く）
XIAO_WID = 17.78
XIAO_THK = 4.46      # 基板の下面（裏のパッド）〜USB-C の上面
XIAO_PCB_T = 1.25    # 基板（裏のパッド込み）。USB-C はこの上に載る
XIAO_USB_OUT = 1.53  # USB-C が基板の端から出る量
USB_W, USB_LEN, USB_H = 8.94, 7.30, 3.21
# ソケットの外形（キー中心から。y は南が +）。公開モデルの端子（x −5.4〜5.4, 中心から南へ 3.6〜6.0）を包む
SOCKET_BOX = (-5.5, 7.5, 2.2, 7.8)
XIAO_BOT = PCB_TOP                                   # XIAO の下面（裏のパッド）= PCB 上面
USB_Z0 = XIAO_BOT + XIAO_PCB_T
# ---- マイコンカバー ----
COVER_CLR = 0.15     # カバーの内側と XIAO の横のすき間（2026-09-30 に 0.5 から詰め、XIAO にぴったり沿わせた）
COVER_CLR_TOP = 0.2  # カバーの天井と XIAO の上面（USB-C の上面）のすき間
COVER_T = 1.2        # カバーの壁と天井の厚み
COVER_T_IN = 2.6     # 内側（キー側）の壁の厚み。磁石（穴 φ2.1）を埋める最小限
COVER_CAP_GAP = 1.0  # カバーの外面〜となりの列のキーキャップ（2026-10-03 に 1.5 から詰めた。北の帯の幅で決まる）
CAP_SIZE = 17.5
COVER_R = 3.0        # カバーの縦の角 R（上の縁の丸み COVER_FILLET 以上）
# ★形は参考画像にならう（2026-09-30）: 天井を COVER_TOP_T に厚くし、外周の上の縁を COVER_FILLET で
#   大きく丸めた、ふくらみのある縁。縁から COVER_RIM 内側の天面を COVER_RECESS へこませる。
#   リセットボタンの真上に押しボタン（C 字の切れ込みでたわむ丸い台と、裏の突起）、
#   LED の真上に穴（ドーナツ形のリングは 2026-10-06 にやめた）
COVER_TOP_T = 2.0
COVER_FILLET = 2.5
COVER_RIM = 2.8
COVER_RECESS = 0.6
BTN_R = 1.8          # 押しボタンの台の半径（丸い頭の半径）
BTN_SLOT = (2.3, 2.9)  # C 字の切れ込み（内径・外径）。カバーの中心側 70° を残して蝶番にする
BTN_HINGE = 70.0
BTN_POST_R = 0.8     # 裏の突起
BTN_GAP = 0.3        # 突起の先〜リセットボタンの頂部
LED_HOLE_R = 1.0
# XIAO の部品（公開モデルの座標: X = 長さ、Y = 厚さ、Z = 幅）
XIAO_RST = (10.41, 1.73, -11.83)     # リセットボタン（中心 x・頂部 y・中心 z）
XIAO_LED = (9.49, 1.30, -0.41)       # RGB LED
XIAO_SHIELD = ((-5.25, 3.00, -12.41), (5.35, 3.00, 0.19))   # nRF52840 モジュールのシールド（対角の 2 点）
SHIELD_WIN_MARGIN = 0.5              # シールドの窓（天面を抜いて上から見せる）の余白
NOTCH_Z = PCB_TOP - 0.2                              # 壁の内側の、XIAO の基板の端が入る溝の底
NOTCH_CLR = 0.2                                      # 壁の切り欠きとカバー、壁の外側の縁と XIAO の基板の端のすき間
USB_PORT_CLR = 0.3                                   # USB-C の口（ケースの縁とカバー）と USB-C のすき間
LIP_T = XIAO_USB_OUT - NOTCH_CLR                     # 壁の外側の縁の厚さ（USB-C の口のまわり、z PLATE_TOP まで）
COVER_TOP = XIAO_BOT + XIAO_THK + COVER_CLR_TOP + COVER_TOP_T  # カバーの天面
MAG_D, MAG_T = 2.0, 1.0                              # 磁石 φ2 × 1（FrostOrtho と同じ）
MAG_POCKET_R, MAG_POCKET_H = (MAG_D + 0.1) / 2, MAG_T + 0.05
# XIAO とカバーは、USB-C が西を向く「局所の向き」（外周の面 x = X_W、XIAO の中心線 y = 0）で作り、
# xiao_place_shape() で 90° 回して北の端に置く（USB-C の先端は北の外周の面 Y_N にそろう）


def _xiao_rect_local():
    x0 = X_W + XIAO_USB_OUT
    return (x0, -XIAO_WID / 2, x0 + XIAO_LEN, XIAO_WID / 2)


def _cover_rect_local():
    x0, y0, x1, y1 = _xiao_rect_local()
    c = COVER_CLR
    return (X_W, y0 - c - COVER_T, x1 + c + COVER_T_IN, y1 + c + COVER_T)


def xiao_xc(side):
    """XIAO の中心の x。カバーをキーキャップから COVER_CAP_GAP、外形の角の丸みから 0.3 離した範囲の中央。"""
    c = _cover_rect_local()
    half = (c[3] - c[1]) / 2
    if side == "L":
        lo = max(k[0] for k in KEYS[side]) + CAP_SIZE / 2 + COVER_CAP_GAP + half
        hi = X_E - R_CONVEX - 0.3 - half
    else:
        lo = X_W + R_CONVEX + 0.3 + half
        hi = min(k[0] for k in KEYS[side]) - CAP_SIZE / 2 - COVER_CAP_GAP - half
    assert lo <= hi + 1e-6, "%s: XIAO のカバーが北の帯に収まらない（%.2f）" % (side, hi - lo)
    return (lo + hi) / 2


def xiao_place_shape(shp, side):
    """局所の向きの形を、アセンブリ座標（北の端、USB-C が北）に置く。"""
    s = shp.copy()
    s.rotate(V(X_W, 0, 0), V(0, 0, 1), 90)
    s.translate(V(xiao_xc(side) - X_W, Y_N, 0))
    return s


def xiao_place_pt(p, side):
    return (xiao_xc(side) - p[1], p[0] - X_W + Y_N)


def _place_rect(r, side):
    x0, y0, x1, y1 = r
    xc = xiao_xc(side)
    return (xc - y1, x0 - X_W + Y_N, xc - y0, x1 - X_W + Y_N)


def xiao_rect(side):
    """XIAO の基板の平面範囲 (x0, y0, x1, y1)。USB-C の先端は北の外周の面にそろう。"""
    return _place_rect(_xiao_rect_local(), side)


def cover_rect(side):
    """カバーの外形の平面範囲 (x0, y0, x1, y1)。北の端は外周の面にそろう。"""
    return _place_rect(_cover_rect_local(), side)


def magnet_points(side):
    """カバーとプレートの磁石の中心（南の厚い壁の両端寄り）。"""
    x0, y0, x1, y1 = _xiao_rect_local()
    x = x1 + COVER_CLR + COVER_T_IN / 2
    return [xiao_place_pt((x, y0 + 1.5), side), xiao_place_pt((x, y1 - 1.5), side)]


def usb_recess(side):
    """外壁〜USB-C の先端（いまは 0 = 面一）。"""
    return (_xiao_rect_local()[0] - XIAO_USB_OUT) - X_W


def floor_bottom_z(side, x):
    """テントの面（机）の z。外側の辺で 0、内側の辺で −TENT_RISE。"""
    return -TENT_RISE * ((x - X_W) / W_OUT if side == "L" else (X_E - x) / W_OUT)


for _side in ("L", "R"):
    _x0, _y0, _x1, _y1 = xiao_rect(_side)
    _c = cover_rect(_side)
    _gap = min(max(abs(k[0] - (_c[0] + _c[2]) / 2) - (_c[2] - _c[0]) / 2, abs(k[1] - (_c[1] + _c[3]) / 2) - (_c[3] - _c[1]) / 2)
               - CAP_SIZE / 2 for k in KEYS[_side] + THUMBS[_side])
    assert _gap >= COVER_CAP_GAP - 1e-6, "%s: カバーがキーキャップに近い（%.2f）" % (_side, _gap)

# ---- タグ（ラベルプレート、2026-10-03 に復活）: 決定案の画像のとおり、3 段目の南の帯にケースの上面から
#      載せる別部品。両端の半円の中心を M2 低頭のネジでケースの上面のめねじへ留める
# ★タグの外側の端を、外周から下側と同じ余白（TAG_MARGIN）に寄せ、タグのある角をタグの端の半円と同じ中心の
#   R（TAG_CORNER_R）で丸める（2026-10-03）。タグの長さ・幅・高さは画像のまま（→ 2026-10-06 に縮めた）
# ★タグを小さくし、ケースの上面の平らな部分の中に余白をそろえて置く（2026-10-06）。以前は高さ 11.81 で、外側の
#   端と南の端が外周の面取りの縁から 0.25 しか離れず、北の端〜上面の穴の縁は 2.54 だった。いまは高さ TAG_H、
#   面取りの縁・上面の穴の縁から TAG_GAP。キー側の端（左は東、右は西）は以前の位置のまま
TAG_GAP = 2.3                       # タグの縁〜外周の面取りの縁・上面の穴の縁
TAG_MARGIN = CHAMFER_W + TAG_GAP    # タグの外側の端・南の端〜外周の面（4.8）
TAG_H = 10.0                        # タグの高さ（y）
_TAG_Y1 = H_MAIN_L - TAG_MARGIN
_TAG_Y0 = _TAG_Y1 - TAG_H
_TAG_IN = {"L": 56.83, "R": 85.48}  # キー側の端の x（以前の位置）
TAG = {"L": (X_OUT["L"] + TAG_MARGIN, _TAG_Y0, _TAG_IN["L"], _TAG_Y1),
       "R": (_TAG_IN["R"], _TAG_Y0, X_OUT["R"] - TAG_MARGIN, _TAG_Y1)}   # x0, y0, x1, y1
TAG_CORNER_R = TAG_H / 2 + TAG_MARGIN   # タグのある角の R（9.8。タグの端の半円と同じ中心）
_hole_s = max(k[1] for k in KEYS["L"]) + CAP_SIZE / 2 + TOP_CLR + PLATE_CLEAR   # 3 段目の南の、上面の穴の縁
assert _TAG_Y0 - _hole_s >= TAG_GAP - 1e-6, "タグが上面の穴の縁に近い（%.2f）" % (_TAG_Y0 - _hole_s)
TAG_T = 1.5


def tag_screws(side):
    x0, y0, x1, y1 = TAG[side]
    r = (y1 - y0) / 2
    return [(x0 + r, y0 + r), (x1 - r, y0 + r)]


# ---- トラックボール --------------------------------------------------------
# ★ZEN Keyboard（E24-GH/zen-firmware の 3d-models、v1.3）の作りをそのまま写す（2026-10-04）。ZEN の STL の
#   断面から寸法を読んだ（ZEN の STL はリポジトリに入れない）。高さはすべて台の底（BASE_BOT）が基準で、
#   ZEN と同じく、台は床の上に置き、プレートの下面は台の上面から 0.3 上に来る
#   - ボールの真下の円い「台」（zen-trackball-parts-PAW3222 の 28 角を円にした）から柱 3 本を立て、柱の溝のベアリング（681X）
#     でボールを受ける。ベアリングの軸は φ1.5 のピンで、柱の斜めの溝から落とし込む
#   - センサー（PAW3222）は台の上面の溝（幅 7.8）に北から入れ、真下からボールを見る
#   - 台の上面から立てた筒（丸い山のねじ）にカバーをねじ込む。反時計回りで外れる。カバーの東西の爪がボールの
#     赤道より上を押さえる。★ZEN はねじの立ち上がりをトッププレートに付けるが、台に付けてトラックボールの部品を
#     ひとまとまりにした（2026-10-04）。筒はプレートの穴を通り、ねじの部分はプレートの上に出る
#   - 台は床の下から M2 の皿のタッピングネジ 2 本で留める
BALL_R = 9.5                         # φ19（ZEN と同じ）
# ねじの筒（台と一体）。台の上面からプレートの上面 + COLLAR_H まで。ねじの部分の寸法は ZEN の立ち上がりと同じ
COLLAR_R = (14.0, 15.0)              # 内半径・外半径
COLLAR_H = 3.0                       # プレートの上に出る高さ（ねじの部分）
PLATE_HOLE_CLR = 0.55                # プレートの穴と筒のすき間（ねじの山の始まり〔外半径 15.45〕が穴の縁に掛かるので広め）
THREAD_PITCH = 1.33
THREAD_PROF_R = 0.5                  # 丸い山（立ち上がり）と溝（カバー）の断面の半径
COLLAR_BEAD_R = COLLAR_R[1] - 0.05   # 立ち上がりの山の中心の半径（ZEN は外半径 − 0.02）
# カバー（r, プレート上面からの dz）。ZEN のカバーの断面
RING_IN_R, RING_OUT_R = 15.48, 16.98 # 筒（ねじの部分）
RING_GROOVE_R = RING_IN_R + 0.36     # カバーの溝の中心の半径
RING_SLEEVE_H = 4.7                  # 筒の上端（外の円すいの始まり）
RING_TOP_OUT_R = 14.34               # 平らな上面の外の縁
RING_UNDER_R = 13.29                 # 口の下面の外の縁（ここから筒の内面へ斜めに下りる）
RING_LIP_R = 10.1                    # 口（ボールより 0.6 大きい。ボールは爪で押さえる）
RING_LIP_Z = (7.2, 7.7)              # 口の下面・平らな上面
# 爪（東西の 2 つ）。口の上に立ち、外面は筒の上の円すいの続き、内面は口と同じ半径。先は内へ折れてボールを押さえる
CLAW_AZ = (0.0, 180.0)
CLAW_HALF_DEG = 20.8                 # 爪の幅（中心から片側の角度）
CLAW_TOP = 11.65                     # 爪の上端（dz）
CLAW_TIP = (9.3, 10.8, 11.4)         # 先の内半径・内へ折れ始める dz・先の下の縁の dz
# 台（ZEN の四角いモジュール）。★床の上面から BASE_SINK 掘り下げた座に置く（ZEN の積み方に合わせると、
# スペーサーが 6.3 になるので、0.3 沈めて 6.0 にした）
BASE_R = 15.5                        # 外形の半径。★ZEN の 28 角から円にした（2026-10-04）。ねじの筒（外半径 15.0）が載る
BASE_H = 6.0
BALL_PLATE_R = RING_OUT_R + 0.35     # トッププレートのボールのまわりの円（カバーが座り、台が通る）
BASE_SINK = 0.3
BASE_SEAT_CLR = 0.2                  # 床の座と台のすき間
BASE_BOT = FLOOR_T - BASE_SINK
BASE_TOP = BASE_BOT + BASE_H
BASE_FLOOR_T = 1.0                   # センサーの溝の底の厚さ
SENSOR_CH_W, SENSOR_CH_S = 7.8, 4.5  # PAW3222 の溝（幅・中心から南の端）。上は開き、北の縁へ抜ける
SENSOR_CH_CHAMFER = 1.0             # 溝の上端（東西の長辺と南の端）の 45° の面取り
# 台を留めるネジ（ケースの底から床を通して台へ。M2 × 3 の皿のタッピングネジ）。ZEN の位置（南西と北東）
BASE_SCREW = [(-10.5, 7.5), (11.5, -7.5)]
BASE_SCREW_LEN = 3.0
BASE_PILOT = (0.9, 1.5)              # 台の下穴（半径・深さ）。ZEN と同じ
# 柱（ZEN の断面の写し。r はボールの軸から、dz は台の上面から）。接線方向の幅 6.0、中央に幅 2.6 の溝
POST_W, POST_SLOT_W = 6.0, 2.6
POST_AZ = (90.0, 210.0, 330.0)       # 柱の向き（y は南が +。1 本を南に）
AXLE = (10.32, 6.5)                  # 軸の位置（r, dz）
POST_PROFILE = [(8.5, -0.2), (13.5, -0.2), (13.5, 7.0), (13.466, 7.259), (13.366, 7.5), (13.207, 7.707),
                (13.0, 7.866), (12.759, 7.966), (12.5, 8.0), (9.5, 8.0), (8.5, 7.0)]
POST_SLOT_PROFILE = [(8.5, -0.2), (13.5, -0.2), (13.5, 7.0), (13.466, 7.259), (13.366, 7.5), (13.207, 7.707),
                     (13.0, 7.866), (12.759, 7.966), (12.57, 8.0), (12.57, 6.0), (12.541, 5.745), (12.425, 5.249),
                     (12.201, 4.792), (11.878, 4.397), (11.474, 4.086), (11.011, 3.874), (10.512, 3.773),
                     (10.002, 3.787), (9.509, 3.917), (9.059, 4.155), (8.673, 4.488), (8.5, 4.677)]
AXLE_SLOT_DEG = 30.0                 # 軸を落とし込む溝の傾き（鉛直から、上ほどボールの軸へ寄る）
BEARING = (2.0, 2.0)                 # 681X（内径 1.5 × 外径 4 × 幅 2）
AXLE_PIN = (0.75, 6.0)               # 軸のピン（半径・長さ）。柱の幅と同じ長さ
# センサー: ZEN の溝に入る幅のモジュールを仮置きする（寸法は実物で直す）
SENSOR_PCB = (7.4, 12.0, 1.6)        # 基板（幅 x・奥行き y・厚さ）。南の端は溝の南の端から 0.2
SENSOR_LENS = (2.5, 3.0)             # チップとレンズ（半径・基板の上の高さ）。仮置き
SENSOR_CH_FLOOR = BASE_BOT + BASE_FLOOR_T
# ボールの中心: ベアリング（軸 AXLE）にボールの面が接する高さ
BRG_ANGLE = math.degrees(math.acos(AXLE[0] / (BALL_R + BEARING[0])))      # 赤道から下へ約 26°
BALL_CZ = BASE_TOP + AXLE[1] + math.sqrt((BALL_R + BEARING[0]) ** 2 - AXLE[0] ** 2)
SENSOR_GAP = BALL_CZ - BALL_R - (SENSOR_CH_FLOOR + SENSOR_PCB[2] + SENSOR_LENS[1])   # レンズの上端〜ボールの下端
BALL_PROTRUDE = BALL_CZ + BALL_R - PLATE_TOP
assert abs(PLATE_BOT - (BASE_TOP + 0.3)) < 1e-6, "プレートの下面が台の上面 + 0.3 でない（ZEN の積み方）"
assert max(r for r, dz in POST_PROFILE) <= COLLAR_R[0] - 0.3, "柱がねじの筒に当たる"
assert PLATE_HOLE_CLR > 0, "プレートの穴が筒に当たる"
assert SENSOR_GAP > 1.5, "センサーとボールが近い"

# ---- アセンブリ用の簡略部品 --------------------------------------------------
GAP_HALVES = 40.0
CAP_H = 5.8          # torabo-tsuki-om-case の RidgeCap（実測 5.802）に合わせた。ステム上端 8.60 を覆う
# LAK に寄せた形（`keycap()`、2026-10-06）。寸法は写真と図からの見立て
CAP_R = 1.5          # 平面の角 R
CAP_WALL_H = 3.6     # 垂直な側面の高さ（下面から）
CAP_TOP_INSET = 1.5  # 上面の縁が側面から内へ入る量（斜めの肩）
CAP_TOP_R = 2.0      # 上面の角 R
CAP_DISH = 0.5       # 上面の円柱のくぼみの深さ（中央）
CAP_Z = PCB_TOP + SW_BODY_TOP        # キャップ下面はハウジング上面に座る
KEY_TRAVEL = 3.0     # Choc V2 のトータルトラベル。押し込んだキャップ下面はプレート上面 + 0.1


# =============================================================================
# 2D のヘルパー（z=0 の面）
# =============================================================================
def rect_face(x0, y0, w, h):
    pts = [V(x0, y0, 0), V(x0 + w, y0, 0), V(x0 + w, y0 + h, 0), V(x0, y0 + h, 0), V(x0, y0, 0)]
    return Part.Face(Part.makePolygon(pts))


def circle_face(cx, cy, r):
    return Part.Face(Part.Wire(Part.makeCircle(r, V(cx, cy, 0))))


def single_face(shape):
    s = shape.removeSplitter()
    faces = sorted(s.Faces, key=lambda f: f.Area, reverse=True)
    if len(faces) != 1:
        raise RuntimeError("面が 1 枚にならない: %s" % ["%.3f" % f.Area for f in faces])
    return faces[0]


def offset_sharp(face, d):
    # 円弧を含む面は交点結合（join=2）で失敗することがある。外形は角をすべて
    # 丸めてあるので、そのときは円弧結合で代える（結果は同じになる）
    try:
        return single_face(face.makeOffset2D(d, join=2))
    except Exception:
        return single_face(face.makeOffset2D(d, join=0))


def offset_round(face, d):
    return single_face(face.makeOffset2D(d, join=0))


def rrect_face(c, w, h, r):
    """中心 c・外形 w×h・角 R の角丸長方形。"""
    return offset_round(rect_face(c[0] - w / 2 + r, c[1] - h / 2 + r, w - 2 * r, h - 2 * r), r)


def rounded_outline(face):
    f = offset_round(offset_round(face, R_CONCAVE), -R_CONCAVE)   # 入り隅を丸める（閉じる）
    return offset_round(offset_round(f, -R_CONVEX), R_CONVEX)      # 角を丸める（開く）


def union_faces(faces):
    """平面の面どうしの和を 1 枚の面で返す。面のまま fuse すると境界で割れるので、
    いったん押し出して立体で足し、底面を取り出す。"""
    solid = faces[0].extrude(V(0, 0, 1))
    for f in faces[1:]:
        solid = solid.fuse(f.extrude(V(0, 0, 1)))
    solid = solid.removeSplitter()
    bottom = [f for f in solid.Faces if f.BoundBox.ZMax < 1e-6]
    return single_face(Part.makeCompound(bottom)) if len(bottom) == 1 else single_face(bottom[0].fuse(bottom[1:]))


_outline_cache = {}


def round_corner(face, cx, cy, r, sx, sy):
    """面の角（cx, cy）を半径 r で丸め直す。sx・sy は角から面の内側へ向かう向き（±1）。"""
    x0 = cx if sx > 0 else cx - r
    y0 = cy if sy > 0 else cy - r
    sq = rect_face(x0, y0, r, r)
    disc = circle_face(cx + sx * r, cy + sy * r, r).common(sq)
    return union_faces([face.cut(sq), disc]) if disc.Area > 0 else face


def outline(side):
    """外形。角は R_CONVEX、入り隅は R_CONCAVE。電池の脚（筒）も外形に沿って切る（2026-10-03）。"""
    if side not in _outline_cache:
        if side == "L":
            raw = union_faces([rect_face(X_OUT["L"], Y_N, X_E - X_OUT["L"], H_MAIN_L - Y_N),
                               rect_face(THUMB_X0_L, Y_N, X_E - THUMB_X0_L, H_THUMB - Y_N)])
        else:
            raw = union_faces([rect_face(X_W, Y_N, X_OUT["R"] - X_W, H_MAIN_R - Y_N),
                               rect_face(X_W, Y_N, THUMB_X1_R - X_W, H_THUMB - Y_N),
                               circle_face(BULGE_C[0], BULGE_C[1], BULGE_R)])
        f = rounded_outline(raw)
        # タグのある角（左は南西、右は南東）をタグの端と同じ中心の R に
        if side == "L":
            f = round_corner(f, X_OUT["L"], H_MAIN_L, TAG_CORNER_R, +1, -1)
        else:
            f = round_corner(f, X_OUT["R"], H_MAIN_R, TAG_CORNER_R, -1, -1)
        _outline_cache[side] = f
    return _outline_cache[side]


def prism(face, z0, h):
    f = face.copy()
    f.translate(V(0, 0, z0))
    return f.extrude(V(0, 0, h))


# =============================================================================
# ケース
# =============================================================================
def tent_halfspace(side):
    """底面より下（切り落とす側）の半空間。内側の縁ほど底が下がる。"""
    box = Part.makeBox(1000, 1000, 1000, V(-500, -500, -1000))
    box.rotate(V(0, 0, 0), V(0, 1, 0), TENT_DEG if side == "L" else -TENT_DEG)
    box.translate(V(X_E if side == "L" else X_W, 0, -TENT_RISE))
    return box


def chamfer_band(ol):
    """外周の面取りの帯（z = CASE_TOP − CHAMFER_H 〜 CASE_TOP）。

    下は外形、上は外形を CHAMFER_W だけ内へ寄せた線（= プレートとトップフレームの落とし込みの縁）。
    2 本の線をまっすぐつなぐので、斜面は面取りの内側の縁から外周まで一定の角度になる。
    """
    lo = ol.OuterWire.copy()
    lo.translate(V(0, 0, CASE_TOP - CHAMFER_H))
    hi = offset_sharp(ol, -CHAMFER_W).OuterWire.copy()
    hi.translate(V(0, 0, CASE_TOP))
    assert len(lo.Edges) == len(hi.Edges), "面取り: 外形と内側の線の辺の数が違う（%d / %d）" % (len(lo.Edges), len(hi.Edges))
    return Part.makeLoft([lo, hi], True, True)


M2_LENGTHS = (3, 4, 5, 6, 8, 10, 12, 14, 16, 20)


def bottom_seat(side, s):
    """下の皿ネジの座（皿もみの下端の z）と長さ。ふつうは床の下面 z = 0 に座らせて M2×4。
    ボールの台を通す点は、スペーサーへ BOT_ENGAGE 入る長さのうち、座が台の底より下に出ない最も長い
    ものにし、台の底から平らな座ぐりで座まで掘る。"""
    zb = foot_bottom_at(side, s)
    top = SPACER_BOT + BOT_ENGAGE
    length = max(n for n in M2_LENGTHS if top - n >= zb - 1e-6)
    return top - length, length


_face_cache = {}


def ball_base_screws():
    """ボールの台をケースに留めるネジ（ケースの中から台へ）。"""
    return [(BULGE_C[0] + dx, BULGE_C[1] + dy) for dx, dy in BASE_SCREW]


def foot_bottom_at(side, s):
    """下の皿ネジの点の、頭が座る面の z（ケースの底 0）。"""
    return 0.0


def bottom_screw_cuts(s, seat):
    """下の皿ネジの通し穴・皿もみ・座ぐり（座より下）。"""
    return [Part.makeCylinder(M2_HOLE_R, SPACER_BOT - seat + 1, V(s[0], s[1], seat - 0.5)),
            Part.makeCone(CSK_R, M2_HOLE_R, CSK_H, V(s[0], s[1], seat)),
            Part.makeCylinder(BOT_CB_R, 30, V(s[0], s[1], seat - 30))]


def _helix_sweep(r, z0, h, prof_r, cx=0.0, cy=0.0):
    """半径 r・ピッチ THREAD_PITCH のつる巻き線に沿って、半径 prof_r の円を掃いた形（右ねじ）。"""
    helix = Part.makeHelix(THREAD_PITCH, h, r)
    helix.translate(V(cx, cy, z0))
    p0 = helix.Vertexes[0].Point
    t = helix.Edges[0].tangentAt(helix.Edges[0].FirstParameter)
    circ = Part.Wire(Part.makeCircle(prof_r, p0, t))
    return Part.Wire(helix.Edges).makePipeShell([circ], True, True)


def ball_pocket_cuts():
    """ケースの、台を置く床の座（BASE_SINK の掘り下げ）と、台を留める皿ネジの穴（下から。右手、アセンブリ座標）。"""
    cx, cy = BULGE_C
    out = [Part.makeCylinder(BASE_R + BASE_SEAT_CLR, FLOOR_T - BASE_BOT + 0.01, V(cx, cy, BASE_BOT))]
    for p in ball_base_screws():
        out += [Part.makeCylinder(M2_HOLE_R, FLOOR_T + 2, V(p[0], p[1], -1)),
                Part.makeCone(CSK_R, M2_HOLE_R, CSK_H, V(p[0], p[1], 0))]
    return out


def _post_solid(profile, t0, t1):
    """柱の断面（r, dz）を接線方向に t0〜t1 だけ押し出した形（局所: r = x、接線 = y）。"""
    w = Part.makePolygon([V(r, t0, BASE_TOP + dz) for r, dz in profile] + [V(profile[0][0], t0, BASE_TOP + profile[0][1])])
    return Part.Face(w).extrude(V(0, t1 - t0, 0))


def ball_base():
    """ボールの台（右手、別部品）。ZEN の PAW3222 用の台（28 角 × 6）を円（半径 BASE_R × 6）にし、カバーをねじ込む筒を足した形。床の座に置き、底から皿のタッピング
    ネジ 2 本で留める。上面に PAW3222 の溝（幅 7.8、中心の 4.5 南から北の縁へ抜け、上端は 45° の面取り）。
    柱 3 本（中央に幅 2.6 のベアリングの溝、両側の半分に軸のピンを落とし込む斜めの溝）は PCB・プレートの穴を
    通ってボールの下へ立つ。"""
    cx, cy = BULGE_C
    b = Part.makeCylinder(BASE_R, BASE_H, V(cx, cy, BASE_BOT))
    w, s_end, c = SENSOR_CH_W, SENSOR_CH_S, SENSOR_CH_CHAMFER
    L = BASE_R + 1 + s_end
    y_n = cy + s_end - L                          # 北の縁より外まで
    ch = Part.makeBox(w, L, BASE_TOP - SENSOR_CH_FLOOR + 1, V(cx - w / 2, y_n, SENSOR_CH_FLOOR))
    lo = Part.makePolygon([V(cx - w / 2, y_n, BASE_TOP - c), V(cx + w / 2, y_n, BASE_TOP - c),
                           V(cx + w / 2, cy + s_end, BASE_TOP - c), V(cx - w / 2, cy + s_end, BASE_TOP - c),
                           V(cx - w / 2, y_n, BASE_TOP - c)])
    hi = Part.makePolygon([V(cx - w / 2 - c - 0.01, y_n, BASE_TOP + 0.01), V(cx + w / 2 + c + 0.01, y_n, BASE_TOP + 0.01),
                           V(cx + w / 2 + c + 0.01, cy + s_end + c + 0.01, BASE_TOP + 0.01),
                           V(cx - w / 2 - c - 0.01, cy + s_end + c + 0.01, BASE_TOP + 0.01), V(cx - w / 2 - c - 0.01, y_n, BASE_TOP + 0.01)])
    b = b.cut(ch.fuse(Part.makeLoft([lo, hi], True)))
    ar, az = AXLE
    t = math.radians(AXLE_SLOT_DEG)
    for a in POST_AZ:
        h = POST_SLOT_W / 2
        post = _post_solid(POST_PROFILE, -POST_W / 2, -h).fuse(_post_solid(POST_PROFILE, h, POST_W / 2))
        post = post.fuse(_post_solid(POST_SLOT_PROFILE, -h - 0.01, h + 0.01))
        # 軸のピンの穴と、上から落とし込む斜めの溝（幅 = ピンの径）
        post = post.cut(Part.makeCylinder(AXLE_PIN[0], POST_W + 2, V(ar, -POST_W / 2 - 1, BASE_TOP + az), V(0, 1, 0)))
        slot = Part.makeBox(2 * AXLE_PIN[0], POST_W + 2, 5.0, V(-AXLE_PIN[0], -POST_W / 2 - 1, 0))
        slot.rotate(V(0, 0, 0), V(0, 1, 0), -AXLE_SLOT_DEG)
        slot.translate(V(ar, 0, BASE_TOP + az))
        post = post.cut(slot)
        post.rotate(V(0, 0, 0), V(0, 0, 1), a)
        b = b.fuse(moved(post, cx, cy))
    b = b.fuse(moved(base_collar(), cx, cy))                               # ねじの筒
    for p in ball_base_screws():
        b = b.cut(Part.makeCylinder(BASE_PILOT[0], BASE_PILOT[1], V(p[0], p[1], BASE_BOT - 0.01)))
    return b.removeSplitter()


def bearings():
    """ベアリング 681X（φ4 × 2）と軸のピン（φ1.5 × 6）。ボールの中心の真下が原点。"""
    r, dz = AXLE
    out = []
    for a in POST_AZ:
        brg = Part.makeCylinder(BEARING[0], BEARING[1], V(r, -BEARING[1] / 2, BASE_TOP + dz), V(0, 1, 0))
        brg = brg.cut(Part.makeCylinder(AXLE_PIN[0], BEARING[1] + 1, V(r, -BEARING[1] / 2 - 0.5, BASE_TOP + dz), V(0, 1, 0)))
        pin = Part.makeCylinder(AXLE_PIN[0] - 0.01, AXLE_PIN[1], V(r, -AXLE_PIN[1] / 2, BASE_TOP + dz), V(0, 1, 0))
        part = Part.makeCompound([brg, pin])
        part.rotate(V(0, 0, 0), V(0, 0, 1), a)
        out.append(part)
    return Part.makeCompound(out)


def base_collar():
    """台の上面から立てるねじの筒と、その丸い山（右手、原点 = ボールの中心の真下）。プレートの穴を通って
    プレートの上に COLLAR_H 出る。"""
    z0, z1 = BASE_TOP - 0.01, PLATE_TOP + COLLAR_H
    c = Part.makeCylinder(COLLAR_R[1], z1 - z0, V(0, 0, z0))
    c = c.cut(Part.makeCylinder(COLLAR_R[0], z1 - z0 + 2, V(0, 0, z0 - 1)))
    bead = _helix_sweep(COLLAR_BEAD_R, PLATE_TOP + 0.3, COLLAR_H - 0.9, THREAD_PROF_R)
    return c.fuse(bead)


def ball_ring():
    """カバー（右手、別部品。原点 = ボールの中心の真下）。ZEN のカバーの写し: 立ち上がりにねじ込む筒（内面に
    丸い溝のねじ）、その上の円すいの外面と平らな上面、口（半径 10.1）、口の上の東西の爪（先が内へ折れて
    ボールの赤道より上を押さえる）。"""
    z = PLATE_TOP
    pts = [(RING_IN_R, 0.0), (RING_OUT_R, 0.0), (RING_OUT_R, RING_SLEEVE_H), (RING_TOP_OUT_R, RING_LIP_Z[1]),
           (RING_LIP_R, RING_LIP_Z[1]), (RING_LIP_R, RING_LIP_Z[0]), (RING_UNDER_R, RING_LIP_Z[0]),
           (RING_IN_R, RING_SLEEVE_H + 0.3)]
    w = Part.makePolygon([V(r, 0, z + dz) for r, dz in pts] + [V(pts[0][0], 0, z + pts[0][1])])
    body = Part.Face(w).revolve(V(0, 0, 0), V(0, 0, 1), 360).removeSplitter()
    # 爪: 外面は筒の上の円すいの続き
    k = (RING_OUT_R - RING_TOP_OUT_R) / (RING_LIP_Z[1] - RING_SLEEVE_H)
    out_r = lambda dz: RING_OUT_R - k * (dz - RING_SLEEVE_H)
    tip_r, bend, tip_lo = CLAW_TIP
    cp = [(RING_LIP_R, RING_LIP_Z[1] - 0.01), (out_r(RING_LIP_Z[1]), RING_LIP_Z[1] - 0.01), (out_r(CLAW_TOP), CLAW_TOP),
          (tip_r, CLAW_TOP), (tip_r, tip_lo), (RING_LIP_R, bend)]
    cw = Part.makePolygon([V(r, 0, z + dz) for r, dz in cp] + [V(cp[0][0], 0, z + cp[0][1])])
    for a in CLAW_AZ:
        claw = Part.Face(cw).revolve(V(0, 0, 0), V(0, 0, 1), 2 * CLAW_HALF_DEG)
        claw.rotate(V(0, 0, 0), V(0, 0, 1), a - CLAW_HALF_DEG)
        body = body.fuse(claw)
    groove = _helix_sweep(RING_GROOVE_R, z - 0.6, COLLAR_H + 0.3, THREAD_PROF_R)
    return body.removeSplitter().cut(groove)


def tag_plate(side):
    """タグ（別部品）。両端が半円の板をトップフレームの上に載せ、半円の中心を低頭ネジで留める。"""
    x0, y0, x1, y1 = TAG[side]
    r = (y1 - y0) / 2
    t = prism(rrect_face(((x0 + x1) / 2, (y0 + y1) / 2), x1 - x0, y1 - y0, r - 0.01), CASE_TOP, TAG_T)
    for s in tag_screws(side):
        t = t.cut(Part.makeCylinder(M2_HOLE_R, 10, V(s[0], s[1], CASE_TOP - 1)))
    return t.removeSplitter()


def cover_notch(side):
    """北の壁の切り欠き。
    - カバーの端が収まる浅い切り欠き（カバーの外形 ＋ NOTCH_CLR、底はプレートの上面）
    - その下は、外側に LIP_T の縁を残し、縁に USB-C の口（カバーの穴と同じ幅・下端）を開ける
    - 縁の内側に、XIAO の基板の端が入る溝（プレートの切り欠きと同じ幅、底 NOTCH_Z）
    カバーを外すと、壁はプレートと面一で続き、USB-C の口だけが開いて見える。"""
    cx0, cy0, cx1, cy1 = _cover_rect_local()
    x0, y0, x1, y1 = _xiao_rect_local()
    outer = offset_round(rrect_face(((cx0 + cx1) / 2, (cy0 + cy1) / 2), cx1 - cx0, cy1 - cy0, COVER_R), NOTCH_CLR)
    seat = prism(outer, PLATE_TOP, 30)
    yc, hw = (y0 + y1) / 2, (y1 - y0) / 2 + COVER_CLR
    pocket = rbox(X_W + LIP_T, X_W + WALL_T + 1.0, yc - hw, yc + hw, NOTCH_Z, PLATE_TOP + 0.01, CNC_R_SMALL)   # 南の端は XIAO の逃げの中
    # USB-C の口: USB-C の長円 ＋ USB_PORT_CLR。上（プレートの上面より上）はカバーの穴が受け持つ
    port = usb_stadium(X_W - 1, LIP_T + 1.01, yc, USB_PORT_CLR)
    return xiao_place_shape(seat.fuse([pocket, port]).removeSplitter(), side)


def xiao_clearance(side):
    """XIAO の下の PCB の張り出しと、XIAO のパッドを逃がす（壁際の段を削る）。"""
    x0, y0, x1, y1 = _xiao_rect_local()
    bx0, bx1 = X_W + WALL_T, x1 + 0.5
    return xiao_place_shape(rbox(bx0, bx1, y0 - 0.5, y1 + 0.5, PCB_BOT - 0.5, PCB_BOT + 29.5, CNC_R), side)


def psw_geom(side):
    """電源スイッチまわりの寸法。s = 外向き（左 +1 ／ 右 −1）、x はすべて外向きに増える量で返す。"""
    s = 1 if side == "L" else -1
    bx = PSW_X[side]                                          # 本体の内側の面
    wall_in = X_E - WALL_T if side == "L" else X_W + WALL_T
    outer = X_E if side == "L" else X_W
    body_out = bx + s * PSW_BODY[0]
    tip = body_out + s * PSW_KNOB_L
    zb0 = PCB_BOT - PSW_BODY[2]                              # 本体の下面（PCB の裏から下がる）
    zc = PCB_BOT - PSW_BODY[2] / 2                           # つまみの中心の高さ
    win_w = SLD_NOSE[0] + PSW_STROKE + 2 * SLD_CLR          # 窓の幅（y）
    win_h = SLD_NOSE[1] + 2 * SLD_CLR                        # 窓の高さ（z）
    keep_w = win_w + PSW_STROKE                              # 抜け止めの幅（窓の裏をふさぐ）
    return dict(s=s, bx=bx, body_out=body_out, tip=tip, wall_in=wall_in, outer=outer, zb0=zb0, zc=zc,
                win_w=win_w, win_h=win_h, keep_w=keep_w)


def xbox(x_a, x_b, y0, y1, z0, z1):
    """x の範囲を向きに関係なく並べ替えて箱を作る。"""
    xa, xb = sorted((x_a, x_b))
    return Part.makeBox(xb - xa, y1 - y0, z1 - z0, V(xa, y0, z0))


def rbox(x_a, x_b, y0, y1, z0, z1, r):
    """平面で見た角を r で丸めた箱（CNC の刃物の通る空洞）。x の範囲は向きに関係なく並べ替える。"""
    xa, xb = sorted((x_a, x_b))
    return prism(_rr(xa, y0, xb, y1, r), z0, z1 - z0)


def power_switch(side, shift=0.0):
    """電源スイッチ（本体 ＋ つまみ）。shift はつまみの位置（ストロークの端は ±1.0）。"""
    g = psw_geom(side)
    body = xbox(g["bx"], g["body_out"], PSW_Y - PSW_BODY[1] / 2, PSW_Y + PSW_BODY[1] / 2, g["zb0"], PCB_BOT)
    k = PSW_KNOB / 2
    knob = xbox(g["body_out"], g["tip"], PSW_Y + shift - k, PSW_Y + shift + k, g["zc"] - k, g["zc"] + k)
    return body.fuse(knob)


def slider(side, shift=0.0):
    """電源スイッチのスライダー（別部品）。shift はスライド量（ストロークの端は ±1.0）。

    首は壁の窓を通って外面から 0.3 出る（先に滑り止めのリブ 3 本）。抜け止めは壁の内側で、窓より
    背が高く、窓よりストロークぶん広いので外へ抜けず、窓の裏もふさぐ。つまみは首と抜け止めを
    通る溝（z 方向に貫通）が挟む。組むときは、ケースの中から首を窓へ差し、そのあと PCB を載せる
    （つまみは上から溝に落ちる）。
    """
    g = psw_geom(side)
    s = g["s"]
    y = PSW_Y + shift
    nh = SLD_NOSE[1] / 2
    # 首は、窓の角 R（CNC_R）からすき間 SLD_CLR を引いた R で丸める（窓の面で見た角）
    x_edges = lambda b: [e for e in b.Edges if e.BoundBox.YLength < 1e-6 and e.BoundBox.ZLength < 1e-6]
    nose = xbox(g["wall_in"] - s * 0.1, g["outer"] + s * 0.3, y - SLD_NOSE[0] / 2, y + SLD_NOSE[0] / 2, g["zc"] - nh, g["zc"] + nh)
    nose = nose.makeFillet(CNC_R - SLD_CLR, x_edges(nose))
    tip = xbox(g["outer"], g["outer"] + s * 0.7, y - SLD_NOSE[0] / 2, y + SLD_NOSE[0] / 2, g["zc"] - nh, g["zc"] + nh)
    tip = tip.makeFillet(CNC_R - SLD_CLR, x_edges(tip))                  # リブを首の断面に収める
    keep = xbox(g["body_out"] + s * 0.1, g["wall_in"] - s * 0.1, y - g["keep_w"] / 2, y + g["keep_w"] / 2,
                g["zb0"] + 0.1, PCB_BOT - 0.15)
    sld = nose.fuse(keep)
    for dy in (-1.2, 0.0, 1.2):
        sld = sld.fuse(xbox(g["outer"] + s * 0.29, g["outer"] + s * 0.6, y + dy - 0.25, y + dy + 0.25, g["zc"] - nh, g["zc"] + nh).common(tip))
    sld = sld.cut(xbox(g["body_out"], g["tip"] + s * 0.3, y - SLD_SLOT / 2, y + SLD_SLOT / 2, -20, 20))
    return sld.removeSplitter()


def psw_window(side):
    """壁の窓（横から削る）。窓の面で見た角を CNC_R で丸める。"""
    g = psw_geom(side)
    s = g["s"]
    win = xbox(g["wall_in"] - s * 0.5, g["outer"] + s * 1, PSW_Y - g["win_w"] / 2, PSW_Y + g["win_w"] / 2,
               g["zc"] - g["win_h"] / 2, g["zc"] + g["win_h"] / 2)
    return win.makeFillet(CNC_R, [e for e in win.Edges if e.BoundBox.YLength < 1e-6 and e.BoundBox.ZLength < 1e-6])


def psw_case_cuts(side):
    """ケース側: 壁の窓、スライダーの抜け止めが動く溝、スイッチ本体の逃げ。"""
    g = psw_geom(side)
    s = g["s"]
    win = psw_window(side)
    # ★スライダーの溝は枠の下にあるので、CNC では底から掘る（床を抜く。2026-10-06）。平面の角を CNC_R で
    #   丸めるので、抜け止めの角が当たらないよう、溝を南北へ CNC_R ずつ延ばす
    cw = g["keep_w"] + PSW_STROKE + 2 * SLD_CLR + 2 * CNC_R
    chan = rbox(g["body_out"], g["wall_in"], PSW_Y - cw / 2, PSW_Y + cw / 2, -1, PCB_BOT, CNC_R)
    body = rbox(g["bx"] - s * 0.3, g["body_out"] + s * 0.3, PSW_Y - PSW_BODY[1] / 2 - 0.3, PSW_Y + PSW_BODY[1] / 2 + 0.3,
                g["zb0"] - 0.3, PLATE_BOT, CNC_R)
    return [win, chan, body]


def cnc_interior(side):
    """中の空洞（床〜プレートの下面）の平面。内周の段の内側のうち、ケースの上面の穴の範囲だけにする。
    枠の下に空洞を残すと、上から刃物が届かない（2026-10-06）。内側の角は CNC_R で丸める。"""
    inner = offset_sharp(outline(side), -WALL_T - LEDGE_W)
    hole = single_face(top_outline(side).makeOffset2D(PLATE_CLEAR, join=0))
    f = single_face(inner.common(hole))
    return offset_round(offset_round(f, -CNC_R), CNC_R)


def bottom_body(side):
    """ケースの下の部分（外形の柱 z 0〜外周の面取りの下端）。底面の外周の縁を BOTTOM_FILLET で丸める。"""
    p = prism(outline(side), 0, CASE_TOP - CHAMFER_H)
    edges = [e for e in p.Edges if e.BoundBox.ZMax < 1e-6]
    return p.makeFillet(BOTTOM_FILLET, edges)


def case_body(side):
    ol = outline(side)
    body = bottom_body(side)                                   # 底は平ら（z = 0）
    body = body.fuse(chamfer_band(ol)).removeSplitter()

    cuts = [
        prism(single_face(top_outline(side).makeOffset2D(PLATE_CLEAR, join=0)), PLATE_BOT, 10),   # 上面の穴（プレートが入る）
        prism(cnc_interior(side), FLOOR_T, PLATE_BOT - FLOOR_T + 0.01),                     # 内部（上面の穴の範囲だけ）
        cover_notch(side),                                                                     # カバーの端の座・USB-C の口・XIAO の端の溝
        xiao_clearance(side),                                                                  # XIAO のまわり
    ]
    cuts += psw_case_cuts(side)                                          # 電源スイッチの窓・スライダーの溝・本体の逃げ
    if side == "R":
        cuts += ball_pocket_cuts()      # ボールの台がはまる床の穴・センサーの基板の溝の出口
    for c in cuts:
        body = body.cut(c)

    # スペーサー: 内周の段にかかる点（奥・手前）は段を丸く逃がす。
    # 床の下: 皿ネジ（下から）。ボールの台を通す点は、皿もみと座ぐりが台の中に来る
    for s in SCREWS[side]:
        seat, _ = bottom_seat(side, s)
        body = body.cut(Part.makeCylinder(SPACER_R + SPACER_CLEAR, PLATE_BOT - SPACER_BOT + 1, V(s[0], s[1], SPACER_BOT)))
        for c in bottom_screw_cuts(s, seat):
            body = body.cut(c)
    # リポバッテリの出し入れ口: 床の穴、底から掘ったふたの座（南へすべる分も）、爪の溝と入れ口、突起の穴
    for c in door_case_cuts(side):
        body = body.cut(c)
    for s in tag_screws(side):                                           # タグのネジのめねじ（M2 の下穴）
        body = body.cut(Part.makeCylinder(TAG_TAP_R, TAG_SCREW_LEN - TAG_T + 0.5, V(s[0], s[1], CASE_TOP - (TAG_SCREW_LEN - TAG_T) - 0.5)))
    return body.removeSplitter()


def door_opening(side):
    """床の穴（= リポバッテリ + LIPO_CLR）の範囲 (x0, y0, x1, y1)。"""
    xc = xiao_xc(side)
    return (xc - LIPO[0] / 2 - LIPO_CLR, LIPO_Y0 - LIPO_CLR, xc + LIPO[0] / 2 + LIPO_CLR, LIPO_Y0 + LIPO[1] + LIPO_CLR)


def door_lid_rect(side):
    """閉めた位置のふたの本体（爪を除く）の範囲 (x0, y0, x1, y1)。"""
    x0, y0, x1, y1 = door_opening(side)
    return (x0 - DOOR_SIDE, y0 - DOOR_END[0], x1 + DOOR_SIDE, y1 + DOOR_END[1])


def _rr(x0, y0, x1, y1, r):
    return rrect_face(((x0 + x1) / 2, (y0 + y1) / 2), x1 - x0, y1 - y0, r)


def door_tabs_y(side):
    """閉めた位置の爪の y の範囲の一覧。"""
    x0, y0, x1, y1 = door_lid_rect(side)
    L, _, _ = DOOR_TAB
    return [(y0 + f * (y1 - y0) - L / 2, y0 + f * (y1 - y0) + L / 2) for f in DOOR_TAB_AT]


def door_bump_pt(side):
    """閉めた位置の、舌の先の突起の中心。"""
    x0, y0, x1, y1 = door_lid_rect(side)
    yo = door_opening(side)[3]
    tl, tw, g = DOOR_TONGUE
    return ((x0 + x1) / 2 + tl / 2 - 1.0, (yo + y1) / 2)


def door_grooves(side):
    """座の東西の、爪が掛かる溝（座の天井の高さ、座の全長）。横向きのアンダーカットなので、CNC では
    座の中から T スロットカッターで削る。"""
    c = DOOR_CLR
    x0, y0, x1, y1 = door_lid_rect(side)
    L, w, z0 = DOOR_TAB
    out = []
    for sx, xe in ((-1, x0 - c), (1, x1 + c)):
        gx0, gx1 = sorted((xe, xe + sx * (w + c)))
        out.append(Part.makeBox(gx1 - gx0 + 0.01, (y1 + DOOR_SLIDE + c) - (y0 - c), DOOR_T - z0 + c,
                                V(gx0 - (0.01 if sx > 0 else 0), y0 - c, z0 - c)))
    return out


def cnc_side_cuts(side):
    """上・下からでなく、横から削ると決めた形（電源スイッチの窓）と、T スロットカッターで削る溝（ふたの爪の溝）。"""
    return [psw_window(side)] + door_grooves(side)


def door_case_cuts(side):
    """ケース側: 床の穴、ふたの座（南へ DOOR_SLIDE のびる）、東西の爪の溝（座の天井の高さ、座の全長）、
    爪の入れ口（開けた位置の爪の下の縁を抜く）、突起の穴。"""
    c = DOOR_CLR
    x0, y0, x1, y1 = door_lid_rect(side)
    L, w, z0 = DOOR_TAB
    # ★リポバッテリの空洞は枠の下にあるので、底から床の穴と同じ形で掘る（2026-10-06）。角は CNC_R
    #   （バッテリの角とは 0.3 のすき間で R1.02 まで当たらない）
    lx0, ly0, lx1, ly1 = door_opening(side)
    out = [prism(_rr(lx0, ly0, lx1, ly1, CNC_R), -1, DOOR_T + LIPO[2] + LIPO_CLR + 1),
           prism(_rr(x0 - c, y0 - c, x1 + c, y1 + DOOR_SLIDE + c, DOOR_R + c), -1, DOOR_T + 1)]
    out += door_grooves(side)
    for sx, xe in ((-1, x0 - c), (1, x1 + c)):
        gx0, gx1 = sorted((xe - sx * CNC_R_SMALL, xe + sx * (w + c)))       # 座の側へ延ばし、角の R を座の中に逃がす
        for ta, tb in door_tabs_y(side):
            out.append(rbox(gx0, gx1, ta + DOOR_SLIDE - c, tb + DOOR_SLIDE + c, -1, z0, CNC_R_SMALL))
    bx, by = door_bump_pt(side)
    out.append(Part.makeCylinder(DOOR_BUMP_HOLE_R, FLOOR_T + 1, V(bx, by, DOOR_T - 0.5)))
    return out


def door_without_bump(side):
    """突起を除いたふた（すべらせる途中は舌がたわんで突起が逃げるので、動きの確認はこれで見る）。"""
    bx, by = door_bump_pt(side)
    return battery_door(side).cut(Part.makeCylinder(DOOR_BUMP[0] + 0.5, 3, V(bx, by, DOOR_T - 0.05)))


def battery_door(side):
    """リポバッテリのふた（別部品、閉めた位置）。本体の東西の縁に爪 3 つずつ、南の端にたわむ舌と突起、裏に滑り止め。"""
    x0, y0, x1, y1 = door_lid_rect(side)
    d = prism(_rr(x0, y0, x1, y1, DOOR_R), 0, DOOR_T)
    L, w, z0 = DOOR_TAB
    for ta, tb in door_tabs_y(side):                    # 爪（溝の下の縁から 0.1 浮かせ、溝の奥から 0.2 離す）
        d = d.fuse(Part.makeBox(w - DOOR_CLR + 0.01, tb - ta, DOOR_T - z0 - 0.1, V(x1 - 0.01, ta, z0 + 0.1)))
        d = d.fuse(Part.makeBox(w - DOOR_CLR + 0.01, tb - ta, DOOR_T - z0 - 0.1, V(x0 - (w - DOOR_CLR), ta, z0 + 0.1)))
    # 抜け止めの舌: 西の端でつながり、ほかの三方を切れ目で切り離す。先に突起
    tl, tw, g = DOOR_TONGUE
    bx, by = door_bump_pt(side)
    tx0, tx1 = bx + 1.0 - tl, bx + 1.0
    slot = Part.makeBox(tl + g, tw + 2 * g, DOOR_T + 2, V(tx0, by - tw / 2 - g, -1)).cut(
        Part.makeBox(tl, tw, DOOR_T + 4, V(tx0 - 0.01, by - tw / 2, -2)))
    d = d.cut(slot)
    br, bh = DOOR_BUMP
    d = d.fuse(Part.makeCone(br, br * 0.4, bh, V(bx, by, DOOR_T - 0.01)))
    # 裏の滑り止め（舌の北、x の全幅の 6 割）
    n, gw, gd, pitch = DOOR_GRIP
    yo = door_opening(side)[3]
    gx = (x1 - x0) * 0.6
    for i in range(n):
        yy = yo - 2.0 - i * pitch
        d = d.cut(Part.makeBox(gx, gw, gd + 1, V((x0 + x1) / 2 - gx / 2, yy - gw / 2, -1)))
    return d


# =============================================================================
# トッププレート（アセンブリ座標: 下面 z = PLATE_BOT）
# =============================================================================
def xiao_window_face(side):
    """プレートの XIAO の切り欠き（カバーの内側と同じ範囲）。北はプレートの縁まで開く。"""
    x0, y0, x1, y1 = _xiao_rect_local()
    c = COVER_CLR
    wx0, wx1 = X_W - 1, x1 + c
    return xiao_place_shape(rrect_face(((wx0 + wx1) / 2, (y0 + y1) / 2), wx1 - wx0, (y1 - y0) + 2 * c, 0.5), side)


_top_cache = {}


def top_outline(side, ball=True):
    """トッププレートの外形。キーキャップ ＋ TOP_CLR の四角・マイコンカバー・（右は）ボールのまわりの和を
    TOP_CLOSE で閉じ（くぼみを埋め）、ケースの壁の内側で切る。ball=False は PCB 用（ボールのまわりを含めない）。"""
    key = (side, ball)
    if key in _top_cache:
        return _top_cache[key]
    # 各形を TOP_CLOSE だけ太らせて足し、全体を TOP_CLOSE だけ細らせる（くぼみとすき間を埋める）。
    # ★キーの四角は角を丸めずに足し、最後に出隅だけを TOP_R で丸める（2026-10-06）。角を丸めた四角を
    #   足すと、となりのキーとの間で角の丸みがつながらず、外形がキーの間で 0.13 くぼんでいた
    g = TOP_CLOSE
    w = CAP_SIZE + 2 * (TOP_CLR + g)
    faces = [rect_face(k[0] - w / 2, k[1] - w / 2, w, w) for k in KEYS[side] + THUMBS[side]]
    x0, y0, x1, y1 = cover_rect(side)
    faces.append(rrect_face(((x0 + x1) / 2, (y0 + y1) / 2), x1 - x0 + 2 * g, y1 - y0 + 2 * g, COVER_R + g))
    if side == "R" and ball:
        faces.append(circle_face(BULGE_C[0], BULGE_C[1], BALL_PLATE_R + g))
    f = single_face(union_faces(faces).makeOffset2D(-g, join=0))
    f = single_face(f.common(offset_sharp(outline(side), -(WALL_T + PLATE_CLEAR))))
    # ★北の縁はキーキャップ ＋ TOP_CLR の線でまっすぐ切る（2026-10-06）。カバーの範囲だけ壁の内側まで出ると、
    #   キーの列との間が TOP_CLOSE の丸みで斜めにつながって見えた。カバーの北の端はケースの浅い切り欠き
    #   （`cover_notch()`、底 PLATE_TOP）に座るので、プレートは要らない
    y_n = min(k[1] for k in KEYS[side]) - CAP_SIZE / 2 - TOP_CLR
    f = single_face(f.common(rect_face(-500, y_n, 1000, 1000)))
    # 出隅を TOP_R で丸める（壁の内側で切った角も。ケースの上面の穴の角は TOP_R + PLATE_CLEAR ≧ CNC_R になる）
    f = offset_round(offset_round(f, -TOP_R), TOP_R)
    _top_cache[key] = f
    return f


def plate(side):
    """トッププレート。外周はキーキャップの外周（`top_outline()`）。ケースの上面の穴の底に入る。"""
    p = prism(top_outline(side), PLATE_BOT, PLATE_T)
    p = p.cut(prism(xiao_window_face(side), PLATE_BOT - 1, 10))     # XIAO の切り欠き
    for m in magnet_points(side):                                     # カバーの磁石の相手
        p = p.cut(Part.makeCylinder(MAG_POCKET_R, MAG_POCKET_H + 1, V(m[0], m[1], PLATE_TOP - MAG_POCKET_H)))
    for k in KEYS[side] + THUMBS[side]:
        p = p.cut(Part.makeBox(SW_HOLE, SW_HOLE, 10, V(k[0] - SW_HOLE / 2, k[1] - SW_HOLE / 2, PLATE_BOT - 1)))
    for s in SCREWS[side]:                                            # 皿ネジ（頭はプレートの上面と面一）
        p = p.cut(Part.makeCylinder(M2_HOLE_R, 10, V(s[0], s[1], PLATE_BOT - 1)))
        p = p.cut(Part.makeCone(M2_HOLE_R, CSK_R, CSK_H + 0.01, V(s[0], s[1], PLATE_TOP - CSK_H)))
    led = LED[side]
    p = p.cut(Part.makeCylinder(0.9, 10, V(led[0], led[1], PLATE_BOT - 1)))
    if side == "R":
        p = p.cut(Part.makeCylinder(COLLAR_R[1] + PLATE_HOLE_CLR, 10, V(BULGE_C[0], BULGE_C[1], PLATE_BOT - 1)))   # 台のねじの筒が通る穴
    return p.removeSplitter()


# =============================================================================
# ボールカップ（原点 = ボール中心の真下。つばをプレートに載せる）
# =============================================================================
# =============================================================================
# 簡略部品
# =============================================================================
def pcb(side):
    """PCB。ケースの上面の穴から入れるので、外形はトッププレート（ボールのまわりを除く）の穴から PCB_IN 内側。"""
    f = single_face(top_outline(side, ball=False).makeOffset2D(PLATE_CLEAR - PCB_IN, join=0))
    f = single_face(f.common(offset_sharp(outline(side), -(WALL_T + LEDGE_W + 0.3))))
    s = prism(f, PCB_BOT, PCB_T)
    # XIAO の下は壁際まで張り出す（USB-C 側のパッドの下にも PCB を置く）
    x0, y0, x1, y1 = _xiao_rect_local()
    tx0, tx1 = X_W + WALL_T + 0.3, x1
    s = s.fuse(xiao_place_shape(Part.makeBox(tx1 - tx0, y1 - y0, PCB_T, V(tx0, y0, PCB_BOT)), side)).removeSplitter()
    # スペーサーの逃げ（縁にかかる点は切り欠きになる）
    for c in SCREWS[side]:
        s = s.cut(Part.makeCylinder(SPACER_R + SPACER_CLEAR, 5, V(c[0], c[1], PCB_BOT - 1)))
    s = s.cut(lipo_box(side, LIPO_CLR, 10))                         # リポバッテリの切り欠き
    return s


def spacers(side):
    return Part.makeCompound([Part.makeCylinder(SPACER_R, SPACER_H, V(s[0], s[1], SPACER_BOT)) for s in SCREWS[side]])


def screws_top(side):
    """上のネジ。プレートの皿ネジ M2×4（頭はプレートの上面と面一、プレート 2.0 ＋ スペーサーへ 2.0）と、
    タグの低頭のタッピングネジ（頭はタグの上面、ケースの上面へ。軸は谷径で描く）。"""
    out = []
    for s in SCREWS[side]:
        h = Part.makeCone(1.0, CSK_R - 0.05, CSK_H, V(s[0], s[1], PLATE_TOP - CSK_H))
        out.append(h.fuse(Part.makeCylinder(1.0, 4.0, V(s[0], s[1], PLATE_TOP - 4.0))))
    for s in tag_screws(side):
        z = CASE_TOP + TAG_T
        h = Part.makeCylinder(LOWHEAD_R, LOWHEAD_H, V(s[0], s[1], z))
        out.append(h.fuse(Part.makeCylinder(TAG_TAP_R, TAG_SCREW_LEN, V(s[0], s[1], z - TAG_SCREW_LEN))))
    return Part.makeCompound(out)

def screws_bottom(side, with_base=True):
    """皿ネジ（下から）。頭は座の皿もみに沈む。ふつうは M2×4（床 2.0 ＋ スペーサーへ 2.0）、
    ボールの台の 2 本は M2×3 の皿のタッピングネジ（床 1.7 を通して台へ 1.3。軸は谷径で描く）。"""
    out = []
    for s in SCREWS[side]:
        seat, length = bottom_seat(side, s)
        h = Part.makeCone(CSK_R, 1.0, CSK_R - 1.0, V(s[0], s[1], seat))
        out.append(h.fuse(Part.makeCylinder(1.0, length, V(s[0], s[1], seat))))
    if side == "R" and with_base:
        for p in ball_base_screws():         # ボールの台の皿のタッピングネジ（ケースの底から）
            h = Part.makeCone(CSK_R, 1.0, CSK_R - 1.0, V(p[0], p[1], 0.0))
            out.append(h.fuse(Part.makeCylinder(FOOT_PILOT_R, BASE_SCREW_LEN, V(p[0], p[1], 0.0))))
    return Part.makeCompound(out)


def lipo_box(side, clr=0.0, h=None):
    """リポバッテリの範囲（XIAO の南の内側の列。x の中心は XIAO にそろえる）。底のふたの上に寝かせる。
    h を渡すと、底（z −1）から h の高さの切り抜き用の箱を返す。"""
    w, l, t = LIPO
    xc = xiao_xc(side)
    hh = t if h is None else h
    z0 = DOOR_T if h is None else -1
    return Part.makeBox(w + 2 * clr, l + 2 * clr, hh, V(xc - w / 2 - clr, LIPO_Y0 - clr, z0))


def xiao(side):
    """XIAO nRF52840（公開モデル）。USB-C を北へ向け、下面を XIAO_BOT に置く。"""
    ref = ref_shape(REF_XIAO)
    if ref is None:
        x0, y0, x1, y1 = _xiao_rect_local()
        local = Part.makeBox(x1 - x0, y1 - y0, XIAO_THK, V(x0, y0, XIAO_BOT)).fuse(_usb_local())
    else:
        local = xiao_place_local(ref.copy())
    return xiao_place_shape(local, side)


_XIAO_BB = []


def xiao_place_local(shp):
    """XIAO のモデル座標の形（または点の Vertex）を、局所の向き（USB-C が西）に置く。

    モデルは X = 長さ（USB-C が +X）、Y = 厚さ（上）、Z = 幅。上から見た向き（y 上向き）で組んでから
    y を反転して、この y 下向きの座標に移す（to_view で元に戻る）。
    """
    if not _XIAO_BB:
        r = ref_shape(REF_XIAO).copy()
        r.rotate(V(0, 0, 0), V(1, 0, 0), 90)
        r.rotate(V(0, 0, 0), V(0, 0, 1), 180)
        _XIAO_BB.append(r.optimalBoundingBox())
    b = _XIAO_BB[0]
    shp.rotate(V(0, 0, 0), V(1, 0, 0), 90)         # 厚さ（Y）→ 上（Z）
    shp.rotate(V(0, 0, 0), V(0, 0, 1), 180)        # USB-C を西へ
    dx = (X_W + usb_recess("L")) - b.XMin
    shp.translate(V(dx, -(b.YMin + b.YLength / 2), XIAO_BOT - b.ZMin))
    return shp.mirror(V(0, 0, 0), V(0, 1, 0))


def xiao_point_local(p):
    """XIAO のモデル座標の点 → 局所の向きの (x, y, z)。"""
    v = xiao_place_local(Part.Vertex(V(*p))).Point
    return (v.x, v.y, v.z)


def cover(side):
    """取り外せるマイコンカバー（アセンブリ座標）。局所の向き（USB-C が西）で作り、北の端へ回して置く。

    天井 COVER_TOP_T、壁 COVER_T（南だけ COVER_T_IN で磁石を埋める）。外周の上の縁は COVER_FILLET で
    丸め、縁から COVER_RIM 内側の天面をへこませる。下面はすべて PLATE_TOP にそろえ、北の端は壁の
    浅い切り欠きの底（壁の外側の縁の上）に、そこから南はプレートの上に座る（2026-10-06）。北の端の壁に
    USB-C の穴（下が開き、壁の縁の口と合わせて USB-C を囲む）。リセットボタンの真上に
    押しボタン、LED の真上に穴。磁石はカバーの下面から埋める。
    """
    cx0, cy0, cx1, cy1 = _cover_rect_local()
    x0, y0, x1, y1 = _xiao_rect_local()
    c = COVER_CLR
    outer = rrect_face(((cx0 + cx1) / 2, (cy0 + cy1) / 2), cx1 - cx0, cy1 - cy0, COVER_R)
    body = prism(outer, PLATE_TOP, COVER_TOP - PLATE_TOP)
    top_edges = [e for e in body.Edges if abs(e.BoundBox.ZMin - COVER_TOP) < 1e-6 and abs(e.BoundBox.ZMax - COVER_TOP) < 1e-6]
    body = body.makeFillet(COVER_FILLET, top_edges)
    # 天面のへこみ
    recess = rrect_face(((cx0 + cx1) / 2, (cy0 + cy1) / 2), cx1 - cx0 - 2 * COVER_RIM, cy1 - cy0 - 2 * COVER_RIM,
                        max(COVER_R - COVER_RIM, 0.8))
    body = body.cut(prism(recess, COVER_TOP - COVER_RECESS, 5))
    # 中（XIAO ＋ すき間）。USB-C の側の端の壁は COVER_T 残す
    ix0, ix1 = X_W + COVER_T, x1 + c
    inner = rrect_face(((ix0 + ix1) / 2, (y0 + y1) / 2), ix1 - ix0, (y1 - y0) + 2 * c, 0.5)
    ceil = COVER_TOP - COVER_TOP_T
    body = body.cut(prism(inner, PLATE_TOP - 1, ceil - PLATE_TOP + 1))
    # USB-C の穴（ケースの縁の口と同じ長円。下はケースの口につながる）
    yc = (y0 + y1) / 2
    body = body.cut(usb_stadium(X_W - 1, COVER_T + 2, yc, USB_PORT_CLR))
    # 押しボタン: C 字の切れ込み（カバーの中心側を蝶番に残す）＋ 丸い頭 ＋ 裏の突起
    bx, by, bz = xiao_point_local(XIAO_RST)
    ccx, ccy = (cx0 + cx1) / 2, (cy0 + cy1) / 2
    toward = math.degrees(math.atan2(ccy - by, ccx - bx))           # 蝶番の向き（カバーの中心）
    ring = Part.makeCylinder(BTN_SLOT[1], 10, V(bx, by, ceil - 1)).cut(Part.makeCylinder(BTN_SLOT[0], 10, V(bx, by, ceil - 2)))
    keep = Part.makeCylinder(BTN_SLOT[1] + 1, 12, V(bx, by, ceil - 2), V(0, 0, 1), BTN_HINGE)
    keep.rotate(V(bx, by, 0), V(0, 0, 1), toward - BTN_HINGE / 2)
    body = body.cut(ring.cut(keep))
    head = Part.makeSphere(BTN_R, V(bx, by, COVER_TOP - COVER_RECESS - BTN_R + 0.9)).common(
        Part.makeCylinder(BTN_R, 10, V(bx, by, COVER_TOP - COVER_RECESS - 0.2)))
    body = body.fuse(head)
    body = body.fuse(Part.makeCylinder(BTN_POST_R, ceil - (bz + BTN_GAP) + 0.01, V(bx, by, bz + BTN_GAP)))
    # シールドの窓（XIAO の四角いモジュールを上から見せる）
    p0, p1 = xiao_point_local(XIAO_SHIELD[0]), xiao_point_local(XIAO_SHIELD[1])
    wx0, wx1 = sorted((p0[0], p1[0]))
    wy0, wy1 = sorted((p0[1], p1[1]))
    m = SHIELD_WIN_MARGIN
    win = rrect_face(((wx0 + wx1) / 2, (wy0 + wy1) / 2), wx1 - wx0 + 2 * m, wy1 - wy0 + 2 * m, 1.0)
    body = body.cut(prism(win, ceil - 1, 10))
    # LED の穴（★まわりのドーナツ形のリングはやめた。2026-10-06）
    lx, ly, lz = xiao_point_local(XIAO_LED)
    body = body.cut(Part.makeCylinder(LED_HOLE_R, 10, V(lx, ly, ceil - 1)))
    # 磁石の穴（下から）
    mx = x1 + c + COVER_T_IN / 2
    for my in (y0 + 1.5, y1 - 1.5):
        body = body.cut(Part.makeCylinder(MAG_POCKET_R, MAG_POCKET_H, V(mx, my, PLATE_TOP)))
    return xiao_place_shape(body.removeSplitter(), side)


def magnets(side):
    """磁石（プレート側とカバー側）。"""
    out = []
    for m in magnet_points(side):
        out.append(Part.makeCylinder(MAG_D / 2, MAG_T, V(m[0], m[1], PLATE_TOP - MAG_T)))
        out.append(Part.makeCylinder(MAG_D / 2, MAG_T, V(m[0], m[1], PLATE_TOP)))
    return Part.makeCompound(out)


def sockets(side):
    """Choc ホットスワップソケットの外形（PCB の裏）。"""
    x0, x1, y0, y1 = SOCKET_BOX
    return Part.makeCompound([
        Part.makeBox(x1 - x0, y1 - y0, SOCKET_H, V(k[0] + x0, k[1] + y0, PCB_BOT - SOCKET_H))
        for k in KEYS[side] + THUMBS[side]])


_ref_cache = {}


def ref_shape(path):
    """参考モデルを 1 回だけ読む。無ければ None（包絡で代える）。"""
    if path not in _ref_cache:
        shp = None
        if os.path.exists(path):
            shp = Part.Shape()
            shp.read(path)
        _ref_cache[path] = shp
    return _ref_cache[path]


def switch_envelope(k):
    """外形図どおりの Choc V2 の包絡（3 段の角柱）。干渉チェックはこれで行う。"""
    def sq(w, z0, z1):
        return Part.makeBox(w, w, z1 - z0, V(k[0] - w / 2, k[1] - w / 2, PCB_TOP + z0))
    return sq(SW_LOW_W, 0, SW_LOW_H).fuse(sq(SW_BODY_W, SW_LOW_H, SW_BODY_TOP)).fuse(
        sq(SW_STEM_W, SW_BODY_TOP, SW_STEM_TOP)).removeSplitter()


def ref_switch():
    """Choc V2 の公開モデル。座面 z=0・ステム上端 z=8.60。

    ★モデルは上から見た向き（y 上向き）なので、y 下向きで組むここでは y を反転して
      おく。最後の to_view で元の向きに戻る。
    """
    shp = ref_shape(REF_SWITCH)
    if shp is None:
        return None
    if "switch" not in _ref_cache:
        b = shp.optimalBoundingBox()
        assert abs(b.XLength - SW_BODY_W) < 0.02 and abs(b.YLength - SW_BODY_W) < 0.02, \
            "Choc V2 モデルの外形が %.2f 角でない: %.3f x %.3f" % (SW_BODY_W, b.XLength, b.YLength)
        assert abs(b.ZMax - SW_STEM_TOP) < 0.02, \
            "Choc V2 モデルのステム上端が %.2f でない: %.3f" % (SW_STEM_TOP, b.ZMax)
        _ref_cache["switch"] = shp.mirror(V(0, 0, 0), V(0, 1, 0))
    return _ref_cache["switch"]


def clip_boxes(side):
    """Choc V2 の爪の範囲（干渉チェックで除く）。"""
    out = []
    for k in KEYS[side] + THUMBS[side]:
        for x0 in (k[0] + SW_HOLE / 2 - 0.01, k[0] - SW_HOLE / 2 - CLIP_OUT + 0.01):
            out.append(Part.makeBox(CLIP_OUT, 2 * CLIP_HALF_W, CLIP_TOP, V(x0, k[1] - CLIP_HALF_W, PCB_TOP)))
    return Part.makeCompound(out)


def switch_bodies(side):
    """スイッチの包絡（干渉チェック用）。"""
    return Part.makeCompound([switch_envelope(k) for k in KEYS[side] + THUMBS[side]])


def switch_housings(side):
    """ステムを除いた包絡（キーキャップとの干渉チェック用。ステムはキャップに入る）。"""
    return Part.makeCompound([
        Part.makeBox(SW_BODY_W, SW_BODY_W, SW_BODY_TOP, V(k[0] - SW_BODY_W / 2, k[1] - SW_BODY_W / 2, PCB_TOP))
        for k in KEYS[side] + THUMBS[side]])


def switches(side):
    """アセンブリに置くスイッチ。公開モデルが無ければ包絡で代える。"""
    ref = ref_switch()
    if ref is None:
        return switch_bodies(side)
    parts = []
    for k in KEYS[side] + THUMBS[side]:
        s = ref.copy()
        s.translate(V(k[0], k[1], PCB_TOP))
        parts.append(s)
    return Part.makeCompound(parts)


def keycap(c):
    """キーキャップ（仮の形）。★JezailFunder の LAK に寄せた（2026-10-06。寸法は公表されていないので、写真と
    図から写した）: 側面は垂直、上は斜めの肩でひとまわり内へ入り、上面は前後方向にくぼんだ円柱面。段ごとの傾きは無い。"""
    lo = prism(rrect_face(c, CAP_SIZE, CAP_SIZE, CAP_R), CAP_Z, CAP_WALL_H)
    w1 = rrect_face(c, CAP_SIZE, CAP_SIZE, CAP_R).OuterWire
    t = CAP_SIZE - 2 * CAP_TOP_INSET
    w2 = rrect_face(c, t, t, CAP_TOP_R).OuterWire
    w1.translate(V(0, 0, CAP_Z + CAP_WALL_H))
    w2.translate(V(0, 0, CAP_Z + CAP_H))
    cap = lo.fuse(Part.makeLoft([w1, w2], True)).removeSplitter()
    # 上面のくぼみ: x 方向の軸の円柱で、上面の前後の縁で深さ 0、中央で CAP_DISH
    r = ((t / 2) ** 2 + CAP_DISH ** 2) / (2 * CAP_DISH)
    dish = Part.makeCylinder(r, CAP_SIZE + 2, V(c[0] - CAP_SIZE / 2 - 1, c[1], CAP_Z + CAP_H - CAP_DISH + r), V(1, 0, 0))
    return cap.cut(dish)


def battery_block(side):
    """リポバッテリ（干渉チェック用の箱）。"""
    return lipo_box(side)


def usb_stadium(x0, length, yc, clr):
    """USB-C の断面（両端が半円の長円）を clr だけ広げ、x 方向に length 押し出した形（局所の向き）。"""
    w, h = USB_W + 2 * clr, USB_H + 2 * clr
    b = Part.makeBox(length, w, h, V(x0, yc - w / 2, USB_Z0 - clr))
    return b.makeFillet(h / 2 - 0.01, [e for e in b.Edges if e.BoundBox.YLength < 1e-6 and e.BoundBox.ZLength < 1e-6])


def _usb_local():
    # ★USB-C のレセプタクルは両端が半円なので、箱でなく長円にする（2026-10-06）
    return usb_stadium(X_W + usb_recess("L"), USB_LEN, 0.0, 0.0)


def usb(side):
    """XIAO の USB-C（干渉チェック用の長円）。"""
    return xiao_place_shape(_usb_local(), side)


def sensor():
    """PAW3222 モジュール（ボールの中心の真下を原点に置いた形。仮置き）。基板を台の溝の底に置き、南の端を溝の
    南の端から 0.2 離す。チップとレンズは基板の上で、ボールの真下。"""
    w, l, t = SENSOR_PCB
    y1 = SENSOR_CH_S - 0.2
    s = Part.makeBox(w, l, t, V(-w / 2, y1 - l, SENSOR_CH_FLOOR))
    return s.fuse(Part.makeCylinder(SENSOR_LENS[0], SENSOR_LENS[1], V(0, 0, SENSOR_CH_FLOOR + t)))


# =============================================================================
# 書き出し
# =============================================================================
def to_view(shape):
    """y 下向きで組んだ形を、上から見た向きに直す。"""
    return shape.mirror(V(0, 0, 0), V(0, 1, 0))


def moved(shape, dx=0.0, dy=0.0, dz=0.0):
    s = shape.copy()
    s.translate(V(dx, dy, dz))
    return s


# 参考モデルは形が細かく、0.02 で割るとスイッチだけで片手 200MB になる。見るだけなので粗く割る
# （スイッチ 1 個あたり約 13000 面 → 片手 15MB 前後）
COARSE_STL = ("switches", "xiao")


def write_stl(shape, path, coarse=False):
    ld, ad = (0.5, 1.0) if coarse else (0.02, 0.2)
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=ld, AngularDeflection=ad, Relative=False)
    mesh.write(path)


def half_parts(side):
    """(ラベル, 形) の一覧。アセンブリ座標、y 下向き。"""
    parts = [
        ("case", case_body(side)),
        ("pcb", pcb(side)),
        ("switches", switches(side)),
        ("plate", plate(side)),
        ("keycaps", Part.makeCompound([keycap(k) for k in KEYS[side]])),
        ("keycaps-thumb", Part.makeCompound([keycap(k) for k in THUMBS[side]])),
        ("lipo", lipo_box(side)),
        ("usb-c", usb(side)),
        ("xiao", xiao(side)),
        ("power-switch", power_switch(side)),
        ("slider", slider(side)),
        ("cover", cover(side)),
        ("magnets", magnets(side)),
        ("sockets", sockets(side)),
        ("spacers", spacers(side)),
        ("screws-top", screws_top(side)),
        ("screws-bottom", screws_bottom(side)),
        ("tag", tag_plate(side)),
        ("battery-door", battery_door(side)),
    ]
    if side == "R":
        cx, cy = BULGE_C
        parts += [
            ("ball-base", ball_base()),
            ("ball-ring", moved(ball_ring(), cx, cy)),
            ("ball", Part.makeSphere(BALL_R, V(cx, cy, BALL_CZ))),
            ("bearings", moved(bearings(), cx, cy)),
            ("sensor", moved(sensor(), cx, cy)),
        ]
    return parts


def insert_parts(side, d):
    """ケースの上面の穴から入れる部品をまとめた形。"""
    names = ["pcb", "sockets", "power-switch", "xiao", "usb-c", "plate", "switches", "spacers"]
    if side == "R":
        names.append("ball-base")
    return Part.makeCompound([d[n] for n in names])


def caps(d):
    return Part.makeCompound([d["keycaps"], d["keycaps-thumb"]])


def _slice_face(shape, z):
    """形を高さ z で切った断面（z = 0 の面に移す）。"""
    wires = shape.slice(V(0, 0, 1), z)
    if not wires:
        return None
    f = Part.makeFace(wires, "Part::FaceMakerBullseye")
    if f.isNull():
        return None
    f.translate(V(0, 0, -z))
    return f


def cnc_undercuts(side, case, dz=CNC_DZ):
    """ケースを CNC で上（z+）と下（z−）から削れるか調べる。高さ dz ごとの断面で、すき間（ケースの外も含む）が
    真上か真下へ抜けているかを見る。抜けていない部分（アンダーカット）のうち、横から削る・T スロットカッターで
    削ると決めたもの（`cnc_side_cuts()`）を除いた残りを (z, 面積, 範囲) の一覧で返す。"""
    bb = case.BoundBox
    box = rect_face(bb.XMin - 2, bb.YMin - 2, bb.XLength + 4, bb.YLength + 4)
    zs = [CNC_Z0 + dz * i for i in range(int((bb.ZMax - CNC_Z0) / dz) + 1)]
    voids = []
    for z in zs:
        m = _slice_face(case, z)
        voids.append(box.cut(m) if m is not None else box.copy())
    top = [None] * len(zs)
    for i in reversed(range(len(zs))):
        top[i] = voids[i] if i == len(zs) - 1 else voids[i].common(top[i + 1])
    bot = [None] * len(zs)
    for i in range(len(zs)):
        bot[i] = voids[i] if i == 0 else voids[i].common(bot[i - 1])
    side_cuts = cnc_side_cuts(side)
    out = []
    for i, z in enumerate(zs):
        tools = [top[i], bot[i]] + [_slice_face(c, z) for c in side_cuts]
        tools = [t for t in tools if t is not None and not t.isNull() and t.Faces]
        u = voids[i].cut(tools) if tools else voids[i]
        if u.Faces and u.Area >= CNC_MIN_AREA:
            b = u.BoundBox
            out.append((z, u.Area, (b.XMin, b.YMin, b.XMax, b.YMax)))
    return out


def check_interference(side, parts):
    d = dict(parts)
    pairs = [
        ("switch, usb-c", switch_bodies(side), d["usb-c"]),
        ("switch, battery", switch_bodies(side), battery_block(side)),
        ("switch, case", switch_bodies(side), d["case"]),
        ("battery, case", battery_block(side), d["case"]),
        ("battery, pcb", battery_block(side), d["pcb"]),
        ("battery, plate", battery_block(side), d["plate"]),
        ("keycaps, battery", Part.makeCompound([d["keycaps"], d["keycaps-thumb"]]), battery_block(side)),
        ("keycaps, switch", Part.makeCompound([d["keycaps"], d["keycaps-thumb"]]), switch_housings(side)),
        ("stem > keycap top", switch_bodies(side), Part.makeBox(1000, 1000, 100, V(-500, -500, CAP_Z + CAP_H))),
        ("switch-model, plate (爪を除く)", d["switches"], d["plate"].cut(clip_boxes(side))),
        ("switch-model, case", d["switches"], d["case"]),
        ("usb-c, case", d["usb-c"], d["case"]),
        ("spacer, switch", d["spacers"], switch_bodies(side)),
        ("spacer, usb-c", d["spacers"], d["usb-c"]),
        ("xiao, case", d["xiao"], d["case"]),
        ("xiao, pcb", d["xiao"], d["pcb"]),
        ("xiao, sockets", d["xiao"], d["sockets"]),
        ("xiao, switch-model", d["xiao"], d["switches"]),
        ("xiao, spacer", d["xiao"], d["spacers"]),
        ("xiao, battery", d["xiao"], battery_block(side)),
        ("xiao, screw-bottom", d["xiao"], d["screws-bottom"]),
        ("xiao, plate", d["xiao"], d["plate"]),
        ("cover, case", d["cover"], d["case"]),
        ("cover, plate", d["cover"], d["plate"]),
        ("cover, xiao", d["cover"], d["xiao"]),
        ("cover, usb-c", d["cover"], d["usb-c"]),
        ("cover, keycaps(pressed)", d["cover"], moved(caps(d), dz=-KEY_TRAVEL)),
        ("cover, switch", d["cover"], switch_bodies(side)),
        ("cover, screw-top", d["cover"], d["screws-top"]),
        ("magnets, case", d["magnets"], d["case"]),
        ("magnets, plate", d["magnets"], d["plate"]),
        ("magnets, cover", d["magnets"], d["cover"]),
        ("power-switch, case", d["power-switch"], d["case"]),
        ("power-switch, pcb", d["power-switch"], d["pcb"]),
        ("power-switch, battery", d["power-switch"], battery_block(side)),
        ("slider, case", d["slider"], d["case"]),
        ("slider(+1), case", slider(side, +PSW_STROKE / 2), d["case"]),
        ("slider(-1), case", slider(side, -PSW_STROKE / 2), d["case"]),
        ("slider(+1), switch(+1)", slider(side, +PSW_STROKE / 2), power_switch(side, +PSW_STROKE / 2)),
        ("slider(-1), switch(-1)", slider(side, -PSW_STROKE / 2), power_switch(side, -PSW_STROKE / 2)),
        ("slider, pcb", d["slider"], d["pcb"]),
        ("slider, plate", d["slider"], d["plate"]),
        ("slider, power-switch", d["slider"], d["power-switch"]),
        ("screw-top, case", d["screws-top"], d["case"]),
        ("below bottom (all)", Part.makeCompound([d["case"], d["lipo"], d["xiao"], d["spacers"], d["battery-door"],
                                                    screws_bottom(side, False)]),
         tent_halfspace(side)),
        ("lipo, case", d["lipo"], d["case"]),
        ("battery-door, case", d["battery-door"], d["case"]),
        ("battery-door, lipo", d["battery-door"], d["lipo"]),
        ("battery-door, screw-bottom", d["battery-door"], d["screws-bottom"]),
        # ふたの動き: 南へ DOOR_SLIDE すべらせた位置（突起を除く。舌がたわむ）と、そこから下へ抜く途中
        ("battery-door(open), case", moved(door_without_bump(side), dy=DOOR_SLIDE), d["case"]),
        ("battery-door(open, drop 1.0), case", moved(door_without_bump(side), dy=DOOR_SLIDE, dz=-1.0), d["case"]),
        ("lipo, pcb", d["lipo"], d["pcb"]),
        ("lipo, plate", d["lipo"], d["plate"]),
        ("lipo, power-switch", d["lipo"], d["power-switch"]),
        ("lipo, switch", d["lipo"], d["switches"]),
        ("lipo, sockets", d["lipo"], d["sockets"]),
        ("lipo, slider", d["lipo"], d["slider"]),
        ("tag, plate", d["tag"], d["plate"]),
        ("case, switch", d["case"], switch_bodies(side)),
        ("case, keycaps", d["case"], caps(d)),
        ("case, keycaps(pressed)", d["case"], moved(caps(d), dz=-KEY_TRAVEL)),
        ("case, pcb", d["case"], d["pcb"]),
        # 組み立て: PCB（スイッチ・ソケット・XIAO・電源スイッチごと）・プレート・スペーサーを、ケースの上面の穴から
        # 真上へ抜けること（4.0 と 8.0 持ち上げた位置でケースに当たらない）。右はボールの台も
        ("insert from top (4.0), case", moved(insert_parts(side, d), dz=4.0), d["case"]),
        ("insert from top (8.0), case", moved(insert_parts(side, d), dz=8.0), d["case"]),
        ("tag, case", d["tag"], d["case"]),
        ("tag, screw-top", d["tag"], d["screws-top"]),
        ("tag, keycaps(pressed)", d["tag"], moved(caps(d), dz=-KEY_TRAVEL)),
        ("tag, switch", d["tag"], switch_bodies(side)),
        ("tag, cover", d["tag"], d["cover"]),
        ("xiao, keycaps(pressed)", d["xiao"], moved(caps(d), dz=-KEY_TRAVEL)),
        ("sockets, case", d["sockets"], d["case"]),
        ("sockets, battery", d["sockets"], battery_block(side)),
        ("sockets, spacer", d["sockets"], d["spacers"]),
        ("spacer, battery", d["spacers"], battery_block(side)),
        ("spacer, case", d["spacers"], d["case"]),
        ("spacer, pcb", d["spacers"], d["pcb"]),
        ("spacer, plate", d["spacers"], d["plate"]),
        ("screw-top, plate", d["screws-top"], d["plate"]),
        ("screw-top, switch", d["screws-top"], switch_bodies(side)),
        ("screw-top, keycaps", d["screws-top"], caps(d)),
        ("screw-top, keycaps(pressed)", d["screws-top"], moved(caps(d), dz=-KEY_TRAVEL)),
        ("screw-top, battery", d["screws-top"], battery_block(side)),
        ("screw-bottom, case", d["screws-bottom"], d["case"]),
        ("screw-bottom, pcb", d["screws-bottom"], d["pcb"]),
        ("screw-bottom, sockets", d["screws-bottom"], d["sockets"]),
        ("screw-bottom, power-switch", d["screws-bottom"], d["power-switch"]),
        ("screw-bottom, slider", d["screws-bottom"], d["slider"]),
    ]
    if side == "R":
        pairs += [
            ("ball-ring, switch", d["ball-ring"], switch_bodies(side)),
            ("ball-ring, case", d["ball-ring"], d["case"]),
            ("ball-ring, pcb", d["ball-ring"], d["pcb"]),
            ("ball-ring, plate", d["ball-ring"], d["plate"]),
            ("ball, plate", d["ball"], d["plate"]),
            ("ball-ring, keycaps(pressed)", d["ball-ring"], moved(caps(d), dz=-KEY_TRAVEL)),
            ("ball-ring, keycaps", d["ball-ring"], caps(d)),
            ("ball, ball-ring", d["ball"], d["ball-ring"]),
            ("sensor, case", d["sensor"], d["case"]),
            ("sensor, pcb", d["sensor"], d["pcb"]),
            ("ball, case", d["ball"], d["case"]),
            ("sensor, plate", d["sensor"], d["plate"]),
            ("sensor, ball-ring", d["sensor"], d["ball-ring"]),
            ("sensor, bearings", d["sensor"], d["bearings"]),
            ("below bottom (ball parts)", Part.makeCompound([d["ball-ring"], d["ball"], d["ball-base"], d["sensor"],
                                                             d["screws-bottom"]]), tent_halfspace(side)),
            ("ball-base, case", d["ball-base"], d["case"]),
            ("ball-base, ball-ring", d["ball-base"], d["ball-ring"]),
            ("ball-base, ball", d["ball-base"], d["ball"]),
            ("ball-base, sensor", d["ball-base"], d["sensor"]),
            ("ball-base, bearings", d["ball-base"], d["bearings"]),
            ("ball-base, screw-bottom", d["ball-base"], d["screws-bottom"]),
            ("ball-ring, spacer", d["ball-ring"], d["spacers"]),
            ("ball, bearings", d["ball"], d["bearings"]),
            ("ball-ring, ball-base", d["ball-ring"], d["ball-base"]),
            ("ball-base, pcb", d["ball-base"], d["pcb"]),
            ("ball-base, sockets", d["ball-base"], d["sockets"]),
            ("ball-base, switch", d["ball-base"], switch_bodies(side)),
            ("ball-base, plate", d["ball-base"], d["plate"]),
            ("ball-ring, screw-top", d["ball-ring"], d["screws-top"]),
            ("ball, keycaps", d["ball"], Part.makeCompound([d["keycaps"], d["keycaps-thumb"]])),
        ]
    fails = []
    for name, a, b in pairs:
        v = a.common(b).Volume
        mark = "OK" if v < 0.001 else "!! 干渉"
        print("    %-22s = %8.3f mm^3  %s" % (name, v, mark))
        if v >= 0.001:
            fails.append("%s: %s (%.3f mm^3)" % (side, name, v))
    return fails


def main():
    for d in (OUT_STEP, OUT_STL, OUT_ASM):
        os.makedirs(d, exist_ok=True)

    doc = FreeCAD.newDocument("assembly")
    objs = []
    fails = []
    for side, dx, tag in (("L", 0.0, "left"), ("R", W + GAP_HALVES, "right")):
        print("[%s]" % tag)
        parts = half_parts(side)
        fails += check_interference(side, parts)
        uc = cnc_undercuts(side, dict(parts)["case"])                  # ケースを上・下から削れるか
        print("    CNC undercut (case)    = %d slices  %s" % (len(uc), "OK" if not uc else "NG"))
        for z, a, (x0, y0, x1, y1) in uc:
            fails.append("%s: CNC で削れない空洞 z %.2f  %.2f mm^2  x %.1f〜%.1f  y %.1f〜%.1f" % (side, z, a, x0, x1, y0, y1))
        for label, shp in parts:
            view = to_view(moved(shp, dx))
            name = "%s-%s" % (label, tag)
            write_stl(view, os.path.join(OUT_ASM, name + ".stl"), label in COARSE_STL)
            o = doc.addObject("Part::Feature", name.replace("-", "_"))
            o.Shape = view
            o.Label = name
            objs.append(o)

        d = dict(parts)
        # 部品単体の STEP（アセンブリ座標のまま、左右それぞれの原点）
        to_view(d["case"]).exportStep(os.path.join(OUT_STEP, "case-%s.step" % tag))
        to_view(d["plate"]).exportStep(os.path.join(OUT_STEP, "plate-%s.step" % tag))

        # 印刷向きの STL（ケースは平らな底を造形台に置く）
        case_print = to_view(d["case"])
        case_print.translate(V(0, 0, -case_print.BoundBox.ZMin))
        write_stl(case_print, os.path.join(OUT_STL, "case-%s.stl" % tag))
        # ボールの台・タグ・リポバッテリのふたはアセンブリの向きのまま（台とふたは平らな底を造形台に置く）
        for label in ("ball-base", "tag", "battery-door"):
            if label not in d:
                continue
            shp = to_view(d[label])
            to_view(d[label]).exportStep(os.path.join(OUT_STEP, "%s-%s.step" % (label, tag)))
            shp.translate(V(0, 0, -shp.BoundBox.ZMin))
            write_stl(shp, os.path.join(OUT_STL, "%s-%s.stl" % (label, tag)))
        plate_print = moved(to_view(d["plate"]), dz=-PLATE_BOT)
        write_stl(plate_print, os.path.join(OUT_STL, "plate-%s.stl" % tag))
        # カバーは天面を造形台に伏せる
        cov = to_view(d["cover"])
        cov.rotate(V(0, 0, 0), V(1, 0, 0), 180)
        cov.translate(V(0, 0, -cov.BoundBox.ZMin))
        write_stl(cov, os.path.join(OUT_STL, "cover-%s.stl" % tag))
        to_view(d["cover"]).exportStep(os.path.join(OUT_STEP, "cover-%s.step" % tag))
        # 電源スイッチのスライダー（アセンブリの向きのまま。平らな下面を造形台に置く）
        sld = to_view(d["slider"])
        sld.translate(V(0, 0, -sld.BoundBox.ZMin))
        write_stl(sld, os.path.join(OUT_STL, "slider-%s.stl" % tag))
        to_view(d["slider"]).exportStep(os.path.join(OUT_STEP, "slider-%s.step" % tag))

    ring = ball_ring()
    ring.exportStep(os.path.join(OUT_STEP, "ball-ring.step"))
    write_stl(moved(ring, dz=-PLATE_TOP), os.path.join(OUT_STL, "ball-ring.stl"))   # 筒の下端を造形台に置く

    doc.recompute()
    Import.export(objs, os.path.join(OUT_STEP, "assembly.step"))

    print("plate_top=%.2f ball_cz=%.2f ball_top_above_plate=%.2f claw_top=%.2f sensor_gap=%.2f brg_angle=%.1f deg"
          % (PLATE_TOP, BALL_CZ, BALL_PROTRUDE, PLATE_TOP + CLAW_TOP, SENSOR_GAP, BRG_ANGLE))
    if fails:
        print("干渉あり:")
        for f in fails:
            print("  - " + f)
    else:
        print("干渉なし")


main()
