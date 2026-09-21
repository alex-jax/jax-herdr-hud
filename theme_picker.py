"""Native, searchable palette previews for Hud settings."""
from gi.repository import Gtk, GLib, Pango
from terminal_themes import palettes


class ThemePicker(Gtk.Dialog):
    def __init__(self, app):
        super().__init__(title='Appearance', transient_for=app.window,
                         destroy_with_parent=True, modal=True)
        self.app = app
        self.set_default_size(790, 650)
        self.add_button('Done', Gtk.ResponseType.CLOSE)
        self.connect('response', lambda *_: self.destroy())
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_border_width(18)
        controls = Gtk.Box(spacing=12)
        controls.pack_start(Gtk.Label(label='Appearance'), False, False, 0)
        self.mode = Gtk.ComboBoxText()
        for key, label in [('system', 'Follow desktop'), ('light', 'Light'), ('dark', 'Dark')]:
            self.mode.append(key, label)
        self.mode.set_active_id(app.theme)
        self.mode.connect('changed', self.change_mode)
        controls.pack_start(self.mode, False, False, 0)
        self.all_palettes = Gtk.CheckButton(label='Show all palettes')
        self.all_palettes.connect('toggled', lambda *_: self.filter_cards())
        controls.pack_end(self.all_palettes, False, False, 0)
        box.pack_start(controls, False, False, 0)
        self.search = Gtk.SearchEntry(placeholder_text='Find a theme…')
        self.search.connect('search-changed', lambda *_: self.filter_cards())
        box.pack_start(self.search, False, False, 0)
        self.summary = Gtk.Label(xalign=0)
        box.pack_start(self.summary, False, False, 0)
        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                                column_spacing=12, row_spacing=12,
                                min_children_per_line=1, max_children_per_line=3)
        self.flow.set_homogeneous(True)
        self.flow.set_valign(Gtk.Align.START)
        scroll.add(self.flow)
        box.pack_start(scroll, True, True, 0)
        note = Gtk.Label(label='Themes apply to the whole Hud, including terminal colors.\n'
                         'Palettes with one variant keep their original colors in either appearance.',
                         xalign=0, wrap=True)
        note.get_style_context().add_class('dim-label')
        box.pack_start(note, False, False, 0)
        self.cards = {}
        items = [('hud', dict(name='Hud classic', primary=True))]
        items += sorted(palettes().items(), key=lambda pair: pair[1]['name'].casefold())
        for key, item in items:
            button = Gtk.Button()
            button.set_size_request(200, 150)
            button.set_tooltip_text(item['name'])
            button.get_accessible().set_name(item['name'])
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
            title = Gtk.Label(xalign=0)
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_max_width_chars(22)
            sample = Gtk.Label(xalign=0)
            swatches = Gtk.Label(xalign=0)
            for label in (title, sample, swatches):
                content.pack_start(label, False, False, 0)
            button.add(content)
            css = Gtk.CssProvider()
            button.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
            button.connect('clicked', lambda _, value=key: self.choose(value))
            self.flow.add(button)
            child = button.get_parent()
            child.palette_key = key
            self.cards[key] = (item, button, title, sample, swatches, css)
        self.flow.set_filter_func(self.matches)
        self.refresh()
        self.show_all()
        self.filter_cards()

    def matches(self, child):
        key = child.palette_key
        item = self.cards[key][0]
        query = self.search.get_text().strip().casefold()
        if query:
            return query in item['name'].casefold()
        return (self.all_palettes.get_active() or item['primary'] or
                key == self.app.settings.get('terminal_palette', 'gnome'))

    def filter_cards(self):
        self.flow.invalidate_filter()
        count = sum(self.matches(child) for child in self.flow.get_children())
        selected = self.app.settings.get('terminal_palette', 'gnome')
        name = self.cards.get(selected, self.cards['gnome'])[0]['name']
        self.summary.set_text(f'{name} selected · {count} themes' if count else 'No themes match your search')

    def refresh(self):
        selected = self.app.settings.get('terminal_palette', 'gnome')
        for key, (item, button, title, sample, swatches, css) in self.cards.items():
            fg, bg, colors = self.app.terminal_colors(key)
            mark = '  ✓' if key == selected else ''
            title.set_markup(f'<span foreground="{fg}" weight="bold">'
                             f'{GLib.markup_escape_text(item["name"] + mark)}</span>')
            sample.set_markup(f'<span foreground="{fg}" font_family="monospace">'
                              'The quick brown\nfox jumps over\nthe lazy dog</span>')
            swatches.set_markup(' '.join(f'<span background="{c}">   </span>' for c in colors[1:7]))
            css.load_from_data(('button { background-image: none; background-color: ' + bg +
                '; border-radius: 14px; box-shadow: none; border: 2px solid ' +
                ('#3584e4' if key == selected else bg) + '; } button:hover { border-color: #3584e4; }').encode())
        self.filter_cards()

    def choose(self, key):
        self.app.settings['terminal_palette'] = key
        self.app.apply_theme()
        self.app.save()

    def change_mode(self, combo):
        self.app.theme = combo.get_active_id()
        self.app.apply_theme()
        self.app.save()
