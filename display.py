import time
import os.path
import pygame
import collections

import sil
import solve

pixels = 600
pygame.init()
surface = pygame.display.set_mode((pixels, pixels))

c_black = pygame.Color(0, 0, 0)
c_poly = pygame.Color(0, 255, 0)
c_poly_int = pygame.Color(40, 40, 40)
c_skeleton = pygame.Color(255, 0, 0)

def print_info_about(p):
    s = p.skeleton
    print("Area:", float(p.area()))
    print("Number of facets:", len(s.facets))
    print("   plus exterior facets:", len(s.all_facets) - len(s.facets))
    print("Facet areas:", *[float(f.area()) for f in s.facets])
    print("Number of points in skeleton:", len(s.points))

    num_edges = 0
    edge_lengths = collections.Counter()
    total_length = 0
    num_rational = 0
    for p in s.points:
        num_edges += len(p.edges)
        for e, _ in p.edges:
            if e.rational:
                edge_lengths[e.length] += 1
                total_length += e.length
                num_rational += 1
    for l in edge_lengths:
        edge_lengths[l] = edge_lengths[l] // 2
    num_edges = num_edges // 2
    total_length = total_length / 2
    num_rational = num_rational // 2

    print("Number of edges in skeleton:", num_edges)
    print("Number of edges with rational edge length:", num_rational)
    print("Total length of edges with rational edge length:", float(total_length))

    el = edge_lengths.most_common()
    el = [(float(l), count) for l, count in el]
    print("Rational edge lengths:", *el)
    print()

def display(p):
    areas = p.areas()
    xs_, ys_ = p.bounds()

    dx = max(xs_[1] - xs_[0], ys_[1] - ys_[0])

    def tx(x):
        return int(pixels * (float((x - xs_[0]) / dx) + 0.25) / (3 / 2))
    def ty(y):
        return pixels - int(pixels * (float((y - ys_[0]) / dx) + 0.25) / (3 / 2))

    surface.fill(c_black)

    for i, poly in enumerate(p.polygons):
        poly_ = []
        for x, y in poly:
            poly_.append((tx(x), ty(y)))

        if areas[i] > 0:
            color = c_poly
        else:
            color = c_poly_int
        pygame.draw.polygon(surface, color, poly_, 0)

    for a, b in p.raw_skeleton:
        ax, ay = tx(a[0]), ty(a[1])
        bx, by = tx(b[0]), ty(b[1])
        pygame.draw.line(surface, c_skeleton, (ax, ay), (bx, by), 3)

    pygame.display.flip()

def display_ps(ps):
    print("Number of facets in solution:", len(ps.facets))
    print("Solution area:", float(ps.area))

    def t(xy):
        return (int(pixels * xy[0]), pixels - int(pixels * xy[1]))

    surface.fill(c_black)
    for facet in ps.facets:
        points = [t(xy) for xy in facet.points]
        pygame.draw.polygon(surface, c_poly, points, 0)
        pygame.draw.polygon(surface, c_skeleton, points, 3)
    pygame.display.flip()

def foo(pid):
    p = sil.Problem.read_by_pid(pid)
    print_info_about(p)
    ps = solve.solve(p)
    display_ps(ps)

def prompt_user():
    while True:
        x = input("Choose a problem id to display or press enter to quit: ")
        if len(x) < 1:
            break

        try:
            pid = int(x.strip())
        except:
            print("Not a number.")
            continue

        if not os.path.isfile("problems/" + str(pid)):
            print("There is no problem with that id.")
            continue

        p = sil.Problem.read_by_pid(pid)
        print_info_about(p)
        display(p)

if __name__ == "__main__":
    prompt_user()
