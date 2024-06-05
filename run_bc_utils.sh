# Load environment variables from .env file
set -a # Automatically export all variables
source $BCU_REPO_DIR/container.env
set +a

. "$BCU_REPO_DIR/bcutils_env/bin/activate" && \
  cd "$BCU_REPO_DIR/bcutils" && \
  echo "BCU_USERNAME=$BCU_USERNAME" && \
  python bc_utils.py #2>&1 | tee -a ./bc_utils.log


