#!/bin/bash
set -e

while [ $# -gt 0 ]; do
    case "$1" in
    --py-version=*)
        PY_VERSION="${1#*=}"
        ;;
    --update-reqs)
        UPDATE_REQS="true"
        ;;        
    *)
        printf "***************************\n"
        printf "* Error: Invalid argument.*\n"
        printf "Arguments\n"
        printf " --py-version='3.11'                            sets the python version tu use, if missing will use 3.11\n"
        printf " --update-reqs                                 if present, regenerate requirements using pip-compile\n"
        printf "***************************\n"
        exit 1
        ;;
    esac
    shift
done
PY_VERSION=${PY_VERSION:="3.11"}
echo Python version is $PY_VERSION

# VIRTUAL_ENV is set in venv/bin/activate or venv/Scripts/activate
setup_venv() {
    local py=${1:-python${PY_VERSION}}
    local venv="${2:-./.venv}"

    echo "Setting up python version ${py} in ${venv}"

    if [[ "$OSTYPE" == "darwin"* || "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Activating (venv) on linux"
        local bin="${venv}/bin/activate"
    else
        echo "Activating (venv) on windows"
        local bin="${venv}/Scripts/activate"
    fi


    # If not already in virtualenv
    # $VIRTUAL_ENV is being set from $venv/bin/activate script
    if [[ -z "${VIRTUAL_ENV}" || "${VIRTUAL_ENV}" != "${PWD}"* ]]; then
        deactivate || 
        echo "* Creating a virtualenv"
        # Install and setup virtualenv
        ${py} -m pip install --user --upgrade pip
        ${py} -m pip install --user virtualenv

        if [ ! -d "${venv}" ]; then
            echo "* Creating and activating virtual environment ${venv}"
            ${py} -m venv "${venv}"
            echo "export PYTHON=${py}" >> "${bin}"    # overwrite ${python} on .zshenv
            # shellcheck source=/dev/null
            source "${bin}" 
            echo "Upgrading pip"
            ${py} -m pip install --upgrade pip
        else
            echo "* Virtual environment ${venv} already exists, activating..."
            # shellcheck source=/dev/null
            source "${bin}" 
        fi
    else
        echo "* Already in a virtual environment!"
        # Upgrade pip just in case
        ${py} -m pip install --upgrade pip
    fi
}

setup_venv python${PY_VERSION} venv



if [ -z "$VIRTUAL_ENV" ]; then
    echo "Did not activate (venv)"
    set +e
    exit 1
fi 

if [ ! -f "requirements.txt" ] || [ ! -f "requirements-dev.txt" ]; then
    echo "Did not find requirements-dev.txt, regenerating requirements"
    UPDATE_REQS="true"
fi

if [ "$UPDATE_REQS" ]; then
    # if UPDATE_REQS is present, regenerate requirements using pip-compile (pip-tools)
    echo Running pip-compile on requirements.in and requirements-dev.in
    python${PY_VERSION} -m pip install pip-tools
    pip-compile --output-file=requirements-dev.txt --resolver=backtracking requirements-dev.in
    pip-compile --output-file=requirements.txt --resolver=backtracking requirements.in
fi 


python${PY_VERSION} -m pip install -r requirements-dev.txt  -i https://repomanager.tools.hcs.cloud/repository/pypi-group/simple

set +e