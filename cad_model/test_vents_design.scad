$fn = 50;

wall_t = 2.0;

// 1. ARCHITECTURAL LOUVERED SIDE VENT MODULE
// length: horizontal length (Y axis)
// height: total height of the grille (Z axis)
// num_slots: number of angled slats
module louvered_side_grille(length=42.0, num_slots=4, slot_h=1.4, pitch=2.6, angle=40) {
    total_h = (num_slots - 1) * pitch + slot_h;
    
    // Outer recessed bevel frame (0.8mm depth into the outer wall)
    translate([0, 0, 0])
        rotate([0, 90, 0])
        hull() {
            for (dy = [-length/2 + 2.0, length/2 - 2.0]) {
                for (dz = [-total_h/2 - 0.8, total_h/2 + 0.8]) {
                    translate([dz, dy, 0]) cylinder(r=1.6, h=0.9, center=true);
                }
            }
        }
    
    // Angled louver slats cutting through the wall
    // Sloping down towards outside (-X) so you cannot see straight in
    for (i = [0 : num_slots - 1]) {
        z_offset = -total_h/2 + slot_h/2 + i * pitch;
        translate([0, 0, z_offset])
            rotate([angle, 0, 0]) // incline across wall
            rotate([0, 90, 0])
            hull() {
                translate([0, -length/2 + slot_h/2]) cylinder(d=slot_h, h=10, center=true);
                translate([0,  length/2 - slot_h/2]) cylinder(d=slot_h, h=10, center=true);
            }
    }
}

// Render test slab with the grille
difference() {
    cube([wall_t, 60, 20]);
    translate([wall_t, 30, 10])
        louvered_side_grille(length=42.0, num_slots=4, slot_h=1.5, pitch=2.8, angle=35);
}
