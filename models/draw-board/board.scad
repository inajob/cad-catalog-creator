module unko()
  scale(1/2)
  import("unko.svg", center = false, dpi = 96);

linear_extrude(height=0.5)
difference(){
    offset(5)
        square([100,100]);
    translate([10,10,0])
    unko();
}