module shapes()
  scale(1.1)
  import("shapes.svg", center = false, dpi = 96);

linear_extrude(height=0.5)
difference(){
    offset(5)
        square([150,100]);
    translate([10,10,0])
    shapes();
}