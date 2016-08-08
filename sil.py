import functools
import fractions
import gmpy2 # requires python 3.4

def _readcoord(s):
    x, y = s.strip().split(",")
    return (fractions.Fraction(x), fractions.Fraction(y))

# positive result if a comes after b
def arg_cmp(a, b):
    xs = a[0] * b[0]
    if xs < 0:
        return a[0] - b[0]
    elif xs > 0:
        return (a[1] * b[0]) - (b[1] * a[0])
    else:
        if a[0] == 0:
            a = 2 * int(a[1] < 0)
        else:
            a = 1 + 2 * int(a[0] > 0)
        if b[0] == 0:
            b = 2 * int(b[1] < 0)
        else:
            b = 1 + 2 * int(b[0] > 0)
        return a - b

def arg_key(xy):
    if xy[1] == 0:
        return (2 * int(xy[0] < 0), 0)
    else:
        return (1 + 2 * int(xy[1] < 0), -xy[0] / xy[1])

# Returns the intersection point of the line segments a-b and c-d or None
# if there is no intersection or if they are parallel
def _intersection(a, b, c, d):
    dax = b[0] - a[0]
    day = b[1] - a[1]
    dcx = d[0] - c[0]
    dcy = d[1] - c[1]

    denom = dax * dcy - day * dcx
    if denom == 0:
        # Line are parallel
        return None

    s = (-day * (a[0] - c[0]) + dax * (a[1] - c[1])) / denom
    t = ( dcx * (a[1] - c[1]) - dcy * (a[0] - c[0])) / denom
    if s >= 0 and s <= 1 and t >= 0 and t <= 1:
        return (a[0] + t * dax, a[1] + t * day)
    else:
        return None

class SkPoint:
    def __init__(self, xy):
        self.xy = xy
        self.x = xy[0]
        self.y = xy[1]

    def init2(self, neighbors):
        # Sorts neighbors in anticlockwise order, starting from positive x-axis
        vs = [(arg_key((n.x - self.x, n.y - self.y)), n) for n in neighbors]
        vs.sort()

        self.edges = []
        for i, v in enumerate(vs):
            edge = SkEdge()
            edge.near = (self, i)
            # edge.far, edge.left, and edge.right defined later
            self.edges.append((edge, v[1]))

        self.facets = [None] * len(neighbors)

    def init3(self):
        for e, p in self.edges:
            for j, a in enumerate(p.edges):
                if a[1] is self:
                    e.far = (p, j)
                    break
            e.init2()

    def init4(self):
        for i in range(len(self.edges)):
            if self.facets[i] is None:
                f = SkFacet()
                curpoint = self
                curindex = i
                points = []
                while len(points) == 0 or not (curpoint is self):
                    curpoint.facets[curindex] = f
                    e, p = curpoint.edges[curindex]
                    e.left = f
                    points.append((curpoint, curindex))

                    curpoint = p
                    curindex = e.far[1] - 1
                    if curindex < 0:
                        curindex += len(p.edges)
                f.points = points

class SkEdge:
    def __init__(self):
        pass

    def init2(self):
        f = self.length_sq()
        self.rational = gmpy2.is_square(f.numerator) and gmpy2.is_square(f.denominator)
        if self.rational:
            n = int(gmpy2.iroot(f.numerator, 2)[0])
            d = int(gmpy2.iroot(f.denominator, 2)[0])
            self.length = fractions.Fraction(n, d)

    def length_sq(self):
        p = self.near[0]
        q = self.far[0]
        return (p.x - q.x) ** 2 + (p.y - q.y) ** 2

class SkFacet:
    def __init__(self):
        pass

    def check_interior(self, polygons):
        if self.area() <= 0:
            self.interior = False
            return

        ys = set()
        for point, _ in self.points:
            ys.add(point.y)
        ys = sorted(ys)
        y = (ys[0] * 997 + ys[1] * 499) / (997 + 499)

        xs = set()
        for point, i in self.points:
            x1 = point.x
            y1 = point.y
            x2, y2 = point.edges[i][1].xy
            if (y1 - y) * (y2 - y) < 0:
                x = x1 + (x2 - x1) * (y - y1) / (y2 - y1)
                xs.add(x)
        xs = sorted(xs)
        x = (xs[0] + xs[1]) / 2

        # The point (x, y) is in the interior of the facet. We need to check if
        # it is in the interior of the main polygon.
        interior = False
        for polygon in polygons:
            for i in range(len(polygon)):
                x1, y1 = polygon[i]
                x2, y2 = polygon[(i + 1) % len(polygon)]
                if (y1 - y) * (y2 - y) < 0:
                    x_ = x1 + (x2 - x1) * (y - y1) / (y2 - y1)
                    if x_ > x:
                        interior = not interior

        self.interior = interior

    def area(self):
        a = 0
        n = len(self.points)
        for i in range(n):
            p = self.points[i][0]
            q = self.points[(i + 1) % n][0]
            a += p.x * q.y - p.y * q.x
        return a / 2

class Skeleton:
    def __init__(self, polygons, edges):
        # self.original = edges
        self.compute_points(polygons, edges)

    def compute_points(self, polygons, edges):
        xy2neighbors = {}
        for e1 in edges:
            xys = set()
            xys.add(e1[0])
            xys.add(e1[1])
            for e2 in edges:
                xy = _intersection(e1[0], e1[1], e2[0], e2[1])
                if xy is not None:
                    xys.add(xy)

            xys = sorted(xys)

            for i, xy in enumerate(xys):
                if xy not in xy2neighbors:
                    xy2neighbors[xy] = []
                if i > 0:
                    xy2neighbors[xy].append(xys[i - 1])
                if i + 1 < len(xys):
                    xy2neighbors[xy].append(xys[i + 1])

        points = []
        xy2point = {}
        for xy in xy2neighbors:
            point = SkPoint(xy)
            xy2point[xy] = point
            points.append(point)

        for point in points:
            point.init2([xy2point[xy] for xy in xy2neighbors[point.xy]])

        for point in points:
            point.init3()

        for point in points:
            point.init4()

        self.points = points

        all_facets = set()
        for point in points:
            for facet in point.facets:
                all_facets.add(facet)
        all_facets = list(all_facets)

        facets = []
        for facet in all_facets:
            facet.check_interior(polygons)
            if facet.interior:
                facets.append(facet)

        self.all_facets = all_facets
        self.facets = facets

class Problem:
    def __init__(self, polygons, skeleton):
        self.polygons = polygons
        self.raw_skeleton = skeleton
        self.skeleton = Skeleton(polygons, skeleton)

    def fromfile(filename):
        with open(filename) as f:
            polygons = []
            n = int(f.readline())
            for i in range(n):
                k = int(f.readline())
                polygon = []
                for j in range(k):
                    polygon.append(_readcoord(f.readline()))
                polygons.append(polygon)

            skeleton = []
            n = int(f.readline())
            for i in range(n):
                a, b = f.readline().split()
                skeleton.append((_readcoord(a), _readcoord(b)))

        return Problem(polygons, skeleton)

    def read_by_pid(pid):
        return Problem.fromfile("problems/" + str(pid))

    def area(self):
        a = 0
        for p in self.polygons:
            n = len(p)
            for i in range(n):
                j = (i + 1) % n
                a += p[i][0] * p[j][1] - p[i][1] * p[j][0]
        return a / 2

    def areas(self):
        a_ = []
        for p in self.polygons:
            a = 0
            n = len(p)
            for i in range(n):
                j = (i + 1) % n
                a += p[i][0] * p[j][1] - p[i][1] * p[j][0]
            a_.append(a / 2)
        return a_

    def bounds(self):
        xs = []
        ys = []
        for point in self.skeleton.points:
            xs.append(point.x)
            ys.append(point.y)
        return ((min(xs), max(xs)), (min(ys), max(ys)))
