module unko()
  scale(0.5)
  translate([-47,-300,0])
  import("cherry.svg", center = false, dpi = 96);

linear_extrude(height=2)
  unko();
