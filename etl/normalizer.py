import re
import logging

class EntityNormalizer:
    def __init__(self, config_pat:str = None):
        # TODO 实际开发中，建议把这个map移到json/yaml配置文件中
        self.alias_map = {
            "apple": "AAPL",
            "apple inc": "AAPL",
            "iphone maker": "AAPL",
            "tsmc": "TSM",
            "taiwan semiconductor": "TSM",
            "nvda": "NVDA",
            "nvidia": "NVDA",
            "nvidia corp": "NVDA"
        }
        # 常见的法律后缀，可以统一剔除
        self.legal_suffixes = re.compile(r"\b(inc|corp|corporation|ltd|plc|co)\b\.?", re.I)

    def _clean(self, name:str) -> str:
        if not name:
            return ""
        s = name.strip().lower()
        s = s.replace(",", "")
        s = self.legal_suffixes.sub("", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def normalize(self, name:str) -> str | None:
        if not name:
            return None
        clean_name = self._clean(name)

        # 优先走手动配置的映射
        if clean_name in self.alias_map:
            return self.alias_map[clean_name]
        
        if name.upper() in self.alias_map.values():
            return name.upper()
        
        # 兜底
        logging.debug(f"Entity not normalized:{name} -> (cleaned: {clean_name})")
        return None
