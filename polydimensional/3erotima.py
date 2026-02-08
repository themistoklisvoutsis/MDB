import pandas as pd
import matplotlib.pyplot as plt


df=pd.read_csv("movies_metadata.csv", low_memory=False)
# εδω κραταω μονο αυτα που χρειαζομαι απο το csv
df=df[["id","title","budget","popularity"]]

#μετατροπη σε αριθμους 
df["budget"]= pd.to_numeric(df["budget"],errors="coerce")
df["popularity"]= pd.to_numeric(df["popularity"],errors="coerce")

#katharisma
df=df.dropna()
df=df[(df["budget"]>0)& (df["popularity"]>0)]

print("Σημεια P1:", len(df))

plt.scatter(df["budget"],df["popularity"],s=2)
plt.xlabel("Budget")
plt.ylabel("Popularity")
plt.title("Movies: Budget vs Popularity")
plt.show()


#convex hull

points =list(zip(df["budget"].tolist(),df["popularity"].tolist()))
def cross(o,a,b):
    return(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])

def convex_hull(points):
    points=sorted(set(points))
    if len(points)<=1:
        return points
    lower=[]
    for p in points:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:
            lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(points):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:
            upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]
hull=convex_hull(points)
print("Hull size:",len(hull))
hull_set = set(hull)  # hull = λίστα (budget, popularity)

hull_movies = df[df.apply(lambda r: (r["budget"], r["popularity"]) in hull_set, axis=1)]
print(hull_movies[["title", "budget", "popularity"]].head(20))



points= list(zip(df["budget"].tolist(),df["popularity"].tolist()))

def skyline_2d(points):
    points = sorted(points, key=lambda x:x[0])
    skyline=[]
    max_pop=-1

    for b, p in points:
        if p> max_pop:
            skyline.append((b,p))
            max_pop=p
    return skyline


sky=skyline_2d(points)
print("Skyline size:", len(sky))
sky_set = set(sky)
sky_movies = df[df.apply(lambda r: (r["budget"], r["popularity"]) in sky_set, axis=1)]
print(sky_movies[["title", "budget", "popularity"]].sort_values(["budget","popularity"]).head(30))


def skyline_bruteforce(points):
    skyline=[]
    n=len(points)
    for i in range(n):
        bi , pi = points[i]
        dominated = False
        for j in range(n):
            if i==j:
                continue
            bj,pj=points[j]
            if (bj<=bi and pj>=pi)and (bj<bi or pj>pi):
                dominated=True
                break
            if not dominated:
                skyline.append((bi,pi))
    return skyline

sample = points[:1000]

sky_fast = skyline_2d(sample)
sky_slow = skyline_bruteforce(sample)

print("fast:", len(sky_fast), "slow:", len(sky_slow), "equal sets:", set(sky_fast)==set(sky_slow))
