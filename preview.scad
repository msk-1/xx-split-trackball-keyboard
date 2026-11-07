// =============================================================================
// build.py が書き出したアセンブリ座標の STL を色付きで並べる（画像・3MF 用）
// 形はここで作らない。寸法を変えるときは build.py を直して流し直す。
// -----------------------------------------------------------------------------
// view = assembled | exploded
// 出力例: openscad -D 'view="exploded"' -o out/assembly-exploded.3mf preview.scad
// =============================================================================

view = "assembled";
ex = (view == "exploded") ? 1 : 0;
// scheme = default | black | white | darkgray（外から見える部品の色をそろえる。基板・ネジ・ボールなどは元の色のまま）
scheme = "default";
mono = [
    // [部品, 黒, 白, ダークグレー]
    ["case",          "#2A2A2C", "#F2F1EF", "#55575B"],
    ["plate",         "#1F1F21", "#FAFAF8", "#4A4C50"],
    ["cover",         "#303033", "#ECEBE8", "#5E6064"],
    ["tag",           "#18181A", "#FFFFFF", "#3E4044"],
    ["keycaps",       "#2C2C2F", "#FDFCFA", "#505256"],
    ["keycaps-thumb", "#3C3C40", "#E4E2DE", "#64666A"],
    ["ball-ring",     "#2A2A2C", "#F2F1EF", "#55575B"],
    ["ball-base",     "#2A2A2C", "#F2F1EF", "#55575B"],
    ["battery-door",  "#2A2A2C", "#F2F1EF", "#55575B"],
    ["slider",        "#3C3C40", "#E4E2DE", "#64666A"],
];
// accent = タグとマイコンカバーの色（例 "#C45E35"）。空なら scheme の色のまま
accent = "";
function part_color(n, c) =
    let(m = [for (r = mono) if (r[0] == n) r])
    (accent != "" && (n == "tag" || n == "cover")) ? accent :
    (scheme == "default" || len(m) == 0) ? c :
    scheme == "black" ? m[0][1] : scheme == "white" ? m[0][2] : m[0][3];

// [ファイル名, 色, 分解図での z オフセット]
parts = [
    ["case",           "#EFECEC",   0],
    ["pcb",            "#2F5D46",  18],
    ["usb-c",          "#B8BCC0",  18],
    ["xiao",           "#2F5D46",   6],
    ["power-switch",   "#3A3A3C",   8],
    ["slider",         "#C45E35",   0],
    ["cover",          "#E4E7E5",  64],
    ["magnets",        "#9aa3a6",  64],
    ["sockets",        "#C44536",  14],
    ["switches",       "#3A3A3C",  32],
    ["plate",          "#F7F5F5",  44],
    ["keycaps",        "#FDFBFC",  60],
    ["keycaps-thumb",  "#D9D5D5",  60],
    ["spacers",        "#B8BCC0",  10],
    ["screws-top",     "#3A3A3C",  52],
    ["screws-bottom",  "#3A3A3C", -80],
    ["lipo",           "#3A5A8C", -26],
    ["ball-base",      "#E2DEDE", -64],
    ["tag",            "#F7F5F5",  52],
    ["battery-door",   "#E2DEDE", -40],
    ["ball-ring",      "#E2DEDE",  36],
    ["ball",           "#C45E35",  70],
    ["bearings",       "#C9CDD1", -22],
    ["sensor",         "#2F5D46", -40],
];
right_only = ["ball-ring", "ball", "bearings", "sensor", "ball-base"];

function right_only_part(n) = len([for (r = right_only) if (r == n) 1]) > 0;

for (p = parts) for (side = ["left", "right"])
    if (side == "right" || !right_only_part(p[0]))
        color(part_color(p[0], p[1])) translate([0, 0, p[2] * ex])
            import(str("out/stl/asm/", p[0], "-", side, ".stl"));
