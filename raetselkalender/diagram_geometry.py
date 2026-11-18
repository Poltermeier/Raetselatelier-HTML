"""Geometry shared by graph generation and drawing."""
import math


def segment_distance(point, start, end):
    """Distance to the finite segment, including its endpoints."""
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx-ax, by-ay
    squared = dx*dx+dy*dy
    if squared == 0:
        return math.hypot(px-ax, py-ay)
    t = max(0, min(1, ((px-ax)*dx+(py-ay)*dy)/squared))
    return math.hypot(px-ax-t*dx, py-ay-t*dy)


def clears_circles(a, b, positions, radius=29, gap=5):
    return all(segment_distance(point, positions[a], positions[b]) > radius+gap
               for key, point in positions.items() if key not in (a, b))


def crosses(edge, other, positions):
    """Proper crossing of two edges; shared endpoints are not crossings."""
    if set(edge) & set(other):
        return False
    a, b = (positions[k] for k in edge)
    c, d = (positions[k] for k in other)
    def orient(p, q, r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    return orient(a, b, c)*orient(a, b, d) < 0 and orient(c, d, a)*orient(c, d, b) < 0


def circle_link(start, end, radius=29):
    """End a drawn connection on the two circle boundaries, never at centers."""
    ax, ay = start
    bx, by = end
    length = math.hypot(bx-ax, by-ay)
    if length <= 2*radius:
        raise ValueError("Verbundene Kreise müssen ausreichend Abstand haben")
    dx, dy = (bx-ax)*radius/length, (by-ay)*radius/length
    return ax+dx, ay+dy, bx-dx, by-dy
