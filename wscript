#
# wscript (hcron)
#

import wscript_lib2 as wscript_lib

srcdir = "."
blddir = "build"

def set_options(ctx):
    wscript_lib.set_options(ctx)

def configure(conf):
    import Options

    conf.env._PACKAGE_FORMAT = Options.options.package_format
    conf.env._PACKAGE_PLATFORM = Options.options.package_platform
    conf.env._PACKAGE_VERSION = "0.15"

    wscript_lib.configure(conf)

    print conf.env

def build(bld):
    if bld.is_install:
        install_only(bld)
        return

def install_only(bld):
    bld.env._PREFIX = bld.env.PREFIX
    bld.env.PREFIX = wscript_lib.get_install_dir(bld, "hcron")

    # control
    wscript_lib.install_control(bld, "hcron")

    # binaries
    wscript_lib.install_static(bld,
        [
            "usr/lib/hcron/hcron-conv.py",
            "usr/lib/hcron/hcron-event.py",
            "usr/lib/hcron/hcron-info.py",
            "usr/lib/hcron/hcron-reload.py",
            "usr/lib/hcron/hcron-scheduler.py",
        ],
        0555)

    # other
    wscript_lib.install_static(bld,
        [
            "etc/**/*",
            "usr/lib/hcron/hcron/*.py",
            "usr/share/**/*",
            "var/**/*",
        ],
        0444)

    wscript_lib.install_static(bld,
        [
            "etc/init.d/hcron",
        ],
        0555)

    # symlinks
    symlink_info = [
        ("usr/bin/hcron-conv", "../lib/hcron/hcron-conv.py"),
        ("usr/bin/hcron-event", "../lib/hcron/hcron-event.py"),
        ("usr/bin/hcron-info", "../lib/hcron/hcron-info.py"),
        ("usr/bin/hcron-reload", "../lib/hcron/hcron-reload.py"),
        ("usr/sbin/hcron-scheduler", "../lib/hcron/hcron-scheduler.py"),
    ]

    for target, link in symlink_info:
        bld.symlink_as("${PREFIX}/%s" % target,
            link)

    bld.save()

def dist():
    from Build import bld

    bld.load()

    dists = {
        "hcron": {
            "names": bld.path.ant_glob("${PREFIX}/**/*"),
        },
    }

    wscript_lib.make_packages(bld, bld.env.PREFIX, dists)

