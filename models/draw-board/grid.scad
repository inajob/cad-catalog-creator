$fn=50;
linear_extrude(height=0.5)
difference(){
    offset(5)
        square([100,60], center=true);
    translate([-27,-30,0]){
        union(){
            for(i = [0:1:10])
                for(j = [0:1:10])
                    translate([i * 6, j * 6,0])
                        offset(1)
                        offset(-1)
                            square([4.5, 4.5], center = true);
        }
    }
}