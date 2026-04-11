"""
Service registry — central wiring point for all PyChem services.

No DI framework. A plain Python class with factory methods.
Created once at startup, passed to consumers via constructor.
"""
from src.core.parallel import ParallelExecutor
from src.core.events import EventBus


class ServiceRegistry:
    """
    Constructs and holds all service instances.

    Usage:
        registry = ServiceRegistry()
        mol = registry.loader.load("protein.pdb")
        registry.forcefield.optimize_geometry(mol)

    Services are added incrementally as they are implemented.
    Initially only executor and event_bus are available.
    """

    def __init__(self):
        self.executor = ParallelExecutor()
        self.event_bus = EventBus()
        # Services added in later phases:
        # self.forcefield = MMFF94Service(self.executor)
        # self.loader = LoaderService(self.executor)
        # self.coord_gen = CoordinateGeneratorService(self.executor)
        # self.descriptors = DescriptorService(self.executor)
        # self.renderer_factory = RendererFactory()

    def shutdown(self):
        """Clean shutdown of all services."""
        self.executor.shutdown()
