"""
SMILES Parser — Recursive descent parser that builds a Molecule from SMILES tokens.

Implements the full SMILES grammar:
    smiles    → chain ('.' chain)*
    chain     → atom (bond? (atom | branch | ring_closure))*
    branch    → '(' bond? chain ')'
"""

from ..core.atom import Atom, Chirality
from ..core.bond import Bond, BondType, BondStereo
from ..core.molecule import Molecule
from .tokenizer import tokenize, TokenType, SMILESTokenizerError
from .valence import calculate_implicit_hydrogens
from .aromaticity import kekulize, perceive_aromaticity
from .stereo import assign_stereo


class SMILESParseError(Exception):
    """Error during SMILES parsing."""
    pass


# Bond token -> BondType mapping
_BOND_MAP = {
    '-': BondType.SINGLE,
    '=': BondType.DOUBLE,
    '#': BondType.TRIPLE,
    ':': BondType.AROMATIC,
}

# Bond token -> BondStereo mapping
_STEREO_MAP = {
    '/': BondStereo.UP,
    '\\': BondStereo.DOWN,
}


def parse_smiles(smiles, name=""):
    """
    Parse a SMILES string into a Molecule object.

    Args:
        smiles: SMILES string
        name: Optional molecule name

    Returns:
        Molecule object with atoms, bonds, implicit H counts,
        ring membership, and aromaticity resolved.

    Raises:
        SMILESParseError on invalid SMILES
    """
    if not smiles or not smiles.strip():
        raise SMILESParseError("Empty SMILES string")

    tokens = tokenize(smiles.strip())
    if not tokens:
        raise SMILESParseError("No valid tokens in SMILES string")

    parser = _SMILESParser(tokens, name)
    mol = parser.parse()
    return mol


class _SMILESParser:
    """Internal recursive descent parser."""

    def __init__(self, tokens, name):
        self.tokens = tokens
        self.pos = 0
        self.mol = Molecule(name)
        self.ring_openings = {}      # ring_num -> (atom_idx, bond_type, stereo)
        self.bond_stereo_info = []    # list of (bond_idx, stereo_type) for E/Z

    def parse(self):
        """Parse full SMILES and return completed Molecule."""
        self._parse_chain(prev_atom_idx=-1)

        # Check for unmatched ring closures
        if self.ring_openings:
            nums = list(self.ring_openings.keys())
            raise SMILESParseError(
                f"Unmatched ring closure(s): {nums}")

        # Check we consumed all tokens
        if self.pos < len(self.tokens):
            tok = self.tokens[self.pos]
            raise SMILESParseError(
                f"Unexpected token at position {tok.pos}: {tok.value}")

        # Post-processing
        self._post_process()

        return self.mol

    def _peek(self):
        """Look at current token without consuming."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _consume(self):
        """Consume and return current token."""
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _parse_chain(self, prev_atom_idx):
        """Parse: atom (bond? (atom | branch | ring_closure))*"""
        # Parse first atom
        atom_idx = self._parse_atom()
        if atom_idx is None:
            return

        # Bond to previous atom
        if prev_atom_idx >= 0:
            self._add_default_bond(prev_atom_idx, atom_idx)

        # Parse rest of chain
        while self.pos < len(self.tokens):
            tok = self._peek()
            if tok is None:
                break

            # ── Dot (disconnection) ──
            if tok.type == TokenType.DOT:
                self._consume()
                # Start a new chain with no connection to current
                self._parse_chain(prev_atom_idx=-1)
                return

            # ── Bond token ──
            if tok.type == TokenType.BOND:
                self._consume()
                bond_type = _BOND_MAP.get(tok.value)
                bond_stereo = _STEREO_MAP.get(tok.value, BondStereo.NONE)

                next_tok = self._peek()
                if next_tok is None:
                    raise SMILESParseError(
                        f"SMILES ends with bond '{tok.value}'")

                if next_tok.type in (TokenType.ATOM, TokenType.BRACKET_ATOM):
                    next_atom_idx = self._parse_atom()
                    if bond_type:
                        bid = self.mol.add_bond(atom_idx, next_atom_idx, bond_type)
                    else:
                        # stereo bond (/ or \) — single bond with stereo
                        bid = self.mol.add_bond(atom_idx, next_atom_idx,
                                                BondType.SINGLE, bond_stereo)
                        self.bond_stereo_info.append((bid, bond_stereo))
                    atom_idx = next_atom_idx

                elif next_tok.type == TokenType.RING_CLOSURE:
                    self._consume()
                    ring_num = next_tok.data['ring_num']
                    self._handle_ring_closure(atom_idx, ring_num,
                                             bond_type=bond_type,
                                             bond_stereo=bond_stereo)

                elif next_tok.type == TokenType.BRANCH_OPEN:
                    # Bond before branch — this sets the bond type for
                    # the first atom inside the branch
                    self._parse_branch(atom_idx, explicit_bond=bond_type,
                                       explicit_stereo=bond_stereo)
                else:
                    raise SMILESParseError(
                        f"Unexpected token after bond: {next_tok.value}")
                continue

            # ── Atom ──
            if tok.type in (TokenType.ATOM, TokenType.BRACKET_ATOM):
                next_atom_idx = self._parse_atom()
                self._add_default_bond(atom_idx, next_atom_idx)
                atom_idx = next_atom_idx
                continue

            # ── Branch ──
            if tok.type == TokenType.BRANCH_OPEN:
                self._parse_branch(atom_idx)
                continue

            # ── Ring closure ──
            if tok.type == TokenType.RING_CLOSURE:
                self._consume()
                ring_num = tok.data['ring_num']
                self._handle_ring_closure(atom_idx, ring_num)
                continue

            # ── Branch close or other — break out ──
            if tok.type == TokenType.BRANCH_CLOSE:
                break

            raise SMILESParseError(f"Unexpected token: {tok.value}")

    def _parse_branch(self, branch_atom_idx, explicit_bond=None, explicit_stereo=None):
        """Parse: '(' bond? chain ')'"""
        tok = self._consume()  # consume '('
        assert tok.type == TokenType.BRANCH_OPEN

        # Check for bond at start of branch
        tok = self._peek()
        if tok and tok.type == TokenType.BOND:
            self._consume()
            bond_type = _BOND_MAP.get(tok.value)
            bond_stereo = _STEREO_MAP.get(tok.value, BondStereo.NONE)

            # Parse atom inside branch
            next_atom_idx = self._parse_atom()
            if next_atom_idx is not None:
                if bond_type:
                    self.mol.add_bond(branch_atom_idx, next_atom_idx, bond_type)
                else:
                    bid = self.mol.add_bond(branch_atom_idx, next_atom_idx,
                                            BondType.SINGLE, bond_stereo)
                    self.bond_stereo_info.append((bid, bond_stereo))

                # Continue parsing the rest of the chain inside the branch
                self._parse_chain_continuation(next_atom_idx)
        elif explicit_bond:
            # Bond was specified before the branch
            next_atom_idx = self._parse_atom()
            if next_atom_idx is not None:
                self.mol.add_bond(branch_atom_idx, next_atom_idx, explicit_bond)
                self._parse_chain_continuation(next_atom_idx)
        else:
            # No explicit bond — use default
            self._parse_chain_inner(branch_atom_idx)

        # Consume closing ')'
        tok = self._peek()
        if tok is None or tok.type != TokenType.BRANCH_CLOSE:
            raise SMILESParseError("Unmatched '(' — expected ')'")
        self._consume()

    def _parse_chain_inner(self, prev_atom_idx):
        """Parse chain inside a branch (same as chain but stops at ')')."""
        # Parse first atom
        atom_idx = self._parse_atom()
        if atom_idx is None:
            return

        # Default bond to previous
        self._add_default_bond(prev_atom_idx, atom_idx)

        # Continue rest of chain
        self._parse_chain_continuation(atom_idx)

    def _parse_chain_continuation(self, atom_idx):
        """Continue parsing a chain from a given atom (after the first atom is parsed)."""
        while self.pos < len(self.tokens):
            tok = self._peek()
            if tok is None:
                break

            if tok.type == TokenType.BRANCH_CLOSE:
                break

            if tok.type == TokenType.DOT:
                self._consume()
                self._parse_chain(prev_atom_idx=-1)
                return

            if tok.type == TokenType.BOND:
                self._consume()
                bond_type = _BOND_MAP.get(tok.value)
                bond_stereo = _STEREO_MAP.get(tok.value, BondStereo.NONE)

                next_tok = self._peek()
                if next_tok is None:
                    raise SMILESParseError(f"SMILES ends with bond '{tok.value}'")

                if next_tok.type in (TokenType.ATOM, TokenType.BRACKET_ATOM):
                    next_atom_idx = self._parse_atom()
                    if bond_type:
                        self.mol.add_bond(atom_idx, next_atom_idx, bond_type)
                    else:
                        bid = self.mol.add_bond(atom_idx, next_atom_idx,
                                                BondType.SINGLE, bond_stereo)
                        self.bond_stereo_info.append((bid, bond_stereo))
                    atom_idx = next_atom_idx
                elif next_tok.type == TokenType.RING_CLOSURE:
                    self._consume()
                    ring_num = next_tok.data['ring_num']
                    self._handle_ring_closure(atom_idx, ring_num,
                                             bond_type=bond_type,
                                             bond_stereo=bond_stereo)
                elif next_tok.type == TokenType.BRANCH_OPEN:
                    self._parse_branch(atom_idx, explicit_bond=bond_type,
                                       explicit_stereo=bond_stereo)
                else:
                    raise SMILESParseError(
                        f"Unexpected token after bond: {next_tok.value}")
                continue

            if tok.type in (TokenType.ATOM, TokenType.BRACKET_ATOM):
                next_atom_idx = self._parse_atom()
                self._add_default_bond(atom_idx, next_atom_idx)
                atom_idx = next_atom_idx
                continue

            if tok.type == TokenType.BRANCH_OPEN:
                self._parse_branch(atom_idx)
                continue

            if tok.type == TokenType.RING_CLOSURE:
                self._consume()
                ring_num = tok.data['ring_num']
                self._handle_ring_closure(atom_idx, ring_num)
                continue

            break

    def _parse_atom(self):
        """Parse an atom token and add it to the molecule. Returns atom index."""
        tok = self._peek()
        if tok is None:
            return None

        if tok.type == TokenType.ATOM:
            self._consume()
            is_aromatic = tok.data.get('aromatic', False)
            symbol = tok.data['symbol']
            atom = Atom(symbol, is_aromatic=is_aromatic)
            return self.mol.add_atom(atom)

        elif tok.type == TokenType.BRACKET_ATOM:
            self._consume()
            d = tok.data
            chirality_val = Chirality.NONE
            if d['chirality'] == 1:
                chirality_val = Chirality.COUNTERCLOCKWISE
            elif d['chirality'] == 2:
                chirality_val = Chirality.CLOCKWISE

            atom = Atom(
                symbol=d['symbol'],
                is_aromatic=d['aromatic'],
                formal_charge=d['charge'],
                isotope=d['isotope'],
                chirality=chirality_val,
                num_explicit_h=d['hcount'],
                atom_class=d['atom_class'],
                in_bracket=True
            )
            return self.mol.add_atom(atom)

        return None

    def _add_default_bond(self, atom1_idx, atom2_idx):
        """Add a bond with default type based on aromaticity."""
        a1 = self.mol.get_atom(atom1_idx)
        a2 = self.mol.get_atom(atom2_idx)

        if a1.is_aromatic and a2.is_aromatic:
            self.mol.add_bond(atom1_idx, atom2_idx, BondType.AROMATIC)
        else:
            self.mol.add_bond(atom1_idx, atom2_idx, BondType.SINGLE)

    def _handle_ring_closure(self, atom_idx, ring_num, bond_type=None, bond_stereo=None):
        """Handle ring closure digit/number."""
        if ring_num in self.ring_openings:
            # Close the ring
            open_atom_idx, open_bond_type, open_stereo = self.ring_openings.pop(ring_num)

            # Determine bond type: explicit > opening specification > default
            final_bond_type = bond_type or open_bond_type
            final_stereo = bond_stereo or open_stereo or BondStereo.NONE

            if final_bond_type is None:
                # Default: aromatic if both atoms aromatic, else single
                a1 = self.mol.get_atom(open_atom_idx)
                a2 = self.mol.get_atom(atom_idx)
                if a1.is_aromatic and a2.is_aromatic:
                    final_bond_type = BondType.AROMATIC
                else:
                    final_bond_type = BondType.SINGLE

            bid = self.mol.add_bond(open_atom_idx, atom_idx,
                                    final_bond_type, final_stereo)
            if final_stereo != BondStereo.NONE:
                self.bond_stereo_info.append((bid, final_stereo))
        else:
            # Open a new ring
            self.ring_openings[ring_num] = (atom_idx, bond_type, bond_stereo)

    def _post_process(self):
        """Post-processing after parsing: implicit H, aromaticity, stereo."""
        mol = self.mol

        # 1. Handle aromaticity: Kekulize aromatic bonds
        kekulize(mol)

        # 2. Calculate implicit hydrogens
        for atom in mol.atoms:
            atom.num_implicit_h = calculate_implicit_hydrogens(atom, mol)

        # 3. Perceive aromaticity flags on rings
        perceive_aromaticity(mol)

        # 4. Assign stereochemistry
        assign_stereo(mol, self.bond_stereo_info)

        # 5. Find rings and mark ring bonds
        mol.find_rings()

        # 6. Assign hybridization
        mol.assign_hybridization()
