"""
Enhanced Molecular Descriptor Engine for PyChem.
Calculates 90+ molecular descriptors across 8 categories.
Uses modular calculator classes for better organization and performance.
"""
import hashlib
import numpy as np
from typing import Dict, List, Optional, Callable, Any
from enum import Enum, auto

from ...core.domain.models.molecule import Molecule
from .descriptor_types import (
    DescriptorCategory,
    DescriptorInfo,
    DescriptorResult,
    CalculationProgress,
    AtomSelection,
    SelectionType
)

# Import calculators
from .calculators import BaseCalculator
from .calculators.constitutional import ConstitutionalCalculator
from .calculators.topological import TopologicalCalculator
from .calculators.geometric import GeometricCalculator
from .calculators.electronic import ElectronicCalculator
from .calculators.quantum import QuantumCalculator
from .calculators.fingerprints import FingerprintCalculator
from .calculators.hybrid import HybridCalculator


class DescriptorCache:
    """Cache for descriptor calculation results."""

    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size

    def _get_molecule_hash(self, molecule: Molecule) -> str:
        """Generate hash for molecule state."""
        atoms_str = "".join(f"{a.symbol}{a.x}{a.y}{a.z}" for a in molecule.atoms)
        bonds_str = "".join(f"{b.begin_atom_idx}{b.end_atom_idx}{b.order}" for b in molecule.bonds)
        return hashlib.md5(f"{atoms_str}{bonds_str}".encode()).hexdigest()

    def _get_selection_hash(self, selection: AtomSelection) -> str:
        """Generate hash for atom selection."""
        return hashlib.md5(str(sorted(selection.atom_indices)).encode()).hexdigest()

    def get_cache_key(self, molecule: Molecule, selection: AtomSelection, descriptor_name: str) -> str:
        """Generate unique cache key."""
        mol_hash = self._get_molecule_hash(molecule)
        sel_hash = self._get_selection_hash(selection)
        return f"{mol_hash}:{sel_hash}:{descriptor_name}"

    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        return self.cache.get(key)

    def set(self, key: str, value: Any):
        """Set cached value with LRU eviction."""
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value

    def clear(self):
        """Clear cache."""
        self.cache.clear()


class DescriptorEngine:
    """
    Enhanced molecular descriptor calculation engine.
    Calculates 90+ descriptors across 8 categories.
    """

    def __init__(self, enable_cache: bool = True):
        self.enable_cache = enable_cache
        self.cache = DescriptorCache() if enable_cache else None
        self.progress_callback = None  # For GUI progress updates

        # Initialize calculator instances
        self.constitutional_calc = ConstitutionalCalculator()
        self.topological_calc = TopologicalCalculator()
        self.geometric_calc = GeometricCalculator()
        self.electronic_calc = ElectronicCalculator()
        self.quantum_calc = QuantumCalculator()
        self.fingerprint_calc = FingerprintCalculator()
        self.hybrid_calc = HybridCalculator()

        # Build descriptor registry
        self.descriptors = self._initialize_descriptors()

    def _initialize_descriptors(self) -> Dict[DescriptorCategory, List[DescriptorInfo]]:
        """Initialize all 90+ descriptors organized by category."""
        return {
            DescriptorCategory.CONSTITUTIONAL: self._get_constitutional_descriptors(),
            DescriptorCategory.TOPOLOGICAL: self._get_topological_descriptors(),
            DescriptorCategory.GEOMETRIC: self._get_geometric_descriptors(),
            DescriptorCategory.ELECTRONIC: self._get_electronic_descriptors(),
            DescriptorCategory.QUANTUM: self._get_quantum_descriptors(),
            DescriptorCategory.FINGERPRINTS: self._get_fingerprint_descriptors(),
            DescriptorCategory.HYBRID: self._get_hybrid_descriptors(),
            DescriptorCategory.CUSTOM: self._get_custom_descriptors(),
        }

    def _get_constitutional_descriptors(self) -> List[DescriptorInfo]:
        """Get constitutional (1D) descriptors."""
        calc = self.constitutional_calc
        return [
            DescriptorInfo("MolecularWeight", "Molecular weight (g/mol)", DescriptorCategory.CONSTITUTIONAL, "sum(atomic_weights)", "g/mol", calculation_function=calc.calc_molecular_weight),
            DescriptorInfo("AtomCount", "Total number of atoms", DescriptorCategory.CONSTITUTIONAL, "len(atoms)", "count", calculation_function=calc.calc_atom_count),
            DescriptorInfo("HeavyAtomCount", "Number of non-hydrogen atoms", DescriptorCategory.CONSTITUTIONAL, "count(non-H)", "count", calculation_function=calc.calc_heavy_atom_count),
            DescriptorInfo("BondCount", "Total number of bonds", DescriptorCategory.CONSTITUTIONAL, "len(bonds)", "count", calculation_function=calc.calc_bond_count),
            DescriptorInfo("RotatableBonds", "Number of rotatable bonds", DescriptorCategory.CONSTITUTIONAL, "count(rotatable)", "count", calculation_function=calc.calc_rotatable_bonds),
            DescriptorInfo("RingCount", "Number of rings", DescriptorCategory.CONSTITUTIONAL, "count(rings)", "count", calculation_function=calc.calc_ring_count),
            DescriptorInfo("AromaticRingCount", "Number of aromatic rings", DescriptorCategory.CONSTITUTIONAL, "count(aromatic_rings)", "count", calculation_function=calc.calc_aromatic_ring_count),
            DescriptorInfo("HeteroRingCount", "Number of heteroatom-containing rings", DescriptorCategory.CONSTITUTIONAL, "count(hetero_rings)", "count", calculation_function=calc.calc_hetero_ring_count),
            DescriptorInfo("Ring5Count", "Number of 5-membered rings", DescriptorCategory.CONSTITUTIONAL, "count(5-rings)", "count", calculation_function=calc.calc_ring5_count),
            DescriptorInfo("Ring6Count", "Number of 6-membered rings", DescriptorCategory.CONSTITUTIONAL, "count(6-rings)", "count", calculation_function=calc.calc_ring6_count),
            DescriptorInfo("LargestRingSize", "Size of the largest ring", DescriptorCategory.CONSTITUTIONAL, "max(ring_sizes)", "count", calculation_function=calc.calc_largest_ring_size),
            DescriptorInfo("HDonorCount", "Number of H-bond donors", DescriptorCategory.CONSTITUTIONAL, "count(H-donors)", "count", calculation_function=calc.calc_h_donor_count),
            DescriptorInfo("HAcceptorCount", "Number of H-bond acceptors", DescriptorCategory.CONSTITUTIONAL, "count(H-acceptors)", "count", calculation_function=calc.calc_h_acceptor_count),
            DescriptorInfo("LipophilicAtomCount", "Number of lipophilic atoms", DescriptorCategory.CONSTITUTIONAL, "count(lipophilic)", "count", calculation_function=calc.calc_lipophilic_count),
            DescriptorInfo("CarbonCount", "Number of carbon atoms", DescriptorCategory.CONSTITUTIONAL, "count(C)", "count", calculation_function=calc.calc_carbon_count),
            DescriptorInfo("NitrogenCount", "Number of nitrogen atoms", DescriptorCategory.CONSTITUTIONAL, "count(N)", "count", calculation_function=calc.calc_nitrogen_count),
            DescriptorInfo("OxygenCount", "Number of oxygen atoms", DescriptorCategory.CONSTITUTIONAL, "count(O)", "count", calculation_function=calc.calc_oxygen_count),
            DescriptorInfo("SulfurCount", "Number of sulfur atoms", DescriptorCategory.CONSTITUTIONAL, "count(S)", "count", calculation_function=calc.calc_sulfur_count),
            DescriptorInfo("PhosphorusCount", "Number of phosphorus atoms", DescriptorCategory.CONSTITUTIONAL, "count(P)", "count", calculation_function=calc.calc_phosphorus_count),
            DescriptorInfo("HalogenCount", "Number of halogen atoms", DescriptorCategory.CONSTITUTIONAL, "count(F,Cl,Br,I)", "count", calculation_function=calc.calc_halogen_count),
            DescriptorInfo("FluorineCount", "Number of fluorine atoms", DescriptorCategory.CONSTITUTIONAL, "count(F)", "count", calculation_function=calc.calc_fluorine_count),
            DescriptorInfo("ChlorineCount", "Number of chlorine atoms", DescriptorCategory.CONSTITUTIONAL, "count(Cl)", "count", calculation_function=calc.calc_chlorine_count),
            DescriptorInfo("BromineCount", "Number of bromine atoms", DescriptorCategory.CONSTITUTIONAL, "count(Br)", "count", calculation_function=calc.calc_bromine_count),
            DescriptorInfo("IodineCount", "Number of iodine atoms", DescriptorCategory.CONSTITUTIONAL, "count(I)", "count", calculation_function=calc.calc_iodine_count),
            DescriptorInfo("HydrogenCount", "Number of hydrogen atoms", DescriptorCategory.CONSTITUTIONAL, "count(H)", "count", calculation_function=calc.calc_hydrogen_count),
            DescriptorInfo("SingleBondCount", "Number of single bonds", DescriptorCategory.CONSTITUTIONAL, "count(single_bonds)", "count", calculation_function=calc.calc_single_bond_count),
            DescriptorInfo("DoubleBondCount", "Number of double bonds", DescriptorCategory.CONSTITUTIONAL, "count(double_bonds)", "count", calculation_function=calc.calc_double_bond_count),
            DescriptorInfo("TripleBondCount", "Number of triple bonds", DescriptorCategory.CONSTITUTIONAL, "count(triple_bonds)", "count", calculation_function=calc.calc_triple_bond_count),
            DescriptorInfo("AromaticBondCount", "Number of aromatic bonds", DescriptorCategory.CONSTITUTIONAL, "count(aromatic_bonds)", "count", calculation_function=calc.calc_aromatic_bond_count),
            DescriptorInfo("HeteroAtomCount", "Number of hetero atoms", DescriptorCategory.CONSTITUTIONAL, "count(hetero)", "count", calculation_function=calc.calc_hetero_atom_count),
            DescriptorInfo("AliphaticCarbonCount", "Number of aliphatic carbons", DescriptorCategory.CONSTITUTIONAL, "count(aliphatic_C)", "count", calculation_function=calc.calc_aliphatic_carbon_count),
            DescriptorInfo("AromaticCarbonCount", "Number of aromatic carbons", DescriptorCategory.CONSTITUTIONAL, "count(aromatic_C)", "count", calculation_function=calc.calc_aromatic_carbon_count),
            DescriptorInfo("NonRingCarbonCount", "Number of non-ring carbon atoms", DescriptorCategory.CONSTITUTIONAL, "count(C_non-ring)", "count", calculation_function=calc.calc_nonring_carbon_count),
            DescriptorInfo("SP3CarbonCount", "Number of sp3 hybridized carbon atoms", DescriptorCategory.CONSTITUTIONAL, "count(sp3_C)", "count", calculation_function=calc.calc_sp3_carbon_count),
            DescriptorInfo("SP2CarbonCount", "Number of sp2 hybridized carbon atoms", DescriptorCategory.CONSTITUTIONAL, "count(sp2_C)", "count", calculation_function=calc.calc_sp2_carbon_count),
            DescriptorInfo("SPCarbonCount", "Number of sp hybridized carbon atoms", DescriptorCategory.CONSTITUTIONAL, "count(sp_C)", "count", calculation_function=calc.calc_sp_carbon_count),
            DescriptorInfo("SP3NitrogenCount", "Number of sp3 hybridized nitrogen atoms", DescriptorCategory.CONSTITUTIONAL, "count(sp3_N)", "count", calculation_function=calc.calc_sp3_nitrogen_count),
            DescriptorInfo("SP2NitrogenCount", "Number of sp2 hybridized nitrogen atoms", DescriptorCategory.CONSTITUTIONAL, "count(sp2_N)", "count", calculation_function=calc.calc_sp2_nitrogen_count),
            DescriptorInfo("SP3OxygenCount", "Number of sp3 hybridized oxygen atoms", DescriptorCategory.CONSTITUTIONAL, "count(sp3_O)", "count", calculation_function=calc.calc_sp3_oxygen_count),
            DescriptorInfo("SP2OxygenCount", "Number of sp2 hybridized oxygen atoms", DescriptorCategory.CONSTITUTIONAL, "count(sp2_O)", "count", calculation_function=calc.calc_sp2_oxygen_count),
            DescriptorInfo("FormalCharge", "Total formal charge", DescriptorCategory.CONSTITUTIONAL, "sum(formal_charges)", "e", calculation_function=calc.calc_formal_charge),
            DescriptorInfo("UnsaturationCount", "Degree of unsaturation", DescriptorCategory.CONSTITUTIONAL, "DBE", "count", calculation_function=calc.calc_unsaturation_count),
            DescriptorInfo("AromaticProportion", "Proportion of aromatic atoms", DescriptorCategory.CONSTITUTIONAL, "aromatic/total", "fraction", calculation_function=calc.calc_aromatic_proportion),
            DescriptorInfo("AliphaticProportion", "Proportion of aliphatic atoms", DescriptorCategory.CONSTITUTIONAL, "aliphatic/total", "fraction", calculation_function=calc.calc_aliphatic_proportion),
            DescriptorInfo("SP3Proportion", "Proportion of sp3 hybridized carbons", DescriptorCategory.CONSTITUTIONAL, "sp3_C/total_C", "fraction", calculation_function=calc.calc_sp3_proportion),
            DescriptorInfo("HeteroProportion", "Proportion of hetero atoms", DescriptorCategory.CONSTITUTIONAL, "hetero/total", "fraction", calculation_function=calc.calc_hetero_proportion),
            DescriptorInfo("HCRatio", "Hydrogen to carbon ratio", DescriptorCategory.CONSTITUTIONAL, "H/C", "ratio", calculation_function=calc.calc_hc_ratio),
            DescriptorInfo("NCRatio", "Nitrogen to carbon ratio", DescriptorCategory.CONSTITUTIONAL, "N/C", "ratio", calculation_function=calc.calc_nc_ratio),
            DescriptorInfo("OCRatio", "Oxygen to carbon ratio", DescriptorCategory.CONSTITUTIONAL, "O/C", "ratio", calculation_function=calc.calc_oc_ratio),
            DescriptorInfo("AmideBondCount", "Number of amide bonds", DescriptorCategory.CONSTITUTIONAL, "count(amide_bonds)", "count", calculation_function=calc.calc_amide_bond_count),
            DescriptorInfo("EsterBondCount", "Number of ester bonds", DescriptorCategory.CONSTITUTIONAL, "count(ester_bonds)", "count", calculation_function=calc.calc_ester_bond_count),
            DescriptorInfo("CarbonylBondCount", "Number of carbonyl bonds", DescriptorCategory.CONSTITUTIONAL, "count(carbonyl_bonds)", "count", calculation_function=calc.calc_carbonyl_bond_count),
            DescriptorInfo("HydroxylGroupCount", "Number of hydroxyl (-OH) groups", DescriptorCategory.CONSTITUTIONAL, "count(OH_groups)", "count", calculation_function=calc.calc_hydroxyl_group_count),
            DescriptorInfo("CarboxylGroupCount", "Number of carboxyl (-COOH) groups", DescriptorCategory.CONSTITUTIONAL, "count(COOH_groups)", "count", calculation_function=calc.calc_carboxyl_group_count),
            DescriptorInfo("AmineGroupCount", "Number of amine groups", DescriptorCategory.CONSTITUTIONAL, "count(amine_groups)", "count", calculation_function=calc.calc_amine_group_count),
            DescriptorInfo("MethylGroupCount", "Number of methyl (-CH3) groups", DescriptorCategory.CONSTITUTIONAL, "count(methyl_groups)", "count", calculation_function=calc.calc_methyl_group_count),
            DescriptorInfo("LongestChain", "Length of longest carbon chain", DescriptorCategory.CONSTITUTIONAL, "max(chain_length)", "count", calculation_function=calc.calc_longest_chain),
            DescriptorInfo("BranchCount", "Number of branches", DescriptorCategory.CONSTITUTIONAL, "count(branches)", "count", calculation_function=calc.calc_branch_count),
            DescriptorInfo("FragmentCount", "Number of disconnected fragments", DescriptorCategory.CONSTITUTIONAL, "count(fragments)", "count", calculation_function=calc.calc_fragment_count),
        ]

    def _get_topological_descriptors(self) -> List[DescriptorInfo]:
        """Get topological (2D) descriptors."""
        calc = self.topological_calc
        return [
            DescriptorInfo("WienerIndex", "Wiener topological index", DescriptorCategory.TOPOLOGICAL, "sum(distance_matrix)", "index", calculation_function=calc.calc_wiener_index),
            DescriptorInfo("ZagrebIndex1", "First Zagreb index", DescriptorCategory.TOPOLOGICAL, "sum(degree^2)", "index", calculation_function=calc.calc_zagreb_index_1),
            DescriptorInfo("ZagrebIndex2", "Second Zagreb index", DescriptorCategory.TOPOLOGICAL, "sum(degree_i * degree_j)", "index", calculation_function=calc.calc_zagreb_index_2),
            DescriptorInfo("BalabanIndex", "Balaban J index", DescriptorCategory.TOPOLOGICAL, "J_index", "index", calculation_function=calc.calc_balaban_index),
            DescriptorInfo("HararyIndex", "Harary index", DescriptorCategory.TOPOLOGICAL, "sum(1/distance)", "index", calculation_function=calc.calc_harary_index),
            DescriptorInfo("RandicIndex", "Randic connectivity index", DescriptorCategory.TOPOLOGICAL, "chi_index", "index", calculation_function=calc.calc_randic_index),
            DescriptorInfo("ConnectivityIndexChi0", "Connectivity index (order 0)", DescriptorCategory.TOPOLOGICAL, "chi_0", "index", calculation_function=calc.calc_connectivity_index_chi0),
            DescriptorInfo("ConnectivityIndexChi1", "Connectivity index (order 1)", DescriptorCategory.TOPOLOGICAL, "chi_1", "index", calculation_function=calc.calc_connectivity_index_chi1),
            DescriptorInfo("KappaShapeIndex1", "Kappa shape index 1", DescriptorCategory.TOPOLOGICAL, "kappa_1", "index", calculation_function=calc.calc_kappa_shape_index_1),
            DescriptorInfo("KappaShapeIndex2", "Kappa shape index 2", DescriptorCategory.TOPOLOGICAL, "kappa_2", "index", calculation_function=calc.calc_kappa_shape_index_2),
            DescriptorInfo("KappaShapeIndex3", "Kappa shape index 3", DescriptorCategory.TOPOLOGICAL, "kappa_3", "index", calculation_function=calc.calc_kappa_shape_index_3),
            DescriptorInfo("HosoyaIndex", "Hosoya index (matchings)", DescriptorCategory.TOPOLOGICAL, "Z_index", "index", calculation_function=calc.calc_hosoya_index),
            DescriptorInfo("PlattIndex", "Platt index (edge degrees)", DescriptorCategory.TOPOLOGICAL, "sum(edge_degrees)", "index", calculation_function=calc.calc_platt_index),
            DescriptorInfo("PolarityNumber", "Polarity number", DescriptorCategory.TOPOLOGICAL, "count(3-dist_pairs)", "count", calculation_function=calc.calc_polarity_number),
            DescriptorInfo("BertzIndex", "Bertz complexity index", DescriptorCategory.TOPOLOGICAL, "complexity_based_index", "index", calculation_function=calc.calc_bertz_index),
            DescriptorInfo("BonchevTrinajsticIndex", "Bonchev-Trinajstic information index", DescriptorCategory.TOPOLOGICAL, "information_based_index", "index", calculation_function=calc.calc_bonchev_trinajstic_index),
            DescriptorInfo("InformationContent0", "Information content (order 0)", DescriptorCategory.TOPOLOGICAL, "entropy_based_index", "bits", calculation_function=calc.calc_information_content_0),
            DescriptorInfo("InformationContent1", "Information content (order 1)", DescriptorCategory.TOPOLOGICAL, "entropy_based_index", "bits", calculation_function=calc.calc_information_content_1),
            DescriptorInfo("EccentricConnectivityIndex", "Eccentric connectivity index", DescriptorCategory.TOPOLOGICAL, "sum(degree*eccentricity)", "index", calculation_function=calc.calc_eccentric_connectivity_index),
            DescriptorInfo("PathCount3", "Number of 3-atom paths", DescriptorCategory.TOPOLOGICAL, "count(3-paths)", "count", calculation_function=calc.calc_path_count_3),
            DescriptorInfo("PathCount4", "Number of 4-atom paths", DescriptorCategory.TOPOLOGICAL, "count(4-paths)", "count", calculation_function=calc.calc_path_count_4),
            DescriptorInfo("AveragePathLength", "Average topological path length", DescriptorCategory.TOPOLOGICAL, "avg_path_length", "index", calculation_function=calc.calc_average_path_length),
            DescriptorInfo("LongestShortestPath", "Longest shortest path (graph diameter)", DescriptorCategory.TOPOLOGICAL, "graph_diameter", "count", calculation_function=calc.calc_longest_shortest_path),
            DescriptorInfo("CyclomaticNumber", "Cyclomatic number (circuit rank)", DescriptorCategory.TOPOLOGICAL, "E - V + C", "count", calculation_function=calc.calc_cyclomatic_number),
            DescriptorInfo("ElectrotopologicalStateIndex", "Electrotopological state index", DescriptorCategory.TOPOLOGICAL, "electronic_topology_index", "index", calculation_function=calc.calc_electrotopological_state_index),
            DescriptorInfo("MolecularTopologicalIndex", "Molecular topological index", DescriptorCategory.TOPOLOGICAL, "topological_complexity", "index", calculation_function=calc.calc_molecular_topological_index),
            DescriptorInfo("HyperWienerIndex", "Hyper-Wiener index", DescriptorCategory.TOPOLOGICAL, "sum(distance + distance^2)", "index", calculation_function=calc.calc_hyper_wiener_index),
        ]

    def _get_geometric_descriptors(self) -> List[DescriptorInfo]:
        """Get geometric (3D) descriptors."""
        calc = self.geometric_calc
        return [
            DescriptorInfo("SASA", "Solvent Accessible Surface Area", DescriptorCategory.GEOMETRIC, "surface_area_calculation", "Å²", calculation_function=calc.calc_sasa),
            DescriptorInfo("MolecularVolume", "Molecular volume", DescriptorCategory.GEOMETRIC, "volume_calculation", "Å³", calculation_function=calc.calc_molecular_volume),
            DescriptorInfo("RadiusOfGyration", "Radius of gyration", DescriptorCategory.GEOMETRIC, "sqrt(sum((r - r_center)^2 / N)", "Å", calculation_function=calc.calc_radius_of_gyration),
            DescriptorInfo("Asphericity", "Molecular asphericity", DescriptorCategory.GEOMETRIC, "eigenvalue_based", "dimensionless", calculation_function=calc.calc_asphericity),
            DescriptorInfo("Eccentricity", "Molecular eccentricity", DescriptorCategory.GEOMETRIC, "eigenvalue_based", "dimensionless", calculation_function=calc.calc_eccentricity),
            DescriptorInfo("PrincipalMoment1", "First principal moment of inertia", DescriptorCategory.GEOMETRIC, "eigenvalue1", "Å²", calculation_function=calc.calc_principal_moment_1),
            DescriptorInfo("PrincipalMoment2", "Second principal moment of inertia", DescriptorCategory.GEOMETRIC, "eigenvalue2", "Å²", calculation_function=calc.calc_principal_moment_2),
            DescriptorInfo("PrincipalMoment3", "Third principal moment of inertia", DescriptorCategory.GEOMETRIC, "eigenvalue3", "Å²", calculation_function=calc.calc_principal_moment_3),
            DescriptorInfo("MolecularDiameter", "Molecular diameter (max distance)", DescriptorCategory.GEOMETRIC, "max_distance", "Å", calculation_function=calc.calc_molecular_diameter),
        ]

    def _get_electronic_descriptors(self) -> List[DescriptorInfo]:
        """Get electronic descriptors."""
        calc = self.electronic_calc
        return [
            DescriptorInfo("TotalCharge", "Total molecular charge", DescriptorCategory.ELECTRONIC, "sum(partial_charges)", "e", calculation_function=calc.calc_total_charge),
            DescriptorInfo("MaxPartialCharge", "Maximum partial charge", DescriptorCategory.ELECTRONIC, "max(partial_charges)", "e", calculation_function=calc.calc_max_partial_charge),
            DescriptorInfo("MinPartialCharge", "Minimum partial charge", DescriptorCategory.ELECTRONIC, "min(partial_charges)", "e", calculation_function=calc.calc_min_partial_charge),
            DescriptorInfo("MaxPositiveCharge", "Maximum positive partial charge", DescriptorCategory.ELECTRONIC, "max_positive", "e", calculation_function=calc.calc_max_positive_charge),
            DescriptorInfo("MaxNegativeCharge", "Maximum negative partial charge", DescriptorCategory.ELECTRONIC, "max_negative", "e", calculation_function=calc.calc_max_negative_charge),
            DescriptorInfo("DipoleMoment", "Molecular dipole moment", DescriptorCategory.ELECTRONIC, "sqrt(sum(charge * position)^2)", "Debye", calculation_function=calc.calc_dipole_moment),
            DescriptorInfo("PolarSurfaceArea", "Polar surface area", DescriptorCategory.ELECTRONIC, "surface_area_of_polar_atoms", "Å²", calculation_function=calc.calc_polar_surface_area),
            DescriptorInfo("APolarSurfaceArea", "Apolar (nonpolar) surface area", DescriptorCategory.ELECTRONIC, "surface_area_of_apolar_atoms", "Å²", calculation_function=calc.calc_apolar_surface_area),
            DescriptorInfo("MeanAbsoluteCharge", "Mean absolute partial charge", DescriptorCategory.ELECTRONIC, "mean(|charge|)", "e", calculation_function=calc.calc_mean_absolute_charge),
        ]

    def _get_quantum_descriptors(self) -> List[DescriptorInfo]:
        """Get quantum descriptors."""
        calc = self.quantum_calc
        return [
            DescriptorInfo("HOMOEnergy", "Highest Occupied Molecular Orbital energy", DescriptorCategory.QUANTUM, "quantum_calculation", "eV", calculation_function=calc.calc_homo_energy),
            DescriptorInfo("LUMOEnergy", "Lowest Unoccupied Molecular Orbital energy", DescriptorCategory.QUANTUM, "quantum_calculation", "eV", calculation_function=calc.calc_lumo_energy),
            DescriptorInfo("HOMOLUMOGap", "HOMO-LUMO energy gap", DescriptorCategory.QUANTUM, "LUMO - HOMO", "eV", calculation_function=calc.calc_homo_lumo_gap),
            DescriptorInfo("ChemicalPotential", "Chemical potential (electronegativity)", DescriptorCategory.QUANTUM, "(HOMO+LUMO)/2", "eV", calculation_function=calc.calc_chemical_potential),
            DescriptorInfo("ChemicalHardness", "Chemical hardness", DescriptorCategory.QUANTUM, "(LUMO-HOMO)/2", "eV", calculation_function=calc.calc_chemical_hardness),
            DescriptorInfo("Softness", "Molecular softness", DescriptorCategory.QUANTUM, "1/hardness", "1/eV", calculation_function=calc.calc_softness),
        ]

    def _get_fingerprint_descriptors(self) -> List[DescriptorInfo]:
        """Get fingerprint descriptors."""
        calc = self.fingerprint_calc
        return [
            DescriptorInfo("MorganFingerprint", "Morgan (circular) fingerprint", DescriptorCategory.FINGERPRINTS, "circular_fingerprint", "bits", calculation_function=calc.calc_morgan_fingerprint),
            DescriptorInfo("MACCSFingerprint", "MACCS keys fingerprint", DescriptorCategory.FINGERPRINTS, "structural_keys", "bits", calculation_function=calc.calc_maccs_fingerprint),
            DescriptorInfo("TopologicalFingerprint", "Topological fingerprint", DescriptorCategory.FINGERPRINTS, "topological_features", "bits", calculation_function=calc.calc_topological_fingerprint),
            DescriptorInfo("AtomPairFingerprint", "Atom pair fingerprint", DescriptorCategory.FINGERPRINTS, "atom_pairs", "bits", calculation_function=calc.calc_atom_pair_fingerprint),
        ]

    def _get_hybrid_descriptors(self) -> List[DescriptorInfo]:
        """Get hybrid/drug-like descriptors."""
        calc = self.hybrid_calc
        return [
            DescriptorInfo("Lipophilicity (LogP)", "Molecular lipophilicity (logP)", DescriptorCategory.HYBRID, "fragment_based_logP", "logP", calculation_function=calc.calc_lipophilicity),
            DescriptorInfo("Polarizability", "Molecular polarizability", DescriptorCategory.HYBRID, "sum(atomic_polarizabilities)", "Å³", calculation_function=calc.calc_polarizability),
            DescriptorInfo("MolarRefractivity", "Molar refractivity", DescriptorCategory.HYBRID, "fragment_based_calculation", "cm³/mol", calculation_function=calc.calc_molar_refractivity),
            DescriptorInfo("LipinskiHBA", "Lipinski H-bond acceptors", DescriptorCategory.HYBRID, "lipinski_hba", "count", calculation_function=calc.calc_lipinski_hba),
            DescriptorInfo("LipinskiHBD", "Lipinski H-bond donors", DescriptorCategory.HYBRID, "lipinski_hbd", "count", calculation_function=calc.calc_lipinski_hbd),
            DescriptorInfo("LipinskiViolationCount", "Lipinski rule of 5 violations", DescriptorCategory.HYBRID, "lipinski_violations", "count", calculation_function=calc.calc_lipinski_violations),
            DescriptorInfo("VeberTPSA", "Veber polar surface area", DescriptorCategory.HYBRID, "veber_psa", "Å²", calculation_function=calc.calc_veber_tpsa),
            DescriptorInfo("DrugLikenessScore", "Drug-likeness score", DescriptorCategory.HYBRID, "drug_score", "score", calculation_function=calc.calc_drug_likeness_score),
            DescriptorInfo("SyntheticAccessibility", "Synthetic accessibility score", DescriptorCategory.HYBRID, "SA_score", "score", calculation_function=calc.calc_synthetic_accessibility),
            DescriptorInfo("Fsp3", "Fraction sp3 hybridized atoms", DescriptorCategory.HYBRID, "sp3/total_C", "fraction", calculation_function=calc.calc_fsp3),
        ]

    def _get_custom_descriptors(self) -> List[DescriptorInfo]:
        """Get custom descriptors."""
        calc = self.constitutional_calc
        return [
            DescriptorInfo("SelectionSize", "Number of atoms in selection", DescriptorCategory.CUSTOM, "len(selection)", "count", calculation_function=calc.calc_atom_count),
            DescriptorInfo("SelectionDensity", "Density of selected atoms", DescriptorCategory.CUSTOM, "selection_size / molecular_volume", "atoms/Å³", calculation_function=self._calc_selection_density),
        ]

    def _calc_selection_density(self, molecule, selection) -> float:
        """Calculate selection density."""
        volume = self.geometric_calc.calc_molecular_volume(molecule, selection)
        if volume > 0:
            return len(selection.atom_indices) / volume
        return 0.0

    def calculate_descriptor(self, molecule: Molecule, descriptor_name: str,
                           selection: Optional[AtomSelection] = None) -> DescriptorResult:
        """Calculate a single descriptor value."""
        if selection is None:
            selection = AtomSelection(
                selection_type=SelectionType.ALL,
                atom_indices=list(range(len(molecule.atoms)))
            )

        for category, descriptors in self.descriptors.items():
            for desc in descriptors:
                if desc.name == descriptor_name:
                    if self.cache:
                        cache_key = self.cache.get_cache_key(molecule, selection, descriptor_name)
                        cached_value = self.cache.get(cache_key)
                        if cached_value is not None:
                            return DescriptorResult(
                                descriptor_name=descriptor_name,
                                value=cached_value,
                            )

                    try:
                        value = desc.calculation_function(molecule, selection)
                        if self.cache:
                            self.cache.set(cache_key, value)
                        return DescriptorResult(
                            descriptor_name=descriptor_name,
                            value=value,
                        )
                    except Exception as e:
                        import traceback
                        print(f"[DESCRIPTOR ERROR] {descriptor_name}: {e}")
                        traceback.print_exc()
                        return DescriptorResult(
                            descriptor_name=descriptor_name,
                            value=None,
                        )

        return DescriptorResult(
            descriptor_name=descriptor_name,
            value=None,
        )

    def calculate_all(self, molecule: Molecule,
                   selection: Optional[AtomSelection] = None,
                   categories: Optional[List[DescriptorCategory]] = None,
                   progress_callback: Optional[Callable[[CalculationProgress], None]] = None) -> Dict[str, DescriptorResult]:
        """Calculate all descriptors for a molecule."""
        if selection is None:
            selection = AtomSelection(
                selection_type=SelectionType.ALL,
                atom_indices=list(range(len(molecule.atoms)))
            )

        results = {}
        categories_to_calc = categories or list(DescriptorCategory)

        total = sum(len(self.descriptors.get(cat, [])) for cat in categories_to_calc)
        completed = 0

        for category in categories_to_calc:
            for desc in self.descriptors.get(category, []):
                result = self.calculate_descriptor(molecule, desc.name, selection)
                results[desc.name] = result

                completed += 1
                if progress_callback:
                    progress = CalculationProgress(
                        current_descriptor=desc.name,
                        current_category=category.value,
                        completed=completed,
                        total=total,
                        percentage=100 * completed / total,
                    )
                    progress_callback(progress)

        return results

    def get_descriptor_info(self, descriptor_name: str) -> Optional[DescriptorInfo]:
        """Get information about a specific descriptor."""
        for category, descriptors in self.descriptors.items():
            for desc in descriptors:
                if desc.name == descriptor_name:
                    return desc
        return None

    def list_descriptors(self, category: Optional[DescriptorCategory] = None) -> List[str]:
        """List available descriptors."""
        if category:
            return [desc.name for desc in self.descriptors.get(category, [])]
        return [desc.name for descriptors in self.descriptors.values() for desc in descriptors]

    def clear_cache(self):
        """Clear the calculation cache."""
        if self.cache:
            self.cache.clear()

    def set_progress_callback(self, callback: Optional[Callable[[CalculationProgress], None]]):
        """Set a progress callback for calculations."""
        self.progress_callback = callback

    def calculate_descriptors(self, molecule: Molecule, selection: AtomSelection,
                             categories: List[DescriptorCategory]) -> Dict[str, DescriptorResult]:
        """Calculate descriptors for given categories (GUI compatibility method)."""
        return self.calculate_all(molecule, selection, categories, self.progress_callback)
