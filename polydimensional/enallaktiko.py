import os
import time
import datetime
import pickle
from rtree import index
from pathlib import Path


# =====================================
# Constants
# =====================================
DT_FORMAT = "%Y-%m-%d %H:%M:%S"
INDEX_NAME = "trajectory_index"
MAP_FILE = "trajectory_map.pkl"


# =====================================
# Safe input helpers
# =====================================
def safe_float(prompt):
    while True:
        val = input(prompt).strip()
        if val == "":
            print("❌ Empty value not allowed.")
            continue
        try:
            return float(val)
        except ValueError:
            print("❌ Invalid number.")


def safe_datetime(prompt):
    while True:
        val = input(prompt).strip()
        try:
            return datetime.datetime.strptime(val, DT_FORMAT)
        except:
            print("❌ Format: YYYY-MM-DD HH:MM:SS")


# =====================================
# Index existence check
# =====================================
def index_exists(name):
    return os.path.exists(name + ".dat") and os.path.exists(name + ".idx")


# =====================================
# Save / Load trajectory map
# =====================================
def save_trajectory_map(data):
    with open(MAP_FILE, "wb") as f:
        pickle.dump(data, f)


def load_trajectory_map():
    with open(MAP_FILE, "rb") as f:
        return pickle.load(f)


# =====================================
# Delete corrupted index files
# =====================================
def delete_index_files():
    for ext in [".dat", ".idx"]:
        fname = INDEX_NAME + ext
        if os.path.exists(fname):
            os.remove(fname)

    if os.path.exists(MAP_FILE):
        os.remove(MAP_FILE)


# =====================================
# Build R-tree (one-time)
# =====================================
def build_rtree(plt_files):

    p = index.Property()
    p.dimension = 3

    idx = index.Index(INDEX_NAME, properties=p, overwrite=True)

    trajectory_files = {}
    trajectory_id = 0

    print("\n⚙️ Building R-tree (first time)...")

    for filepath in plt_files:

        try:
            with open(filepath, "r") as f:

                for _ in range(6):
                    next(f)

                lats, lons, times = [], [], []

                for line in f:

                    parts = line.strip().split(",")

                    lat = float(parts[0])
                    lon = float(parts[1])

                    dt = datetime.datetime.strptime(
                        parts[5] + " " + parts[6],
                        DT_FORMAT
                    )

                    t = dt.timestamp()

                    lats.append(lat)
                    lons.append(lon)
                    times.append(t)

                if not lats:
                    continue

                bbox = (
                    min(lons),
                    min(lats),
                    min(times),
                    max(lons),
                    max(lats),
                    max(times)
                )

                idx.insert(trajectory_id, bbox)

                trajectory_files[trajectory_id] = filepath

                trajectory_id += 1

        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    save_trajectory_map(trajectory_files)

    print(f"✅ Indexed {trajectory_id} trajectories")

    return idx, trajectory_files


# =====================================
# R-tree Query
# =====================================
def people_per_box(idx, trajectory_files):

    print("\n--- Enter Query Parameters (R-tree) ---")

    x1 = safe_float("Enter x1 (longitude min): ")
    x2 = safe_float("Enter x2 (longitude max): ")
    y1 = safe_float("Enter y1 (latitude min): ")
    y2 = safe_float("Enter y2 (latitude max): ")

    t1 = safe_datetime("Enter start time: ").timestamp()
    t2 = safe_datetime("Enter end time: ").timestamp()

    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    t1, t2 = min(t1, t2), max(t1, t2)

    start_time = time.perf_counter()

    query_box = (x1, y1, t1, x2, y2, t2)

    candidate_ids = list(idx.intersection(query_box))

    matches = set()

    for traj_id in candidate_ids:

        filepath = trajectory_files[traj_id]

        try:
            with open(filepath, "r") as f:

                for _ in range(6):
                    next(f)

                for line in f:

                    parts = line.strip().split(",")

                    lat = float(parts[0])
                    lon = float(parts[1])

                    dt = datetime.datetime.strptime(
                        parts[5] + " " + parts[6],
                        DT_FORMAT
                    )

                    t = dt.timestamp()

                    if x1 <= lon <= x2 and y1 <= lat <= y2 and t1 <= t <= t2:
                        matches.add(traj_id)
                        break

        except:
            continue

    total_time = time.perf_counter() - start_time

    print("\n==============================")
    print(f"Candidates (R-tree): {len(candidate_ids)}")
    print(f"Final matches: {len(matches)}")
    print("==============================")

    if matches:

        print("Matching users:")

        for tid in matches:

            p = Path(trajectory_files[tid])
            user_folder = p.parts[-3]

            print(user_folder)

    else:
        print("No matching trajectories.")

    print(f"Finished in {total_time:.4f} seconds")


# =====================================
# Brute Force Query
# =====================================
def people_per_box_bruteforce(plt_files):

    print("\n--- Enter Query Parameters (Brute Force) ---")

    x1 = safe_float("Enter x1 (longitude min): ")
    x2 = safe_float("Enter x2 (longitude max): ")
    y1 = safe_float("Enter y1 (latitude min): ")
    y2 = safe_float("Enter y2 (latitude max): ")

    t1 = safe_datetime("Enter start time: ").timestamp()
    t2 = safe_datetime("Enter end time: ").timestamp()

    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    t1, t2 = min(t1, t2), max(t1, t2)

    start_time = time.perf_counter()

    matches = set()

    for filepath in plt_files:

        try:
            with open(filepath, "r") as f:

                for _ in range(6):
                    next(f)

                for line in f:

                    parts = line.strip().split(",")

                    lat = float(parts[0])
                    lon = float(parts[1])

                    dt = datetime.datetime.strptime(
                        parts[5] + " " + parts[6],
                        DT_FORMAT
                    )

                    t = dt.timestamp()

                    if x1 <= lon <= x2 and y1 <= lat <= y2 and t1 <= t <= t2:
                        matches.add(filepath)
                        break

        except:
            continue

    total_time = time.perf_counter() - start_time

    print("\n==============================")
    print(f"Brute Force Matches: {len(matches)}")
    print("==============================")

    if matches:

        print("Matching users:")

        for path in matches:

            p = Path(path)
            user_folder = p.parts[-3]

            print(user_folder)

    else:
        print("No matching trajectories.")

    print(f"Finished in {total_time:.4f} seconds")


# =====================================
# Menu
# =====================================
def main_menu(idx, trajectory_files, plt_files):

    while True:

        print("\n========== MENU ==========")
        print("1. People per box (R-tree)")
        print("2. People per box (Brute Force)")
        print("3. Exit")
        print("==========================")

        choice = input("\nChoose option: ").strip()

        if choice == "1":
            people_per_box(idx, trajectory_files)

        elif choice == "2":
            people_per_box_bruteforce(plt_files)

        elif choice == "3":
            print("Closing program safely...")
            break

        else:
            print("Invalid option.")


# =====================================
# Get all .plt files
# =====================================
def get_all_plt_files(root_folder):

    plt_files = []

    for root, _, files in os.walk(root_folder):

        for file in files:

            if file.lower().endswith(".plt"):
                plt_files.append(os.path.join(root, file))

    return plt_files


# =====================================
# Main
# =====================================
def main():

    root_folder = "C:\\lesson02\\Geolife Trajectories 1.3\\Data"

    if not os.path.exists(root_folder):

        print("❌ Folder not found.")
        return

    print("Scanning for .plt files...")

    plt_files = get_all_plt_files(root_folder)

    print(f"Found {len(plt_files)} trajectory files")

    if not plt_files:
        return

    idx = None
    trajectory_files = None


    if index_exists(INDEX_NAME) and os.path.exists(MAP_FILE):

        print("📂 Trying to load existing R-tree...")

        try:

            p = index.Property()
            p.dimension = 3

            idx = index.Index(INDEX_NAME, properties=p)

            trajectory_files = load_trajectory_map()

            list(idx.intersection((0, 0, 0, 1, 1, 1)))

            print("✅ Index loaded successfully.")

        except Exception as e:

            print("⚠️ Corrupted index. Rebuilding...")
            print("Reason:", e)

            delete_index_files()

            idx, trajectory_files = build_rtree(plt_files)

    else:

        print("⚙️ No index found. Building new one...")

        idx, trajectory_files = build_rtree(plt_files)


    try:
        main_menu(idx, trajectory_files, plt_files)

    finally:

        if idx:
            print("Closing index...")
            idx.close()



# =====================================
# Run
# =====================================
if __name__ == "__main__":
    main()