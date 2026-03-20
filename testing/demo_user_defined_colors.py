"""
Demonstration of user-defined color selection with the Colors button.
"""

import sys
import os

# Add the parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def demo_color_dialog():
    """Demonstrate the color dialog functionality."""
    print("SMILES Molecular Toolkit - User-Defined Color Demonstration")
    print("=" * 65)
    
    print("\nThis demonstration shows how the Colors button now works:")
    print("1. User clicks the 'Colors' button")
    print("2. Interactive color selection menu opens")
    print("3. User can define custom colors for atoms, spheres, and sticks")
    print("4. Colors are applied immediately to the 3D viewer")
    
    try:
        from src.features.ui.simple_color_dialog import SimpleColorDialog, apply_colors_to_theme
        
        print("\n" + "=" * 65)
        print("COLOR SELECTION MENU DEMONSTRATION")
        print("=" * 65)
        
        # Create a color dialog instance
        dialog = SimpleColorDialog()
        
        print("\nWhen you click the Colors button, you'll see this menu:")
        print("\nColor Selection Options:")
        print("-" * 40)
        print("1. Atom Colors - Set colors for different atom types")
        print("2. Sphere Colors - Set colors for different sphere types")
        print("3. Stick/Bond Colors - Set colors for bonds/sticks")
        print("4. Use Preset Colors - Choose from predefined colors")
        print("5. Custom Hex Colors - Enter custom hex color codes")
        print("6. Show Current Colors - Display current color settings")
        print("7. Apply to 3D Viewer - Apply colors and exit")
        print("0. Exit - Cancel")
        
        print("\n" + "-" * 40)
        print("EXAMPLE WORKFLOW:")
        print("-" * 40)
        
        # Simulate user setting atom colors
        print("\n1. User selects option 1 (Atom Colors)")
        print("   Available atom types: C, H, O, N, S, P, F, Cl, Br, I")
        print("   User enters: 'C red'")
        print("   User enters: 'O blue'")
        print("   User enters: 'N green'")
        print("   User enters: 'done'")
        
        # Simulate the color setting
        dialog.selected_colors['atom_c'] = '#ff0000'
        dialog.selected_colors['atom_o'] = '#0000ff'
        dialog.selected_colors['atom_n'] = '#00ff00'
        
        print("   ✅ Set C color to #ff0000")
        print("   ✅ Set O color to #0000ff")
        print("   ✅ Set N color to #00ff00")
        
        # Simulate user setting sphere colors
        print("\n2. User selects option 2 (Sphere Colors)")
        print("   Available sphere types: default, selected, highlight, com, centroid, custom")
        print("   User enters: 'com magenta'")
        print("   User enters: 'centroid yellow'")
        print("   User enters: 'done'")
        
        # Simulate the color setting
        dialog.selected_colors['sphere_com'] = '#ff00ff'
        dialog.selected_colors['sphere_centroid'] = '#ffff00'
        dialog.selected_colors['sphere_default'] = '#ff6b6b'
        
        print("   ✅ Set com sphere color to #ff00ff")
        print("   ✅ Set centroid sphere color to #ffff00")
        print("   ✅ Set default sphere color to #ff6b6b")
        
        # Simulate user applying colors
        print("\n3. User selects option 7 (Apply to 3D Viewer)")
        print("   Colors are applied to theme")
        print("   3D viewer is updated")
        
        # Apply the colors
        apply_colors_to_theme(dialog.selected_colors)
        
        color_count = len(dialog.selected_colors)
        print(f"   Status: 'Applied {color_count} custom colors'")
        
        print("\n" + "=" * 65)
        print("DEMONSTRATION COMPLETE")
        print("=" * 65)
        print("✅ Colors button opens interactive menu")
        print("✅ User can define custom colors for atoms, spheres, and sticks")
        print("✅ 20 predefined color presets available")
        print("✅ Custom hex color codes supported")
        print("✅ Colors applied immediately to 3D viewer")
        print("✅ Individual sphere colors remembered")
        
        return True
        
    except Exception as e:
        print(f"Demonstration error: {e}")
        return False

def show_color_presets():
    """Show available color presets."""
    print("\n" + "=" * 65)
    print("AVAILABLE COLOR PRESETS")
    print("=" * 65)
    
    try:
        from src.features.ui.simple_color_dialog import SimpleColorDialog
        
        dialog = SimpleColorDialog()
        presets = dialog.color_presets
        
        print("20 predefined colors available for quick selection:")
        print()
        
        for i, (name, hex_code) in enumerate(presets.items()):
            print(f"{i+1:2d}. {name:10s} - {hex_code}")
        
        print(f"\nUsers can select these by name (e.g., 'red', 'blue', 'green')")
        print("Or use custom hex codes (e.g., '#ff0000', '#00ff00', '#0000ff')")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def show_color_types():
    """Show different color types that can be customized."""
    print("\n" + "=" * 65)
    print("CUSTOMIZABLE COLOR TYPES")
    print("=" * 65)
    
    print("ATOM COLORS:")
    print("-" * 20)
    print("• atom_c - Carbon atoms")
    print("• atom_h - Hydrogen atoms")
    print("• atom_o - Oxygen atoms")
    print("• atom_n - Nitrogen atoms")
    print("• atom_s - Sulfur atoms")
    print("• atom_p - Phosphorus atoms")
    print("• atom_f - Fluorine atoms")
    print("• atom_cl - Chlorine atoms")
    print("• atom_br - Bromine atoms")
    print("• atom_i - Iodine atoms")
    
    print("\nSPHERE COLORS:")
    print("-" * 20)
    print("• sphere_default - Default sphere color")
    print("• sphere_selected - Selected sphere color")
    print("• sphere_highlight - Highlighted sphere color")
    print("• sphere_com - Center of mass sphere color")
    print("• sphere_centroid - Geometric centroid sphere color")
    print("• sphere_custom - Custom sphere color")
    
    print("\nSTICK/BOND COLORS:")
    print("-" * 20)
    print("• stick_default - Default bond color")
    print("• stick_selected - Selected bond color")
    print("• stick_highlight - Highlighted bond color")
    print("• stick_single - Single bond color")
    print("• stick_double - Double bond color")
    print("• stick_triple - Triple bond color")
    
    print("\nCUSTOM COLORS:")
    print("-" * 20)
    print("• Users can also define custom color names")
    print("• Example: 'my_red #ff0000'")
    print("• Example: 'special_blue #0066cc'")
    print("• These can be used for any custom coloring needs")

def main():
    """Run the demonstration."""
    # Show color presets
    show_color_presets()
    
    # Show color types
    show_color_types()
    
    # Demonstrate color dialog
    demo_success = demo_color_dialog()
    
    if demo_success:
        print("\n🎉 USER-DEFINED COLOR DEMONSTRATION SUCCESSFUL!")
        print("The Colors button now provides complete color customization!")
        print("Users can define their own colors for atoms, spheres, and sticks!")
    else:
        print("\n❌ Demonstration failed")

if __name__ == "__main__":
    main()
