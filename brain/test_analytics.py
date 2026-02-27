from analytics import AnalyticsEngine
import json

e = AnalyticsEngine()
results = []
results.append(("GREAT DAY  (200min, 2dist, 90%acc, peak=10)", e.generate_report(200, 2, 90, 10)))
results.append(("AVERAGE    (120min, 5dist, 60%acc, peak=14)", e.generate_report(120, 5, 60, 14)))
results.append(("ROUGH DAY  ( 40min,12dist, 30%acc, peak=22)", e.generate_report(40, 12, 30, 22)))
results.append(("OVERWORKED (450min, 9dist, 70%acc, peak=23)", e.generate_report(450, 9, 70, 23)))
results.append(("ZERO       (  0min, 0dist,  0%acc, peak=12)", e.generate_report(0, 0, 0, 12)))

lines = []
for label, r in results:
    lines.append(f"{label} => {json.dumps(r)}")

with open("test_output.txt", "w") as f:
    f.write("\n".join(lines))
print("Written to test_output.txt")
