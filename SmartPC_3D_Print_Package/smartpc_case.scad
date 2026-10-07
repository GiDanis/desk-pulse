// ====================================================================
// SmartPC Case for OrangePi Zero 3W with Official Heatsink & Fan
// Seamless Stacking with Hagibis 3.5" IPS Screen Dock (B0D3CW311P)
// Stile 1 Refined: Solid Front (No through-holes), Dual Wide Side Vents, No SD Hole
// ====================================================================

// --- PART SELECTION ---
// 0 = Full Assembly Preview
// 1 = Bottom Base (Ready to slice & print)
// 2 = Top Lid / Stacking Tray (Ready to slice & print)
// 3 = Exploded Assembly View
part = 0; 
style = 1; // 1 = Classic (Top 1), 4 = Deluxe (SE/30 Studio Ultra-Dettagliato)

$fn = 50; // High curve smoothness

// --- EXTERNAL ENCLOSURE DIMENSIONS (Matches Hagibis Base) ---
case_w = 99.0;      // Width (mm)
case_d = 72.0;      // Depth (mm)
case_h = 25.0;      // Total Height (mm)
corner_r = 3.5;     // External corner radius
wall_t = 2.0;       // Wall thickness
front_wall_t = 2.8; // Thicker front wall for deep sculpted retro reliefs
floor_t = 2.0;      // Bottom floor thickness
ceiling_t = 2.0;    // Top plate thickness

// Vertical Split
base_h = 17.5;      // Base height
lid_h = 7.5;        // Lid height (17.5 + 7.5 = 25.0mm)

// Stacking Tray Rim (Seats Hagibis dock on top)
lip_h = 1.4;        // Height of top lip
lip_clearance = 0.4;// 0.2mm per side clearance (99.4 x 72.4mm tray)

// --- ORANGE PI ZERO 3W & HEATSINK SPECS ---
pcb_w = 65.0;
pcb_d = 32.0;
pcb_t = 1.6;
heatsink_h = 11.8;  // Official aluminum heatsink + 2006 fan height
standoff_h = 3.5;   // Standoff height for bottom components clearance

// Board Placement: Placed against rear wall for direct rear I/O
pcb_x = 9.0;        // Left offset (7.0mm from inner left wall)
pcb_y = case_d - wall_t - pcb_d - 0.5; // ~37.5mm from front

// 4x PCB Mounting Holes (58.0mm x 23.0mm spacing)
// Screws go from bottom into official heatsink M2.5 threaded legs
mount_holes = [
    [pcb_x + 3.5,  pcb_y + 4.5],   // Front-Left (GPIO side)
    [pcb_x + 61.5, pcb_y + 4.5],   // Front-Right (GPIO side)
    [pcb_x + 61.5, pcb_y + 27.5],  // Rear-Right (Ports side)
    [pcb_x + 3.5,  pcb_y + 27.5]   // Rear-Left (Ports side)
];

// Lid Fastening Posts (4 corners with zero board interference)
lid_posts = [
    [wall_t + 4.0, front_wall_t + 4.0],          // Front-Left corner
    [case_w - wall_t - 4.0, front_wall_t + 4.0], // Front-Right corner
    [case_w - wall_t - 4.0, case_d - wall_t - 4.5], // Rear-Right
    [wall_t + 3.5, case_d - wall_t - 4.5]        // Rear-Left
];

// --- 2D & 3D GEOMETRY HELPERS ---

module rounded_rect_2d(x, y, r) {
    hull() {
        translate([r, r]) circle(r=r);
        translate([x - r, r]) circle(r=r);
        translate([x - r, y - r]) circle(r=r);
        translate([r, y - r]) circle(r=r);
    }
}

module rounded_box(x, y, z, r) {
    linear_extrude(height=z) rounded_rect_2d(x, y, r);
}

module capsule_slot(length, height, depth) {
    rotate([90, 0, 0])
    linear_extrude(height=depth, center=true)
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

// ====================================================================
// MODULE: BOTTOM BASE (MAIN BODY)
// ====================================================================
module bottom_base() {
    difference() {
        union() {
            // Main solid rounded box
            rounded_box(case_w, case_d, base_h, corner_r);
        }

        // Inner hollow cavity (accounting for front_wall_t)
        translate([wall_t, front_wall_t, floor_t])
            rounded_box(case_w - 2*wall_t, case_d - wall_t - front_wall_t, base_h + 1, corner_r - 1.0);

        // Step rebate for top lid alignment lip (female joint)
        translate([wall_t - 0.8, front_wall_t - 0.8, base_h - 2.5])
            rounded_box(case_w - 2*(wall_t - 0.8), case_d - wall_t - front_wall_t + 2*0.8, 3.0, corner_r - 0.5);

        // --- REAR PORTS CUTOUTS (I/O) ---
        // 1. Mini-HDMI Port (Center X = pcb_x + 12.4 = 21.4mm)
        translate([pcb_x + 12.4, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
            cube([11.8, 3*wall_t, 6.2], center=true);
            translate([0, wall_t/2 + 0.6, 0])
                cube([13.2, wall_t + 1, 7.8], center=true);
        }

        // 2. USB-C 1 Port - OTG / DisplayPort Alt Mode (Center X = pcb_x + 41.4 = 50.4mm)
        translate([pcb_x + 41.4, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
            cube([10.5, 3*wall_t, 6.0], center=true);
            translate([0, wall_t/2 + 0.6, 0])
                cube([12.0, wall_t + 1, 7.6], center=true);
        }

        // 3. USB-C 2 Port - Power IN 5V 3A (Center X = pcb_x + 54.0 = 63.0mm)
        translate([pcb_x + 54.0, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
            cube([10.5, 3*wall_t, 6.0], center=true);
            translate([0, wall_t/2 + 0.6, 0])
                cube([12.0, wall_t + 1, 7.6], center=true);
        }

        // ============================================================
        // SOLID SCULPTED FRONT (NO THROUGH-HOLES, CLEAN RETRO FINISH)
        // ============================================================
        
        // 1. Bezel Recess Frame (0.8mm step-in)
        translate([case_w/2, 0.4, base_h/2])
            cube([case_w - 12.0, 0.8, base_h - 4.0], center=true);

        // 2. 3D Floppy Drive Bay (1.4mm blind recess into the bezel)
        translate([case_w/2 + 3.0, 0.7, base_h - 4.4]) {
            cube([44.0, 1.4, 2.4], center=true);
            // Eject button recess
            translate([25.0, 0, 0])
                cube([4.5, 1.4, 3.2], center=true);
            // Eject pinhole
            translate([29.0, 0, 0])
                rotate([90, 0, 0])
                cylinder(d=1.2, h=2.0, center=true);
        }

        // 3. Iconic "Snow White" Grooves (Blind 1.2mm deep horizontal ribs)
        // These are true blind grooves: beautifully visible, catch shadows, NO holes!
        for (i = [0:4]) {
            translate([case_w/2, 0.7, 3.2 + i*2.1])
                capsule_slot(length=64.0, height=1.3, depth=1.4);
        }

        // 4. Vintage Rainbow Logo Pocket (Top-Left, 0.8mm deep)
        translate([12.0, 0.4, base_h - 4.4])
            cube([9.5, 0.8, 9.5], center=true);

        // 5. Status LED Bezel (Pin-hole for light, with concentric ring)
        translate([12.0, 0, 4.2])
            rotate([90, 0, 0]) {
                cylinder(d=2.0, h=3*wall_t, center=true); // small pinhole for LED light
                translate([0, 0, -0.4])
                    cylinder(d=4.8, h=0.8, center=true);  // outer concentric bezel
            }

        // ============================================================
        // DUAL WIDE SIDE VENTS (LATERAL COOL AIR INTAKE & EXHAUST)
        // ============================================================
        
        // --- FIANCO SINISTRO: 2 Feritoie Orizzontali di Aspirazione Aria ---
        // (Nessun foro SD! Parete chiusa e pulita con due feritoie ampie)
        for (k = [0:1]) {
            translate([0, case_d/2 - 2.0, 6.0 + k*5.0])
                capsule_slot_side(length=38.0, height=2.4, depth=3*wall_t);
        }

        // --- FIANCO DESTRO: 2 Feritoie Orizzontali Simmetriche di Espulsione ---
        // (Allineate con il flusso della ventola e le alette del dissipatore)
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
        // 1. PCB Heatsink Direct Mounting (M2.5 countersunk from bottom)
        for (pos = mount_holes) {
            translate([pos[0], pos[1], -1]) {
                cylinder(d=2.8, h=floor_t + standoff_h + 2); // M2.5 clearance
                cylinder(d=5.4, h=1.4 + 1);                  // Screw head pocket
            }
        }

        // 2. Lid Fastening Screws (Countersunk from bottom)
        for (pos = lid_posts) {
            translate([pos[0], pos[1], -1]) {
                cylinder(d=2.8, h=base_h + 2);
                cylinder(d=5.4, h=1.4 + 1);
            }
        }

        // --- BOTTOM: 4x Rubber Foot Pockets (8.5mm dia x 1.4mm deep) ---
        translate([8.0, 8.0, -0.1]) cylinder(d=8.5, h=1.4);
        translate([case_w - 8.0, 8.0, -0.1]) cylinder(d=8.5, h=1.4);
        translate([case_w - 8.0, case_d - 8.0, -0.1]) cylinder(d=8.5, h=1.4);
        translate([8.0, case_d - 8.0, -0.1]) cylinder(d=8.5, h=1.4);
    }

    // --- INTERIOR PILLARS: PCB Mounting Standoffs ---
    for (pos = mount_holes) {
        difference() {
            translate([pos[0], pos[1], floor_t])
                cylinder(d=4.8, h=standoff_h);
            translate([pos[0], pos[1], floor_t - 0.5])
                cylinder(d=2.8, h=standoff_h + 1);
        }
    }

    // --- INTERIOR PILLARS: Lid Fastening Corner Posts ---
    for (i = [0:2]) {
        pos = lid_posts[i];
        difference() {
            translate([pos[0], pos[1], floor_t])
                cylinder(d=6.5, h=base_h - floor_t);
            translate([pos[0], pos[1], floor_t - 0.5])
                cylinder(d=2.8, h=base_h + 1);
        }
    }
    // Rear-Left post
    difference() {
        translate([lid_posts[3][0], lid_posts[3][1], floor_t])
            cylinder(d=5.2, h=base_h - floor_t);
        translate([lid_posts[3][0], lid_posts[3][1], floor_t - 0.5])
            cylinder(d=2.8, h=base_h + 1);
    }
}

// ====================================================================

module rounded_rect_centered_2d(w, h, r) {
    hull() {
        translate([-w/2 + r, -h/2 + r]) circle(r=r);
        translate([ w/2 - r, -h/2 + r]) circle(r=r);
        translate([ w/2 - r,  h/2 - r]) circle(r=r);
        translate([-w/2 + r,  h/2 - r]) circle(r=r);
    }
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

module vertical_capsule_cut(width, height, depth) {
    translate([0, depth/2 - 0.05, 0])
    rotate([90, 0, 0])
    linear_extrude(height=depth + 0.1, center=true)
    hull() {
        translate([0, -height/2 + width/2]) circle(d=width);
        translate([0,  height/2 - width/2]) circle(d=width);
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


module base_model() {
    if (style == 4) {
        bottom_base_deluxe();
    } else {
        bottom_base();
    }
}
// MODULE: TOP LID / STACKING TRAY
// ====================================================================
module top_lid() {
    difference() {
        union() {
            // Main top plate
            rounded_box(case_w, case_d, lid_h, corner_r);

            // Stacking Rim (Perimeter lip holding Hagibis base)
            translate([0, 0, lid_h])
                difference() {
                    rounded_box(case_w, case_d, lip_h, corner_r);
                    translate([lip_clearance/2, lip_clearance/2, -0.1])
                        rounded_box(case_w - lip_clearance, case_d - lip_clearance, lip_h + 0.5, corner_r - 0.5);
                }

            // Male interlocking lip sliding into base body
            translate([wall_t - 0.6, front_wall_t - 0.6, -2.2])
                difference() {
                    rounded_box(case_w - 2*(wall_t - 0.6), case_d - wall_t - front_wall_t + 2*0.6, 2.2, corner_r - 0.8);
                    translate([wall_t, wall_t, -0.5])
                        rounded_box(case_w - 2*(wall_t - 0.6) - 2*wall_t, case_d - wall_t - front_wall_t + 2*0.6 - 2*wall_t, 3.0, corner_r - 1.5);
                }
        }

        // Inner hollow cavity of lid
        translate([wall_t, front_wall_t, -2.5])
            rounded_box(case_w - 2*wall_t, case_d - wall_t - front_wall_t, lid_h - ceiling_t + 2.5, corner_r - 1.0);

        // Pilot holes for M2.5 lid screws
        for (pos = lid_posts) {
            translate([pos[0], pos[1], -3])
                cylinder(d=2.3, h=lid_h + 1);
        }

        // Air relief channels on the stacking tray perimeter
        for (gx = [12:3.5:28]) {
            translate([gx, case_d - 10.0, lid_h - 1.0])
                cube([2.0, 10.0, 1.8], center=true);
        }
    }
}

// ====================================================================
// RENDER VIEW SELECTION
// ====================================================================
if (part == 0) {
    // Assembled preview with classic vintage Macintosh beige
    color("#E3D9C8") base_model();
    color("#D9CFBD") translate([0, 0, base_h]) top_lid();
}
else if (part == 1) {
    // Bottom Base only (Print orientation: flat on bed)
    base_model();
}
else if (part == 2) {
    // Top Lid only (Print orientation: top lip flat or upside down)
    rotate([180, 0, 0]) translate([0, -case_d, -lid_h - lip_h]) top_lid();
}
else if (part == 3) {
    // Exploded view
    color("#E3D9C8") base_model();
    color("#D9CFBD") translate([0, 0, base_h + 22]) top_lid();
}
