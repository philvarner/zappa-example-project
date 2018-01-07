#!/usr/bin/env sh
export PYENV_DIR="$HOME/.pyenv"

# ensure pyenv is installed
if [ -d ~/.pyenv ]
then
    echo "pyenv is already installed."
else
    echo "pyenv is not installed - installing..."
    git clone https://github.com/pyenv/pyenv.git "$PYENV_DIR"
    echo "done"
fi

# initialize pyenv shims
export PATH="$PYENV_DIR/bin:$PATH"
eval "$(pyenv init -)"

# ensure python 3.6.2 is installed
pyenv install -s 3.6.2

# initialize project virtualenv
export VENV_BIN_DIR="$PYENV_DIR/versions/3.6.2/bin"
export PATH="$VENV_BIN_DIR:$PATH"

pip install pipenv
pipenv install --dev

# invoke doesn't inherit the venv set by 'pipenv run', only when it's run from within 'pipenv shell'
# 'pipenv shell' doesn't work on Jenkins, failing with 'termios.error: (25, 'Inappropriate ioctl for device')'
# so, the solution is to use venv to explicitly enter the environment

export VENV_HOME_DIR=$(pipenv --venv)
source ${VENV_HOME_DIR}/bin/activate
