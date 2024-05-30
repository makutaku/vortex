. "$BCU_REPO_DIR/bcutils_env/bin/activate" && \
  cd "$BCU_REPO_DIR/bcutils" && \
  python bc_utils.py #2>&1 | tee -a ./bc_utils.log


