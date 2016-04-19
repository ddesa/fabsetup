import os.path
import re
import sys
import tempfile
from functools import wraps
from os.path import dirname, isdir, isfile, join

import fabric.api
import fabric.contrib.files
import fabric.operations
from fabric.context_managers import quiet
from fabric.state import env
from fabric.network import needs_host

from utils import flo, print_full_name, print_doc1, blue, yellow, magenta
from utils import filled_out_template


@needs_host
def _func(kwargs, localhost=fabric.api.local, remote=fabric.api.run):
    env.host = env.host_string
    func = remote
    if env.host_string == 'localhost':
        func = localhost
    else:
        kwargs.pop('capture', None)
    return func, kwargs


def run(*args, **kwargs):
    func, kwargs = _func(kwargs)
    return func(*args, **kwargs)


def exists(*args, **kwargs):
    func, kwargs = _func(kwargs, localhost=os.path.exists, remote=fabric.contrib.files.exists)
    if func == os.path.exists:
        args_list = list(args)
        args_list[0] = os.path.expanduser(args[0])
        args = tuple(args_list)
    return func(*args, **kwargs)


def put(*args, **kwargs):
    func, kwargs = _func(kwargs, remote=fabric.operations.put)
    if func == fabric.api.local:
        from_, to = [os.path.expanduser(arg) for arg in args]
        args = [flo('cp  {from_}  {to}')]
        kwargs = {}
    return func(*args, **kwargs)


def needs_repo_fabsetup_custom(func):
    '''Decorator, ensures that fabsetup_custom exists and it's a git repo.'''
    from fabric.api import local
    @wraps(func)
    def wrapper(*args, **kwargs):
        custom_dir = join(dirname(dirname(__file__)), 'fabsetup_custom')
        presetting_dir = join(dirname(dirname(__file__)), 'fabfile_data',
                'presetting_fabsetup_custom')
        if not isdir(custom_dir):
            print(yellow('\n** **     Init ') + yellow('fabsetup_custom', bold=True) + yellow('      ** **\n'))
            print(yellow('** Create files in dir fabsetup_custom **'))
            local(flo('mkdir -p {custom_dir}'))
            local(flo('cp -rv --no-clobber {presetting_dir}/. {custom_dir}'))
        else:
            with quiet():
                local(flo('cp -r --no-clobber {presetting_dir}/. {custom_dir}'))

        if not isdir(join(custom_dir, '.git')):
            print(yellow('\n** Git repo fabsetup_custom: init and first commit **'))
            local(flo('cd {custom_dir} && git init'))
            local(flo('cd {custom_dir} && git add .'))
            local(flo('cd {custom_dir} && git commit -am "Initial commit"'))
            print(yellow("** Done. Don't forget to create a backup of your fabsetup_custom repo **\n"))
            print(yellow("** But do not make it public, it's custom **\n", bold=True))
        else:
            with quiet():
                res = local(flo('cd {custom_dir} && git status --porcelain'), capture=True)
                if res:
                    print(yellow('\n** git repo  fabsetup_custom  has uncommitted changes: **'))
                    print(yellow(res, bold=True))
                    print(yellow("** Don't forget to commit them and make a backup of your repo **\n"))
        return func(*args, **kwargs)
    return wrapper


def needs_packages(*packages):
    '''Decorator, ensures that packages are installed.'''
    def real_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for package in packages:
                with quiet():
                    res = run(flo('dpkg --list {package}'))
                if res.return_code != 0:
                    install_package(package)
            return func(*args, **kwargs)
        return wrapper
    return real_decorator


def task(func):
    '''Composition of decorator functions for inherent self-documentation on
    task execution.
    
    On execution, each task prints out its name and its first docstring line.
    '''
    return fabric.api.task(print_full_name(color=magenta)(print_doc1(func)))


def install_packages(packages):
    '''Install Ubuntu packages given by list.'''
    packages_str = '  '.join(packages)
    run(flo('sudo  apt-get install  {packages_str}')) # FIXME: incorporate fabrics sudo()


def install_package(package):
    '''Install Ubuntu package given by param package.'''
    install_packages([package])


@needs_packages('git')
def checkup_git_repos(repos, base_dir='~/repos'):
    '''Checkout or update git repos.

    repos must be a list of dicts each with an url and optional with a name
    value.
    '''
    run(flo('mkdir -p {base_dir}'))
    for repo in repos:
        name = repo.get('name', None)
        if not name:
            name = re.match(r'.*/([^.]+)\.git', repo['url']).group(1)
        assert name is not None
        assert name != ''
        if not exists(flo('{base_dir}/{name}/.git')):
            url = repo['url']
            run(flo('  &&  '.join([
                    'cd {base_dir}',
                    'git clone  {url}  {name}'
            ])))
        else:
            # FIXME: reset + fetch instead of pull
            run(flo('cd {base_dir}/{name}  &&  git pull'))


def checkup_git_repo(url, name=None, base_dir='~/repos'):
    '''Checkout or update a git repo.'''
    if name:
        checkup_git_repos([{'name': name, 'url': url}], base_dir)
    else:
        checkup_git_repos([{'url': url}], base_dir)


def _install_file_from_template(from_template, to_, **substitutions):
    from_str = filled_out_template(from_template, **substitutions)
    with tempfile.NamedTemporaryFile(prefix='fabsetup') as tmp_file:
        with open(tmp_file.name, 'w') as fp:
            fp.write(from_str)
        to_dir = dirname(to_)
        run(flo('mkdir -p  {to_dir}'))
        put(tmp_file.name, to_)


def install_file(path, **substitutions):
    '''Install file with path on the host target.

    The from file is the first of this list which exists:
     * custom file
     * custom file.template
     * common file
     * common file.template
    '''
    from_head = dirname(dirname(__file__))
    from_tail = join('files', path)
    if path.startswith('~/'):
        from_tail = join('files', 'home', 'USERNAME', path[2:])
    from_common = join(from_head, 'fabfile_data', from_tail)
    from_custom = join(from_head, 'fabsetup_custom', from_tail)
    path_dir = dirname(path)
    if isfile(from_custom):
        run(flo('mkdir -p  {path_dir}'))
        put(from_custom, path)
    elif isfile(from_custom + '.template'):
        _install_file_from_template(from_custom + '.template', to_=path,
                **substitutions)
    elif isfile(from_common):
        run(flo('mkdir -p  {path_dir}'))
        put(from_common, path)
    else:
        _install_file_from_template(from_common + '.template', to_=path,
                **substitutions)


def install_user_command(command, **substitutions):
    '''Install command executable file into users bin dir.

    If a custom executable exists it would be installed instead of the "normal"
    one.  The executable also could exist as a <command>.template file.
    '''
    path = flo('~/bin/{command}')
    install_file(path, **substitutions)
    run(flo('chmod 755 {path}'))
