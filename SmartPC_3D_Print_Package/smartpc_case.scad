// ====================================================================
// SmartPC Case for Orange Pi Zero 3W with Active Cooler + Hagibis 3.5" IPS
// Unified Master Model: 104 x 77 mm Footprint, 6-Degree Incline Lid
// EXACTLY 3 MODELS:
//   1. smartpc_base_style1_classic.stl (Top 1 Clean Mac SE)
//   2. smartpc_base_style1_deluxe.stl  (SE/30 Studio Edition)
//   3. smartpc_lid_incline6deg.stl     (6-Degree Solid Wedge Drop-In Cradle)
// ====================================================================

// --- PART SELECTION ---
// 0 = Full Assembly Preview Classic
// 1 = Base Style 1 Classic (Export STL)
// 2 = Base Style 1 Deluxe (Export STL)
// 3 = Top Lid Incline 6-Degree (Export STL)
// 4 = Full Assembly Preview Deluxe with Hagibis Dock
// 5 = Exploded Assembly View
part = 0;

$fn = 60;

// --- EXTERNAL ENCLOSURE DIMENSIONS (104 x 77 mm) ---
case_w = 104.0;      // Outer Width (mm) - slightly larger than Hagibis (99mm)
case_d = 77.0;       // Outer Depth (mm) - slightly larger than Hagibis (72mm)
base_h = 17.5;       // Bottom Base Height (mm)
corner_r = 3.5;      // External Corner Radius
wall_t = 2.4;        // Reinforced Shell Wall Thickness (> 1.2mm everywhere, min 1.6mm at rebate/scoop)
front_wall_t = 3.2;  // Reinforced Front Wall Thickness (min 1.6mm at deepest relief)
floor_t = 2.5;       // Reinforced Bottom Floor Thickness (min 1.3mm at countersinks, min 1.7mm at feet)

// --- HAGIBIS DOCK DROP-IN CRADLE & 6-DEGREE INCLINE SPECS ---
cradle_w = 99.6;     // Hagibis dock width (99.0 + 0.6mm tolerance)
cradle_d = 72.6;     // Hagibis dock depth (72.0 + 0.6mm tolerance)
cradle_r = 3.0;      // Hagibis corner radius
cradle_depth = 2.2;  // Perimeter retention lip height ("ad incastro")

tilt_angle = 6.0;    // 6.0 degrees incline
delta_z = case_d * tan(tilt_angle); // ~8.09 mm slope height difference

ceiling_t = 2.2;       // Solid floor thickness under Hagibis ("coperchio intero", > 1.2mm)
rear_inner_h = 4.0;    // Internal clearance above heatsink at rear
z_floor_rear = rear_inner_h + ceiling_t; // 6.2 mm
z_rim_rear = z_floor_rear + cradle_depth; // 8.4 mm

z_floor_front = z_floor_rear + delta_z;  // ~14.29 mm (Front is HIGHER than Rear)
z_rim_front = z_rim_rear + delta_z;      // ~16.49 mm

cradle_x = (case_w - cradle_w) / 2; // 2.2 mm perimeter retention rim (> 1.2mm)
cradle_y = (case_d - cradle_d) / 2; // 2.2 mm perimeter retention rim (> 1.2mm)

// --- BASE & LID REINFORCED INTERLOCKING JOINT (Zero Thin Walls >= 1.5mm) ---
reb_x = 1.6;        // Base female rebate side/rear outer rim wall (1.6mm > 1.5mm)
reb_y_front = 2.4;  // Base female rebate front rim wall (2.4mm > 1.5mm)
reb_depth = 2.5;    // Base female rebate depth (mm)

lip_x = 1.85;       // Lid male lip side/rear offset (0.25mm sliding clearance from 1.6mm rim)
lip_y_front = 2.65; // Lid male lip front offset (0.25mm sliding clearance from 2.4mm rim)
lip_t = 1.5;        // Reinforced solid male lip wall thickness (1.5mm >= 1.5mm DFM standard!)
lip_h = 2.2;        // Lid male lip height (slides 2.2mm into 2.5mm rebate, 0.3mm vertical clearance)

cav_x = lip_x + lip_t;             // 3.35mm - lid inner cavity starts flush with inside of male lip
cav_y_front = lip_y_front + lip_t; // 4.15mm - lid front cavity starts flush with inside of male lip

// --- ORANGE PI ZERO 3W & HEATSINK SPECS ---
pcb_w = 65.0;
pcb_d = 32.0;
pcb_t = 1.6;
heatsink_h = 11.8;  // Official aluminum heatsink + 2006 fan height
standoff_h = 3.5;   // Standoff height for bottom components clearance

// Board Placement (Rear-aligned for direct port accessibility)
pcb_x = 11.5;
pcb_y = case_d - wall_t - pcb_d - 0.5; // Rear-aligned with wall

// 4x PCB Mounting Holes (58.0mm x 23.0mm spacing)
mount_holes = [
    [pcb_x + 3.5,  pcb_y + 4.5],   // Front-Left (GPIO side)
    [pcb_x + 61.5, pcb_y + 4.5],   // Front-Right (GPIO side)
    [pcb_x + 61.5, pcb_y + 27.5],  // Rear-Right (Ports side)
    [pcb_x + 3.5,  pcb_y + 27.5]   // Rear-Left (Ports side)
];

// Lid Fastening Posts (4 corners)
lid_posts = [
    [wall_t + 4.0, front_wall_t + 4.0],             // Front-Left
    [case_w - wall_t - 4.0, front_wall_t + 4.0],    // Front-Right
    [case_w - wall_t - 4.0, case_d - wall_t - 4.5], // Rear-Right
    [wall_t + 4.0, case_d - wall_t - 4.5]           // Rear-Left
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

module front_cut(w, h, depth) {
    translate([0, depth/2 - 0.05, 0]) cube([w, depth + 0.1, h], center=true);
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
    hull() {
        translate([0, -length_y/2 + r, -height_z/2 + r]) rotate([0, 90, 0]) cylinder(r=r, h=depth_x + 0.1, center=true);
        translate([0,  length_y/2 - r, -height_z/2 + r]) rotate([0, 90, 0]) cylinder(r=r, h=depth_x + 0.1, center=true);
        translate([0,  length_y/2 - r,  height_z/2 - r]) rotate([0, 90, 0]) cylinder(r=r, h=depth_x + 0.1, center=true);
        translate([0, -length_y/2 + r,  height_z/2 - r]) rotate([0, 90, 0]) cylinder(r=r, h=depth_x + 0.1, center=true);
    }
}

// ====================================================================
// MODULE: BASE COMMON CORE (Ports, Screws, Standoffs, Rebate)
// ====================================================================
module base_common_cutouts() {
    // Inner hollow cavity
    translate([wall_t, front_wall_t, floor_t])
        rounded_box(case_w - 2*wall_t, case_d - wall_t - front_wall_t, base_h + 1, corner_r - 1.0);

    // Female step rebate for lid male lip (1.6mm rim wall >= 1.5mm, 2.5mm deep)
    translate([reb_x, reb_y_front, base_h - reb_depth])
        rounded_box(case_w - 2*reb_x, case_d - reb_x - reb_y_front, reb_depth + 1, corner_r - 0.5);

    // --- REAR I/O PORTS ---
    // 1. Mini-HDMI (Center X = pcb_x + 12.4)
    translate([pcb_x + 12.4, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
        cube([11.8, 3*wall_t, 6.2], center=true);
        translate([0, wall_t/2 + 0.6, 0])
            cube([13.2, wall_t + 1, 7.8], center=true);
    }

    // 2. USB-C 1 - OTG (Center X = pcb_x + 41.4)
    translate([pcb_x + 41.4, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
        cube([10.5, 3*wall_t, 6.0], center=true);
        translate([0, wall_t/2 + 0.6, 0])
            cube([12.0, wall_t + 1, 7.5], center=true);
    }

    // 3. USB-C 2 - Host (Center X = pcb_x + 55.4)
    translate([pcb_x + 55.4, case_d, floor_t + standoff_h + pcb_t + 2.5]) {
        cube([10.5, 3*wall_t, 6.0], center=true);
        translate([0, wall_t/2 + 0.6, 0])
            cube([12.0, wall_t + 1, 7.5], center=true);
    }

    // --- 1. REAR EXHAUST VENTILATION (Thermal exhaust away from user) ---
    // Right exhaust bank (to the right of USB-C 2)
    for (rz = [5.5, 9.0, 12.5]) {
        translate([88.0, case_d, rz])
            rotate([90, 0, 0])
            hull() {
                translate([-6.5, 0]) cylinder(d=1.5, h=3*wall_t, center=true);
                translate([ 6.5, 0]) cylinder(d=1.5, h=3*wall_t, center=true);
            }
    }
    // Left exhaust bank (to the left of Mini-HDMI)
    for (rz = [5.5, 9.0, 12.5]) {
        translate([11.0, case_d, rz])
            rotate([90, 0, 0])
            hull() {
                translate([-4.0, 0]) cylinder(d=1.5, h=3*wall_t, center=true);
                translate([ 4.0, 0]) cylinder(d=1.5, h=3*wall_t, center=true);
            }
    }

    // --- 2. PRECISION BOTTOM INTAKE GRILLE (Under CPU & Active Cooler) ---
    // Recessed intake bay (depth 0.4mm into 2.5mm floor -> 2.1mm floor remaining)
    translate([pcb_x + 8, pcb_y + 4, -0.6])
        rounded_box(pcb_w - 16, pcb_d - 8, 1.0, 2.0);
    // Staggered precision racetrack intake matrix (6 cols x 4 rows)
    // Webbing: 1.8mm between rows, 4.4mm between cols (exceeds 0.8mm limit)
    for (col = [0 : 5]) {
        for (row = [0 : 3]) {
            slot_x = pcb_x + 13.0 + col * 6.2;
            slot_y = pcb_y + 8.0 + row * 5.4 + (col % 2) * 1.5;
            translate([slot_x, slot_y, -1])
                hull() {
                    translate([0, -0.9, 0]) cylinder(d=1.8, h=floor_t + 2);
                    translate([0,  0.9, 0]) cylinder(d=1.8, h=floor_t + 2);
                }
        }
    }

    // PCB screw holes (M2.5 countersunk from bottom, 1.2mm depth -> 1.3mm floor remaining > 1.2mm)
    for (pos = mount_holes) {
        translate([pos[0], pos[1], -1]) {
            cylinder(d=2.8, h=floor_t + standoff_h + 2);
            cylinder(d=5.4, h=1.2 + 1);
        }
    }

    // Lid fastening screw holes (M2.5 countersunk from bottom)
    // Coaxial with rubber foot pockets (Apple/Mac style: rubber feet conceal screws flush!)
    // Completely eliminates the 0.08mm overlap warning (DFM Point B)
    for (pos = lid_posts) {
        translate([pos[0], pos[1], -1]) {
            cylinder(d=2.8, h=base_h + 2);
            cylinder(d=5.4, h=0.8 + 1.2 + 1);
        }
        // Concentric rubber foot pocket: diameter 8.5mm, depth 0.8mm
        translate([pos[0], pos[1], -0.1])
            cylinder(d=8.5, h=0.8 + 0.1);
    }
}

module base_internal_pillars() {
    // PCB Standoff pillars (OD 5.6mm, ID 2.8mm -> wall thickness 1.4mm > 1.2mm)
    for (pos = mount_holes) {
        difference() {
            translate([pos[0], pos[1], floor_t]) cylinder(d=5.6, h=standoff_h);
            translate([pos[0], pos[1], floor_t - 0.5]) cylinder(d=2.8, h=standoff_h + 1);
        }
    }

    // Lid screw pillars (OD 8.8mm, ID 2.8mm, stops exactly at rebate shelf base_h - reb_depth)
    // Solid 3.0mm wall fully encases 8.5mm foot pockets and eliminates 0.58mm thin floor warning (Cindy Flag A)
    for (pos = lid_posts) {
        difference() {
            translate([pos[0], pos[1], floor_t]) cylinder(d=8.8, h=base_h - reb_depth - floor_t);
            translate([pos[0], pos[1], floor_t - 0.5]) cylinder(d=2.8, h=base_h + 1);
        }
    }
}

// Module for Architectural Louvered Side Grille
module louvered_side_grille(side="left", length=40.0, num_slats=4) {
    x_pos = (side == "left") ? 0 : case_w;
    angle_dir = (side == "left") ? 35 : -35;
    slat_pitch = 3.2;
    slat_cut_w = 1.3;
    total_h = (num_slats - 1) * slat_pitch + slat_cut_w; // Fin thickness between slats = 1.32mm > 1.2mm

    translate([x_pos, case_d/2 - 2.0, 8.5]) {
        // Recessed shadow-line architectural bezel (depth 0.6mm into 2.4mm wall -> 1.8mm wall remaining)
        rotate([0, 90, 0])
            linear_extrude(height=1.2, center=true)
            hull() {
                r = 2.0;
                translate([-total_h/2 - 1.2 + r, -length/2 - 1.5 + r]) circle(r=r);
                translate([ total_h/2 + 1.2 - r, -length/2 - 1.5 + r]) circle(r=r);
                translate([ total_h/2 + 1.2 - r,  length/2 + 1.5 - r]) circle(r=r);
                translate([-total_h/2 - 1.2 + r,  length/2 + 1.5 - r]) circle(r=r);
            }

        // Louver slats angled 35 degrees downward through the wall thickness
        for (i = [0 : num_slats - 1]) {
            z_offset = -total_h/2 + slat_cut_w/2 + i * slat_pitch;
            translate([0, 0, z_offset])
                rotate([0, angle_dir, 0])
                rotate([0, 90, 0])
                hull() {
                    translate([0, -length/2 + 0.8]) cylinder(d=slat_cut_w, h=10, center=true);
                    translate([0,  length/2 - 0.8]) cylinder(d=slat_cut_w, h=10, center=true);
                }
        }
    }
}

// ====================================================================
// MODEL 1: BASE STYLE 1 CLASSIC (Mac SE Clean - Top 1)
// ====================================================================
module smartpc_base_style1_classic() {
    difference() {
        rounded_box(case_w, case_d, base_h, corner_r);
        base_common_cutouts();

        // Front Face: Solid Retro Sculpted Relief Grooves (Zero through-holes!)
        for (i = [0:1]) {
            translate([case_w/2, 0, 5.0 + i*3.5])
                horizontal_capsule_cut(length=64.0, height=1.5, depth=1.4);
        }
        // Apple-style status pip recess (depth 0.8mm into 3.2mm front wall -> 2.4mm wall remaining)
        translate([16.0, 0.4, 5.0]) {
            rotate([90, 0, 0]) cylinder(d=2.2, h=0.8, center=true);
        }

        // Flanks: Architectural Louvered Grilles (4 precision downward slats)
        louvered_side_grille(side="left", length=42.0, num_slats=4);
        louvered_side_grille(side="right", length=42.0, num_slats=4);
    }
    base_internal_pillars();
}

// ====================================================================
// MODEL 2: BASE STYLE 1 DELUXE (SE/30 Studio Edition)
// ====================================================================
module smartpc_base_style1_deluxe() {
    difference() {
        rounded_box(case_w, case_d, base_h, corner_r);
        base_common_cutouts();


        // Front Face: Apple Logo / Vintage Rainbow Plaque Recess (Left, blind relief depth 0.8mm -> 2.4mm wall remaining)
        translate([11.0, 0.4, 3.6]) {
            rotate([90, 0, 0]) cylinder(d1=3.6, d2=2.4, h=0.8, center=true);
        }
        translate([15.5, 0.4, 3.6]) {
            front_cut(w=2.0, h=2.0, depth=0.8);
        }

        // Acoustic Speaker Dimple Matrix (2x4)
        for (rx = [0:1]) {
            for (rz = [0:3]) {
                translate([21.0 + rx*2.6, 0.5, 4.0 + rz*2.3])
                    rotate([90, 0, 0])
                    cylinder(d1=1.5, d2=0.4, h=1.2, center=true);
            }
        }

        // Deluxe SuperDrive Bay Assembly (Upper Right)
        // Spacing engineered with solid bridges >= 1.6mm (Eliminates Flag A: 0.30mm)
        translate([60.0, 0, 12.4]) {
            front_cut(w=36.0, h=2.0, depth=1.0);
            translate([-2.0, 0, 0]) front_cut(w=28.0, h=0.7, depth=1.2);
            // Tactile Eject Button with Thumb Dish
            translate([22.0, 0, 0]) {
                front_cut(w=3.2, h=2.2, depth=1.0);
                translate([0, 0.4, 0]) rotate([90, 0, 0]) cylinder(d=1.6, h=0.8, center=true);
            }
            // Drive Activity LED Lens
            translate([26.0, 0, 0]) front_cut(w=1.6, h=1.2, depth=0.8);
            // Emergency Manual Eject Pinhole
            translate([29.2, 0, 0]) rotate([90, 0, 0]) cylinder(d=1.2, h=2.0, center=true);
        }

        // Typographic Nameplate Recess ("SmartPC / 30")
        translate([60.0 - 4.0, 0, 9.6]) front_cut(w=34.0, h=1.6, depth=0.7);

        // Snow White Horizontal Ribs (3 lower ribs)
        for (i = [0:2]) {
            translate([60.0, 0, 3.2 + i*2.0])
                horizontal_capsule_cut(length=60.0, height=1.2, depth=1.4);
        }

        // Flanks: Ergonomic Recessed Carry Scoops with 3 Robust Angled Louvers
        // Scoop depth 0.6mm into 2.4mm wall -> 1.8mm wall remaining (> 1.5mm)
        // Louver fin thickness = 1.75mm solid resin (> 1.5mm DFM standard, Eliminates Flag B: 0.60mm)
        // Left Flank
        translate([0.3, case_d/2 - 2.0, 8.5])
            side_carry_scoop(length_y=46.0, height_z=12.0, depth_x=0.6, r=2.5);
        for (i = [-1, 0, 1]) {
            translate([0, case_d/2 - 2.0, 8.5 + i * 3.6])
                rotate([0, 35, 0])
                rotate([0, 90, 0])
                hull() {
                    translate([0, -15.0]) cylinder(d=1.2, h=3*wall_t, center=true);
                    translate([0,  15.0]) cylinder(d=1.2, h=3*wall_t, center=true);
                }
        }
        // Right Flank
        translate([case_w - 0.3, case_d/2 - 2.0, 8.5])
            side_carry_scoop(length_y=46.0, height_z=12.0, depth_x=0.6, r=2.5);
        for (i = [-1, 0, 1]) {
            translate([case_w, case_d/2 - 2.0, 8.5 + i * 3.6])
                rotate([0, -35, 0])
                rotate([0, 90, 0])
                hull() {
                    translate([0, -15.0]) cylinder(d=1.2, h=3*wall_t, center=true);
                    translate([0,  15.0]) cylinder(d=1.2, h=3*wall_t, center=true);
                }
        }
    }
    base_internal_pillars();
}

// ====================================================================
// MODEL 3: TOP LID 6-DEGREE INCLINE (Universal for Classic & Deluxe)
// (Solid Continuous Floor "Coperchio Intero" + Drop-In Cradle + Upper Vents)
// ====================================================================
module smartpc_lid_incline6deg() {
    difference() {
        union() {
            difference() {
                union() {
                    // 1. Main outer wedge body
                    intersection() {
                        rounded_box(case_w, case_d, z_rim_front + 10, corner_r);
                        
                        // Sloped cutting plane: Front (Y=0) is at z_rim_front, sloping down by 6 deg towards rear
                        translate([0, 0, z_rim_front])
                            rotate([-tilt_angle, 0, 0])
                            translate([-10, -10, -100])
                            cube([case_w + 20, case_d * 2, 100]);
                    }

                    // 2. Male alignment lip (slides 2.2mm down into base female rebate, solid 1.5mm wall >= 1.5mm)
                    // Eliminates the 0.60mm thin wall warning (DFM Point A)
                    translate([lip_x, lip_y_front, -lip_h])
                        difference() {
                            rounded_box(case_w - 2*lip_x, case_d - lip_x - lip_y_front, lip_h + 0.1, corner_r - 0.8);
                            translate([lip_t, lip_t, -0.5])
                                rounded_box(case_w - 2*lip_x - 2*lip_t, case_d - lip_x - lip_y_front - 2*lip_t, lip_h + 1, corner_r - 1.5);
                        }
                }

                // --- SUBTRACTIONS ---

                // 3. Hagibis Drop-In Cradle Pocket (2.2mm deep retention rim, perfectly fitted)
                translate([0, 0, z_rim_front])
                    rotate([-tilt_angle, 0, 0])
                    translate([cradle_x, cradle_y / cos(tilt_angle), -cradle_depth])
                    rounded_box(cradle_w, cradle_d / cos(tilt_angle), cradle_depth + 10, cradle_r);

                // 4. Internal Component Cavity: smooth continuous 1.5mm male lip into 3.35mm outer wall
                translate([cav_x, cav_y_front, 0.0])
                    intersection() {
                        rounded_box(case_w - 2*cav_x, case_d - cav_x - cav_y_front, 50, corner_r - 1.0);
                        
                        translate([-cav_x, -cav_y_front, z_rim_front - cradle_depth - ceiling_t])
                            rotate([-tilt_angle, 0, 0])
                            translate([-10, -10, -100])
                            cube([case_w + 20, case_d * 2, 100]);
                    }
            }

            // 5. Internal Corner Screw Bosses (Solid pillars anchoring directly to ceiling!)
            intersection() {
                for (pos = lid_posts) {
                    translate([pos[0], pos[1], -lip_h])
                        cylinder(d=6.5, h=z_rim_front + 5);
                }
                
                translate([0, 0, z_rim_front - cradle_depth - ceiling_t + 0.1])
                    rotate([-tilt_angle, 0, 0])
                    translate([-10, -10, -100])
                    cube([case_w + 20, case_d * 2, 100]);
            }
        }

        // 6. Upper Flank Ventilation Slats (2 matching slim louvers on each side, fin = 1.32mm)
        for (i = [0 : 1]) {
            // Left Flank (Cutter h=18.0mm cleanly penetrates 3.35mm wall, eliminates Cindy 0.32mm thin skin)
            translate([0, case_d/2 - 2.0, 4.2 + i * 3.0])
                rotate([0, 35, 0])
                rotate([0, 90, 0])
                hull() {
                    translate([0, -16.0]) cylinder(d=1.3, h=18.0, center=true);
                    translate([0,  16.0]) cylinder(d=1.3, h=18.0, center=true);
                }
            // Right Flank
            translate([case_w, case_d/2 - 2.0, 4.2 + i * 3.0])
                rotate([0, -35, 0])
                rotate([0, 90, 0])
                hull() {
                    translate([0, -16.0]) cylinder(d=1.3, h=18.0, center=true);
                    translate([0,  16.0]) cylinder(d=1.3, h=18.0, center=true);
                }
        }

        // 7. Upper Rear Exhaust Slat (Single wide slot at Z=2.4mm, leaves >3.1mm solid roof material)
        translate([52.0, case_d, 2.4])
            rotate([90, 0, 0])
            hull() {
                translate([-18.0, 0]) cylinder(d=1.4, h=18.0, center=true);
                translate([ 18.0, 0]) cylinder(d=1.4, h=18.0, center=true);
            }

        // 8. Blind Screw Pilot Holes for M2.5 (No holes on top surface!)
        // Front posts (taller): hole depth 7.5mm (stops at Z=4.5, ceiling is at Z=11.5)
        for (i = [0, 1]) {
            pos = lid_posts[i];
            translate([pos[0], pos[1], -lip_h - 0.5])
                cylinder(d=2.3, h=7.5);
        }
        // Rear posts (shorter): hole depth 4.2mm (stops at Z=1.2, ceiling is at Z=3.5)
        for (i = [2, 3]) {
            pos = lid_posts[i];
            translate([pos[0], pos[1], -lip_h - 0.5])
                cylinder(d=2.3, h=4.2);
        }
    }
}

// ====================================================================
// MOCKUP OF HAGIBIS 3.5" IPS DOCK
// ====================================================================
module hagibis_dock_mockup() {
    translate([cradle_x + 0.3, cradle_y + 0.3, base_h + z_rim_front - cradle_depth])
        rotate([-tilt_angle, 0, 0]) {
            // Main dark gray dock body
            color("#3E3E42") rounded_box(99.0, 72.0, 15.0, 3.0);
            // Upright monitor frame tilted slightly back
            color("#252528")
                translate([4.5, 6.0, 15.0])
                rotate([-8.0, 0, 0])
                cube([90.0, 14.0, 58.0]);
            // IPS Screen glass
            color("#42A5F5")
                translate([10.0, 5.0, 21.0])
                rotate([-8.0, 0, 0])
                cube([79.0, 1.2, 48.0]);
        }
}

// ====================================================================
// RENDER SELECTION
// ====================================================================
if (part == 0) {
    // Full Assembly: Classic Base + 6-deg Incline Lid + Hagibis Dock
    color("#E3D9C8") smartpc_base_style1_classic();
    color("#D9CFBD") translate([0, 0, base_h]) smartpc_lid_incline6deg();
    hagibis_dock_mockup();
}
else if (part == 1) {
    // STL Export: Base Style 1 Classic (Print flat on bed)
    smartpc_base_style1_classic();
}
else if (part == 2) {
    // STL Export: Base Style 1 Deluxe (Print flat on bed)
    smartpc_base_style1_deluxe();
}
else if (part == 3) {
    // STL Export: Top Lid Incline 6-Degree (Print flat on bed)
    smartpc_lid_incline6deg();
}
else if (part == 4) {
    // Full Assembly: Deluxe Base + 6-deg Incline Lid + Hagibis Dock
    color("#E3D9C8") smartpc_base_style1_deluxe();
    color("#D9CFBD") translate([0, 0, base_h]) smartpc_lid_incline6deg();
    hagibis_dock_mockup();
}
else if (part == 5) {
    // Exploded View
    color("#E3D9C8") smartpc_base_style1_classic();
    color("#D9CFBD") translate([0, 0, base_h + 22]) smartpc_lid_incline6deg();
    translate([0, 0, 42]) hagibis_dock_mockup();
}

