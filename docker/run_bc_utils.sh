# Environment variables should be set externally (via container, systemd, etc.)
# No need to source env files - application reads from environment directly

. "$BCU_REPO_DIR/bcutils_env/bin/activate" && \
  cd "$BCU_REPO_DIR/bcutils" && \
  echo "Starting bc_utils with BCU_USERNAME=${BCU_USERNAME:-<not_set>}" && \
  python bc_utils.py #2>&1 | tee -a ./bc_utils.log


