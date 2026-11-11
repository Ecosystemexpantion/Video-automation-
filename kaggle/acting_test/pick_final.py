"""Copies the final (longest) render out of a Kaggle output folder. Usage: pick_final.py <dir> <dest.mp4>"""
import glob, os, shutil, sys

files = sorted(glob.glob(os.path.join(sys.argv[1], "**", "*.mp4"), recursive=True), key=os.path.basename)
if not files:
    sys.exit("No video produced")
shutil.copy(files[-1], sys.argv[2])
print("Final render:", os.path.basename(files[-1]), "of", len(files), "saved chunks")
