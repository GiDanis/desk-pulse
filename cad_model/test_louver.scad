$fn = 50;

module louver_vent(width_y = 44.0, height_z = 9.0, wall_depth_x = 3.5, num_slats = 4, angle = 45) {
    // A recessed framed louvered vent
    // Slat openings are angled at 45 degrees downward
    bezel_r = 1.8;
    
    // Outer recessed bezel
    translate([0, 0, 0])
        rotate([0, 90, 0])
        hull() {
            translate([-height_z/2 + bezel_r, -width_y/2 + bezel_r]) circle(r=bezel_r);
            translate([ height_z/2 - bezel_r, -width_y/2 + bezel_r]) circle(r=bezel_r);
            translate([ height_z/2 - bezel_r,  width_y/2 - bezel_r]) circle(r=bezel_r);
            translate([-height_z/2 + bezel_r,  width_y/2 - bezel_r]) circle(r=bezel_r);
        };
}

