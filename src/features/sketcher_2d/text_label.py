# -*- coding: utf-8 -*-
from .drawing_parents import DrawableObject, Color, Font, Align
from src.shared.qt_compat import QGraphicsTextItem, QFont, QColor

global text_id_no
text_id_no = 1

class TextLabel(DrawableObject):
    def __init__(self, x, y, text="Text"):
        DrawableObject.__init__(self)
        self.x = x
        self.y = y
        self.text = text
        self.font_name = "Arial"
        self.font_size = 14
        self._text_item = None
        self._bg_item = None
        self._focus_item = None
        self._selection_item = None
        global text_id_no
        self.id = 'text' + str(text_id_no)
        text_id_no += 1

    @property
    def pos(self):
        return self.x, self.y

    def set_pos(self, x, y):
        self.x, self.y = x, y

    def draw(self):
        self.clear_drawings()
        if not self.paper: return
        
        font = Font(self.font_name, self.font_size)
        
        if not self.text:
            # Show a placeholder rectangle when text is empty
            box_width = 80
            box_height = 20
            rect = [self.x - box_width/2, self.y - box_height/2, 
                    self.x + box_width/2, self.y + box_height/2]
            self._text_item = self.paper.addRect(rect, color=(100, 100, 100), width=1, fill=(240, 240, 240))
        else:
            # Show text with a background box for visibility
            self._text_item = self.paper.addHtmlText(self.text, (self.x, self.y), font=font, 
                                                     align=Align.HCenter | Align.VCenter, color=self.color)
            # Add a light background rectangle behind text
            bbox = self.paper.itemBoundingBox(self._text_item)
            bg_rect = [bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2]
            self._bg_item = self.paper.addRect(bg_rect, color=(200, 200, 200), width=1, fill=(255, 255, 255))
            self._bg_item.setZValue(-1)
        
        self.paper.addFocusable(self._text_item, self)

    def clear_drawings(self):
        if not self.paper: return
        if self._text_item:
            try:
                self.paper.removeFocusable(self._text_item)
                self.paper.removeItem(self._text_item)
            except:
                pass
            self._text_item = None
        if self._bg_item:
            try:
                self.paper.removeItem(self._bg_item)
            except:
                pass
            self._bg_item = None
        if self._focus_item:
            try:
                self.paper.removeItem(self._focus_item)
            except:
                pass
            self._focus_item = None
        if self._selection_item:
            try:
                self.paper.removeItem(self._selection_item)
            except:
                pass
            self._selection_item = None

    def set_focus(self, focus):
        if not self.paper: return
        if focus:
            bbox = self.bounding_box()
            from .app_data import Settings
            self._focus_item = self.paper.addRect(bbox, color=(200, 200, 255), width=1)
            self.paper.toSelectionLayer(self._focus_item)
        else:
            if self._focus_item:
                try:
                    self.paper.removeItem(self._focus_item)
                except:
                    pass
                self._focus_item = None

    def set_selected(self, select):
        if not self.paper: return
        if select:
            bbox = self.bounding_box()
            from .app_data import Settings
            self._selection_item = self.paper.addRect(bbox, color=Settings.selection_color, width=1)
            self.paper.toSelectionLayer(self._selection_item)
        else:
            if self._selection_item:
                try:
                    self.paper.removeItem(self._selection_item)
                except:
                    pass
                self._selection_item = None

    def bounding_box(self):
        if self._text_item and self.paper:
            return self.paper.itemBoundingBox(self._text_item)
        return [self.x - 20, self.y - 10, self.x + 20, self.y + 10]

    def get_center(self):
        return self.x, self.y

    def move_by(self, dx, dy):
        self.x += dx
        self.y += dy
        self.draw()

    def rotate(self, angle, center):
        # Text doesn't rotate in this implementation
        pass

    def delete_from_paper(self):
        if self.paper:
            self.paper.removeObject(self)
        self.clear_drawings()
