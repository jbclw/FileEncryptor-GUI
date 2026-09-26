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

def validate_encrypt_inputs(src, pw, pw2=None, keyfile="", recipient=""):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_enc_file"))
    if recipient:
        # 非对称（rage）：不需要密码，改校验收件人公钥
        if not (recipient.startswith("age1") or os.path.isfile(recipient)):
            errs.append(("error", "msg_recipient_invalid"))
    else:
        errs += _key_or_password_errors(pw, pw2, keyfile, "msg_enter_enc_pw")
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_src_not_exist"))
    return errs

def validate_decrypt_inputs(src, pw, keyfile="", rage=False):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_ptd"))
    if rage:
        # rage 解密只能靠私钥文件（-k），密码不适用
        if not keyfile:
            errs.append(("error", "msg_need_privkey"))
        elif not os.path.isfile(keyfile):
            errs.append(("error", "msg_keyfile_not_exist"))
    else:
        errs += _key_or_password_errors(pw, None, keyfile, "msg_enter_dec_pw")
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_file_not_exist"))
    if src and os.path.isfile(src):
        ok_ext = ".age" if rage else ".ptd"
        if not src.lower().endswith(ok_ext):
            errs.append(("warning", "msg_not_age" if rage else "msg_not_ptd"))
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

def validate_rewrap_inputs(src, old_pw, new_pw, new_pw2=None, old_keyfile=""):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_container"))
    elif not os.path.isfile(src):
        errs.append(("error", "msg_file_not_exist"))
    elif not src.lower().endswith(".ptd"):
        errs.append(("warning", "msg_not_ptd"))
    if old_keyfile:
        if not os.path.isfile(old_keyfile):
            errs.append(("error", "msg_keyfile_not_exist"))
    elif not old_pw:
        errs.append(("warning", "msg_enter_old_pw"))
    if not new_pw:
        errs.append(("warning", "msg_enter_new_pw"))
    elif new_pw2 is not None and new_pw != new_pw2:
        errs.append(("warning", "msg_new_pw_mismatch"))
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
                       compression_level=None, keyfile="", sha256=False, recipient=""):
    """单文件加密参数。

    recipient 非空 -> 非对称（rage）模式：-m rage -r <公钥|公钥文件>。
    该模式下不使用算法/zstd/密钥文件/--sha256（引擎会忽略，故不传）。
    """
    args = ["-e", src]
    if out:
        args += ["-o", out]
    if recipient:
        args += ["-m", "rage", "-r", recipient]
    else:
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
        if sha256:
            args.append("--sha256")
    if recycle:
        args.append("--recycle-source")
    elif delete:
        args.append("-de")
    args.append("-y")
    return args

def build_decrypt_args(src, out="", keyfile="", rage=False):
    args = ["-d", src]
    if out:
        args += ["-o", out]
    if rage:
        args += ["-m", "rage"]
    if keyfile:
        args += ["-k", keyfile]
    args.append("-y")
    return args

def build_batch_encrypt_args(src, out="", algo="", delete=False, recycle=False, zstd=False,
                             compression_level=None, keyfile="", sha256=False):
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
    if sha256:
        args.append("--sha256")
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

def build_rewrap_args(src, new_keyfile, old_keyfile=""):
    """密钥轮换：旧密码经 -k 或交互输入，新密码必须来自文件（--new-key-file）。"""
    args = ["--rewrap", src]
    if old_keyfile:
        args += ["-k", old_keyfile]
    args += ["--new-key-file", new_keyfile, "-y"]
    return args

def build_keygen_args(out_dir=""):
    """生成 X25519 密钥对：公钥打印到 stdout，私钥写入 <out_dir>/rage_private.txt"""
    args = ["-g"]
    if out_dir:
        args += ["-o", out_dir]
    return args