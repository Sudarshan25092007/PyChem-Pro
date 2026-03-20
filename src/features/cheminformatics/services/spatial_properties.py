import math
import numpy as np

def generate_sphere_points(n_points=160):
    """Generate uniformly distributed points on a sphere using Golden Section spiral."""
    points = []
    offset = 2.0 / n_points
    increment = math.pi * (3.0 - math.sqrt(5.0))  # golden angle
    for i in range(n_points):
        y = ((i * offset) - 1) + (offset / 2)
        r = math.sqrt(1 - y * y)
        phi = i * increment
        x = math.cos(phi) * r
        z = math.sin(phi) * r
        points.append([x, y, z])
    return np.array(points, dtype=np.float32)

def compute_sasa(molecule, probe_radius=1.4, n_sphere_points=160):
    """
    Compute Shrake-Rupley Solvent Accessible Surface Area (SASA) for each atom.
    Assigns the result to `atom.sasa` and `atom.sasa_points` (for visualization).
    Uses fast NumPy vectorization for point-cloud collision testing.
    """
    if not molecule.atoms:
        return 0.0

    points = generate_sphere_points(n_sphere_points)
    point_area = 4 * math.pi / n_sphere_points
    
    # Pre-extract data for speed
    positions = []
    radii = []
    for atom in molecule.atoms:
        if atom.has_coords:
            positions.append([atom.x, atom.y, atom.z])
            # vdw_radius + probe_radius
            radii.append(atom.element.vdw_radius + probe_radius)
        else:
            positions.append([0.0, 0.0, 0.0])
            radii.append(0.0)
            
    positions = np.array(positions, dtype=np.float32)
    radii_sq = np.array(radii, dtype=np.float32) ** 2
    
    total_sasa = 0.0
    
    for i, atom in enumerate(molecule.atoms):
        atom.sasa = 0.0
        atom.sasa_points = []
        if not atom.has_coords:
            continue
            
        center_i = positions[i]
        radius_i = radii[i]
        
        # Test points forming a sphere around atom i
        test_points = center_i + radius_i * points
        
        accessible_count = 0
        accessible_dots = []
        
        for p in test_points:
            dx = positions - p
            dist_sq = np.sum(dx*dx, axis=1)
            # ignore self
            dist_sq[i] = 99999.0
            
            # If any dist_sq < radii_sq, point is intersecting another atom
            if not np.any(dist_sq < radii_sq):
                accessible_count += 1
                accessible_dots.append((p[0], p[1], p[2]))
                
        sasa_i = accessible_count * point_area * (radius_i ** 2)
        atom.sasa = sasa_i
        atom.sasa_points = accessible_dots
        total_sasa += sasa_i
        
    molecule.properties['sasa'] = total_sasa
    return total_sasa

def compute_center_of_mass(molecule):
    """Compute the mass-weighted Center of Mass (COM) for the molecule."""
    total_mass = 0.0
    com = np.zeros(3, dtype=np.float64)
    
    for atom in molecule.atoms:
        if atom.has_coords:
            mass = atom.element.mass
            com[0] += mass * atom.x
            com[1] += mass * atom.y
            com[2] += mass * (atom.z or 0.0)
            total_mass += mass
            
    if total_mass > 0:
        com /= total_mass
        
    molecule.properties['center_of_mass'] = tuple(com)
    return tuple(com)
