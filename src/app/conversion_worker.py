"""
ConversionWorker — Background SMILES-to-3D conversion thread.
"""

from src.shared.qt_compat import QObject, Signal


class ConversionWorker(QObject):
    """Worker for background SMILES conversion."""
    finished = Signal(object, str)  # (molecule, error_msg)
    progress = Signal(int)

    def __init__(self, smiles):
        super().__init__()
        self.smiles = smiles

    def run(self):
        try:
            self.progress.emit(10)

            # Parse SMILES
            from src.features.smiles_parser.services.parser import parse_smiles
            mol = parse_smiles(self.smiles, use_bkchem_tokenizer=True)
            self.progress.emit(30)

            # Generate 2D coordinates using OASA
            from src.features.layout_2d.generators.coordgen2d_smiles_pure_oasa import CoordinateGenerator2DSMILES
            generator = CoordinateGenerator2DSMILES(mol)
            coords_2d = generator.generate()

            # Map coordinates to a flat 3D representation (z=0)
            for atom in mol.atoms:
                if atom.index in coords_2d:
                    x, y = coords_2d[atom.index]
                    atom.x = float(x)
                    atom.y = float(y)
                    atom.z = 0.0
                else:
                    atom.x, atom.y, atom.z = 0.0, 0.0, 0.0
            self.progress.emit(70)

            # Compute charges
            from src.features.cheminformatics.electrostatics.gasteiger import compute_gasteiger_charges
            compute_gasteiger_charges(mol)
            self.progress.emit(90)

            # Assign types for export
            mol.assign_sybyl_types()
            self.progress.emit(100)

            self.finished.emit(mol, "")
        except Exception as e:
            self.finished.emit(None, str(e))
