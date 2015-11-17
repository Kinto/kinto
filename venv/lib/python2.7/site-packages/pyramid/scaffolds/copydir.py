# (c) 2005 Ian Bicking and contributors; written for Paste
# (http://pythonpaste.org) Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php

import os
import sys
import pkg_resources

from pyramid.compat import (
    input_,
    native_,
    url_quote as compat_url_quote,
    escape,
    )

fsenc = sys.getfilesystemencoding()

class SkipTemplate(Exception):
    """
    Raised to indicate that the template should not be copied over.
    Raise this exception during the substitution of your template
    """

def copy_dir(source, dest, vars, verbosity, simulate, indent=0,
             sub_vars=True, interactive=False, overwrite=True,
             template_renderer=None, out_=sys.stdout):
    """
    Copies the ``source`` directory to the ``dest`` directory.

    ``vars``: A dictionary of variables to use in any substitutions.

    ``verbosity``: Higher numbers will show more about what is happening.

    ``simulate``: If true, then don't actually *do* anything.

    ``indent``: Indent any messages by this amount.

    ``sub_vars``: If true, variables in ``_tmpl`` files and ``+var+``
    in filenames will be substituted.

    ``overwrite``: If false, then don't every overwrite anything.

    ``interactive``: If you are overwriting a file and interactive is
    true, then ask before overwriting.

    ``template_renderer``: This is a function for rendering templates (if you
    don't want to use string.Template).  It should have the signature
    ``template_renderer(content_as_string, vars_as_dict,
    filename=filename)``.
    """
    def out(msg):
        out_.write(msg)
        out_.write('\n')
        out_.flush()
    # This allows you to use a leading +dot+ in filenames which would
    # otherwise be skipped because leading dots make the file hidden:
    vars.setdefault('dot', '.')
    vars.setdefault('plus', '+')
    use_pkg_resources = isinstance(source, tuple)
    if use_pkg_resources:
        names = sorted(pkg_resources.resource_listdir(source[0], source[1]))
    else:
        names = sorted(os.listdir(source))
    pad = ' '*(indent*2)
    if not os.path.exists(dest):
        if verbosity >= 1:
            out('%sCreating %s/' % (pad, dest))
        if not simulate:
            makedirs(dest, verbosity=verbosity, pad=pad)
    elif verbosity >= 2:
        out('%sDirectory %s exists' % (pad, dest))
    for name in names:
        if use_pkg_resources:
            full = '/'.join([source[1], name])
        else:
            full = os.path.join(source, name)
        reason = should_skip_file(name)
        if reason:
            if verbosity >= 2:
                reason = pad + reason % {'filename': full}
                out(reason)
            continue # pragma: no cover
        if sub_vars:
            dest_full = os.path.join(dest, substitute_filename(name, vars))
        sub_file = False
        if dest_full.endswith('_tmpl'):
            dest_full = dest_full[:-5]
            sub_file = sub_vars
        if use_pkg_resources and pkg_resources.resource_isdir(source[0], full):
            if verbosity:
                out('%sRecursing into %s' % (pad, os.path.basename(full)))
            copy_dir((source[0], full), dest_full, vars, verbosity, simulate,
                     indent=indent+1, sub_vars=sub_vars, 
                     interactive=interactive, overwrite=overwrite,
                     template_renderer=template_renderer, out_=out_)
            continue
        elif not use_pkg_resources and os.path.isdir(full):
            if verbosity:
                out('%sRecursing into %s' % (pad, os.path.basename(full)))
            copy_dir(full, dest_full, vars, verbosity, simulate,
                     indent=indent+1, sub_vars=sub_vars, 
                     interactive=interactive, overwrite=overwrite,
                     template_renderer=template_renderer, out_=out_)
            continue
        elif use_pkg_resources:
            content = pkg_resources.resource_string(source[0], full)
        else:
            f = open(full, 'rb')
            content = f.read()
            f.close()
        if sub_file:
            try:
                content = substitute_content(
                    content, vars, filename=full,
                    template_renderer=template_renderer
                    )
            except SkipTemplate: 
                continue # pragma: no cover
            if content is None:  
                continue  # pragma: no cover
        already_exists = os.path.exists(dest_full)
        if already_exists:
            f = open(dest_full, 'rb')
            old_content = f.read()
            f.close()
            if old_content == content:
                if verbosity:
                    out('%s%s already exists (same content)' %
                          (pad, dest_full))
                continue # pragma: no cover
            if interactive:
                if not query_interactive(
                    native_(full, fsenc), native_(dest_full, fsenc),
                    native_(content, fsenc), native_(old_content, fsenc),
                    simulate=simulate, out_=out_):
                    continue
            elif not overwrite:
                continue # pragma: no cover 
        if verbosity and use_pkg_resources:
            out('%sCopying %s to %s' % (pad, full, dest_full))
        elif verbosity:
            out(
                '%sCopying %s to %s' % (pad, os.path.basename(full),
                                        dest_full))
        if not simulate:
            f = open(dest_full, 'wb')
            f.write(content)
            f.close()

def should_skip_file(name):
    """
    Checks if a file should be skipped based on its name.

    If it should be skipped, returns the reason, otherwise returns
    None.
    """
    if name.startswith('.'):
        return 'Skipping hidden file %(filename)s'
    if name.endswith(('~', '.bak')):
        return 'Skipping backup file %(filename)s'
    if name.endswith(('.pyc', '.pyo')):
        return 'Skipping %s file ' % os.path.splitext(name)[1] + '%(filename)s'
    if name.endswith('$py.class'):
        return 'Skipping $py.class file %(filename)s'
    if name in ('CVS', '_darcs'):
        return 'Skipping version control directory %(filename)s'
    return None

# Overridden on user's request:
all_answer = None

def query_interactive(src_fn, dest_fn, src_content, dest_content,
                      simulate, out_=sys.stdout):
    def out(msg):
        out_.write(msg)
        out_.write('\n')
        out_.flush()
    global all_answer
    from difflib import unified_diff, context_diff
    u_diff = list(unified_diff(
        dest_content.splitlines(),
        src_content.splitlines(),
        dest_fn, src_fn))
    c_diff = list(context_diff(
        dest_content.splitlines(),
        src_content.splitlines(),
        dest_fn, src_fn))
    added = len([l for l in u_diff if l.startswith('+')
                   and not l.startswith('+++')])
    removed = len([l for l in u_diff if l.startswith('-')
                   and not l.startswith('---')])
    if added > removed:
        msg = '; %i lines added' % (added-removed)
    elif removed > added:
        msg = '; %i lines removed' % (removed-added)
    else:
        msg = ''
    out('Replace %i bytes with %i bytes (%i/%i lines changed%s)' % (
        len(dest_content), len(src_content),
        removed, len(dest_content.splitlines()), msg))
    prompt = 'Overwrite %s [y/n/d/B/?] ' % dest_fn
    while 1:
        if all_answer is None:
            response = input_(prompt).strip().lower()
        else:
            response = all_answer
        if not response or response[0] == 'b':
            import shutil
            new_dest_fn = dest_fn + '.bak'
            n = 0
            while os.path.exists(new_dest_fn):
                n += 1
                new_dest_fn = dest_fn + '.bak' + str(n)
            out('Backing up %s to %s' % (dest_fn, new_dest_fn))
            if not simulate:
                shutil.copyfile(dest_fn, new_dest_fn)
            return True
        elif response.startswith('all '):
            rest = response[4:].strip()
            if not rest or rest[0] not in ('y', 'n', 'b'):
                out(query_usage)
                continue
            response = all_answer = rest[0]
        if response[0] == 'y':
            return True
        elif response[0] == 'n':
            return False
        elif response == 'dc':
            out('\n'.join(c_diff))
        elif response[0] == 'd':
            out('\n'.join(u_diff))
        else:
            out(query_usage)

query_usage = """\
Responses:
  Y(es):    Overwrite the file with the new content.
  N(o):     Do not overwrite the file.
  D(iff):   Show a unified diff of the proposed changes (dc=context diff)
  B(ackup): Save the current file contents to a .bak file
            (and overwrite)
  Type "all Y/N/B" to use Y/N/B for answer to all future questions
"""

def makedirs(dir, verbosity, pad):
    parent = os.path.dirname(os.path.abspath(dir))
    if not os.path.exists(parent):
        makedirs(parent, verbosity, pad)  # pragma: no cover
    os.mkdir(dir)

def substitute_filename(fn, vars):
    for var, value in vars.items():
        fn = fn.replace('+%s+' % var, str(value))
    return fn

def substitute_content(content, vars, filename='<string>',
                       template_renderer=None):
    v = standard_vars.copy()
    v.update(vars)
    return template_renderer(content, v, filename=filename)

def html_quote(s):
    if s is None:
        return ''
    return escape(str(s), 1)

def url_quote(s):
    if s is None:
        return ''
    return compat_url_quote(str(s))

def test(conf, true_cond, false_cond=None):
    if conf:
        return true_cond
    else:
        return false_cond

def skip_template(condition=True, *args):
    """
    Raise SkipTemplate, which causes copydir to skip the template
    being processed.  If you pass in a condition, only raise if that
    condition is true (allows you to use this with string.Template)

    If you pass any additional arguments, they will be used to
    instantiate SkipTemplate (generally use like
    ``skip_template(license=='GPL', 'Skipping file; not using GPL')``)
    """
    if condition:
        raise SkipTemplate(*args)

standard_vars = {
    'nothing': None,
    'html_quote': html_quote,
    'url_quote': url_quote,
    'empty': '""',
    'test': test,
    'repr': repr,
    'str': str,
    'bool': bool,
    'SkipTemplate': SkipTemplate,
    'skip_template': skip_template,
    }

