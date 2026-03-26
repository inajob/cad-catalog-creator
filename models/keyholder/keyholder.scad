$fn=50;
module heart()
  scale(0.5)
  translate([-47,-40,0])
  import("complex-heart.svg", center = false, dpi = 96);

linear_extrude(height=3)
  heart();
