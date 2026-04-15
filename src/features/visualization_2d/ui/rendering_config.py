
class RenderingConfig:
    """Consolidated constants and logic for 2D molecular rendering."""
    
    # Base proportions
    FONT_SIZE_RATIO = 0.32
    MAX_FONT_SIZE = 20
    MIN_FONT_SIZE = 10
    
    @staticmethod
    def get_gaps(v):
        """Calculate character and subscript gaps based on scale/export."""
        is_export = v._original_scale is not None
        base_scale = v._original_scale if is_export else v._scale
        export_factor = v._scale / base_scale if base_scale > 0 else 1.0
        
        if is_export:
            # Keep export gaps stable as they were verified as "perfect"
            char_gap = max(11, int(9 * export_factor))
            sub_gap = max(9, int(8 * export_factor))
        else:
            # Decreased on-screen gaps for a tighter, cleaner look
            char_gap = max(3, int(v._scale * 0.07))
            sub_gap = max(2, int(v._scale * 0.05))
            
        return char_gap, sub_gap, export_factor

    @staticmethod
    def get_v_offset(fm, export_factor):
        """Standard vertical offset for capital letters at bond junctions."""
        # Aligning the mid-height of capital letters with the junction (sy)
        # Using a slightly larger offset to lower symbols based on visual feedback.
        return (fm.ascent() / 2)

    @staticmethod
    def get_h_offset(export_factor):
        """Standard horizontal offset for labels to achieve visual balance."""
        if export_factor > 1.0:
            # Slightly move left (negative) for export to compensate for font bearings
            return -max(1, int(1.5 * export_factor))
        return 0
