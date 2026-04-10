# Testing Folder

This folder contains automated tests for the SMILES to 3D application.

## Test Files

### gui_layout_tests.py
Tests for the GUI layout changes including:
- Installed Plugins dialog functionality
- Horizontal splitter sizing (75% main area)
- Menu structure updates

## Running Tests

```bash
cd d:\coded_By_Me\SMILES
python testing\gui_layout_tests.py
```

## Test Categories

### Unit Tests
Test individual components in isolation:
- Dialog creation and widget initialization
- Plugin selection and management
- Layout calculations

### Integration Tests
Test component interactions:
- Dialog signals and main window communication
- Menu action connections
- Plugin system integration

## Notes

- Tests require PySide6 to be installed
- Some GUI tests use mock objects to avoid needing a full application instance
- Tests are designed to run in a headless environment for CI/CD

## Adding New Tests

When adding new tests:
1. Create a new test class inheriting from `unittest.TestCase`
2. Use `setUpClass` to initialize QApplication if needed
3. Add descriptive test method names starting with `test_`
4. Run tests with `python testing\gui_layout_tests.py -v`

## Future Test Plans

- Add visual regression tests for GUI changes
- Add performance tests for large molecule loading
- Add plugin loading/unloading stress tests
