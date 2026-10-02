// パラメータ設定
stem_w = 12;   // 軸の幅
stem_l = 25;   // 軸の長さ
head_w = 32;   // 矢印の頭の幅
head_l = 20;   // 矢印の頭の長さ
height = 8;    // 立ち上げの高さ（厚み）

module hatching_rectangle(w, h, thick, pitch, deg) {
    // 矩形全体の対角線長（パターンを十分に覆うためのサイズ）
    diag = sqrt(w*w + h*h) * 2;
    
    intersection() {
        // 切り抜く外枠の矩形
        square([w, h]);
        
        // 斜め線のパターン
        translate([w/2, h/2]) // 矩形の中心を軸に回転
        rotate([0, 0, deg])
        for (i = [-diag/2 : pitch : diag/2]) {
            translate([i, 0])
            square([thick, diag], center = true);
        }
    }
}

linear_extrude(height=1)
    union(){
        difference(){
            square([100,40]);
            translate([3,10,0])
              scale(2.1){
                translate([2,0,0])
                text("inajob", font="Arial:style=Bold");
                //text("♥ ★ ◆", font="MS UI Gothic:style=Regular");
              }
        }

        translate([50,-22,0])
        polygon(points = [
            [-stem_w / 2,  stem_l],  // 1: 軸の上左
            [ stem_w / 2,  stem_l],  // 2: 軸の上右
            [ stem_w / 2,  0],       // 3: 軸の下右
            [ head_w / 2,  0],       // 4: 頭の右端
            [ 0,          -head_l],  // 5: 矢印の先端（下）
            [-head_w / 2,  0],       // 6: 頭の左端
            [-stem_w / 2,  0]        // 7: 軸の下左
        ]);
    }
translate([50,-40,-5+1])
difference(){
    cube([10,5,10],center=true);
    rotate([0,90,90])
        cylinder(h = 50, d = 3, center = true, $fn = 100);
}
linear_extrude(height=1)
    hatching_rectangle(100, 40, 0.8, 3, 45);
