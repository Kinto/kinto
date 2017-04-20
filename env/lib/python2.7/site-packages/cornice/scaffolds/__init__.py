# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
try:  # pyramid 1.0.X
    # "pyramid.paster.paste_script..." doesn't exist past 1.0.X
    from pyramid.paster import paste_script_template_renderer
    from pyramid.paster import PyramidTemplate
except ImportError:
    try:  # pyramid 1.1.X, 1.2.X
        # trying to import "paste_script_template_renderer" fails on 1.3.X
        from pyramid.scaffolds import paste_script_template_renderer
        from pyramid.scaffolds import PyramidTemplate
    except ImportError:  # pyramid >=1.3a2
        paste_script_template_renderer = None  # NOQA
        from pyramid.scaffolds import PyramidTemplate  # NOQA


class CorniceTemplate(PyramidTemplate):
    _template_dir = 'cornice'
    summary = "A Cornice application"
    template_renderer = staticmethod(paste_script_template_renderer)
