class Transform:
    def __init__(self, cos, sin, dx, dy, flip):
        self.cos = cos
        self.sin = sin
        self.dx = dx
        self.dy = dy
        self.flip = flip

    def map(self, x, y):
        if self.flip:
            return (self.cos * x - self.sin * y + self.dx,-(self.sin * x + self.cos * y + self.dy))
        else:
            return (self.cos * x - self.sin * y + self.dx, self.sin * x + self.cos * y + self.dy)

    def inverse(self):
        if self.flip:
            dx = self.cos * (-self.dx) - self.sin * self.dy
            dy = self.sin * (-self.dx) + self.cos * self.dy
            return Transform(self.cos, self.sin, dx, dy, True)
        else:
            dx = -(self.cos * self.dx + self.sin * self.dy)
            dy = -(-self.sin * self.dx + self.cos * self.dy)
            return Transform(self.cos, -self.sin, dx, dy, False)

    # do this transform followed by the other transform
    def compose(self, other):
        if self.flip:
            cos = self.cos * other.cos + self.sin * other.sin
            sin = -self.cos * other.sin + self.sin * other.cos
            dx = other.dx + (other.cos * self.dx + other.sin * self.dy)
            dy = -other.dy + (-other.sin * self.dx + other.cos * self.dy)
            return Transform(cos, sin, dx, dy, not other.flip)
        else:
            cos = self.cos * other.cos - self.sin * other.sin
            sin = self.cos * other.sin + self.sin * other.cos
            dx = other.dx + (other.cos * self.dx - other.sin * self.dy)
            dy = other.dy + (other.sin * self.dx + other.cos * self.dy)
            return Transform(cos, sin, dx, dy, other.flip)

    # Return the transform that flips over the specified edge
    def flipedge(px, py, qx, qy):
        # L2 = edge.length_sq()
        L2 = (px - qx) ** 2 + (py - qy) ** 2
        cos = ((px - qx) ** 2 - (py - qy) ** 2) / L2
        sin = -2 * (px - qx) * (py - qy) / L2
        dx = px - (cos * px - sin * py)
        dy = -py - (sin * px + cos * py)
        return Transform(cos, sin, dx, dy, True)

    # Returns a Transform that sends the specified edge to (0, 0)#(L, 0), and
    # puts the left facet of the edge into the upper right quadrant.
    def base(edge):
        px = edge.near[0].x
        py = edge.near[0].y
        qx = edge.far[0].x
        qy = edge.far[0].y
        L = edge.length
        cos = (qx - px) / L
        sin = (py - qy) / L
        dx = (px ** 2 + py ** 2 - px * qx - py * qy) / L
        dy = (px * qy - qx * py) / L
        return Transform(cos, sin, dx, dy, False)

    # Same, but sends the far point to (0, 0) instead of the near point
    def baseflipped(edge):
        px = edge.far[0].x
        py = edge.far[0].y
        qx = edge.near[0].x
        qy = edge.near[0].y
        L = edge.length
        cos = (qx - px) / L
        sin = (py - qy) / L
        dx = (px ** 2 + py ** 2 - px * qx - py * qy) / L
        dy = (px * qy - qx * py) / L
        return Transform(cos, sin, dx, dy, True)

# Returns whether the line segments intersect, returns False if the intersection
# is a mutual endpoint or if they are parallel
def intersect(a, b, c, d):
    dax = b[0] - a[0]
    day = b[1] - a[1]
    dcx = d[0] - c[0]
    dcy = d[1] - c[1]

    denom = dax * dcy - day * dcx
    if denom == 0:
        # Line are parallel
        return False

    s = (-day * (a[0] - c[0]) + dax * (a[1] - c[1])) / denom
    t = ( dcx * (a[1] - c[1]) - dcy * (a[0] - c[0])) / denom
    return (s > 0 and s < 1 and t > 0 and t < 1)
