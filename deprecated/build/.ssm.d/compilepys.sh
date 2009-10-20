#! /bin/sh
#
# compilepys.sh libPath [...]

if [ $# -gt 0 ]; then
    for libPath in $@; do
        if [ -d "${libPath}" ]; then
            # clean out compiled (.pyc) files
            rm -f "${libPath}"/*.pyc
        fi
    
        # compile files
        st="import compileall; compileall.compile_dir(\"${libPath}\", force=1)"
        echo "${st}" | python -
    done
fi
