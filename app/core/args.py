import os

def validate_encrypt_inputs(src, pw, pw2=None):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_enc_file"))
    if not pw:
        errs.append(("warning", "msg_enter_enc_pw"))
    elif pw2 is not None and pw != pw2:
        errs.append(("warning", "msg_pw_mismatch"))
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_src_not_exist"))
    return errs

def validate_decrypt_inputs(src, pw):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_ptd"))
    if not pw:
        errs.append(("warning", "msg_enter_dec_pw"))
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_file_not_exist"))
    if src and os.path.isfile(src) and not src.lower().endswith(".ptd"):
        errs.append(("warning", "msg_not_ptd"))
    return errs

def validate_batch_encrypt_inputs(src, pw, pw2=None):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_src_dir"))
    if not pw:
        errs.append(("warning", "msg_enter_enc_pw"))
    elif pw2 is not None and pw != pw2:
        errs.append(("warning", "msg_pw_mismatch"))
    if src and not os.path.isdir(src):
        errs.append(("error", "msg_src_dir_not_exist"))
    return errs

def validate_batch_decrypt_inputs(src, pw):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_src_dir"))
    if not pw:
        errs.append(("warning", "msg_enter_dec_pw"))
    if src and not os.path.isdir(src):
        errs.append(("error", "msg_src_dir_not_exist"))
    return errs

def ensure_output_dir(out):
    if not out:
        return None
    if not os.path.isdir(out):
        try:
            os.makedirs(out, exist_ok=True)
        except Exception:
            return ("error", "msg_cannot_create_dir")
    return None

def build_encrypt_args(src, out="", algo="", delete=False, recycle=False, zstd=False, compression_level=None):
    args = ["-e", src]
    if out:
        args += ["-o", out]
    if algo.startswith("AEGIS"):
        args += ["-m", "aegis256"]
    elif algo.startswith("XChaCha"):
        args += ["-m", "xchacha20"]
    if zstd:
        args.append("-zstd")
        if compression_level is not None:
            args += ["--compression-level", str(compression_level)]
    if recycle:
        args.append("--recycle-source")
    elif delete:
        args.append("-de")
    args.append("-y")
    return args

def build_decrypt_args(src, out=""):
    args = ["-d", src]
    if out:
        args += ["-o", out]
    args.append("-y")
    return args

def build_batch_encrypt_args(src, out="", algo="", delete=False, recycle=False, zstd=False, compression_level=None):
    args = ["-be", "-i", src]
    if out:
        args += ["-o", out]
    if algo.startswith("AEGIS"):
        args += ["-m", "aegis256"]
    if zstd:
        args.append("-zstd")
        if compression_level is not None:
            args += ["--compression-level", str(compression_level)]
    if recycle:
        args.append("--recycle-source")
    elif delete:
        args.append("-de")
    args.append("-y")
    return args

def build_batch_decrypt_args(src, out=""):
    args = ["-bd", "-i", src]
    if out:
        args += ["-o", out]
    # 2.x 批量解密默认不还原原名，-rn 开启还原（与 1.x 行为一致）
    args += ["-rn", "-y"]
    return args