// Test script for various elaborate front panel designs
$fn = 40;
case_w = 99.0;
base_h = 17.5;
wall_t = 2.0;

module capsule_slot(length, height, depth) {
    rotate([90, 0, 0])
    linear_extrude(height=depth, center=true)
    hull() {
        translate([-length/2 + height/2, 0]) circle(d=height);
        translate([ length/2 - height/2, 0]) circle(d=height);
    }
}

// Stile 1: Macintosh Classic / SE (Iconic & Detailed)
// - Inset Bezel Frame
// - 3D Floppy Drive with Eject Button & Bezel
// - Snow White Horizontal Slats
// - Rainbow Logo Recessed Badge Pocket
// - Concentric Power Button / LED Ring
module front_style_mac_classic() {
    union() {
        // 1. Recessed Front Bezel Frame (The entire front face has a 1.2mm step-in)
        translate([case_w/2, 0.6, base_h/2])
            cube([case_w - 10.0, 1.2, base_h - 4.0], center=true);
            
        // 2. High-Detail Floppy Drive Bay
        translate([case_w/2, 0, base_h - 4.5]) {
            // Recessed slot
            cube([46.0, 3*wall_t, 2.8], center=true);
            // Eject button pocket
            translate([24.0, 0, 0])
                cube([4.0, 3*wall_t, 4.0], center=true);
        }
        
        // 3. Snow White Horizontal Vents (5 rows)
        for (i = [0:4]) {
            translate([case_w/2, 0, 3.2 + i*2.2])
                capsule_slot(length=case_w - 24.0, height=1.3, depth=3*wall_t);
        }
        
        // 4. Recessed Logo Badge Pocket (Front-Left)
        translate([11.5, 0.6, base_h - 4.5])
            cube([9.0, 1.5, 9.0], center=true);
            
        // 5. LED Bezel with Concentric Ring
        translate([11.5, 0, 4.5])
            rotate([90, 0, 0]) {
                cylinder(d=3.0, h=3*wall_t, center=true);
                translate([0, 0, -wall_t]) cylinder(d=5.5, h=1.0, center=true);
            }
    }
}

echo "Test front definitions ready";
