// ====================================================================
// SmartPC Case: Stile 1 Deluxe (SE/30 Studio Edition)
// Perfectly Balanced, High-Density Vintage Macintosh Detailing
// ====================================================================

part = 0; // 0 = Assembled, 1 = Base only, 2 = Lid only
$fn = 50;

case_w = 99.0;
case_d = 72.0;
base_h = 17.5;
lid_h = 7.5;
corner_r = 3.5;
wall_t = 2.0;
front_wall_t = 2.8;
floor_t = 2.0;
ceiling_t = 2.0;
standoff_h = 3.5;
pcb_t = 1.6;
lip_h = 1.4;
lip_clearance = 0.4;

pcb_w = 65.0;
pcb_d = 32.0;
pcb_x = 9.0;
pcb_y = case_d - wall_t - pcb_d - 0.5;

mount_holes = [
    [pcb_x + 3.5,  pcb_y + 4.5],
    [pcb_x + 61.5, pcb_y + 4.5],
    [pcb_x + 61.5, pcb_y + 27.5],
    [pcb_x + 3.5,  pcb_y + 27.5]
];

lid_posts = [
    [wall_t + 4.0, front_wall_t + 4.0],
    [case_w - wall_t - 4.0, front_wall_t + 4.0],
    [case_w - wall_t - 4.0, case_d - wall_t - 4.5],
    [wall_t + 3.5, case_d - wall_t - 4.5]
];

module rounded_rect_2d(x, y, r) {
    hull() {
        translate([r, r]) circle(r=r);
        translate([x - r, r]) circle(r=r);
        translate([x - r, y - r]) circle(r=r);
        translate([r, y - r]) circle(r=r);
    }
}

module rounded_rect_centered_2d(w, h, r) {
    hull() {
        translate([-w/2 + r, -h/2 + r]) circle(r=r);
        translate([ w/2 - r, -h/2 + r]) circle(r=r);
        translate([ w/2 - r,  h/2 - r]) circle(r=r);
        translate([-w/2 + r,  h/2 - r]) circle(r=r);
    }
}

module rounded_box(x, y, z, r) {
    linear_extrude(height=z) rounded_rect_2d(x, y, r);
}

module front_cut(w, h, depth) {
    translate([0, depth/2 - 0.05, 0])
        cube([w, depth + 0.1, h], center=true);
}

module horizontal_capsule_cut(length, height, depth) {
    translate([0, depth/2 - 0.05, 0])
    rotate([90, 0, 0])
    linear_extrude(height=depth + 0.1, center=true)
    hull() {
        translate([-length/2 + height/2, 0]) circle(d=height);
        translate([ length/2 - height/2, 0]) circle(d=height);
    }
}

module capsule_slot_side(length, height, depth) {
    rotate([0, 90, 0])
    linear_extrude(height=depth, center=true)
    hull() {
        translate([0, -length/2 + height/2]) circle(d=height);
        translate([0,  length/2 - height/2]) circle(d=height);
    }
}

module side_carry_scoop(length_y, height_z, depth_x, r) {
    rotate([0, 90, 0])
    linear_extrude(height=depth_x + 0.1, center=true)
    rounded_rect_centered_2d(height_z, length_y, r);
}

module bottom_base_deluxe() {
    difference() {
        union() {
            rounded_box(case_w, case_d, base_h, corner_r);
        }

        // Inner hollow cavity
        translate([wall_t, front_wall_t, floor_t])
            rounded_box(case_w - 2*wall_t, case_d - wall_t - front_wall_t, base_h + 1, corner_r - 1.0);

        // Step rebate for top lid alignment lip
        translate([wall_t - 0.8, front_wall_t - 0.8, base_h - 2.5])
            rounded_box(case_w - 2*(wall_t - 0.8), case_d - wall_t - front_wall_t + 2*0.8, 3.0, corner_r - 0.5);

        // --- REAR PORTS CUTOUTS (I/O) ---
        // 1. Mini-HDMI
        translate([pcb_x + 12.4, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
            cube([11.8, 3*wall_t, 6.2], center=true);
            translate([0, wall_t/2 + 0.6, 0]) cube([13.2, wall_t + 1, 7.8], center=true);
        }
        // 2. USB-C 1
        translate([pcb_x + 41.4, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
            cube([10.5, 3*wall_t, 6.0], center=true);
            translate([0, wall_t/2 + 0.6, 0]) cube([12.0, wall_t + 1, 7.6], center=true);
        }
        // 3. USB-C 2
        translate([pcb_x + 54.0, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
            cube([10.5, 3*wall_t, 6.0], center=true);
            translate([0, wall_t/2 + 0.6, 0]) cube([12.0, wall_t + 1, 7.6], center=true);
        }

        // ============================================================
        // DELUXE FRONT SCULPTING (SOLID RETRO SE/30 STUDIO)
        // ============================================================
        
        // 1. Perimeter Shadow Channel (Frames faceplate)
        translate([case_w/2, 0.5, base_h/2])
            rotate([90, 0, 0])
            linear_extrude(height=1.2, center=true)
            difference() {
                rounded_rect_centered_2d(case_w - 10.0, base_h - 3.4, 2.0);
                rounded_rect_centered_2d(case_w - 11.8, base_h - 5.2, 1.2);
            }

        // 2. Vintage Rainbow Logo Pocket with Leaf Notch (Top-Left)
        translate([12.5, 0, 10.6]) {
            front_cut(w=7.4, h=7.4, depth=0.6);
            front_cut(w=6.2, h=6.2, depth=1.2);
            // Leaf notch
            translate([0, 0, 3.4])
                rotate([0, 45, 0])
                front_cut(w=1.2, h=1.2, depth=1.2);
        }

        // 3. Status LED Bezel & Reset Pinhole (Bottom-Left)
        translate([11.0, 0, 3.6]) {
            rotate([90, 0, 0]) {
                cylinder(d=2.0, h=3*wall_t, center=true);
                translate([0, 0, -0.6]) cylinder(d1=4.0, d2=2.2, h=1.2, center=true);
            }
        }
        translate([15.5, 0, 3.6]) {
            rotate([90, 0, 0]) cylinder(d=1.2, h=3*wall_t, center=true);
            front_cut(w=1.8, h=1.8, depth=0.7);
        }

        // 4. Acoustic Speaker Matrix (2 cols x 4 rows blind conical dimples)
        // Acting as a sleek vertical transition between badge and floppy
        for (rx = [0:1]) {
            for (rz = [0:3]) {
                translate([21.0 + rx*2.6, 0.5, 4.0 + rz*2.3])
                    rotate([90, 0, 0])
                    cylinder(d1=1.5, d2=0.4, h=1.2, center=true);
            }
        }

        // 5. Deluxe Floppy SuperDrive Bay Assembly (Upper Right)
        translate([57.0, 0, 12.4]) {
            // Main disc slot mouth
            front_cut(w=42.0, h=2.2, depth=1.4);
            // Internal dust shutter flap seam
            translate([-4.0, 0, 0])
                front_cut(w=32.0, h=0.7, depth=2.0);

            // Tactile Eject Button with Thumb Dish
            translate([23.5, 0, 0]) {
                front_cut(w=4.4, h=2.8, depth=1.5);
                translate([0, 0.4, 0])
                    rotate([90, 0, 0])
                    cylinder(d=1.9, h=1.0, center=true);
            }

            // Drive Activity LED Lens
            translate([27.2, 0, 0])
                front_cut(w=1.8, h=1.2, depth=1.0);

            // Emergency Manual Eject Pinhole
            translate([29.5, 0, 0])
                rotate([90, 0, 0])
                cylinder(d=1.1, h=2.5, center=true);
        }

        // 6. Typographic Nameplate Recess ("SmartPC / 30")
        translate([57.0 - 4.0, 0, 9.6])
            front_cut(w=32.0, h=1.6, depth=0.7);

        // 7. Iconic "Snow White" Grooves (3 Sleek Horizontal Ribs)
        for (i = [0:2]) {
            translate([57.0, 0, 3.2 + i*2.0])
                horizontal_capsule_cut(length=58.0, height=1.2, depth=1.4);
        }

        // ============================================================
        // ERGONOMIC RECESSED SIDE CARRY SCOOPS WITH NESTED SLATS
        // ============================================================

        // --- FIANCO SINISTRO ---
        translate([0.45, case_d/2 - 2.0, 8.5])
            side_carry_scoop(length_y=46.0, height_z=10.5, depth_x=0.9, r=2.5);

        // 2 Lateral Air Intake Slats (nested inside scoop)
        for (k = [0:1]) {
            translate([0, case_d/2 - 2.0, 6.0 + k*5.0])
                capsule_slot_side(length=38.0, height=2.4, depth=3*wall_t);
        }

        // --- FIANCO DESTRO ---
        translate([case_w - 0.45, case_d/2 - 2.0, 8.5])
            side_carry_scoop(length_y=46.0, height_z=10.5, depth_x=0.9, r=2.5);

        // 2 Lateral Air Exhaust Slats (nested inside scoop)
        for (k = [0:1]) {
            translate([case_w, case_d/2 - 2.0, 6.0 + k*5.0])
                capsule_slot_side(length=38.0, height=2.4, depth=3*wall_t);
        }

        // --- BOTTOM FLOOR: Griglie di aerazione inferiori ---
        for (gx = [18:6:50]) {
            for (gy = [14:6:28]) {
                translate([gx, gy, -1])
                    rounded_box(4.0, 4.0, floor_t + 2, 1.0);
            }
        }

        // --- SCREW MOUNTING HOLES ---
        for (pos = mount_holes) {
            translate([pos[0], pos[1], -1]) {
                cylinder(d=2.8, h=floor_t + standoff_h + 2);
                cylinder(d=5.4, h=1.4 + 1);
            }
        }

        for (pos = lid_posts) {
            translate([pos[0], pos[1], -1]) {
                cylinder(d=2.8, h=base_h + 2);
                cylinder(d=5.4, h=1.4 + 1);
            }
        }

        // Rubber Foot Pockets
        translate([8.0, 8.0, -0.1]) cylinder(d=8.5, h=1.4);
        translate([case_w - 8.0, 8.0, -0.1]) cylinder(d=8.5, h=1.4);
        translate([case_w - 8.0, case_d - 8.0, -0.1]) cylinder(d=8.5, h=1.4);
        translate([8.0, case_d - 8.0, -0.1]) cylinder(d=8.5, h=1.4);
    }

    // --- INTERIOR PILLARS: PCB Standoffs ---
    for (pos = mount_holes) {
        difference() {
            translate([pos[0], pos[1], floor_t]) cylinder(d=4.8, h=standoff_h);
            translate([pos[0], pos[1], floor_t - 0.5]) cylinder(d=2.8, h=standoff_h + 1);
        }
    }

    // --- INTERIOR PILLARS: Lid Posts ---
    for (i = [0:2]) {
        pos = lid_posts[i];
        difference() {
            translate([pos[0], pos[1], floor_t]) cylinder(d=5.6, h=base_h - floor_t);
            translate([pos[0], pos[1], floor_t - 0.5]) cylinder(d=2.8, h=base_h + 1);
        }
    }
    difference() {
        translate([lid_posts[3][0], lid_posts[3][1], floor_t]) cylinder(d=5.2, h=base_h - floor_t);
        translate([lid_posts[3][0], lid_posts[3][1], floor_t - 0.5]) cylinder(d=2.8, h=base_h + 1);
    }
}

// Module top lid
module top_lid() {
    difference() {
        union() {
            rounded_box(case_w, case_d, lid_h, corner_r);
            translate([0, 0, lid_h])
                difference() {
                    rounded_box(case_w, case_d, lip_h, corner_r);
                    translate([lip_clearance/2, lip_clearance/2, -0.1])
                        rounded_box(case_w - lip_clearance, case_d - lip_clearance, lip_h + 0.5, corner_r - 0.5);
                }
            translate([wall_t - 0.6, front_wall_t - 0.6, -2.2])
                difference() {
                    rounded_box(case_w - 2*(wall_t - 0.6), case_d - wall_t - front_wall_t + 2*0.6, 2.2, corner_r - 0.8);
                    translate([wall_t, wall_t, -0.5])
                        rounded_box(case_w - 2*(wall_t - 0.6) - 2*wall_t, case_d - wall_t - front_wall_t + 2*0.6 - 2*wall_t, 3.0, corner_r - 1.5);
                }
        }
        translate([wall_t, front_wall_t, -2.5])
            rounded_box(case_w - 2*wall_t, case_d - wall_t - front_wall_t, lid_h - ceiling_t + 2.5, corner_r - 1.0);
        for (pos = lid_posts) {
            translate([pos[0], pos[1], -3]) cylinder(d=2.3, h=lid_h + 1);
        }
        for (gx = [12:3.5:28]) {
            translate([gx, case_d - 10.0, lid_h - 1.0]) cube([2.0, 10.0, 1.8], center=true);
        }
    }
}

if (part == 0) {
    color("#E3D9C8") bottom_base_deluxe();
    color("#D9CFBD") translate([0, 0, base_h]) top_lid();
}
else if (part == 1) {
    bottom_base_deluxe();
}
else if (part == 2) {
    rotate([180, 0, 0]) translate([0, -case_d, -lid_h - lip_h]) top_lid();
}
