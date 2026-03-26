$fn=50;
linear_extrude(height=0.5)
difference(){
    offset(5)
        square([100,60], center=true);
    translate([-25,0,0]){
        union(){
            circle(r=5);
            for(i = [0:1:10])
                rotate([0,0,(i+0.5)*360/10])
                    translate([17,0,0])
                        offset(1)
                        offset(-1)
                            square([15, 4], center = true);
        }
    }
    translate([20,0,0])
        offset(1)
            offset(-1)
            square([50, 4], center = true);
}