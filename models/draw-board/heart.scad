$fn=50;
module heart()
  scale(1/10)
  rotate([0,0,0])
  translate([-50,-260,0])
  import("heart.svg", center = false, dpi = 96);

linear_extrude(height=0.5)
difference(){
    offset(5)
        square([100,60], center=true);
    translate([-27,-30,0]){
        union(){
            for(i = [0:1:10])
                for(j = [0:1:10])
                    translate([i * 6, j * 6,0])
                            //square([4.5, 4.5], center = true);
                            heart();
        }
    }
}