$fn = 50;

wall_t = 2.0;

module horizontal_louver_grille(length=42.0, num_slots=3, slot_h=1.5, pitch=3.2, louver_angle=40) {
    total_h = (num_slots - 1) * pitch + slot_h;
    
    // 1. Recessed Architectural Bezel (0.7mm shallow frame)
    translate([0, 0, 0])
        rotate([0, 90, 0])
        hull() {
            r = 1.8;
            translate([-total_h/2 - 1.0 + r, -length/2 - 1.2 + r]) circle(r=r);
            translate([ total_h/2 + 1.0 - r, -length/2 - 1.2 + r]) circle(r=r);
            translate([ total_h/2 + 1.0 - r,  length/2 + 1.2 - r]) circle(r=r);
            translate([-total_h/2 - 1.0 + r,  length/2 + 1.2 - r]) circle(r=r);
        }

    // 2. Horizontal Louver Slots (Horizontal along Y, angled downward through the wall X)
    for (i = [0 : num_slots - 1]) {
        z_pos = -total_h/2 + slot_h/2 + i * pitch;
        translate([0, 0, z_pos])
            rotate([0, louver_angle, 0]) // Angled through wall thickness!
            rotate([0, 90, 0])
            hull() {
                translate([0, -length/2 + slot_h/2]) cylinder(d=slot_h, h=10, center=true);
                translate([0,  length/2 - slot_h/2]) cylinder(d=slot_h, h=10, center=true);
            }
    }
}

difference() {
    cube([wall_t, 60, 25]);
    translate([wall_t, 30, 12.5])
        horizontal_louver_grille(length=42.0, num_slots=3, slot_h=1.5, pitch=3.2, louver_angle=35);
}
