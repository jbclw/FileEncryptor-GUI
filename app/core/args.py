import os

def _key_or_password_errors(pw, pw2, keyfile, missing_pw_key):
    """密钥文件与密码二选一（对应 CLI 的 -k / 交互输入）。

    指定密钥文件时校验其存在、不再要求密码；否则按原逻辑校验密码与确认密码。
    """
    if keyfile:
        if not os.path.isfile(keyfile):
            return [("error", "msg_keyfile_not_exist")]
        return []
    if not pw:
        return [("warning", missing_pw_key)]
    if pw2 is not None and pw != pw2:
        return [("warning", "msg_pw_mismatch")]
    return []

def validate_encrypt_inputs(src, pw, pw2=None, keyfile=""):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_enc_file"))
    errs += _key_or_password_errors(pw, pw2, keyfile, "msg_enter_enc_pw")
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_src_not_exist"))
    return errs

def validate_decrypt_inputs(src, pw, keyfile=""):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_ptd"))
    errs += _key_or_password_errors(pw, None, keyfile, "msg_enter_dec_pw")
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_file_not_exist"))
    if src and os.path.isfile(src) and not src.lower().endswith(".ptd"):
        errs.append(("warning", "msg_not_ptd"))
    return errs

def validate_batch_encrypt_inputs(src, pw, pw2=None, keyfile=""):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_src_dir"))
    errs += _key_or_password_errors(pw, pw2, keyfile, "msg_enter_enc_pw")
    if src and not os.path.isdir(src):
        errs.append(("error", "msg_src_dir_not_exist"))
    return errs

def validate_batch_decrypt_inputs(src, pw, keyfile=""):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_src_dir"))
    errs += _key_or_password_errors(pw, None, keyfile, "msg_enter_dec_pw")
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

def build_encrypt_args(src, out="", algo="", delete=False, recycle=False, zstd=False,
                       compression_level=None, keyfile=""):
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
    if keyfile:
        args += ["-k", keyfile]
    if recycle:
        args.append("--recycle-source")
    elif delete:
        args.append("-de")
    args.append("-y")
    return args

def build_decrypt_args(src, out="", keyfile=""):
    args = ["-d", src]
    if out:
        args += ["-o", out]
    if keyfile:
        args += ["-k", keyfile]
    args.append("-y")
    return args

def build_batch_encrypt_args(src, out="", algo="", delete=False, recycle=False, zstd=False,
                             compression_level=None, keyfile=""):
    args = ["-be", "-i", src]
    if out:
        args += ["-o", out]
    if algo.startswith("AEGIS"):
        args += ["-m", "aegis256"]
    if zstd:
        args.append("-zstd")
        if compression_level is not None:
            args += ["--compression-level", str(compression_level)]
    if keyfile:
        args += ["-k", keyfile]
    if recycle:
        args.append("--recycle-source")
    elif delete:
        args.append("-de")
    args.append("-y")
    return args

def build_batch_decrypt_args(src, out="", keyfile=""):
    args = ["-bd", "-i", src]
    if out:
        args += ["-o", out]
    if keyfile:
        args += ["-k", keyfile]
    # 2.x 批量解密默认不还原原名，-rn 开启还原（与 1.x 行为一致）
    args += ["-rn", "-y"]
    return args