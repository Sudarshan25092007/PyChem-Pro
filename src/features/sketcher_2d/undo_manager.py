# -*- coding: utf-8 -*-
# Adapted from ChemCanvas (GPLv3)
import copy

class UndoManager:
    MAX_UNDO_LEVELS = 50

    def __init__(self, paper):
        self.paper = paper
        self._stack = []
        self._pos = -1
        self.save_current_state("empty paper")

    def save_current_state(self, name=''):
        if self._pos < len(self._stack) - 1:
            self._stack = self._stack[:self._pos + 1]
        
        if len(self._stack) >= self.MAX_UNDO_LEVELS:
            self._stack.pop(0)
            self._pos -= 1
            
        self._stack.append(PaperState(self.paper, name))
        self._pos += 1

    def undo(self):
        if self._pos > 0:
            self._pos -= 1
            self._stack[self._pos].restore_state()
            return True
        return False

    def redo(self):
        if self._pos < len(self._stack) - 1:
            self._pos += 1
            self._stack[self._pos].restore_state()
            return True
        return False

class PaperState:
    def __init__(self, paper, name):
        self.paper = paper
        self.name = name
        self.top_levels = list(self.paper.objects)
        self.objects_data = []
        
        # Recursively collect all objects and their state
        all_objs = self._get_all_objects(self.top_levels)
        for obj in all_objs:
            state = {}
            for attr in getattr(obj, "meta__undo_properties", []):
                state[attr] = getattr(obj, attr)
            for attr in getattr(obj, "meta__undo_copy", []):
                state[attr] = copy.copy(getattr(obj, attr))
            self.objects_data.append((obj, state))

    def _get_all_objects(self, top_levels):
        objs = []
        stack = list(top_levels)
        visited = set()
        while stack:
            obj = stack.pop()
            if obj in visited: continue
            visited.add(obj)
            objs.append(obj)
            for attr in getattr(obj, "meta__undo_children_to_record", []):
                children = getattr(obj, attr)
                stack.extend(children)
        return objs

    def restore_state(self):
        # 1. Remove objects currently on paper that are NOT in this state
        target_objs = [data[0] for data in self.objects_data]
        current_objs = self._get_all_objects(self.paper.objects)
        
        for obj in current_objs:
            if obj not in target_objs:
                obj.delete_from_paper()
        
        # 2. Restore attributes and redraw
        for obj, state in self.objects_data:
            obj.paper = self.paper
            for attr, val in state.items():
                if attr in getattr(obj, "meta__undo_copy", []):
                    setattr(obj, attr, copy.copy(val))
                else:
                    setattr(obj, attr, val)
            obj.draw()
            
        self.paper.objects = list(self.top_levels)
        self.paper.redraw_dirty_objects()
