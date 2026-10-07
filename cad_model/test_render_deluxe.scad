include <smartpc_case.scad>

module deluxe_front() {
    // 1. Chamfered Perimeter Bezel (Frame)
    // Bevel frame stepped in
    translate([case_w/2, 0.35, base_h/2])
        cube([case_w - 9.0, 0.7, base_h - 3.2], center=true);
    translate([case_w/2, 0.7, base_h/2])
        cube([case_w - 11.5, 0.7, base_h - 4.5], center=true);

    // 2. Dual-Tier Vintage Apple Badge Frame (Top-Left)
    translate([12.0, 0.5, base_h - 4.8]) {
        // Outer beveled frame
        cube([10.5, 0.6, 10.5], center=true);
        // Inner pocket
        translate([0, 0.3, 0])
            cube([9.0, 0.8, 9.0], center=true);
        // Leaf notch at top
        translate([0, 0.3, 5.0])
            rotate([0, 45, 0]) cube([1.5, 0.8, 1.5], center=true);
    }

    // 3. Power LED & Programmer Reset Pocket
    translate([12.0, 0, 3.8]) {
        rotate([90, 0, 0]) {
            cylinder(d=2.0, h=3*wall_t, center=true);
            translate([0, 0, -0.5]) cylinder(d=4.2, h=1.0, center=true);
        }
    }
    // Programmer's switch / reset pin
    translate([16.8, 0, 3.8]) {
        rotate([90, 0, 0])
            cylinder(d=1.2, h=3*wall_t, center=true);
        translate([0, 0.4, 0])
            cube([2.4, 0.8, 2.4], center=true);
    }

    // 4. Acoustic Speaker Matrix (Blind conical micro-dimples, 4 rows x 3 cols)
    for (rx = [0:3]) {
        for (rz = [0:2]) {
            translate([22.5 + rx*3.2, 0.6, 2.8 + rz*2.6])
                rotate([90, 0, 0])
                cylinder(d1=1.8, d2=0.4, h=1.0, center=true);
        }
    }

    // 5. Deluxe Floppy SuperDrive Assembly
    // Main feed slot mouth
    translate([62.0, 0.6, base_h - 4.4]) {
        // Beveled lead-in mouth
        cube([46.0, 1.2, 2.6], center=true);
        // Inner dust shutter seam
        translate([-4.0, 0.5, 0])
            cube([36.0, 1.2, 0.8], center=true);

        // Tactile Eject Button with dish
        translate([17.5, 0, 0]) {
            // Recessed trench around button
            cube([5.6, 1.3, 3.4], center=true);
            // Thumb dish
            translate([0, 0.4, 0])
                rotate([90, 0, 0])
                cylinder(d=2.4, h=1.2, center=true);
        }

        // Drive Activity Lens
        translate([22.2, 0.3, 0])
            cube([2.2, 1.0, 1.5], center=true);

        // Manual Eject Pinhole
        translate([25.0, 0, 0])
            rotate([90, 0, 0])
            cylinder(d=1.1, h=2.5, center=true);
    }

    // 6. Typographic Nameplate Recess (e.g. "SmartPC / 30")
    translate([62.0 - 4.0, 0.4, base_h - 7.6])
        cube([34.0, 0.8, 2.0], center=true);

    // 7. Precision "Snow White" Ribs (Right section, 4 sleek horizontal lines)
    for (i = [0:3]) {
        translate([62.0, 0.7, 2.5 + i*2.2])
            capsule_slot(length=50.0, height=1.3, depth=1.4);
    }

    // 8. Front Contrast / Volume Pill Rocker Accent (Between speaker and ribs)
    translate([36.0, 0.4, 5.8]) {
        // Recessed pill bezel
        capsule_slot(length=4.5, height=9.0, depth=0.8);
        // Rocker split seam
        cube([3.0, 1.0, 0.6], center=true);
    }
}

module deluxe_side_left() {
    // Recessed Ergonomic Side Grip Pocket (SE Carry Scoop)
    translate([0.45, case_d/2 - 2.0, 8.5])
        rounded_box_side(width=48.0, height=13.0, depth=0.9, r=3.0);
    
    // 2 Lateral Air Intake Slats (inside the grip pocket)
    for (k = [0:1]) {
        translate([0, case_d/2 - 2.0, 6.0 + k*5.0])
            capsule_slot_side(length=38.0, height=2.4, depth=3*wall_t);
    }
}

module rounded_box_side(width, height, depth, r) {
    rotate([0, 90, 0])
    linear_extrude(height=depth, center=true)
    hull() {
        translate([-height/2 + r, -width/2 + r]) circle(r=r);
        translate([ height/2 - r, -width/2 + r]) circle(r=r);
        translate([ height/2 - r,  width/2 - r]) circle(r=r);
        translate([-height/2 + r,  width/2 - r]) circle(r=r);
    }
}
