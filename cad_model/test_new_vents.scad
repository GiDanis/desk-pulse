$fn = 60;

case_w = 104.0;
case_d = 77.0;
base_h = 17.5;
corner_r = 3.5;
wall_t = 2.0;
front_wall_t = 2.8;
floor_t = 2.0;

pcb_w = 65.0;
pcb_d = 32.0;
pcb_x = 11.5;
pcb_y = case_d - wall_t - 32.0 - 0.5; // ~42.5mm

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

// --- 1. REFINED ARCHITECTURAL LOUVERED SIDE VENT ---
module architectural_side_vent(side="left") {
    // 3 precision horizontal slats nested inside an elegant recessed bezel
    x_pos = (side == "left") ? 0 : case_w;
    angle_dir = (side == "left") ? 35 : -35;
    
    translate([x_pos, case_d/2 - 2.0, 8.5]) {
        // Recessed shadow-line bezel (depth 0.8mm, rounded ends)
        rotate([0, 90, 0])
            hull() {
                r = 2.0;
                translate([-4.8 + r, -22.0 + r]) circle(r=r);
                translate([ 4.8 - r, -22.0 + r]) circle(r=r);
                translate([ 4.8 - r,  22.0 - r]) circle(r=r);
                translate([-4.8 + r,  22.0 - r]) circle(r=r);
            }
        
        // 3 horizontal louvers angled downward through the wall (35 degrees)
        for (i = [-1 : 1]) {
            translate([0, 0, i * 3.0])
                rotate([0, angle_dir, 0])
                rotate([0, 90, 0])
                hull() {
                    translate([0, -18.5]) cylinder(d=1.5, h=10, center=true);
                    translate([0,  18.5]) cylinder(d=1.5, h=10, center=true);
                }
        }
    }
}

// --- 2. HIGH-PERFORMANCE BOTTOM INTAKE GRILLE ---
module precision_bottom_intake() {
    // Recessed intake tray under CPU / Fan
    translate([pcb_x + 8, pcb_y + 4, -0.6])
        rounded_box(pcb_w - 16, pcb_d - 8, 1.0, 2.0);
    
    // Array of staggered racetrack ventilation slots
    // 6 columns x 4 rows
    for (col = [0 : 5]) {
        for (row = [0 : 3]) {
            slot_x = pcb_x + 13 + col * 6.2;
            slot_y = pcb_y + 8 + row * 4.6 + (col % 2) * 1.5;
            translate([slot_x, slot_y, -1])
                hull() {
                    translate([0, -1.2, 0]) cylinder(d=1.8, h=floor_t + 2);
                    translate([0,  1.2, 0]) cylinder(d=1.8, h=floor_t + 2);
                }
        }
    }
}

// --- 3. REAR EXHAUST VENTS ---
module rear_exhaust_vents() {
    // Zone right of USB-C 2 (X between 78 and 98)
    for (rz = [6.0, 9.5, 13.0]) {
        translate([87.0, case_d, rz])
            rotate([90, 0, 0])
            hull() {
                translate([-6.5, 0]) cylinder(d=1.6, h=3*wall_t, center=true);
                translate([ 6.5, 0]) cylinder(d=1.6, h=3*wall_t, center=true);
            }
    }
}

// Test render of the bottom base with these new vents
module test_base_with_vents() {
    difference() {
        rounded_box(case_w, case_d, base_h, corner_r);
        
        // Inner hollow cavity
        translate([wall_t, front_wall_t, floor_t])
            rounded_box(case_w - 2*wall_t, case_d - wall_t - front_wall_t, base_h + 1, corner_r - 1.0);
            
        // Left side vent
        architectural_side_vent(side="left");
        
        // Right side vent
        architectural_side_vent(side="right");
        
        // Bottom intake
        precision_bottom_intake();
        
        // Rear exhaust
        rear_exhaust_vents();
    }
}

test_base_with_vents();

