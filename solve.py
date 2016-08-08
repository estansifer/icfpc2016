import os
import os.path
import time
import random

import helper
import sil

now = time.monotonic

def priority(xy):
    return (2 * xy[0] - 1) ** 2 + (2 * xy[1] - 1) ** 2

class Edge:
    def __init__(self, facet, index):
        self.facet = facet
        self.index = index
        self.a = facet.points[index]
        self.b = facet.points[(index + 1) % facet.n]
        self.ta = facet.transform_inv.map(self.a[0], self.a[1])
        self.tb = facet.transform_inv.map(self.b[0], self.b[1])
        self.midpoint = ((self.a[0] + self.b[0]) / 2, (self.a[1] + self.b[1]) / 2)
        self.priority = max(priority(self.a), priority(self.b))

class SourceFacet:
    def __init__(self, target, transform):
        self.target = target
        self.transform = transform
        self.transform_inv = transform.inverse()
        self.n = len(target.points)
        self.points = []
        for point, _ in target.points:
            self.points.append(transform.map(point.x, point.y))
        self.area = self.compute_area()

    def make_edges(self):
        return [Edge(self, i) for i in range(self.n)]

    def compute_area(self):
        a = 0
        for i in range(self.n):
            p = self.points[i]
            q = self.points[(i + 1) % self.n]
            a += p[0] * q[1] - p[1] * q[0]
        return abs(a) / 2

class PartialSolution:
    def __init__(self, problem):
        self.closed_edges = []
        self.open_edges = []
        self.facets = []
        self.problem = problem
        self.area = 0
        self.targetted_facets = set()

    def next_edge(self):
        return max(self.open_edges, key = lambda e : e.priority)

    def in_interior(self, xy):
        interior = False
        x, y = xy
        for e in self.closed_edges + self.open_edges:
            x1, y1 = e.a
            x2, y2 = e.b
            ys = (y1 - y) * (y2 - y)
            if ys == 0:
                if y1 < y or y2 < y:
                    interior = not interior
            elif ys < 0:
                x_ = x1 + (x2 - x1) * (y - y1) / (y2 - y1)
                if x_ > x:
                    interior = not interior

        return interior

    def is_done(self):
        return self.area == 1

    # Returns a new PartialSolution, does not modify the existing one
    # Returns None if it doesn't work
    def extend_if_possible(self, facet):
        # print("Extending...")
        # Check if any part of the new facet leaves the box
        for x, y in facet.points:
            if x < 0 or x > 1 or y < 0 or y > 1:
                return None

        # Remove any edges that lie on the boundary
        new = PartialSolution(self.problem)
        new.closed_edges = list(self.closed_edges)
        new.open_edges = list(self.open_edges)
        new.facets = list(self.facets)
        fe = facet.make_edges()

        for e in list(fe):
            m = e.midpoint
            if m[0] == 0 or m[0] == 1 or m[1] == 0 or m[1] == 1:
                fe.remove(e)
                new.closed_edges.append(e)

        # Check if any edge of the new facet has an interior inside the existing solution
        for e in fe:
            if self.in_interior(e.midpoint):
                return None

        # Check if any edge of the new facet intersects badly the existing solution
        for e in fe:
            for e2 in self.open_edges:
                if helper.intersect(e.a, e.b, e2.a, e2.b):
                    return None

        # For each intersection check if the transforms are consistent, and remove any
        # finished edges

        for e in list(fe):
            for e2 in self.open_edges:
                if e.a == e2.a:
                    if e.ta != e2.ta:
                        return None
                if e.a == e2.b:
                    if e.ta != e2.tb:
                        return None
                if e.b == e2.a:
                    if e.tb != e2.ta:
                        return None
                if e.b == e2.b:
                    if e.tb != e2.tb:
                        return None
                if (e.a == e2.a and e.b == e2.b) or (e.a == e2.b and e.b == e2.a):
                    new.open_edges.remove(e2)
                    fe.remove(e)

        # Add edges to existing lists
        new.open_edges.extend(fe)
        new.facets.append(facet)
        new.targetted_facets = set(self.targetted_facets)
        new.targetted_facets.add(facet.target)
        new.area = self.area + facet.area

        if new.area > 1:
            # This really shouldn't be necessary :(
            print ("G")
            return None

        # Are we done?
        if new.is_done():
            # Check that there are not any unmatched edges
            if len(new.open_edges) > 0:
                # print("Extra edges")
                return None
            # we also need to check if there are any target facets we never used
            for tf in self.problem.skeleton.facets:
                if tf not in new.targetted_facets:
                    # print(len(new.targetted_facets))
                    # print(len(self.problem.skeleton.facets))
                    # print("Missing facets")
                    return None

        # print("    Successful")
        return new

    def candidate_new_facets(self):
        edge = self.next_edge()

        f = edge.facet
        i = edge.index
        t = f.transform

        t1 = t.compose(helper.Transform.flipedge(edge.a[0], edge.a[1], edge.b[0], edge.b[1]))
        f1 = SourceFacet(f.target, t1)

        p, j = f.target.points[i]
        if t.flip:
            tf = p.facets[(j - 1 + len(p.facets)) % len(p.facets)]
        else:
            tf = p.facets[(j + 1) % len(p.facets)]

        if tf.interior:
            f2 = SourceFacet(tf, t)
            return [f1, f2]
        else:
            return [f1]

    def candidate_starting_facets(self):
        facets = []
        for p in self.problem.skeleton.points:
            for e, _ in p.edges:
                if e.rational:
                    if e.left.interior:
                        t = helper.Transform.base(e)
                        t = helper.Transform.baseflipped(e)
                        facets.append(SourceFacet(e.left, helper.Transform.base(e)))
                        facets.append(SourceFacet(e.left, helper.Transform.baseflipped(e)))
        return facets

    def print_solution(self, filename):
        points = set()
        for facet in self.facets:
            n = len(facet.points)
            for i in range(n):
                p = facet.points[i]
                points.add((p, facet.transform_inv.map(p[0], p[1])))
        points = list(points)

        fs = []
        for facet in self.facets:
            f = []
            for p in facet.points:
                for i, q in enumerate(points):
                    if p == q[0]:
                        f.append(i)
                        break
            fs.append(f)

        with open(filename, 'w') as f_:
            f_.write(str(len(points)))
            f_.write('\n')
            for point, _ in points:
                f_.write(str(point[0]) + ',' + str(point[1]))
                f_.write('\n')
            f_.write(str(len(fs)))
            f_.write('\n')
            for f in fs:
                f_.write(str(len(f)))
                for i in f:
                    f_.write(' ')
                    f_.write(str(i))
                f_.write('\n')
            for _, point in points:
                f_.write(str(point[0]) + ',' + str(point[1]))
                f_.write('\n')

def solve(problem, timelimit = 5):
    start = now()

    stack = []
    ps = PartialSolution(problem)
    for facet in ps.candidate_starting_facets():
        ps_ = ps.extend_if_possible(facet)
        if ps_ is not None:
            stack.append(ps_)

    while len(stack) > 0:
        ps = stack.pop()
        # print(len(stack), ps.area, len(ps.facets), len(ps.open_edges))
        # for oe in ps.open_edges:
            # print("    ", oe.a, oe.b)

        if ps.is_done():
            return ps

        fs = ps.candidate_new_facets()

        if len(fs) > 1:
            cur = now()
            if cur - start > timelimit:
                return -1

        for f in fs:
            ps_ = ps.extend_if_possible(f)
            if ps_ is not None:
                stack.append(ps_)
    return None

def unsolved_pids():
    xs = os.listdir("problems")
    ys = set(os.listdir("solutions"))
    zs = set(os.listdir("failed"))

    res = []
    for x in xs:
        if (x not in ys) and (x not in zs):
            res.append(int(x))
    return sorted(res)

if __name__ == "__main__":
    pids = unsolved_pids()
    random.shuffle(pids)
    for pid in pids:
        if os.path.isfile("solutions/" + str(pid)) or os.path.isfile("failed/" + str(pid)):
            continue

        print ("Solving problem " + str(pid))
        x = solve(sil.Problem.read_by_pid(pid))
        if x == -1:
            print ("Out of time")
            open("failed/" + str(pid), 'a')
        elif x is None:
            print ("No solution???")
            open("failed/" + str(pid), 'a')
        else:
            print ("Success!")
            x.print_solution("solutions/" + str(pid))
