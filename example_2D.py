from src.parser.parser import parse_smiles
from src.parser.coordgen2d import CoordinateGenerator2D
from src.parser.render2d import Renderer2D

# 1. Parse SMILES
mol = parse_smiles("CC(/C=C/C(=O)NO)=C\[C@@H](C)[C@H]1CC[C@H]2/C(=C/C=C3\C[C@@H](O)C[C@@H](O)C3)CCC[C@]12C")

# 2. Generate Coordinates
coords = CoordinateGenerator2D(mol).generate()

# 3. Draw it!
Renderer2D(mol, coords).draw()