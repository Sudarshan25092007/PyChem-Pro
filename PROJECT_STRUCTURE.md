# SMILES Molecular Toolkit - Project Structure

## 📁 Clean Project Organization

The SMILES molecular toolkit has been reorganized for better maintainability and clarity.

## 📂 Directory Structure

```
SMILES/
├── 📄 Essential Files
│   ├── main.py                 # Main application entry point
│   ├── run_app.bat            # Windows application launcher
│   ├── requirements.txt       # Python dependencies
│   ├── build.py               # Build and packaging script
│   └── PROJECT_STRUCTURE.md   # This file
│
├── 📦 src/                    # Source code (essential)
│   ├── app/                   # Application GUI and main window
│   ├── core/                  # Core domain models (Molecule, Atom, Bond)
│   ├── features/              # Feature implementations
│   │   ├── cheminformatics/   # Quantum methods (AM1, PM3, MMFF94)
│   │   ├── visualization_3d/  # 3D molecular visualization
│   │   ├── visualization_2d/  # 2D molecular visualization
│   │   └── ...                # Other features
│   └── shared/                # Shared utilities and UI components
│
├── 🧪 tests/                  # Unit tests (essential)
│   ├── test_am1.py           # AM1 method unit tests
│   ├── test_mmff94.py        # MMFF94 method unit tests
│   └── ...                   # Other unit tests
│
├── 🔬 testing/               # Development and debugging tests
│   ├── README.md             # Testing documentation
│   ├── debug_am1_failure.py  # AM1 debugging script
│   ├── debug_cartoon.py      # PyMOL debugging script
│   ├── test_am1_performance.py # AM1 performance tests
│   └── example_2D.py         # 2D example script
│
└── 📚 docs/                   # Complete documentation
    ├── DOCUMENTATION_INDEX.md # Master documentation index
    ├── AM1_SEMIEMPIRICAL_IMPLEMENTATION.md
    ├── PM3_IMPLEMENTATION_AND_AM1_PERFORMANCE_FIX.md
    ├── AM1_GUI_INTEGRATION.md
    ├── AM1_CHARGE_CALCULATION_FIX.md
    ├── MMFF94_OPTIMIZATION_FIX.md
    ├── PYMOL_CARTOON_FIX_COMPLETE.md
    ├── LARGE_PDB_PERFORMANCE.md
    └── ...                   # All other documentation files
```

## 🎯 File Classification

### ✅ Essential Files (Keep in Root)
These files are required for running the application:
- **`main.py`** - Application entry point
- **`run_app.bat`** - Windows launcher
- **`requirements.txt`** - Dependencies
- **`build.py`** - Build script
- **`src/`** - All source code
- **`tests/`** - Unit tests

### 🧪 Testing Files (Moved to `testing/`)
Development and debugging scripts:
- **`debug_am1_failure.py`** - AM1 debugging
- **`debug_cartoon.py`** - PyMOL debugging
- **`test_am1_performance.py`** - Performance tests
- **`example_2D.py`** - 2D examples

### 📚 Documentation Files (Moved to `docs/`)
All project documentation:
- **Implementation guides** - AM1, PM3, MMFF94
- **Fix documentation** - Performance and bug fixes
- **User guides** - GUI integration and usage
- **Technical specs** - Architecture and design

## 🚀 Quick Start

### For Users
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
# or
run_app.bat
```

### For Developers
```bash
# Run unit tests
python -m pytest tests/

# Run development tests
python testing/debug_am1_failure.py
python testing/test_am1_performance.py

# View documentation
cat docs/DOCUMENTATION_INDEX.md
```

## 📋 Recent Changes

### ✅ Completed Organization
1. **Created `testing/` folder** - All development scripts moved here
2. **Organized `docs/` folder** - All documentation consolidated
3. **Clean root directory** - Only essential files remain
4. **Added documentation** - Comprehensive README and index files
5. **Updated structure docs** - Clear file classification

### 📊 Before vs After

#### Before (Cluttered Root)
```
SMILES/
├── main.py
├── run_app.bat
├── requirements.txt
├── build.py
├── debug_am1_failure.py      # ❌ Clutter
├── debug_cartoon.py          # ❌ Clutter
├── test_am1_performance.py   # ❌ Clutter
├── example_2D.py             # ❌ Clutter
├── AM1_*.md                  # ❌ Many docs
├── PM3_*.md                  # ❌ Many docs
├── MMFF94_*.md               # ❌ Many docs
├── PYMOL_*.md                # ❌ Many docs
└── ... (15+ more files)      # ❌ Hard to navigate
```

#### After (Organized)
```
SMILES/
├── main.py                   # ✅ Essential
├── run_app.bat              # ✅ Essential
├── requirements.txt         # ✅ Essential
├── build.py                 # ✅ Essential
├── src/                     # ✅ Essential
├── tests/                   # ✅ Essential
├── testing/                 # ✅ Organized tests
│   ├── README.md
│   └── *.py (all test files)
├── docs/                    # ✅ Organized docs
│   ├── DOCUMENTATION_INDEX.md
│   └── *.md (all docs)
└── PROJECT_STRUCTURE.md     # ✅ This guide
```

## 🔧 Maintenance Guidelines

### Adding New Files
- **Source code**: Add to appropriate `src/` subdirectory
- **Unit tests**: Add to `tests/` directory
- **Development tests**: Add to `testing/` directory
- **Documentation**: Add to `docs/` directory and update index

### File Naming Conventions
- **Tests**: `test_[feature].py` (unit tests) or `debug_[issue].py` (debugging)
- **Documentation**: `[FEATURE]_[DESCRIPTION].md`
- **Source**: Follow existing naming patterns in `src/`

### Documentation Updates
- **New features**: Update relevant documentation files
- **Bug fixes**: Document fixes in appropriate files
- **API changes**: Update implementation guides
- **Index maintenance**: Keep `DOCUMENTATION_INDEX.md` current

## 📈 Benefits of New Structure

### 🎯 For Users
- **Clean installation**: Only essential files in root
- **Easy navigation**: Clear separation of concerns
- **Better documentation**: Organized and indexed

### 👨‍💻 For Developers
- **Focused development**: Tests separated from production code
- **Easy debugging**: Centralized testing scripts
- **Comprehensive docs**: Well-organized documentation

### 🔧 For Maintenance
- **Clean repository**: Easy to understand structure
- **Scalable organization**: Room for growth
- **Version control**: Better file tracking

## 📞 Support

### Finding Information
- **General help**: Check `docs/DOCUMENTATION_INDEX.md`
- **Specific issues**: Look in relevant documentation files
- **Development**: Use scripts in `testing/` folder
- **API reference**: Check implementation guides

### Contributing
- **Code changes**: Follow existing patterns in `src/`
- **Tests**: Add to appropriate test directories
- **Documentation**: Update docs and index
- **Structure**: Maintain this organization

---

**Last Updated**: March 19, 2026  
**Purpose**: Project organization and structure guide  
**Maintainer**: SMILES Molecular Toolkit Development Team
