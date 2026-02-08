from intervaltree import Interval, IntervalTree
import random
import time
import math
import pandas as pd

# Stabbing queries : δίνεται ένα σημείο στον άξονα (έστω x). Ζητούμενο είναι να βρούμε ποια είναι τα διαστήματα τα οποία περιέχουν το σημείο x.
# Interval queries : ζητάμε ποιά intervals τέμνουν το [a,b]

def interval_tree_experiments(n):
    tree = IntervalTree() # δημιουργία άδειου IntervalTree

    intervals = set()
    
    # Δημιουργία n τυχαίων intervals
    start1 = time.perf_counter()
    while len(intervals) < n:
        low = random.randint(0, 10**7)
        high = low + random.randint(1, 50)

        if(low, high) not in intervals:
            tree.addi(low, high)
            intervals.add((low, high))
    end1 = time.perf_counter()

    avg_insert_time = (end1 - start1) / n


    start2 = time.perf_counter() # έναρξη μέτρησης χρόνου για stabbing queries
    for _ in range(500000): # 500.000 queries
        point = random.randint(0, 10**7)
        tree.at(point) # Βρες όλα τα διαστήματα που περιέχουν το σημείο
    end2 = time.perf_counter() # τέλος μέτρησης χρόνου για stabbing queries

    avg_stabbingtime = (end2 - start2) / 500000


    

    start3 = time.perf_counter() # έναρξη μέτρησης χρόνου για interval queries
    for _ in range(500000): # 500.000 queries
        a = random.randint(0, 10**7)
        b = a + random.randint(1, 100)
        tree.overlap(a, b) 
    end3 = time.perf_counter() # τέλος μέτρησης χρόνου για stabbing queries

    avg_intervaltime = (end3 - start3) / 500000


    # Διαγραφή n τυχαίων intervals
    start4 = time.perf_counter()
    for low, high in intervals:
        tree.removei(low, high)
    end4 = time.perf_counter()

    avg_delete_time = (end4 - start4) / n

    return avg_stabbingtime, avg_insert_time, avg_delete_time, avg_intervaltime


# Δημιουργία Segment tree 
class SegmentTree:
    def __init__(self, low, high):
        self.low = low
        self.high = high
        self.intervals = []
        self.left = None
        self.right = None

    def insert(self, l, r):
        mid = (self.low + self.high) // 2

        if l <= mid <= r:
            self.intervals.append((l, r))
            return

        if not self.left:
            self.left = SegmentTree(self.low, mid)
            self.right = SegmentTree(mid + 1, self.high)

        if r < mid:
            self.left.insert(l, r)
        else:
            self.right.insert(l, r)


    def stabbing_query(self, point, result):
        for l, r in self.intervals:
            if l <= point <= r:
                result.append((l, r))

        if self.low == self.high:
            return

        mid = (self.low + self.high) // 2

        if point <= mid and self.left:
            self.left.stabbing_query(point, result)
        elif point > mid and self.right:
            self.right.stabbing_query(point, result)


    def interval_query(self, l, r, result):
        mid = (self.low + self.high) // 2

        # Έλεγχος μόνο στα intervals του κόμβου
        for il, ir in self.intervals:
            if not (ir < l or il > r):
                result.append((il, ir))

        if self.low == self.high:
            return

        # Πηγαίνεις μόνο όπου χρειάζεται
        if l <= mid and self.left:
            self.left.interval_query(l, r, result)
        if r > mid and self.right:
            self.right.interval_query(l, r, result)



def segment_tree_experiments(n):
    MAX_RANGE = 10**7
    tree = SegmentTree(0, MAX_RANGE)

    intervals = set()

    # Insert
    start5 = time.perf_counter()
    while len(intervals) < n:
        low = random.randint(0, MAX_RANGE)
        high = low + random.randint(1, 50)

        if (low, high) not in intervals:
            tree.insert(low, high)
            intervals.add((low, high))
    end5 = time.perf_counter()

    avg_insert = (end5 - start5) / n

    # Stabbing queries
    start6 = time.perf_counter()
    for _ in range(500000):
        point = random.randint(0, MAX_RANGE)
        res = []
        tree.stabbing_query(point, res)
    end6 = time.perf_counter()

    avg_stab = (end6 - start6) / 500000

    # Interval queries
    start7 = time.perf_counter()
    for _ in range(500000):
        a = random.randint(0, MAX_RANGE)
        b = a + random.randint(1, 100)
        res = []
        tree.interval_query(a, b, res)
    end7 = time.perf_counter()

    avg_interval = (end7 - start7) / 500000

    return avg_stab, avg_insert, avg_interval


def interval_exp():
    sizes = [1000, 2000, 4000, 8000, 16000]
    rows = []

    for n in sizes:
        avg_stab, avg_ins, avg_dlt, avg_interval = interval_tree_experiments(n)

        rows.append({
            "Structure": "IntervalTree",
            "n": n,
            "log2(n)": math.log2(n),
            "Insert": avg_ins,
            "Delete": avg_dlt,
            "Stabbing": avg_stab,
            "Interval": avg_interval,
        })

    return rows


def segment_exp():
    sizes = [1000, 2000, 4000, 8000, 16000]
    rows = []

    for n in sizes:
        avg_stab, avg_ins, avg_interval = segment_tree_experiments(n)

        rows.append({
            "Structure": "SegmentTree",
            "n": n,
            "log2(n)": math.log2(n),
            "Insert": avg_ins,
            "Stabbing": avg_stab,
            "Interval": avg_interval,
        })

    return rows
        

def main():
    print("\nResults for stabbing queries, interval queries ,inserts, deletes:\n")

    interval_result = interval_exp()
    segment_result = segment_exp()

    df = pd.DataFrame(interval_result + segment_result)

    # Υπολογισμός time/log2(n)
    df["Insert/log"] = df["Insert"] / df["log2(n)"]
    df["Stabbing/log"] = df["Stabbing"] / df["log2(n)"]
    df["Interval/log"] = df["Interval"] / df["log2(n)"]

    # Στρογγυλοποίηση για καθαρή εκτύπωση
    print(df.round(8))


main() # Κλήση main