"""
File Readers — Import molecules from MOL, SDF, and MOL2 file formats.

Reads MDL V2000 MOL/SDF and Tripos MOL2 formats into Molecule objects.
"""

import re
from ..core.atom import Atom
from ..core.bond import Bond, BondType
from ..core.molecule import Molecule


def read_mol(filepath_or_string, is_string=False):
    """
    Read a molecule from MDL V2000 MOL file.

    Args:
        filepath_or_string: File path or MOL content string
        is_string: If True, treat first arg as content string

    Returns:
        Molecule object with atoms, bonds, and coordinates
    """
    if is_string:
        lines = filepath_or_string.split('\n')
    else:
        with open(filepath_or_string, 'r') as f:
            lines = f.read().split('\n')

    if len(lines) < 4:
        raise ValueError("MOL file too short")

    # Header: line 0 = name, line 1 = program/timestamp, line 2 = comment
    mol_name = lines[0].strip()
    mol = Molecule(name=mol_name)

    # Counts line (line 3)
    counts_line = lines[3]
    num_atoms = int(counts_line[0:3].strip())
    num_bonds = int(counts_line[3:6].strip())

    # Atom block: lines 4 to 4+num_atoms-1
    for i in range(num_atoms):
        line = lines[4 + i]
        x = float(line[0:10].strip())
        y = float(line[10:20].strip())
        z = float(line[20:30].strip())
        symbol = line[31:34].strip()

        # Charge code
        charge_code = 0
        if len(line) >= 39:
            try:
                charge_code = int(line[36:39].strip())
            except ValueError:
                pass

        formal_charge = _mdl_charge_decode(charge_code)

        atom = Atom(symbol, formal_charge=formal_charge)
        atom.x = x
        atom.y = y
        atom.z = z
        mol.add_atom(atom)

    # Bond block: lines 4+num_atoms to 4+num_atoms+num_bonds-1
    bond_start = 4 + num_atoms
    for i in range(num_bonds):
        line = lines[bond_start + i]
        a1 = int(line[0:3].strip()) - 1  # Convert to 0-indexed
        a2 = int(line[3:6].strip()) - 1
        bond_type_code = int(line[6:9].strip())

        stereo = 0
        if len(line) >= 12:
            try:
                stereo = int(line[9:12].strip())
            except ValueError:
                pass

        bt = _mdl_bond_type(bond_type_code)
        mol.add_bond(a1, a2, bt, stereo)

    # Properties block — look for M  CHG and M  ISO
    for i in range(bond_start + num_bonds, len(lines)):
        line = lines[i]
        if line.startswith('M  END'):
            break
        if line.startswith('M  CHG'):
            num_entries = int(line[6:9].strip())
            for j in range(num_entries):
                offset = 9 + j * 8
                atom_idx = int(line[offset:offset+4].strip()) - 1
                charge = int(line[offset+4:offset+8].strip())
                if 0 <= atom_idx < len(mol.atoms):
                    mol.atoms[atom_idx].formal_charge = charge
        elif line.startswith('M  ISO'):
            num_entries = int(line[6:9].strip())
            for j in range(num_entries):
                offset = 9 + j * 8
                atom_idx = int(line[offset:offset+4].strip()) - 1
                isotope = int(line[offset+4:offset+8].strip())
                if 0 <= atom_idx < len(mol.atoms):
                    mol.atoms[atom_idx].isotope = isotope

    return mol


def read_sdf(filepath_or_string, is_string=False):
    """
    Read the first molecule from an SDF file.

    Args:
        filepath_or_string: File path or SDF content string
        is_string: If True, treat first arg as content string

    Returns:
        Molecule object
    """
    if is_string:
        content = filepath_or_string
    else:
        with open(filepath_or_string, 'r') as f:
            content = f.read()

    # Split by $$$$ and take first block
    blocks = content.split('$$$$')
    if not blocks or not blocks[0].strip():
        raise ValueError("No molecule found in SDF file")

    mol_block = blocks[0].strip()

    # Read as MOL
    mol = read_mol(mol_block, is_string=True)

    # Parse data fields
    data_section = mol_block.split('M  END')
    if len(data_section) > 1:
        data_text = data_section[1]
        field_pattern = re.compile(r'>\s*<([^>]+)>\s*\n(.+?)(?=\n>|\n\s*$)', re.DOTALL)
        for match in field_pattern.finditer(data_text):
            key = match.group(1).strip()
            value = match.group(2).strip()
            mol.properties[key] = value

    return mol


def read_mol2(filepath_or_string, is_string=False):
    """
    Read a molecule from Tripos MOL2 file.

    Args:
        filepath_or_string: File path or MOL2 content string
        is_string: If True, treat first arg as content string

    Returns:
        Molecule object with atoms, bonds, coordinates, and partial charges
    """
    if is_string:
        content = filepath_or_string
    else:
        with open(filepath_or_string, 'r') as f:
            content = f.read()

    lines = content.split('\n')

    # Find section markers
    sections = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('@<TRIPOS>'):
            section_name = stripped.replace('@<TRIPOS>', '')
            sections[section_name] = i

    mol_name = ""
    if 'MOLECULE' in sections:
        mol_start = sections['MOLECULE']
        if mol_start + 1 < len(lines):
            mol_name = lines[mol_start + 1].strip()

    mol = Molecule(name=mol_name)

    # Parse ATOM section
    if 'ATOM' not in sections:
        raise ValueError("No ATOM section found in MOL2 file")

    atom_start = sections['ATOM'] + 1
    atom_end = len(lines)
    # Find end of atom section (next section marker or EOF)
    for i in range(atom_start, len(lines)):
        if lines[i].strip().startswith('@<TRIPOS>'):
            atom_end = i
            break

    for i in range(atom_start, atom_end):
        line = lines[i].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 6:
            continue

        # atom_id atom_name x y z atom_type [subst_id subst_name charge]
        atom_name = parts[1]
        x = float(parts[2])
        y = float(parts[3])
        z = float(parts[4])
        atom_type = parts[5]

        # Extract element symbol from SYBYL type (e.g., "C.3" -> "C", "N.am" -> "N")
        symbol = atom_type.split('.')[0]
        # Handle special cases
        if symbol.upper() in ('CL', 'BR'):
            symbol = symbol[0].upper() + symbol[1].lower()
        elif len(symbol) == 1:
            symbol = symbol.upper()
        else:
            symbol = symbol[0].upper() + symbol[1:].lower()

        atom = Atom(symbol)
        atom.x = x
        atom.y = y
        atom.z = z
        atom.sybyl_type = atom_type

        # Parse partial charge
        if len(parts) >= 9:
            try:
                atom.partial_charge = float(parts[8])
            except ValueError:
                pass

        mol.add_atom(atom)

    # Parse BOND section
    if 'BOND' in sections:
        bond_start = sections['BOND'] + 1
        bond_end = len(lines)
        for i in range(bond_start, len(lines)):
            if lines[i].strip().startswith('@<TRIPOS>'):
                bond_end = i
                break

        for i in range(bond_start, bond_end):
            line = lines[i].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue

            # bond_id origin_atom_id target_atom_id bond_type
            a1 = int(parts[1]) - 1  # 0-indexed
            a2 = int(parts[2]) - 1
            bond_type_str = parts[3].lower()

            if bond_type_str == '2':
                bt = BondType.DOUBLE
            elif bond_type_str == '3':
                bt = BondType.TRIPLE
            elif bond_type_str in ('ar', 'am'):
                bt = BondType.AROMATIC
            else:
                bt = BondType.SINGLE

            if 0 <= a1 < len(mol.atoms) and 0 <= a2 < len(mol.atoms):
                mol.add_bond(a1, a2, bt)

    return mol


def _mdl_charge_decode(charge_code):
    """Convert MDL V2000 charge code to formal charge."""
    code_map = {
        0: 0,
        1: 3,
        2: 2,
        3: 1,
        5: -1,
        6: -2,
        7: -3,
    }
    return code_map.get(charge_code, 0)


def _mdl_bond_type(code):
    """Convert MDL bond type code to BondType."""
    if code == 1:
        return BondType.SINGLE
    elif code == 2:
        return BondType.DOUBLE
    elif code == 3:
        return BondType.TRIPLE
    elif code == 4:
        return BondType.AROMATIC
    else:
        return BondType.SINGLE


def read_pdb(filepath):
    """
    Read a molecule/protein from PDB file format.

    Optimized for large files - processes records in a single pass with
    efficient secondary structure lookup using dictionaries.

    Parses ATOM/HETATM records, CONECT bonds, and HELIX/SHEET secondary structure.
    Stores residue name, chain ID, residue number, and secondary structure type
    on each atom for protein visualization.

    Args:
        filepath: Path to PDB file

    Returns:
        Molecule object with atoms, bonds, coordinates, and structural metadata
    """
    mol = Molecule(name="")
    conect_records = []
    helix_ranges = []   # (chain, start_res, end_res)
    sheet_ranges = []   # (chain, start_res, end_res)

    serial_to_idx = {}  # PDB serial number -> molecule atom index
    
    # Pre-allocate lists for better performance
    atoms_to_add = []
    
    # Use more efficient file reading
    with open(filepath, 'r', buffering=8192) as f:  # 8KB buffer
        for line in f:
            if len(line) < 6:
                continue
                
            record = line[0:6]
            
            # Fast path for most common records
            if record.startswith('ATOM') or record.startswith('HETATM'):
                try:
                    # Parse coordinates efficiently
                    serial = int(line[6:11])
                    atom_name = line[12:16].strip()
                    res_name = line[17:20].strip()
                    chain_id = line[21]
                    res_seq = int(line[22:26])
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])

                    # Element symbol - optimized lookup
                    element = ''
                    if len(line) >= 78:
                        element = line[76:78].strip()
                    if not element:
                        name_clean = atom_name.lstrip('0123456789')
                        if len(name_clean) >= 2:
                            first_two = name_clean[:2].upper()
                            if first_two in ('CL', 'BR', 'FE', 'ZN', 'MG', 'CA', 'NA', 'MN', 'CU', 'CO', 'NI'):
                                element = first_two
                            else:
                                element = name_clean[0].upper()
                        elif name_clean:
                            element = name_clean[0].upper()

                    # B-factor - optimized parsing
                    b_factor = 0.0
                    if len(line) >= 66:
                        try:
                            b_factor = float(line[60:66])
                        except ValueError:
                            pass

                    # Create atom and store for batch addition
                    atom = Atom(element)
                    atom.x = x
                    atom.y = y
                    atom.z = z
                    atom.pdb_name = atom_name
                    atom.res_name = res_name
                    atom.chain_id = chain_id
                    atom.res_seq = res_seq
                    atom.b_factor = b_factor
                    atom.is_hetatm = record.startswith('HETATM')
                    
                    atoms_to_add.append((serial, atom))
                    
                except (ValueError, IndexError):
                    continue
                    
            elif record.startswith('HEADER'):
                mol.name = line[10:50].strip()
                
            elif record.startswith('HELIX'):
                try:
                    chain = line[19]
                    start_res = int(line[21:25])
                    end_res = int(line[33:37])
                    helix_ranges.append((chain, start_res, end_res))
                except (ValueError, IndexError):
                    pass
                    
            elif record.startswith('SHEET'):
                try:
                    chain = line[21]
                    start_res = int(line[22:26])
                    end_res = int(line[33:37])
                    sheet_ranges.append((chain, start_res, end_res))
                except (ValueError, IndexError):
                    pass
                
            elif record.startswith('CONECT'):
                try:
                    parts = line[6:].split()
                    if len(parts) >= 2:
                        origin = int(parts[0])
                        for target_str in parts[1:]:
                            target = int(target_str)
                            conect_records.append((origin, target))
                except ValueError:
                    pass

    # Batch add atoms for better performance
    for serial, atom in atoms_to_add:
        idx = mol.add_atom(atom)
        serial_to_idx[serial] = idx

    # Efficient secondary structure assignment using range dictionaries
    if helix_ranges or sheet_ranges:
        # Convert ranges to dictionaries for O(1) lookup
        helix_dict = {}
        for chain, start, end in helix_ranges:
            if chain not in helix_dict:
                helix_dict[chain] = []
            helix_dict[chain].append((start, end))
            
        sheet_dict = {}
        for chain, start, end in sheet_ranges:
            if chain not in sheet_dict:
                sheet_dict[chain] = []
            sheet_dict[chain].append((start, end))
        
        # Assign secondary structure efficiently
        for atom in mol.atoms:
            if not hasattr(atom, 'chain_id') or not atom.chain_id:
                atom.ss_type = 'C'
                continue
                
            chain_id = atom.chain_id
            res_seq = atom.res_seq
            
            # Check helix
            if chain_id in helix_dict:
                for start, end in helix_dict[chain_id]:
                    if start <= res_seq <= end:
                        atom.ss_type = 'H'
                        break
                else:
                    # Check sheet
                    if chain_id in sheet_dict:
                        for start, end in sheet_dict[chain_id]:
                            if start <= res_seq <= end:
                                atom.ss_type = 'E'
                                break
                        else:
                            atom.ss_type = 'C'
                    else:
                        atom.ss_type = 'C'
            else:
                atom.ss_type = 'C'
    else:
        # No secondary structure data - set all to coil
        for atom in mol.atoms:
            atom.ss_type = 'C'

    # Add bonds from CONECT records (optimized)
    added_bonds = set()
    for serial1, serial2 in conect_records:
        if serial1 in serial_to_idx and serial2 in serial_to_idx:
            idx1 = serial_to_idx[serial1]
            idx2 = serial_to_idx[serial2]
            bond_key = tuple(sorted((idx1, idx2)))
            if bond_key not in added_bonds:
                mol.add_bond(idx1, idx2, BondType.SINGLE)
                added_bonds.add(bond_key)

    # Auto-detect bonds if no CONECT records (optimized)
    if not conect_records and len(mol.atoms) > 0:
        _auto_bond_pdb(mol)

    # Store secondary structure ranges on the molecule
    mol.properties['helix_ranges'] = helix_ranges
    mol.properties['sheet_ranges'] = sheet_ranges
    mol.properties['is_protein'] = any(
        hasattr(a, 'res_name') and a.res_name in _AMINO_ACIDS
        for a in mol.atoms)

    return mol


_AMINO_ACIDS = {
    'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLU', 'GLN', 'GLY', 'HIS', 'ILE',
    'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER', 'THR', 'TRP', 'TYR', 'VAL',
    'MSE', 'SEC', 'PYL',
}

# Covalent bond distance cutoffs by element pair (Angstroms)
_COVALENT_RADII = {
    'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'S': 1.05, 'P': 1.07,
    'F': 0.57, 'Cl': 0.99, 'Br': 1.14, 'I': 1.33, 'Se': 1.20,
    'Fe': 1.32, 'Zn': 1.22, 'Mg': 1.41, 'Ca': 1.76, 'Na': 1.66,
    'Mn': 1.39, 'Cu': 1.32, 'Co': 1.26, 'Ni': 1.24,
}


def _auto_bond_pdb(mol):
    """Auto-detect bonds in a PDB molecule by covalent distance."""
    import math
    n = len(mol.atoms)
    tolerance = 0.4  # Angstroms tolerance

    for i in range(n):
        a1 = mol.atoms[i]
        r1 = _COVALENT_RADII.get(a1.symbol, 1.5)
        for j in range(i + 1, n):
            a2 = mol.atoms[j]
            r2 = _COVALENT_RADII.get(a2.symbol, 1.5)
            max_dist = r1 + r2 + tolerance

            dx = a1.x - a2.x
            if abs(dx) > max_dist:
                continue
            dy = a1.y - a2.y
            if abs(dy) > max_dist:
                continue
            dz = (a1.z or 0) - (a2.z or 0)
            if abs(dz) > max_dist:
                continue

            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist <= max_dist and dist > 0.4:
                mol.add_bond(i, j, BondType.SINGLE)

