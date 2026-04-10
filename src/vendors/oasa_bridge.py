"""
Bridge between main application's Domain Molecule and OASA's molecule graph representations.
"""

import src.vendors.oasa.config as oasa_config

def domain_to_oasa_mol(domain_mol):
    """
    Converts internal Domain Molecule to OASA compatible graph.
    Returns: (oasa_molecule, atom_idx_map)
    where atom_idx_map maps domain atom indices to OASA vertices.
    """
    oasa_mol = oasa_config.Config.create_molecule()
    
    atom_map = {}
    for atom in domain_mol.atoms:
        if atom.symbol == 'H':
            continue
            
        v = oasa_mol.create_vertex()
        v.symbol = atom.symbol
        v.charge = atom.formal_charge
        v.isotope = atom.isotope
        v.explicit_hydrogens = atom.num_explicit_h if atom.num_explicit_h is not None else 0
        
        # Merge physical explicit neighbors into OASA's single text-node format 
        for n_idx in domain_mol.get_neighbors(atom.index):
            if domain_mol.atoms[n_idx].symbol == 'H':
                v.explicit_hydrogens += 1
        
        if atom.is_aromatic:
            v.properties_['aromatic'] = 1
        
        # Handle stereo mapping here if needed in SMILES generator
        from src.core.domain.models.atom import Chirality
        if atom.chirality == Chirality.COUNTERCLOCKWISE:
            v.properties_['stereo'] = '@'
        elif atom.chirality == Chirality.CLOCKWISE:
            v.properties_['stereo'] = '@@'
            
        # Copy 2D coordinates if they exist
        if hasattr(atom, 'x2d') and atom.x2d is not None:
            v.x = atom.x2d
            v.y = atom.y2d
            v.z = getattr(atom, 'z2d', 0.0)
            
        oasa_mol.add_vertex(v)
        atom_map[atom.index] = v
        
    for bond in domain_mol.bonds:
        if bond.begin_atom_idx not in atom_map or bond.end_atom_idx not in atom_map:
            continue
            
        v1 = atom_map[bond.begin_atom_idx]
        v2 = atom_map[bond.end_atom_idx]
        e = oasa_mol.create_edge()
        
        from src.core.domain.models.bond import BondType, BondStereo
        if bond.bond_type == BondType.DOUBLE:
            e.order = 2
        elif bond.bond_type == BondType.TRIPLE:
            e.order = 3
        elif bond.bond_type == BondType.AROMATIC:
            e.aromatic = True
            e.order = 1
        else:
            e.order = 1
            
        if bond.stereo == BondStereo.UP:
            e.properties_['stereo'] = '/'
        elif bond.stereo == BondStereo.DOWN:
            e.properties_['stereo'] = '\\'
            
        oasa_mol.add_edge(v1, v2, e=e)
        
    oasa_mol.add_missing_hydrogens()
    return oasa_mol, atom_map
