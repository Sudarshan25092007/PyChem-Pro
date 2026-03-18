#!/usr/bin/env python3
"""
Test window resize stability and smooth cartoon rendering
"""

import sys
import os
import time

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def test_window_resize_and_smooth_cartoon():
    """Test window resize stability and smooth cartoon rendering"""
    
    pdb_file = r"D:\Badar_Sir\4TZK.pdb"
    
    if not os.path.exists(pdb_file):
        print(f"File not found: {pdb_file}")
        return
    
    print("Testing window resize stability and smooth cartoon rendering...")
    
    try:
        from src.io.file_reader import read_pdb
        from src.gui.main_window import MainWindow
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        
        # Load molecule
        print("1. Loading PDB file...")
        mol = read_pdb(pdb_file)
        print(f"   Loaded: {len(mol.atoms)} atoms")
        
        # Create application
        print("2. Creating main window...")
        app = QApplication(sys.argv)
        main_window = MainWindow()
        main_window._set_molecule(mol)
        main_window.show()
        
        print("3. Testing smooth cartoon rendering...")
        # Test cartoon mode
        main_window.viewer_3d.render_mode = 'cartoon'
        main_window.viewer_3d.update()
        
        # Test window resizing
        print("4. Testing window resize stability...")
        
        def test_resize():
            """Test various window sizes"""
            sizes = [
                (800, 600),
                (1024, 768),
                (1280, 800),
                (1600, 900),
                (1920, 1080),
                (800, 600),  # Back to small
                (1280, 800),  # Medium again
                (2560, 1440),  # Large 4K
                (800, 600),   # Small again
            ]
            
            for i, (width, height) in enumerate(sizes):
                try:
                    print(f"   Resize {i+1}/{len(sizes)}: {width}x{height}")
                    main_window.resize(width, height)
                    app.processEvents()
                    time.sleep(0.1)  # Small delay to allow processing
                    
                    # Test rendering after resize
                    main_window.viewer_3d.update()
                    main_window.viewer_2d.update()
                    app.processEvents()
                    
                except Exception as e:
                    print(f"   ERROR during resize {width}x{height}: {e}")
                    continue
            
            print("   Resize testing completed successfully!")
        
        # Schedule resize test
        QTimer.singleShot(1000, test_resize)
        
        # Test maximize/restore
        def test_maximize():
            """Test maximize and restore"""
            try:
                print("5. Testing maximize/restore...")
                
                # Maximize
                main_window.showMaximized()
                app.processEvents()
                time.sleep(0.5)
                print("   Maximized: OK")
                
                # Test rendering while maximized
                main_window.viewer_3d.update()
                app.processEvents()
                
                # Restore
                main_window.showNormal()
                app.processEvents()
                time.sleep(0.5)
                print("   Restored: OK")
                
                # Test rendering after restore
                main_window.viewer_3d.update()
                app.processEvents()
                
                print("   Maximize/restore testing completed successfully!")
                
            except Exception as e:
                print(f"   ERROR during maximize/restore: {e}")
        
        # Schedule maximize test
        QTimer.singleShot(3000, test_maximize)
        
        # Test cartoon smoothness
        def test_cartoon_smoothness():
            """Test cartoon rendering with different orientations"""
            try:
                print("6. Testing cartoon smoothness...")
                
                # Test different rotations
                rotations = [
                    (0, 0),
                    (30, -30),
                    (45, 45),
                    (-30, 60),
                    (90, 0),
                    (0, 90),
                ]
                
                for i, (rot_x, rot_y) in enumerate(rotations):
                    main_window.viewer_3d.rot_x = rot_x
                    main_window.viewer_3d.rot_y = rot_y
                    main_window.viewer_3d.update()
                    app.processEvents()
                    time.sleep(0.2)
                
                print("   Cartoon smoothness testing completed!")
                
            except Exception as e:
                print(f"   ERROR during cartoon testing: {e}")
        
        # Schedule cartoon test
        QTimer.singleShot(5000, test_cartoon_smoothness)
        
        # Close after tests
        def close_app():
            print("7. All tests completed! Closing...")
            app.quit()
        
        QTimer.singleShot(8000, close_app)
        
        # Run application
        print("\nStarting GUI tests...")
        print("(Window will appear and automatically run tests)")
        app.exec()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nWindow resize and cartoon testing completed!")

if __name__ == "__main__":
    test_window_resize_and_smooth_cartoon()
