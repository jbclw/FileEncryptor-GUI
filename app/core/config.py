import os
import configparser

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))

class ConfigManager:
    def __init__(self, config_file=None):
        self.config_file = config_file or os.path.join(_CONFIG_DIR, "config.ini")
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding='utf-8')
            except Exception as e:
                print(f"加载配置失败: {e}")

    def _save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def get(self, section, key, default=None):
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def getint(self, section, key, default=0):
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def getboolean(self, section, key, default=False):
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def set(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))

    def save(self):
        self._save_config()

_config = None

def get_config():
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config