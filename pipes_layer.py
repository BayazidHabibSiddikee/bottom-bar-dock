"""pipes_layer.py — the animated 'pipes' texture as a reusable background
layer.

This used to be its own QWidget stacked with the matrix rain and cycled
between the two. Now it's the only animation, and it runs in *two* places
at once (left panel + right panel) as a low-alpha texture sitting between
the flat deck background and each panel's real content (the mission graph
on the left, the stats/dock on the right) — so it's a plain helper object,
not a widget: the owning panel calls `.paint(painter)` at the start of its
own paintEvent, before drawing anything else on top.
"""
import random
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QFont, QColor

PIPE_CHARS = {
    'h': '━', 'v': '┃',
    'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛',
    'cross': '╋',
}
PIPE_COLORS = [
    QColor(97, 175, 239),    # One Dark blue
    QColor(152, 195, 121),   # One Dark green
    QColor(229, 192, 123),   # One Dark yellow
    QColor(198, 120, 221),   # One Dark purple
    QColor(86, 182, 194),    # One Dark cyan
    QColor(224, 108, 117),   # One Dark red
]


class PipesLayer(QObject):
    def __init__(self, widget, cell=16, interval=80, max_alpha=140):
        """widget: the panel that owns this layer — used for sizing and to
        trigger repaints. max_alpha caps how strong the texture reads, so
        it stays a background layer rather than competing with the graph
        or the stats text drawn on top of it."""
        super().__init__(widget)
        self._widget = widget
        self.cell_w = self.cell_h = cell
        self.max_alpha = max_alpha
        self.grid = {}    # (col,row) -> (char, QColor, age)
        self.pipes = []   # active pipes: {col,row,dir,color,len}
        self._frame = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(interval)

    def _cols(self):
        return max(1, self._widget.width() // self.cell_w)

    def _rows(self):
        return max(1, self._widget.height() // self.cell_h)

    def _tick(self):
        self._frame += 1
        cols, rows = self._cols(), self._rows()

        if len(self.pipes) < 8 and random.random() < 0.15:
            self.pipes.append({
                'col': random.randint(0, cols - 1),
                'row': random.randint(0, rows - 1),
                'dir': random.choice(['h', 'v']),
                'color': random.choice(PIPE_COLORS),
                'len': 0,
            })

        dead = []
        for k in list(self.grid):
            ch, col_c, age = self.grid[k]
            if age <= 0:
                dead.append(k)
            else:
                self.grid[k] = (ch, col_c, age - 1)
        for k in dead:
            del self.grid[k]

        dead_pipes = []
        for pipe in self.pipes:
            c, r = pipe['col'], pipe['row']
            d = pipe['dir']
            ch = PIPE_CHARS['h'] if d == 'h' else PIPE_CHARS['v']
            self.grid[(c, r)] = (ch, pipe['color'], 60)
            pipe['len'] += 1

            if random.random() < 0.12:
                old_d = d
                pipe['dir'] = 'v' if d == 'h' else 'h'
                corner_map = {('h', 'v'): PIPE_CHARS['tl'], ('v', 'h'): PIPE_CHARS['br']}
                corner = corner_map.get((old_d, pipe['dir']), PIPE_CHARS['cross'])
                self.grid[(c, r)] = (corner, pipe['color'], 60)

            if pipe['dir'] == 'h':
                pipe['col'] = (c + random.choice([-1, 1])) % cols
            else:
                pipe['row'] = (r + random.choice([-1, 1])) % rows

            if pipe['len'] > random.randint(20, 60):
                dead_pipes.append(pipe)

        for p in dead_pipes:
            if p in self.pipes:
                self.pipes.remove(p)

        if self._frame % 400 == 0:
            self.grid.clear()

        self._widget.update()

    def paint(self, p):
        """Call at the top of the owning widget's paintEvent, before
        drawing that widget's real content — this is the bottom layer."""
        font = QFont("monospace", 11)
        p.setFont(font)
        for (c, r), (ch, color, age) in self.grid.items():
            alpha = min(self.max_alpha, age * 2)
            col = QColor(color.red(), color.green(), color.blue(), alpha)
            p.setPen(col)
            p.drawText(c * self.cell_w, r * self.cell_h + self.cell_h - 2, ch)
