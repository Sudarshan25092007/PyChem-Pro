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

            # Generate 3D coordinates
            from src.features.layout_3d import generate_3d_coordinates
            generate_3d_coordinates(mol, optimize=True, max_opt_steps=100)
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
