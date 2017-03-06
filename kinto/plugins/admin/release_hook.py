import subprocess


def main(data):
    """
    Example of data for after-checkout:

    {'tag': '6.1.0.dev0',
     'tagdir': '/tmp/kinto-6.1.0.dev0-yap7gojl/gitclone',
     'workingdir': '/home/mathieu/Code/Mozilla/kinto',
     'name': 'kinto',
     'reporoot': '/home/mathieu/Code/Mozilla/kinto',
     'tagworkingdir': '/tmp/kinto-6.1.0.dev0-yap7gojl/gitclone',
     'nothing_changed_yet': '- Nothing changed yet.',
     'version': '6.1.0.dev0',
     'tag_already_exists': True
    }
    """
    tagdir = data['tagdir']
    subprocess.run(["make", "build-kinto-admin"])
