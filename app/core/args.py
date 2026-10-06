import os
import re

# 非对称收件人公钥：经典 X25519（age1…）、PQC 混合（MLKEM1-…）、X448-…，或公钥文件路径
_RECIPIENT_PREFIXES = ("age1", "MLKEM1-", "X448-")

# 算法显示名 -> CLI 取值（CLI 3.0.0：xchacha20 | aegis256 | aes-gcm | sm4 | x25519 | x448）
ALGO_LABELS = ("XChaCha20-Poly1305", "AEGIS-256", "AES-256-GCM", "SM4-GCM")
_ALGO_CLI = dict(zip(ALGO_LABELS, ("xchacha20", "aegis256", "aes-gcm", "sm4")))

# 分卷尺寸：数值 + 可选单位（引擎侧下限 1MB，越界由引擎报错）
_SPLIT_RE = re.compile(r"^\d+(?:\.\d+)?\s*(?:B|K|KB|M|MB|G|GB|T|TB)?$", re.IGNORECASE)


def _is_recipient_ok(recipient):
    return recipient.startswith(_RECIPIENT_PREFIXES) or os.path.isfile(recipient)

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

def validate_split_size(size):
    """分卷尺寸：留空 = 不分卷"""
    if not size:
        return []
    if not _SPLIT_RE.match(size.strip()):
        return [("error", "msg_split_invalid")]
    return []

def validate_encrypt_inputs(src, pw, pw2=None, keyfile="", recipient="", pack=False, split=""):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_pack_dir" if pack else "msg_select_enc_file"))
    if recipient:
        # 非对称（-m x25519）：不需要密码，改校验收件人公钥
        if not _is_recipient_ok(recipient):
            errs.append(("error", "msg_recipient_invalid"))
    else:
        errs += _key_or_password_errors(pw, pw2, keyfile, "msg_enter_enc_pw")
    if src:
        if pack:
            # 打包（-p）输入为目录树
            if not os.path.isdir(src):
                errs.append(("error", "msg_src_dir_not_exist"))
        elif not os.path.isfile(src):
            errs.append(("error", "msg_src_not_exist"))
    errs += validate_split_size(split)
    return errs

def validate_decrypt_inputs(src, pw, keyfile="", asym=False):
    errs = []
    if not src:
        errs.append(("warning", "msg_select_ptd"))
    if asym:
        # 非对称解密：必须给身份私钥；引擎按密钥材料自动识别，不传 -m
        if not keyfile:
            errs.append(("error", "msg_need_privkey"))
        elif not os.path.isfile(keyfile):
            errs.append(("error", "msg_keyfile_not_exist"))
    else:
        errs += _key_or_password_errors(pw, None, keyfile, "msg_enter_dec_pw")
    if src and not os.path.isfile(src):
        errs.append(("error", "msg_file_not_exist"))
    elif src and not src.lower().endswith(".ptd"):
        # 非对称产物自 CLI 3.0.0 起同样是 .ptd 容器（分卷为 .001.ptd）
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

def validate_wrap_inputs(dek_file, out_path="", pubkey="", keyfile="", pw=""):
    """密钥封装：待封装密钥文件必填；公钥封装时校验公钥，否则密码/密钥文件二选一"""
    errs = []
    if not dek_file:
        errs.append(("warning", "msg_select_wrap_src"))
    elif not os.path.isfile(dek_file):
        errs.append(("error", "msg_file_not_exist"))
    if pubkey:
        if not _is_recipient_ok(pubkey):
            errs.append(("error", "msg_recipient_invalid"))
    else:
        errs += _key_or_password_errors(pw, None, keyfile, "msg_enter_dec_pw")
    if out_path:
        parent = os.path.dirname(os.path.abspath(out_path))
        if parent and not os.path.isdir(parent):
            errs.append(("error", "msg_cannot_create_dir"))
    return errs

def validate_unwrap_inputs(blob, out_path="", identity="", keyfile="", pw=""):
    """密钥解封：.fekw 必填；身份私钥封装时给 --identity，否则密码/密钥文件二选一"""
    errs = []
    if not blob:
        errs.append(("warning", "msg_select_unwrap_src"))
    elif not os.path.isfile(blob):
        errs.append(("error", "msg_file_not_exist"))
    if identity:
        if not os.path.isfile(identity):
            errs.append(("error", "msg_keyfile_not_exist"))
    else:
        errs += _key_or_password_errors(pw, None, keyfile, "msg_enter_dec_pw")
    if out_path:
        parent = os.path.dirname(os.path.abspath(out_path))
        if parent and not os.path.isdir(parent):
            errs.append(("error", "msg_cannot_create_dir"))
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
                       compression_level=None, keyfile="", sha256=False, recipient="",
                       pack=False, split="", watermark=False, wm_key=""):
    """单文件加密参数。

    非对称：-m x25519 -r <公钥|公钥文件>（CLI 3.0.0 已移除 -m rage 别名，
    产物为 .ptd 容器）。该模式支持 zstd，但引擎忽略 --sha256，故不传；
    与 --pack 互斥（引擎对二者组合直接报错）。
    分卷：-s <尺寸>（产物 .001.ptd / .002.ptd …）。
    """
    args = ["-e", src]
    if pack:
        args.append("-p")
    if out:
        args += ["-o", out]
    if recipient:
        args += ["-m", "x25519", "-r", recipient]
    else:
        cli = _ALGO_CLI.get(algo)
        if cli:
            args += ["-m", cli]
        if sha256:
            args.append("--sha256")
        if keyfile:
            args += ["-k", keyfile]
    if zstd:
        args.append("-zstd")
        if compression_level is not None:
            args += ["--compression-level", str(compression_level)]
    if watermark:
        args.append("--watermark")
        if wm_key:
            args += ["--wm-sign", wm_key]
    if split:
        args += ["-s", split]
    if recycle:
        args.append("--recycle-source")
    elif delete:
        args.append("-de")
    if delete or recycle:
        # 目录输入时引擎会二次确认；界面已由用户显式勾选，代为确认
        args.append("--source-delete-ok")
    args.append("-y")
    return args

def build_decrypt_args(src, out="", keyfile="", preview=False, max_bytes=None,
                       no_extract=False, force_decrypt=False):
    """解密参数。非对称容器不必传 -m，引擎按 -k 的密钥材料自动识别。"""
    args = ["-d", src]
    if out and not preview:
        args += ["-o", out]
    if keyfile:
        args += ["-k", keyfile]
    if preview:
        args.append("--preview")
        if max_bytes:
            args += ["--max-bytes", str(max_bytes)]
    if no_extract:
        args.append("--no-extract")
    if force_decrypt:
        args.append("--force-decrypt")
    args.append("-y")
    return args

def build_batch_encrypt_args(src, out="", algo="", delete=False, recycle=False, zstd=False,
                             compression_level=None, keyfile="", sha256=False):
    args = ["-be", "-i", src]
    if out:
        args += ["-o", out]
    cli = _ALGO_CLI.get(algo)
    if cli:
        args += ["-m", cli]
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
    if delete or recycle:
        # 批量输入必为目录，引擎会二次确认；勾选即为用户确认
        args.append("--source-delete-ok")
    args.append("-y")
    return args

def build_batch_decrypt_args(src, out="", keyfile=""):
    args = ["-bd", "-i", src]
    if out:
        args += ["-o", out]
    if keyfile:
        args += ["-k", keyfile]
    # 批量解密默认不还原原名，-rn 开启还原（与 1.x 行为一致）
    args += ["-rn", "-y"]
    return args

def build_rewrap_args(src, new_keyfile, old_keyfile=""):
    """密钥轮换：旧密码经 -k 或交互输入，新密码必须来自文件（--new-key-file）。"""
    args = ["--rewrap", src]
    if old_keyfile:
        args += ["-k", old_keyfile]
    args += ["--new-key-file", new_keyfile, "-y"]
    return args

def build_keygen_args(out_dir="", x448=False, no_pqc=False):
    """生成密钥对：公钥打印到 stdout 并写入 <out_dir>/rage_public.txt，
    私钥写入 <out_dir>/rage_private.txt。默认 X25519 + ML-KEM-768 混合（PQC）。"""
    args = ["-g"]
    if x448:
        args.append("-x448")
    if no_pqc:
        args.append("--no-pqc")
    if out_dir:
        args += ["-o", out_dir]
    return args

def build_wm_keygen_args(priv_pem):
    """生成水印签名密钥：私钥写入 priv_pem，公钥打印到 stdout"""
    return ["--wm-keygen", priv_pem]

def build_watermark_extract_args(src, pubkey=""):
    """查看（并可选验签）密文尾部水印，不需密码"""
    args = ["--watermark-extract", src]
    if pubkey:
        args += ["--wm-verify", pubkey]
    return args

def build_wrap_args(dek_file, out_path="", alg="", to_pub="", keyfile=""):
    """把 32 字节数据密钥（DEK）封装成 .fekw"""
    args = ["--wrap-key", dek_file]
    if alg:
        args += ["--wrap-alg", alg]
    if to_pub:
        args += ["--wrap-to", to_pub]
    elif keyfile:
        args += ["-k", keyfile]
    if out_path:
        args += ["--wrap-out", out_path]
    return args

def build_unwrap_args(blob, out_path="", identity="", keyfile=""):
    """把 .fekw 解回 DEK"""
    args = ["--unwrap-key", blob]
    if identity:
        args += ["--identity", identity]
    elif keyfile:
        args += ["-k", keyfile]
    if out_path:
        args += ["--unwrap-out", out_path]
    return args
