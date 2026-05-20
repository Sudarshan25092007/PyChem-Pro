import sys
import re

def patch_gl():
    with open('src/features/visualization_3d/ui/gl_widget.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Imports
    content = content.replace(
        "QOpenGLShaderProgram, QOpenGLShader, QOpenGLBuffer, COLORS",
        "QOpenGLShaderProgram, QOpenGLShader, QOpenGLBuffer, Signal, COLORS"
    )

    # 2. Signals
    content = content.replace(
        "    zoom : float\n        Zoom factor (pixels per Angstrom, roughly).\n    \"\"\"\n\n    def __init__(self, parent=None):",
        "    zoom : float\n        Zoom factor (pixels per Angstrom, roughly).\n    \"\"\"\n    \n    # Signals (matching MolViewer3D)\n    atom_hovered = Signal(int)\n    atom_clicked = Signal(int)\n    selection_changed = Signal(object)\n    delete_requested = Signal(object)\n\n    def __init__(self, parent=None):"
    )

    # 3. _num_mesh_indices -> _num_mesh_vertices
    content = content.replace(
        "self._vbo_mesh = None\n        self._num_mesh_indices = 0\n        self._vao_atoms = None\n        self._vao_mesh = None",
        "self._vbo_mesh = None\n        self._num_mesh_vertices = 0\n        self._vao_atoms = None\n        self._vao_mesh = None"
    )

    # 4. Centering
    old_centering = """        for i, atom in enumerate(atoms):
            if atom.has_coords:
                positions[i] = [atom.x, atom.y, atom.z if atom.z is not None else 0.0]
            c = _element_color_float(atom.symbol)
            colors[i] = c
            radii[i] = _display_radius(atom.symbol)
            symbols.append(atom.symbol)

        self._positions = positions"""
    
    new_centering = """        for i, atom in enumerate(atoms):
            if atom.has_coords:
                positions[i] = [atom.x, atom.y, atom.z if atom.z is not None else 0.0]
            c = _element_color_float(atom.symbol)
            colors[i] = c
            radii[i] = _display_radius(atom.symbol)
            symbols.append(atom.symbol)
            
        # Center to origin
        if n > 0:
            self._centroid = np.mean(positions, axis=0)
            positions -= self._centroid
        else:
            self._centroid = np.zeros(3, dtype=np.float32)

        self._positions = positions"""
    content = content.replace(old_centering, new_centering)

    # 5. initializeGL VAOs
    old_init = """            gl.glEnable(0x8861)   # GL_MULTISAMPLE

            self._init_shaders()
            self.gl_available = True
            print(f"[GL] Context ready — OpenGL {major}.{minor} Renderer: {self._gl_renderer_string}")"""
            
    new_init = """            gl.glEnable(0x8861)   # GL_MULTISAMPLE

            self._init_shaders()
            
            from src.shared.qt_compat import QOpenGLVertexArrayObject
            self._vao_atoms = QOpenGLVertexArrayObject()
            self._vao_atoms.create()
            
            self._vao_mesh = QOpenGLVertexArrayObject()
            self._vao_mesh.create()

            self.gl_available = True
            print(f"[GL] Context ready — OpenGL {major}.{minor} Renderer: {self._gl_renderer_string}")"""
    content = content.replace(old_init, new_init)

    # 6. paintGL bindings
    old_paint = """            # 1. Draw Mesh (Protein Cartoon)
            if self._vbo_mesh and self._num_mesh_indices > 0:
                self._draw_mesh(gl, proj, view)
                
            # 2. Draw Atoms (Sphere Impostors)
            if self._vbo_atoms and len(self._positions) > 0:
                self._draw_atoms(gl, proj, view)"""
                
    new_paint = """            # 1. Draw Mesh (Protein Cartoon)
            if self._vbo_mesh and getattr(self, '_num_mesh_vertices', 0) > 0:
                if self._vao_mesh: self._vao_mesh.bind()
                self._draw_mesh(gl, proj, view)
                if self._vao_mesh: self._vao_mesh.release()
                
            # 2. Draw Atoms (Sphere Impostors)
            if self._vbo_atoms and len(self._positions) > 0:
                if self._vao_atoms: self._vao_atoms.bind()
                self._draw_atoms(gl, proj, view)
                if self._vao_atoms: self._vao_atoms.release()"""
    content = content.replace(old_paint, new_paint)
    
    # 7. update buffers
    pattern = re.compile(r"    def _update_gl_buffers\(self\):.*?    def _get_projection_matrix\(self\):", re.DOTALL)
    new_buffers = """    def _update_gl_buffers(self):
        \"\"\"Upload molecule data to GPU buffers.\"\"\"
        if not self.gl_available: return
        import time
        t_upd = time.time()
        try:
            self.makeCurrent()
            gl = self.context().functions()
            
            # 1. Atoms Buffer (Center, Color, Radius, Offset)
            if self._vbo_atoms: self._vbo_atoms.destroy()
            n = len(self._positions)
            if n > 0:
                import numpy as np
                data = np.zeros(n * 6 * 9, dtype=np.float32)
                for i in range(6):
                    data[i*9+0::54] = self._positions[:, 0]
                    data[i*9+1::54] = self._positions[:, 1]
                    data[i*9+2::54] = self._positions[:, 2]
                    data[i*9+3::54] = self._colors[:, 0]
                    data[i*9+4::54] = self._colors[:, 1]
                    data[i*9+5::54] = self._colors[:, 2]
                    data[i*9+6::54] = self._radii * self.sphere_scale
                offsets = np.array([[-1, -1], [1, -1], [1, 1], [-1, -1], [1, 1], [-1, 1]], dtype=np.float32)
                for i in range(6):
                    data[i*9+7::54] = offsets[i, 0]
                    data[i*9+8::54] = offsets[i, 1]
                from src.shared.qt_compat import QOpenGLBuffer
                self._vbo_atoms = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
                self._vbo_atoms.create()
                self._vbo_atoms.bind()
                self._vbo_atoms.allocate(data.tobytes(), len(data.tobytes()))
            
            # 2. Protein Mesh Buffer
            if self.molecule and self.molecule.properties.get('is_protein'):
                from src.features.visualization_3d.services.cartoon_generator import generate_cartoon_mesh
                t_mesh = time.time()
                v, t, c = generate_cartoon_mesh(self.molecule)
                if v is not None:
                    if self._vbo_mesh: self._vbo_mesh.destroy()
                    indices = t.flatten()
                    v_flat = v[indices] - self._centroid
                    c_flat = c[indices]
                    self._num_mesh_vertices = len(v_flat)
                    mdata = np.zeros(self._num_mesh_vertices * 9, dtype=np.float32)
                    mdata[0::9] = v_flat[:, 0]
                    mdata[1::9] = v_flat[:, 1]
                    mdata[2::9] = v_flat[:, 2]
                    mdata[3::9] = c_flat[:, 0]
                    mdata[4::9] = c_flat[:, 1]
                    mdata[5::9] = c_flat[:, 2]
                    for i in range(0, self._num_mesh_vertices, 3):
                        p1, p2, p3 = v_flat[i], v_flat[i+1], v_flat[i+2]
                        norm = np.cross(p2 - p1, p3 - p1)
                        mag = np.linalg.norm(norm)
                        if mag > 1e-6: norm /= mag
                        mdata[i*9+6:i*9+9] = norm
                        mdata[i*9+15:i*9+18] = norm
                        mdata[i*9+24:i*9+27] = norm
                    from src.shared.qt_compat import QOpenGLBuffer
                    self._vbo_mesh = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
                    self._vbo_mesh.create()
                    self._vbo_mesh.bind()
                    self._vbo_mesh.allocate(mdata.tobytes(), len(mdata.tobytes()))
                    self._ibo_mesh = None
                    print(f"[GL] Mesh buffer updated in {time.time()-t_mesh:.3f}s")
            else:
                self._vbo_mesh = None

            print(f"[Performance] Total GL Buffer update took {time.time()-t_upd:.3f}s")

        except Exception as e:
            print(f"[GL] Buffer update error: {e}")

    def _get_projection_matrix(self):"""
    content = pattern.sub(new_buffers, content)

    # 8. replace draw methods
    pattern_draw = re.compile(r"    def _draw_atoms\(self, gl, proj, view\):.*?    def _pack_bonds\(self, mol, atoms, atom_colors\):", re.DOTALL)
    new_draw = """    def _draw_atoms(self, gl, proj, view):
        self._shader_sphere.bind()
        self._shader_sphere.setUniformValue("projection", proj)
        self._shader_sphere.setUniformValue("view", view)
        
        self._vbo_atoms.bind()
        self._shader_sphere.enableAttributeArray(0)
        self._shader_sphere.setAttributeBuffer(0, 0x1406, 0, 3, 36)
        self._shader_sphere.enableAttributeArray(1)
        self._shader_sphere.setAttributeBuffer(1, 0x1406, 12, 3, 36)
        self._shader_sphere.enableAttributeArray(2)
        self._shader_sphere.setAttributeBuffer(2, 0x1406, 24, 1, 36)
        self._shader_sphere.enableAttributeArray(3)
        self._shader_sphere.setAttributeBuffer(3, 0x1406, 28, 2, 36)
        
        gl.glDrawArrays(0x0004, 0, len(self._positions) * 6)
        
    def _draw_mesh(self, gl, proj, view):
        self._shader_mesh.bind()
        self._shader_mesh.setUniformValue("projection", proj)
        self._shader_mesh.setUniformValue("view", view)
        from src.shared.qt_compat import QMatrix4x4, QVector3D
        self._shader_mesh.setUniformValue("model", QMatrix4x4())
        self._shader_mesh.setUniformValue("lightPos", QVector3D(50, 50, 100))
        self._shader_mesh.setUniformValue("viewPos", QVector3D(0, 0, 100))
        self._shader_mesh.setUniformValue("lightColor", QVector3D(1, 1, 1))
        
        self._vbo_mesh.bind()
        self._shader_mesh.enableAttributeArray(0)
        self._shader_mesh.setAttributeBuffer(0, 0x1406, 0, 3, 36)
        self._shader_mesh.enableAttributeArray(1)
        self._shader_mesh.setAttributeBuffer(1, 0x1406, 12, 3, 36)
        self._shader_mesh.enableAttributeArray(2)
        self._shader_mesh.setAttributeBuffer(2, 0x1406, 24, 3, 36)
        
        gl.glDrawArrays(0x0004, 0, self._num_mesh_vertices)

    def _pack_bonds(self, mol, atoms, atom_colors):"""
    content = pattern_draw.sub(new_draw, content)

    with open('src/features/visualization_3d/ui/gl_widget.py', 'w', encoding='utf-8') as f:
        f.write(content)

patch_gl()
