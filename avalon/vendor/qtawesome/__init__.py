"""
qtawesome - use font-awesome in PyQt / PySide applications

This is a port to Python of the C++ QtAwesome library by Rick Blommers
"""
from .iconic_font import IconicFont, set_global_defaults
from .animation import Pulse, Spin
from ._version import version_info, __version__
from ..Qt import QtGui

_resource = {'iconic': None, }


def _instance():
    output_instance = _resource['iconic']
    if output_instance:
        # Check stored font ids are still available
        for font_id in tuple(output_instance.fontid.values()):
            font_families = QtGui.QFontDatabase.applicationFontFamilies(
                font_id
            )
            # Reset font if font id is not available
            if not font_families:
                output_instance = None
                break

    if output_instance is None:
        _resource['iconic'] = IconicFont(
            (
                'fa',
                'fontawesome-webfont.ttf',
                'fontawesome-webfont-charmap.json'
            ),
            (
                'ei',
                'elusiveicons-webfont.ttf',
                'elusiveicons-webfont-charmap.json'
            )
        )
    return _resource['iconic']


def icon(*args, **kwargs):
    return _instance().icon(*args, **kwargs)


def load_font(*args, **kwargs):
    return _instance().load_font(*args, **kwargs)


def charmap(prefixed_name):
    prefix, name = prefixed_name.split('.')
    return _instance().charmap[prefix][name]


def font(*args, **kwargs):
    return _instance().font(*args, **kwargs)


def set_defaults(**kwargs):
    return set_global_defaults(**kwargs)
