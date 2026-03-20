# Testing and Development Scripts

This folder contains testing scripts and debugging tools used during development of the SMILES molecular toolkit.

## Files Description

### 🐛 Debugging Scripts

#### `debug_am1_failure.py`
- **Purpose**: Debug AM1 charge calculation failures
- **Usage**: `python debug_am1_failure.py`
- **Tests**: H₂, H₂O, unsupported elements
- **Output**: Detailed SCF convergence information and charge results

#### `debug_cartoon.py`
- **Purpose**: Debug PyMOL cartoon rendering issues
- **Usage**: `python debug_cartoon.py`
- **Tests**: Cartoon visibility and styling problems
- **Output**: Rendering diagnostics and fixes

### ⚡ Performance Tests

#### `test_am1_performance.py`
- **Purpose**: Test AM1 optimization performance improvements
- **Usage**: `python test_am1_performance.py`
- **Tests**: Water and methanol optimization speed
- **Output**: Timing results and convergence metrics

### 📚 Examples

#### `example_2D.py`
- **Purpose**: Demonstrate 2D molecular operations
- **Usage**: `python example_2D.py`
- **Tests**: 2D coordinate generation and optimization
- **Output**: 2D molecular visualization examples

## Running Tests

### Prerequisites
Ensure you're in the SMILES root directory:
```bash
cd /path/to/SMILES
```

### Run Individual Tests
```bash
# Run AM1 debugging
python testing/debug_am1_failure.py

# Run performance tests
python testing/test_am1_performance.py

# Run cartoon debugging
python testing/debug_cartoon.py

# Run 2D example
python testing/example_2D.py
```

### Run All Tests
```bash
# Simple test runner
for file in testing/*.py; do
    echo "Running $file..."
    python "$file"
    echo "---"
done
```

## Test Categories

### 🔬 Quantum Method Tests
- **AM1**: Charge calculation and optimization
- **PM3**: Charge calculation and comparison with AM1
- **Convergence**: SCF procedure stability
- **Performance**: Optimization speed improvements

### 🎨 Visualization Tests
- **PyMOL Integration**: Cartoon rendering fixes
- **3D Visualization**: Molecular display issues
- **2D Visualization**: Coordinate generation and layout

### ⚡ Performance Tests
- **Optimization Speed**: AM1 vs MMFF94 performance
- **Large Molecules**: Performance with increasing size
- **Memory Usage**: Resource consumption analysis

### 🐛 Debugging Tools
- **Error Diagnosis**: Identify common failure points
- **Convergence Issues**: SCF oscillation detection
- **Parameter Validation**: Method-specific parameter checks

## Expected Outputs

### Successful AM1 Test
```
=== AM1 Debug Script ===
1. Testing H2 molecule...
   H2 AM1 success: True
   H2 charges: [0.000, 0.000]
```

### Successful Performance Test
```
=== AM1 Performance Test ===
Completed in 0.36 seconds
Success: True
[PASS] AM1 optimization working efficiently
```

### Common Issues and Solutions

#### Import Errors
- **Issue**: `ModuleNotFoundError`
- **Solution**: Ensure you're running from SMILES root directory
- **Check**: Python path includes `src/` directory

#### Convergence Failures
- **Issue**: SCF does not converge
- **Solution**: Methods now use approximations for GUI compatibility
- **Check**: Status messages for specific error information

#### Performance Issues
- **Issue**: Tests running slowly
- **Solution**: AM1 optimization has been ~20x speedup
- **Check**: Test results should complete in seconds

## Development Guidelines

### Adding New Tests
1. **Create descriptive filename**: `test_[feature].py` or `debug_[issue].py`
2. **Add documentation**: Include purpose, usage, and expected output
3. **Update README**: Add new test to this documentation
4. **Test integration**: Ensure tests work with current codebase

### Test Standards
- **Error handling**: Catch and report exceptions clearly
- **Output formatting**: Use consistent, readable output format
- **Performance timing**: Include timing information for performance tests
- **Success indicators**: Clear PASS/FAIL indicators

### Maintenance
- **Regular updates**: Keep tests current with codebase changes
- **Documentation**: Update this README when adding tests
- **Cleanup**: Remove obsolete tests and update documentation

## Integration with Main Application

### Test Results in Development
- **AM1 fixes**: Performance improvements integrated into main codebase
- **PM3 implementation**: Full integration with GUI
- **Visualization fixes**: PyMOL rendering improvements
- **Documentation**: Comprehensive documentation updates

### Continuous Testing
- **Before commits**: Run relevant tests to ensure no regressions
- **After changes**: Update tests to reflect new functionality
- **Performance monitoring**: Track optimization improvements over time

---

**Note**: These testing scripts are for development and debugging purposes. They are not required for normal operation of the SMILES molecular toolkit but are invaluable for development and troubleshooting.
