#!/usr/bin/env python3
"""Write KiCad project (.kicad_pro with net classes) and custom DRC rules (.kicad_dru) for a board basename."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import LINE_NETS, POWER_NETS

def write(base):
    def nc(name, clr, tw):
        return {"name": name, "clearance": clr, "track_width": tw, "via_diameter": 1.6, "via_drill": 0.8,
                "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_width": 0.6, "diff_pair_gap": 0.4,
                "diff_pair_via_gap": 0.4, "wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
                "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647 if name == "Default" else 0}
    pro = {
      "board": {"design_settings": {
          "defaults": {}, "diff_pair_dimensions": [], "drc_exclusions": [],
          "rules": {"min_clearance": 0.4, "min_track_width": 0.6, "min_through_hole_diameter": 0.8,
                    "min_hole_clearance": 0.25, "min_copper_edge_clearance": 0.5, "min_via_diameter": 1.6,
                    "min_via_annular_width": 0.3, "min_hole_to_hole": 0.25, "min_microvia_diameter": 0.2,
                    "min_microvia_drill": 0.1, "min_silk_clearance": 0.0, "min_text_height": 0.8,
                    "min_text_thickness": 0.08, "solder_mask_to_copper_clearance": 0.0},
          "rule_severities": {"silk_overlap": "ignore", "silk_over_copper": "ignore", "silk_edge_clearance": "ignore",
                              "courtyards_overlap": "warning", "lib_footprint_issues": "ignore", "lib_footprint_mismatch": "ignore",
                              "footprint_type_mismatch": "ignore", "text_height": "ignore", "text_thickness": "ignore",
                              "missing_courtyard": "ignore", "npth_inside_courtyard": "ignore", "pth_inside_courtyard": "ignore",
                              "padstack": "ignore", "isolated_copper": "warning", "starved_thermal": "warning"},
          "track_widths": [0.0, 0.6, 0.8, 1.0], "via_dimensions": [], "zones_allow_external_fillets": False}},
      "meta": {"filename": os.path.basename(base) + ".kicad_pro", "version": 3},
      "net_settings": {"classes": [nc("Default", 0.4, 0.6), nc("PWR", 0.4, 1.0), nc("LINE", 0.5, 1.0)],
                       "meta": {"version": 4},
                       "netclass_patterns": [{"netclass": "LINE", "pattern": n} for n in LINE_NETS] +
                                            [{"netclass": "PWR", "pattern": n} for n in POWER_NETS]},
      "pcbnew": {"page_layout_descr_file": ""},
    }
    json.dump(pro, open(base + ".kicad_pro", "w"), indent=2)
    dru = '''(version 1)
# Domofon - reguly pod frezowanie V 30 deg / 0,2 mm
(rule "izolacja_galwaniczna"
  (constraint clearance (min 4.0mm))
  (condition "A.NetClass == 'LINE' && B.NetClass != 'LINE' && B.Type != 'Text'"))
(rule "track_min_signal"
  (layer B.Cu)
  (condition "A.Type == 'Track' && A.NetClass == 'Default'")
  (constraint track_width (min 0.6mm)))
(rule "track_min_power"
  (condition "A.Type == 'Track' && A.NetClass == 'PWR'")
  (constraint track_width (min 1.0mm)))
(rule "track_min_line"
  (condition "A.Type == 'Track' && A.NetClass == 'LINE'")
  (constraint track_width (min 1.0mm)))
'''
    open(base + ".kicad_dru", "w").write(dru)

if __name__ == '__main__':
    write(sys.argv[1])
