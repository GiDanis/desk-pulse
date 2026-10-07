$fn = 50;

case_w = 104.0;
case_d = 77.0;
corner_r = 3.5;

// Hagibis cradle dimensions
cradle_w = 99.6;
cradle_d = 72.6;
cradle_r = 3.0;
cradle_depth = 2.5;

// Tilt specs
tilt_angle = 6.0;
h_front_floor = 4.0; // Floor of the cradle at the very front (Y=0)
h_front_rim = h_front_floor + cradle_depth; // 6.5mm

wall_t = 2.0;
front_wall_t = 2.8;

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

module top_lid_inclined() {
    difference() {
        union() {
            // Main solid rounded block (tall enough to be sliced by 6-deg plane)
            rounded_box(case_w, case_d, 25.0, corner_r);

            // Male alignment lip sliding into base
            translate([wall_t - 0.6, front_wall_t - 0.6, -2.2])
                difference() {
                    rounded_box(case_w - 2*(wall_t - 0.6), case_d - wall_t - front_wall_t + 2*0.6, 2.2, corner_r - 0.8);
                    translate([wall_t, wall_t, -0.5])
                        rounded_box(case_w - 2*(wall_t - 0.6) - 2*wall_t, case_d - wall_t - front_wall_t + 2*0.6 - 2*wall_t, 3.0, corner_r - 1.5);
                }
        }

        // 1. Cut the top surface to the 6-degree inclined rim plane
        translate([0, 0, h_front_rim])
            rotate([-tilt_angle, 0, 0])
            translate([-10, -10, 0])
            cube([case_w + 20, case_d * 2, 40]);

        // 2. Cut the recessed cradle for the Hagibis dock (tilted at 6 degrees)
        // Centered: margin = (104 - 99.6)/2 = 2.2mm
        cradle_x = (case_w - cradle_w) / 2;
        cradle_y = (case_d - cradle_d) / 2;
        
        // We cut the pocket tilted at 6 degrees starting from h_front_floor
        translate([cradle_x, 0, h_front_floor])
            rotate([-tilt_angle, 0, 0])
            translate([0, cradle_y, 0])
            rounded_box(cradle_w, cradle_d, 30.0, cradle_r);

        // 3. Rear Cable Pass Notch (U-shaped notch on the rear rim)
        translate([case_w/2, case_d, h_front_rim + case_d*tan(tilt_angle) - 1.0])
            cube([26.0, 10.0, 6.0], center=true);

        // 4. Screw pilot holes (4 corners for M2.5)
        for (pos = [
            [wall_t + 4.0, front_wall_t + 4.0],
            [case_w - wall_t - 4.0, front_wall_t + 4.0],
            [case_w - wall_t - 4.0, case_d - wall_t - 4.5],
            [wall_t + 3.5, case_d - wall_t - 4.5]
        ]) {
            translate([pos[0], pos[1], -3])
                cylinder(d=2.3, h=10);
        }
    }
}

top_lid_inclined();
